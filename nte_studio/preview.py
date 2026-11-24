"""Small streaming, sample-free synthesizer for auditioning selected MIDI parts."""
from array import array
from bisect import bisect_left
import math
import sys

from .model import SheetError

WAVE = tuple(math.sin(2 * math.pi * i / 2048) + .18 * math.sin(4 * math.pi * i / 2048)
             for i in range(2048))


class PreviewSynth:
    """Render bounded PCM chunks. Unselected parts never enter the mixer."""

    def __init__(self, song, selected_keys, speed=1.0, sample_rate=44100):
        if not .25 <= speed <= 4:
            raise SheetError('Preview speed must be between 0.25 and 4.')
        self.sample_rate = sample_rate
        self.total_frames = math.ceil(song.duration / speed * sample_rate)
        self.voices = sorted(
            (round(n.start / speed * sample_rate), round(n.end / speed * sample_rate),
             n.pitch, n.velocity, part.key)
            for part in song.parts if not part.percussion for n in part.notes
        )
        self.starts = [v[0] for v in self.voices]
        self.frame = 0
        self.selected_keys = frozenset(selected_keys)
        self.active = []
        self.index = 0

    @property
    def duration(self):
        return self.total_frames / self.sample_rate

    def seek(self, seconds):
        self.frame = max(0, min(self.total_frames, round(seconds * self.sample_rate)))
        self.index = bisect_left(self.starts, self.frame)
        self.active = [v for v in self.voices[:self.index]
                       if v[1] > self.frame and v[4] in self.selected_keys]

    def select(self, keys):
        self.selected_keys = frozenset(keys)
        self.seek(self.frame / self.sample_rate)

    def render(self, frames, channels=1, floating=False):
        start, end = self.frame, min(self.total_frames, self.frame + max(0, frames))
        if end <= start:
            return b''
        while self.index < len(self.voices) and self.voices[self.index][0] < end:
            voice = self.voices[self.index]
            if voice[4] in self.selected_keys:
                self.active.append(voice)
            self.index += 1
        mix = [0.0] * (end - start)
        attack, release = max(1, round(self.sample_rate * .006)), max(1, round(self.sample_rate * .012))
        for on, off, pitch, velocity, _ in self.active:
            left, right = max(on, start), min(off, end)
            if left >= right:
                continue
            increment = 440 * 2 ** ((pitch - 69) / 12) * 2048 / self.sample_rate
            phase = (left - on) * increment
            amplitude = .12 * velocity / 127
            for frame in range(left, right):
                envelope = min(1.0, (frame - on) / attack, (off - frame) / release)
                mix[frame - start] += WAVE[int(phase) & 2047] * amplitude * envelope
                phase += increment
        self.active = [v for v in self.active if v[1] > end]
        self.frame = end
        # Smooth saturation protects dense chords from hard clipping.
        samples = array('f' if floating else 'h')
        for value in mix:
            value = value / (1 + abs(value))
            sample = value if floating else round(value * 32767)
            samples.extend([sample] * channels)
        if sys.byteorder != 'little':
            samples.byteswap()
        return samples.tobytes()
