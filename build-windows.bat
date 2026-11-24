@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .build-venv
if errorlevel 1 goto failed
".build-venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto failed
".build-venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --onedir --name "NTE Guitar Sheet Studio" --add-data "nte_studio/assets;nte_studio/assets" main.py
if errorlevel 1 goto failed
echo.
echo Windows application created in dist\NTE Guitar Sheet Studio\
echo Share the entire folder, not just the EXE.
pause
exit /b
:failed
echo Build failed. See the error above. Run this script on Windows with Python 3.10 or newer.
pause
exit /b 1
