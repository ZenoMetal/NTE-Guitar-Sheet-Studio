"""Qt audio output for the streaming MIDI preview; no external player required."""
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
try:
    from PySide6.QtMultimedia import QtAudio
except ImportError:  # Older supported PySide6 releases used the QAudio namespace.
    from PySide6.QtMultimedia import QAudio as QtAudio

from .model import SheetError
from .preview import PreviewSynth


class MidiPlayer(QObject):
    changed = Signal()
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.song, self.synth, self.sink, self.output = None, None, None, None
        self.selected_keys, self.speed = set(), 1.0
        self.state, self.base_position, self.volume = 'stopped', 0.0, .7
        self.pending = b''
        self.timer = QTimer(self)
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.pump)

    @property
    def duration(self):
        return self.song.duration / self.speed if self.song else 0

    @property
    def position(self):
        elapsed = self.sink.processedUSecs() / 1_000_000 if self.sink else 0
        return min(self.duration, self.base_position + elapsed)

    def load(self, song, selected_keys, speed):
        self.stop()
        self.song, self.selected_keys, self.speed = song, set(selected_keys), speed
        self.changed.emit()

    def release_audio(self):
        self.timer.stop()
        if self.sink:
            self.sink.reset()
            self.sink.deleteLater()
        self.sink = self.output = self.synth = None
        self.pending = b''

    def stop(self):
        self.release_audio()
        self.state, self.base_position = 'stopped', 0.0
        self.changed.emit()

    def pause(self):
        if self.state == 'playing':
            position = self.position
            self.release_audio()
            self.state, self.base_position = 'paused', position
            self.changed.emit()

    def select(self, selected_keys):
        self.selected_keys = set(selected_keys)
        if not self.selected_keys:
            self.pause()
        elif self.state == 'playing':
            # Flush buffered samples too, so a muted part cannot linger.
            self.seek(self.position)
        self.changed.emit()

    def set_speed(self, speed):
        source_position = self.position * self.speed
        playing = self.state == 'playing'
        self.release_audio()
        self.speed = speed
        self.base_position = min(self.duration, source_position / speed)
        self.state = 'paused' if self.base_position else 'stopped'
        if playing:
            self.play()
        self.changed.emit()

    def set_volume(self, value):
        self.volume = value
        if self.sink:
            self.sink.setVolume(value)

    def seek(self, seconds):
        playing = self.state == 'playing'
        self.release_audio()
        self.base_position = max(0, min(self.duration, seconds))
        self.state = 'paused'
        if playing and self.base_position < self.duration:
            self.play()
        self.changed.emit()

    def play(self):
        if not self.song or not self.selected_keys or self.state == 'playing':
            return
        try:
            device = QMediaDevices.defaultAudioOutput()
            if device.isNull():
                raise SheetError('No audio output device is available. Connect speakers or headphones and try again.')
            preferred = device.preferredFormat()
            fmt = (preferred if preferred.sampleFormat() in
                   (QAudioFormat.SampleFormat.Int16, QAudioFormat.SampleFormat.Float) else None)
            for channels in dict.fromkeys((1, device.preferredFormat().channelCount())):
                if fmt:
                    break
                for rate in (44100, 48000, 22050):
                    for sample_format in (QAudioFormat.SampleFormat.Int16, QAudioFormat.SampleFormat.Float):
                        candidate = QAudioFormat()
                        candidate.setSampleRate(rate)
                        candidate.setChannelCount(channels)
                        candidate.setSampleFormat(sample_format)
                        if device.isFormatSupported(candidate):
                            fmt = candidate
                            break
                    if fmt:
                        break
                if fmt:
                    break
            if fmt is None:
                raise SheetError('This audio device does not support a compatible preview format.')
            if self.base_position >= self.duration:
                self.base_position = 0
            self.synth = PreviewSynth(self.song, self.selected_keys, self.speed, fmt.sampleRate())
            self.synth.seek(self.base_position)
            self.format = fmt
            self.sink = QAudioSink(device, fmt, self)
            self.sink.setBufferSize(fmt.bytesForDuration(80_000))
            self.sink.setVolume(self.volume)
            self.output = self.sink.start()
            if self.output is None or self.sink.error() not in (QtAudio.Error.NoError, QtAudio.Error.UnderrunError):
                raise SheetError(f'Could not open the audio output device ({self.sink.error().name}). '
                                 'Check your system audio settings.')
            self.state = 'playing'
            self.pump()
            if self.sink:
                self.timer.start()
            self.changed.emit()
        except Exception as exc:
            self.release_audio()
            self.state = 'paused'
            self.failed.emit(str(exc))
            self.changed.emit()

    def pump(self):
        if not self.sink or self.state != 'playing':
            return
        if self.sink.error() not in (QtAudio.Error.NoError, QtAudio.Error.UnderrunError):
            self.pause()
            self.failed.emit('Audio playback stopped. Check your output device and try again.')
            return
        available = self.sink.bytesFree()
        if not self.pending:
            frames = min(2048, available // self.format.bytesPerFrame())
            if frames:
                self.pending = self.synth.render(frames, self.format.channelCount(),
                                                 self.format.sampleFormat() == QAudioFormat.SampleFormat.Float)
        if self.pending and available:
            written = self.output.write(self.pending[:available])
            if written < 0:
                self.pause()
                self.failed.emit('Could not send preview audio to the output device.')
                return
            self.pending = self.pending[written:]
        if (not self.pending and self.synth.frame >= self.synth.total_frames
                and self.sink.state() == QtAudio.State.IdleState):
            self.release_audio()
            self.state, self.base_position = 'stopped', self.duration
        self.changed.emit()
