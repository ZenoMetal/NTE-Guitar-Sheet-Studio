"""Read-only MIDI library and local sheet collection, with legacy title lookup."""
from dataclasses import dataclass
import json
import os
from pathlib import Path

from .storage import data_directory


def export_roots(home=None):
    home = Path(home) if home else Path.home()
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local'))
        names = ('NTE Guitar Sheet Studio', 'NTE Local Music Sheet Creator', 'NTE Sheet Studio')
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
        names = ('nte-guitar-sheet-studio', 'nte-local-music-sheet-creator', 'nte-sheet-studio')
    return [data_directory() / 'exports', *(base / name / 'exports' for name in names)]


def midi_files(folder):
    root = Path(folder).expanduser()
    if not folder or not root.is_dir():
        return []
    return sorted((p for p in root.iterdir() if p.is_file() and p.suffix.lower() in ('.mid', '.midi')),
                  key=lambda p: p.name.casefold())


@dataclass
class SheetEntry:
    path: Path
    code: str
    title: str
    duration: float
    tone: str
    modified: float


def read_collection(folder, roots=None):
    """Never add metadata to game JSON. Recover titles from export sidecars."""
    if not folder or not Path(folder).is_dir():
        return [], []
    files = list(Path(folder).glob('guitar_note_*.json'))
    wanted = {file.stem.removeprefix('guitar_note_').upper() for file in files}
    titles = {}
    for root in (export_roots() if roots is None else roots):
        root = Path(root)
        if not root.is_dir():
            continue
        for file in root.glob('*/conversion.json'):
            if file.parent.name[-32:].upper() not in wanted:
                continue
            try:
                if file.stat().st_size > 4 * 1024 * 1024:
                    continue
                record = json.loads(file.read_text(encoding='utf-8'))
                key = record.get('local_note_id') or record.get('noteId')
                if key and record.get('title'):
                    titles.setdefault(str(key).upper(), str(record['title']))
            except (OSError, ValueError, TypeError, AttributeError):
                continue
    entries, warnings = [], []
    for file in files:
        try:
            stat = file.stat()
            if stat.st_size > 32 * 1024 * 1024:
                raise ValueError('File exceeds 32 MB')
            record = json.loads(file.read_text(encoding='utf-8-sig'))
            code = str(record.get('noteId') or file.stem.removeprefix('guitar_note_')).upper()
            title = titles.get(code) or next((str(record[k]) for k in ('title', 'name', 'songName', 'sheetName')
                                              if record.get(k)), '')
            # Some imported recordings have no title stored anywhere. Keep their ID visible.
            tone = next((op.get('audioType', 'Clean') for op in record.get('operations', [])
                         if isinstance(op, dict) and op.get('type') == 'AudioType'), 'Clean')
            duration = float(record.get('durationMs', 0)) / 1000
            entries.append(SheetEntry(file, code, title, duration, tone, stat.st_mtime))
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            warnings.append(f'{file.name}: {exc}')
    entries.sort(key=lambda item: (-item.modified, item.title.casefold(), item.code))
    return entries, warnings
