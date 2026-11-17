@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 goto python_missing
)
".venv\Scripts\python.exe" -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo Installing the desktop interface. Internet is needed only for this first setup.
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto setup_failed
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo The application could not start. Please read the error above.
    pause
)
exit /b
:python_missing
echo Python 3.10 or newer is required. Install it from https://www.python.org/downloads/
echo Enable the Python launcher or Add Python to PATH, then run this file again.
pause
exit /b 1
:setup_failed
echo Setup failed. Check your connection and Python version, then try again.
pause
exit /b 1
