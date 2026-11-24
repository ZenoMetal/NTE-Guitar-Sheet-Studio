"""Native PyInstaller packages; run on Linux for AppImage or Windows for EXE."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nte_studio import __version__
NAME = 'NTE Guitar Sheet Studio'
OUT = ROOT / 'release-dist'
OUT.mkdir(exist_ok=True)

def run(*args, **kwargs):
    subprocess.run([str(x) for x in args], check=True, cwd=ROOT, **kwargs)

args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
        '--name', NAME, '--add-data', str(ROOT / 'nte_studio/assets') + os.pathsep + 'nte_studio/assets']
if sys.platform == 'win32':
    from PIL import Image
    icon = ROOT / 'build' / 'icon.ico'; icon.parent.mkdir(exist_ok=True)
    Image.open(ROOT / 'nte_studio/assets/icon.png').save(icon, sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    run(*args, '--onefile', '--icon', icon, 'main.py')
    artifact = OUT / f'NTE-Guitar-Sheet-Studio-{__version__}-Windows-x64.exe'
    shutil.copy2(ROOT / 'dist' / (NAME + '.exe'), artifact)
    run(artifact, '--self-test', env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))
else:
    run(*args, '--onedir', 'main.py')
    appdir = ROOT / 'build' / 'Studio.AppDir'
    if appdir.exists(): shutil.rmtree(appdir)
    payload = appdir / 'usr/lib/studio'; payload.parent.mkdir(parents=True)
    shutil.copytree(ROOT / 'dist' / NAME, payload)
    for file in ('README.md','THIRD_PARTY.md'):
        shutil.copy2(ROOT / file, payload / file)
    shutil.copytree(ROOT / 'licenses', payload / 'licenses')
    run(payload / NAME, '--self-test', env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))
    apprun = appdir / 'AppRun'
    apprun.write_text('#!/bin/sh\nHERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nexec "$HERE/usr/lib/studio/NTE Guitar Sheet Studio" "$@"\n')
    apprun.chmod(0o755)
    (appdir / 'nte-guitar-sheet-studio.desktop').write_text('[Desktop Entry]\nType=Application\nName=NTE Guitar Sheet Studio\nExec=AppRun\nIcon=nte-guitar-sheet-studio\nCategories=AudioVideo;Audio;Midi;\nTerminal=false\n')
    shutil.copy2(ROOT / 'nte_studio/assets/icon.png', appdir / 'nte-guitar-sheet-studio.png')
    (appdir / '.DirIcon').symlink_to('nte-guitar-sheet-studio.png')
    tool = os.environ.get('APPIMAGETOOL') or shutil.which('appimagetool')
    if not tool: raise SystemExit('Set APPIMAGETOOL to the official appimagetool executable.')
    artifact = OUT / f'NTE-Guitar-Sheet-Studio-{__version__}-Linux-x86_64.AppImage'
    run(tool, '--no-appstream', appdir, artifact, env=dict(os.environ, ARCH='x86_64', APPIMAGE_EXTRACT_AND_RUN='1'))
    artifact.chmod(0o755)
    run(artifact, '--self-test', env=dict(os.environ, QT_QPA_PLATFORM='offscreen', APPIMAGE_EXTRACT_AND_RUN='1'))
with artifact.open('rb') as stream:
    checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
(OUT / (artifact.name + '.sha256')).write_text(checksum + '  ' + artifact.name + '\n')
print(artifact)
