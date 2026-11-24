# Third-party runtime

The desktop interface uses PySide6 (Qt for Python), distributed by The Qt Company.
MIDI preview uses Qt Multimedia audio output and the application's own
sample-free synthesizer. No third-party soundfont or instrument samples are included.
PySide6 is available under LGPLv3/GPLv3 and commercial licensing options.
Qt and PySide6 retain their respective copyright notices and licenses.

Project and licensing information:

- <https://www.qt.io/qt-for-python>
- <https://doc.qt.io/qtforpython-6/licenses.html>
- <https://code.qt.io/cgit/pyside/pyside-setup.git/>

The source application installs unmodified PySide6 wheels into a local virtual
environment, or uses the user's already installed PySide6 runtime. The Windows
build script uses PyInstaller, whose licensing information is available at
<https://pyinstaller.org/en/stable/license.html>.

No downloaded song arrangements are included in this application. The small
practice pattern and generated example MIDI are original test fixtures.
