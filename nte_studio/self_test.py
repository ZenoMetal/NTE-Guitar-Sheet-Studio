"""Offline packaging smoke test. Never writes into the NTE game cache."""
import json
from pathlib import Path
import tempfile

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from .convert import convert
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
        assert window.tabs.count() == 2
        window.close()
        print(json.dumps({'status': 'passed', 'qt_window': 'rendered', 'tabs': 2,
                          'text_to_json': 'passed', 'temporary_install': 'verified',
                          'real_game_cache_modified': False}))
    return 0
