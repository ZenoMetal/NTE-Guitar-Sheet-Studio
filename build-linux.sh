#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$task_root"
python3 -m venv .build-venv
.build-venv/bin/python -m pip install -r requirements.txt 'pyinstaller>=6.16,<7'
.build-venv/bin/python -m PyInstaller --noconfirm --clean --windowed --onedir \
  --name 'NTE Local Music Sheet Creator' \
  --add-data "$task_root/nte_studio/assets:nte_studio/assets" main.py
cp README.md THIRD_PARTY.md 'dist/NTE Local Music Sheet Creator/'
cp -R licenses 'dist/NTE Local Music Sheet Creator/'
echo 'Build complete: dist/NTE Local Music Sheet Creator/'
