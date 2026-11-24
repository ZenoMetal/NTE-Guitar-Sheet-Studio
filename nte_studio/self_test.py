"""Offline packaging smoke test. Never writes into the NTE game cache."""
import json
from pathlib import Path
import tempfile

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from .convert import convert
from .model import MidiSong, Note, Part
from .preview import PreviewSynth
from .storage import install_sheet
from .text_sheet import PRESETS, parse_text
from .ui import StudioWindow, set_dark_palette


def run():
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    set_dark_palette(app)
    with tempfile.TemporaryDirectory(prefix='nte-studio-selftest-') as tmp:
        root = Path(tmp)
        settings = QSettings(str(root / 'settings.ini'), QSettings.Format.IniFormat)
        window = StudioWindow(settings)
        window.show()
        app.processEvents()
        notes, duration = parse_text('[tuo] - (tyu)', PRESETS['Virtual Piano / Roblox (C2–C7)'])
        doc, report = convert(notes, source_duration=duration)
        result = install_sheet(doc, report, 'Self test', root / 'GuitarNotes', root / 'exports')
        window.conversion_finished(result)
        window.tabs.setCurrentIndex(1)
        app.processEvents()
        assert not window.grab().isNull(), 'The Qt window did not render.'
        assert Path(result['target']).read_bytes() == Path(result['backup']).read_bytes()
        assert window.code.text() == doc['noteId']
        assert window.tabs.count() == 3
        song = MidiSong([Part('lead', 'Lead', 0, 0, [Note(0, 1, 69)]),
                         Part('bass', 'Bass', 1, 32, [Note(0, 1, 45)])], 1, [(0, 120)])
        window.song = song
        window.populate_tracks(song)
        window.player.load(song, window.selected_part_keys(), 1)
        window.track_table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
        assert window.player.selected_keys == {'lead'}, 'USE selection did not reach the audio player.'
        actual = PreviewSynth(song, window.player.selected_keys, sample_rate=8000).render(4000)
        reference = PreviewSynth(MidiSong(song.parts[:1], 1, [(0, 120)]), {'lead'}, sample_rate=8000).render(4000)
        assert actual == reference and any(actual), 'Unchecked part leaked into preview audio.'
        window.select_parts(False)
        assert not window.play_button.isEnabled()
        window.text_input.setPlainText('[tuo] - (tyu) [tuo]')
        steps = window.steps.currentData()
        window.length_minutes.setValue(0)
        window.length_seconds.setValue(1.037)
        window.fit_length.setChecked(True)
        window.update_text_timing()
        assert window.steps.currentData() == steps
        assert not window.bpm.isEnabled()
        _, duration = parse_text(window.text_input.toPlainText(), window.current_mapping(),
                                 steps_per_beat=steps, target_duration=window.target_text_duration())
        assert abs(duration - 1.037) < 1e-9
        window.fit_length.setChecked(False)
        assert window.bpm.isEnabled()
        for language in ('en', 'de', 'es', 'fr', 'ja', 'zh'):
            window.apply_settings(language, 'light', str(root / 'GuitarNotes'), str(root))
            assert window.language == language
        window.apply_settings('en', 'dark', str(root / 'GuitarNotes'), str(root))
        assert window.track_table.minimumHeight() == 510
        window.tone.setChecked(True)
        assert window.tone.currentText() == 'Distortion'
        window.tone.setChecked(False)
        assert window.tone.currentText() == 'Clean'
        window.close()
        print(json.dumps({'status': 'passed', 'qt_window': 'rendered', 'tabs': 3,
                          'text_to_json': 'passed', 'temporary_install': 'verified',
                          'selected_track_audio': 'passed', 'target_length_and_fixed_steps': 'passed',
                          'real_game_cache_modified': False}))
    return 0
