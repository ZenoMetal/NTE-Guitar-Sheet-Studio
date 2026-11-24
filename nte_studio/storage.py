"""Find NTE caches on Windows/Proton and install new sheets without overwrites."""
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .convert import validate
from .model import SheetError


def data_directory():
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'NTE Guitar Sheet Studio'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'nte-guitar-sheet-studio'


def detect_destinations(home=None, environ=None, platform=None):
    home = Path(home) if home else Path.home()
    env = os.environ if environ is None else environ
    platform = os.name if platform is None else platform
    candidates = []

    def add(base, label, allow_new=False):
        for name, suffix in [('Saved_GlobalSteam', 'Steam'), ('Saved_Global', 'Standalone')]:
            folder = base / name / 'GuitarNotes'
            if folder.is_dir() or (allow_new and (base / name).is_dir()):
                candidates.append((f'{label} · {suffix}', folder))

    if platform == 'nt':
        base = Path(env.get('LOCALAPPDATA', home / 'AppData/Local')) / 'HT'
        add(base, 'Windows', allow_new=True)
    else:
        steam_roots = [home / '.local/share/Steam', home / '.steam/steam',
                       home / '.var/app/com.valvesoftware.Steam/.local/share/Steam']
        libraries = list(steam_roots)
        # Common user-mounted libraries, including custom diskmounts used
        # when a Steam library is absent from libraryfolders.vdf.
        for mount_root in (home / 'diskmounts', Path('/mnt'),
                           Path('/run/media') / home.name, Path('/media') / home.name):
            if mount_root.is_dir():
                try:
                    libraries.extend(mount_root.glob('*/SteamLibrary'))
                except OSError:
                    pass
        for steam in steam_roots:
            config = steam / 'steamapps/libraryfolders.vdf'
            if config.is_file():
                try:
                    data = config.read_text(encoding='utf-8', errors='replace')
                    libraries.extend(Path(p.replace('\\\\', '\\')) for p in re.findall(r'"path"\s*"([^"\n]+)"', data))
                except OSError:
                    pass
        for library in libraries:
            users = library / 'steamapps/compatdata/4508340/pfx/drive_c/users'
            if users.is_dir():
                try:
                    for user in users.iterdir():
                        library_label = library.parent.name if library.name == 'SteamLibrary' else library.name
                        add(user / 'AppData/Local/HT', f'Proton ({library_label})', allow_new=True)
                except OSError:
                    continue
        # Explicit Wine/Proton prefixes are useful for non-Steam launchers.
        for prefix in (env.get('WINEPREFIX'), env.get('STEAM_COMPAT_DATA_PATH')):
            if prefix:
                root = Path(prefix)
                if (root / 'pfx').is_dir():
                    root /= 'pfx'
                users = root / 'drive_c/users'
                if users.is_dir():
                    for user in users.iterdir():
                        add(user / 'AppData/Local/HT', 'Wine/Proton', allow_new=True)
    seen, result = set(), []
    for label, path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved not in seen:
            seen.add(resolved)
            result.append((label, resolved))
    return result


def write_new(path, payload):
    """Write a new file, publish atomically where supported, never replace one."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.nte-studio-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        if os.name == 'nt':
            # Windows rename refuses an existing destination.
            os.rename(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except OSError as exc:
                if exc.errno not in (errno.EPERM, errno.EOPNOTSUPP, errno.ENOSYS):
                    raise
                # FAT/network filesystems may not support hard links. O_EXCL
                # still prevents replacing an existing user recording.
                with path.open('xb') as f:
                    try:
                        f.write(payload)
                        f.flush()
                        os.fsync(f.fileno())
                    except Exception:
                        path.unlink(missing_ok=True)
                        raise
    finally:
        Path(temporary).unlink(missing_ok=True)


def install_sheet(document, report, title, destination, export_root=None):
    validate(document)
    if not str(destination).strip():
        raise SheetError('Choose the GuitarNotes destination folder first.')
    destination = Path(destination).expanduser()
    if not destination.is_absolute():
        raise SheetError('The destination must be an absolute folder path.')
    export_root = Path(export_root) if export_root else data_directory() / 'exports'
    slug = re.sub(r'[^\w. -]+', '', title, flags=re.UNICODE).strip(' .')[:80] or 'Untitled sheet'
    # Each export gets its own directory; the NTE file keeps its exact name.
    export_dir = export_root / f"{slug}_{document['noteId']}"
    filename = f"guitar_note_{document['noteId']}.json"
    backup = export_dir / filename
    target = destination / filename
    payload = (json.dumps(document, indent='\t', ensure_ascii=False) + '\n').encode('utf-8')
    metadata = {**report, 'title': title or 'Untitled sheet',
                'created_utc': datetime.now(timezone.utc).isoformat(),
                'local_note_id': document['noteId'], 'destination': str(target),
                'sha256': hashlib.sha256(payload).hexdigest()}
    try:
        write_new(backup, payload)
        write_new(export_dir / 'conversion.json', (json.dumps(metadata, indent=2) + '\n').encode())
    except OSError as exc:
        raise SheetError(f'Could not save the export backup: {exc}') from exc
    try:
        write_new(target, payload)
        if target.read_bytes() != payload:
            raise OSError('The installed file does not match the generated file.')
    except OSError as exc:
        raise SheetError(f'The sheet was created, but could not be installed.\n\nBackup: {backup}\n\nDestination: {target}\n\n{exc}') from exc
    return {'code': document['noteId'], 'target': str(target), 'backup': str(backup),
            'report': metadata, 'title': title or 'Untitled sheet'}
