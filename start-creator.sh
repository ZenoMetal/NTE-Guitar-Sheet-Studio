#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
task_python="${NTE_STUDIO_PYTHON:-python3}"
if ! command -v "$task_python" >/dev/null 2>&1; then
    echo 'Python 3.10 or newer is required. Install Python using your distribution package manager.' >&2
    exit 1
fi
# Prefer the already-installed desktop runtime, without changing the system.
if "$task_python" -c 'import PySide6' >/dev/null 2>&1; then
    exec "$task_python" main.py
fi
if [[ ! -x .venv/bin/python ]]; then
    "$task_python" -m venv .venv
fi
if ! .venv/bin/python -c 'import PySide6' >/dev/null 2>&1; then
    echo 'Installing the desktop interface. Internet is needed only for this first setup.'
    .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python main.py
