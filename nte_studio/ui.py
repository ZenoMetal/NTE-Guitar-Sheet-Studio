"""English desktop UI. All file conversion work runs outside the UI thread."""
from dataclasses import replace
import json
from pathlib import Path
import traceback

from PySide6.QtCore import QObject, QRunnable, QSettings, QThreadPool, Qt, Signal, Slot, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import __version__
from .convert import convert
from .midi import read_midi
from .model import Options, SheetError, pitch_name
from .storage import data_directory, detect_destinations, install_sheet
from .text_sheet import PRESETS, load_mapping, parse_text

DEMO = '[tuo] - t y u - [yip] -- (tyu) [tuo]'

STYLE = '''
QWidget { background: #10151f; color: #e9edf5; font-family: "Segoe UI", "DejaVu Sans"; font-size: 13px; }
QMainWindow { background: #10151f; }
QLabel { background: transparent; }
QLabel#eyebrow { color: #8b9ab0; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
QLabel#heading { font-size: 29px; font-weight: 700; }
QLabel#muted { color: #9aa9bc; }
QLabel#badge { background: #17332f; color: #91e0bd; border: 1px solid #2c5145; border-radius: 11px; padding: 5px 12px; font-size: 11px; font-weight: 600; }
QLabel#section { color: #c4cfdf; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#resultTitle { font-size: 16px; font-weight: 600; }
QLabel#success { color: #91e0bd; }
QFrame#card { background: #171e2a; border: 1px solid #2a3546; border-radius: 12px; }
QFrame#drop { background: #1b2535; border: 1px dashed #4a6280; border-radius: 10px; }
QFrame#drop QLabel { background: transparent; border: none; }
QTabWidget::pane { border: 1px solid #2a3546; border-radius: 0px 12px 12px 12px; background: #171e2a; }
QTabBar::tab { background: #10151f; color: #8e9eb5; padding: 13px 25px; border-bottom: 2px solid #2a3546; font-weight: 600; }
QTabBar::tab:selected { color: #9fe7c7; background: #171e2a; border-bottom: 2px solid #83dcb4; }
QTabBar::tab:hover { color: #e9edf5; }
QPushButton { background: #253247; border: 1px solid #384b66; border-radius: 7px; padding: 9px 13px; font-weight: 600; }
QPushButton:hover { background: #30425b; border-color: #6380a4; }
QPushButton:pressed { background: #1c2a3e; }
QPushButton:disabled { color: #647186; background: #1c2430; border-color: #283446; }
QPushButton#primary { color: #11271e; background: #94e2bd; border: none; padding: 13px 20px; font-size: 14px; }
QPushButton#primary:hover { background: #b0f0d1; }
QPushButton#primary:disabled { background: #334b43; color: #93a69e; }
QPushButton#subtle { background: transparent; border: 1px solid #344258; padding: 6px 10px; color: #b8c9e1; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: #101722; color: #e9edf5; border: 1px solid #344258; border-radius: 6px; padding: 8px; selection-background-color: #356751; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #8fd4b3; }
QLineEdit#code { color: #a8ebcb; background: #111d1b; font-family: "DejaVu Sans Mono", "Consolas"; font-size: 12px; padding: 12px 9px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #1b2535; selection-background-color: #344b65; border: 1px solid #344258; }
QTableWidget { background: #141c28; alternate-background-color: #192331; border: 1px solid #2c394b; border-radius: 6px; gridline-color: #273344; }
QTableWidget::item { padding: 6px; }
QHeaderView::section { background: #202c3d; color: #aab9cd; border: none; border-bottom: 1px solid #344258; padding: 9px 6px; font-size: 11px; font-weight: 600; }
QTableWidget QComboBox { padding: 4px; margin: 2px; border: none; }
QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #65758d; border-radius: 4px; background: #121b29; }
QCheckBox::indicator:checked { background: #91dfb9; border: 3px solid #4b7e65; }
QProgressBar { border: none; border-radius: 3px; background: #243146; max-height: 5px; }
QProgressBar::chunk { background: #91dfb9; border-radius: 3px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #151c28; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #3c4b61; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #243247; color: #fff; border: 1px solid #52657e; padding: 6px; }
QMessageBox, QDialog { background: #171e2a; }
'''


def label(text, name=None, wrap=False):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def button(text, action, name=None):
    w = QPushButton(text)
    if name:
        w.setObjectName(name)
    w.clicked.connect(action)
    return w


class WorkerSignals(QObject):
    done = Signal(object)
    failed = Signal(str)
    finished = Signal()


class Worker(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function, self.signals = function, WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.function()
        except Exception as exc:
            self.signals.failed.emit(str(exc) or type(exc).__name__)
        else:
            self.signals.done.emit(result)
        finally:
            self.signals.finished.emit()


class DropZone(QFrame):
    fileDropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName('drop')
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).suffix.lower() in ('.mid', '.midi'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.fileDropped.emit(event.mimeData().urls()[0].toLocalFile())
        event.acceptProposedAction()


class MappingDialog(QDialog):
    def __init__(self, mapping, parent):
        super().__init__(parent)
        self.setWindowTitle('Keyboard mapping')
        self.resize(570, 580)
        layout = QVBoxLayout(self)
        layout.addWidget(label('Each character maps to a MIDI pitch (0–127). C4 = 60.\nEscape reserved characters in sheet text: \\[  \\]  \\-  \\(.', 'muted', True))
        self.editor = QPlainTextEdit(json.dumps(mapping, indent=2, ensure_ascii=False))
        self.editor.setFont(QFont('DejaVu Sans Mono', 11))
        layout.addWidget(self.editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.check_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.mapping = mapping

    def check_and_accept(self):
        try:
            self.mapping = load_mapping(self.editor.toPlainText())
        except SheetError as exc:
            QMessageBox.warning(self, 'Check the mapping', str(exc))
            return
        self.accept()


class StudioWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings or QSettings('NTE Local Music Sheet Creator', 'NTE Local Music Sheet Creator')
        self.song, self.midi_path, self.last_result = None, None, None
        self.pool, self.jobs = QThreadPool(self), set()
        self.setWindowTitle('NTE Local Music Sheet Creator')
        self.resize(1260, 960)
        self.setMinimumSize(980, 760)
        assets = Path(__file__).parent / 'assets'
        down = (assets / 'chevron-down.svg').as_posix()
        up = (assets / 'chevron-up.svg').as_posix()
        self.setStyleSheet(STYLE + f'''
            QComboBox::down-arrow {{ image: url("{down}"); width: 12px; height: 8px; }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{up}"); width: 10px; height: 6px; }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{down}"); width: 10px; height: 6px; }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 18px; border: none; }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 18px; border: none; }}
        ''')
        icon_path = assets / 'icon.svg'
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.custom_mapping = dict(PRESETS[next(iter(PRESETS))])
        try:
            saved = self.settings.value('custom_mapping', '')
            if saved:
                self.custom_mapping = load_mapping(saved)
        except SheetError:
            pass
        outer = QWidget()
        self.setCentralWidget(outer)
        page = QVBoxLayout(outer)
        page.setContentsMargins(28, 23, 28, 18)
        page.setSpacing(17)
        top = QHBoxLayout()
        branding = QVBoxLayout()
        branding.setSpacing(5)
        branding.addWidget(label('NTE  /  LOCAL MUSIC SHEET CREATOR', 'eyebrow'))
        branding.addWidget(label('Your music. In the game.', 'heading'))
        branding.addWidget(label('Import a MIDI or paste a sheet. We handle the conversion and installation.', 'muted'))
        top.addLayout(branding)
        top.addStretch()
        badge = label('LOCAL  ·  OFFLINE', 'badge')
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        top.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
        page.addLayout(top)
        body = QHBoxLayout()
        body.setSpacing(20)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.addTab(self.scroll_tab(self.midi_tab()), '01   MIDI file')
        self.tabs.addTab(self.scroll_tab(self.text_tab()), '02   Text sheet')
        body.addWidget(self.tabs, 1)
        sidebar = QWidget()
        sidebar.setFixedWidth(344)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(14)
        side.addWidget(self.settings_card())
        side.addWidget(self.destination_card())
        side.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(355)
        scroll.setWidget(sidebar)
        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        right_column.addWidget(scroll, 1)
        self.create_button = button('Create && install sheet', self.create_sheet, 'primary')
        self.create_button.setMinimumHeight(48)
        right_column.addWidget(self.create_button)
        helper = label('Validates, saves a backup and installs the JSON.', 'muted')
        helper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_column.addWidget(helper)
        body.addLayout(right_column)
        page.addLayout(body, 1)
        page.addWidget(self.result_card())
        bottom = QHBoxLayout()
        self.status = label('Ready. Your source files stay on this computer.', 'muted')
        bottom.addWidget(self.status, 1)
        bottom.addWidget(label(f'v{__version__}  ·  NTE JSON v6', 'muted'))
        page.addLayout(bottom)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.hide()
        page.addWidget(self.progress)
        self.refresh_destinations()

    def scroll_tab(self, widget):
        widget.setMinimumHeight(555)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll

    def card(self):
        frame = QFrame()
        frame.setObjectName('card')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 17, 18, 17)
        layout.setSpacing(12)
        return frame, layout

    def midi_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        zone = DropZone()
        zone.fileDropped.connect(self.load_midi)
        drop = QVBoxLayout(zone)
        drop.setContentsMargins(20, 20, 20, 20)
        title = label('Drop a MIDI file here', 'resultTitle')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop.addWidget(title)
        sub = label('Standard MIDI · .mid or .midi · up to 16 MB', 'muted')
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop.addWidget(sub)
        self.browse_button = button('Browse MIDI file…', self.browse_midi)
        drop.addWidget(self.browse_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(zone)
        self.file_label = label('No MIDI file selected', 'muted', True)
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.file_label)
        heading = QHBoxLayout()
        heading.addWidget(label('CHOOSE YOUR TRACKS', 'section'))
        heading.addStretch()
        heading.addWidget(button('Select all', lambda: self.select_parts(True), 'subtle'))
        heading.addWidget(button('Clear', lambda: self.select_parts(False), 'subtle'))
        layout.addLayout(heading)
        self.track_table = QTableWidget(0, 6)
        self.track_table.setHorizontalHeaderLabels(['USE', 'TRACK', 'CH.', 'NOTES', 'RANGE', 'ROLE'])
        self.track_table.verticalHeader().hide()
        self.track_table.setAlternatingRowColors(True)
        self.track_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.track_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column, width in [(0, 43), (2, 42), (3, 58), (4, 95), (5, 113)]:
            self.track_table.setColumnWidth(column, width)
        self.track_table.setMinimumHeight(170)
        layout.addWidget(self.track_table, 1)
        layout.addWidget(label('Percussion is excluded. Set a melody track to Lead to preserve it in dense passages.', 'muted', True))
        row = QHBoxLayout()
        self.sustain = QCheckBox('Read MIDI sustain pedal')
        self.sustain.setChecked(True)
        self.sustain.setToolTip('Reloads the MIDI when changed. Pedal holds become longer note durations.')
        self.sustain.toggled.connect(self.reload_midi)
        row.addWidget(self.sustain)
        row.addStretch()
        row.addWidget(label('Speed', 'muted'))
        self.speed = QDoubleSpinBox()
        self.speed.setRange(.25, 4)
        self.speed.setSingleStep(.05)
        self.speed.setValue(1)
        self.speed.setSuffix('×')
        row.addWidget(self.speed)
        layout.addLayout(row)
        return page

    def text_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(13)
        row = QHBoxLayout()
        row.addWidget(label('KEYBOARD LAYOUT', 'section'))
        row.addStretch()
        row.addWidget(button('Syntax guide', self.show_syntax, 'subtle'))
        layout.addLayout(row)
        mapping_row = QHBoxLayout()
        self.layout_combo = QComboBox()
        self.layout_combo.addItems([*PRESETS, 'Custom key mapping'])
        saved_layout = self.settings.value('text_layout', '')
        if self.layout_combo.findText(saved_layout) >= 0:
            self.layout_combo.setCurrentText(saved_layout)
        mapping_row.addWidget(self.layout_combo, 1)
        mapping_row.addWidget(button('View / edit mapping', self.edit_mapping, 'subtle'))
        layout.addLayout(mapping_row)
        layout.addWidget(label('Paste keyboard letters, chords and rests below.', 'muted'))
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText('[vaqg] --- t - [bagw] -- [cage]\n\n[abc] = chord     (abc) = fast roll     - = rest\n\nChoose the layout used by your source sheet.')
        self.text_input.setFont(QFont('DejaVu Sans Mono', 12))
        self.text_input.setMinimumHeight(210)
        layout.addWidget(self.text_input, 1)
        options = QGridLayout()
        options.addWidget(label('Tempo (BPM)', 'muted'), 0, 0)
        options.addWidget(label('Steps per beat', 'muted'), 0, 1)
        options.addWidget(label('Note length', 'muted'), 0, 2)
        self.bpm = QDoubleSpinBox()
        self.bpm.setRange(20, 400)
        self.bpm.setValue(120)
        self.bpm.setDecimals(1)
        self.steps = QComboBox()
        for value, text in [(1, '1 · quarter notes'), (2, '2 · eighth notes'), (4, '4 · sixteenth notes'), (8, '8 · thirty-second notes')]:
            self.steps.addItem(text, value)
        self.steps.setCurrentIndex(1)
        self.gate = QSpinBox()
        self.gate.setRange(10, 100)
        self.gate.setValue(85)
        self.gate.setSuffix('%')
        for column, widget in enumerate((self.bpm, self.steps, self.gate)):
            options.addWidget(widget, 1, column)
        layout.addLayout(options)
        demo_row = QHBoxLayout()
        demo_row.addWidget(button('Insert example', self.insert_example, 'subtle'))
        demo_row.addStretch()
        layout.addLayout(demo_row)
        layout.addWidget(label('Text timing is a template: each note/chord takes one step. Spaces and line breaks separate tokens; dashes add rests. Adjust tempo to match your song.', 'muted', True))
        return page

    def settings_card(self):
        frame, layout = self.card()
        layout.addWidget(label('MAKE IT YOURS', 'section'))
        self.sheet_title = QLineEdit()
        self.sheet_title.setPlaceholderText('Sheet title')
        self.sheet_title.setMaxLength(120)
        layout.addWidget(self.sheet_title)
        grid = QGridLayout()
        grid.addWidget(label('Guitar tone', 'muted'), 0, 0)
        grid.addWidget(label('Transpose', 'muted'), 0, 1)
        self.tone = QComboBox()
        self.tone.addItems(['Clean', 'Distortion'])
        saved_tone = self.settings.value('tone', 'Clean')
        if saved_tone in ('Clean', 'Distortion'):
            self.tone.setCurrentText(saved_tone)
        self.transpose = QSpinBox()
        self.transpose.setRange(-48, 48)
        self.transpose.setSuffix(' st')
        self.transpose.setToolTip('Transpose all notes by semitones before range fitting.')
        grid.addWidget(self.tone, 1, 0)
        grid.addWidget(self.transpose, 1, 1)
        grid.addWidget(label('Simultaneous notes', 'muted'), 2, 0)
        grid.addWidget(label('Pitch range', 'muted'), 2, 1)
        self.voices = QSpinBox()
        self.voices.setRange(1, 5)
        self.voices.setValue(5)
        grid.addWidget(self.voices, 3, 0)
        grid.addWidget(label('E3 – D#6', 'muted'), 3, 1)
        layout.addLayout(grid)
        self.range_mode = QComboBox()
        self.range_mode.addItems(['Octave fold', 'Drop outside range', 'Reject outside range'])
        self.range_mode.setToolTip('Octave fold preserves pitch class but may change voicing. Reject lets you adjust transposition instead.')
        layout.addWidget(self.range_mode)
        self.trim_lead = QCheckBox('Trim silence before the first note')
        self.trim_lead.setChecked(True)
        layout.addWidget(self.trim_lead)
        return frame

    def destination_card(self):
        frame, layout = self.card()
        header = QHBoxLayout()
        header.addWidget(label('INSTALL DESTINATION', 'section'))
        header.addStretch()
        header.addWidget(button('Rescan', self.refresh_destinations, 'subtle'))
        layout.addLayout(header)
        self.destination_combo = QComboBox()
        self.destination_combo.currentIndexChanged.connect(self.destination_selected)
        layout.addWidget(self.destination_combo)
        self.destination = QLineEdit()
        self.destination.setPlaceholderText('Choose your GuitarNotes folder')
        self.destination.setToolTip('Windows: %LOCALAPPDATA%\\HT\\Saved_Global[Steam]\\GuitarNotes. Linux: the equivalent directory inside your Proton prefix.')
        layout.addWidget(self.destination)
        layout.addWidget(button('Choose folder…', self.browse_destination, 'subtle'))
        self.destination_hint = label('Steam, standalone and Proton folders are detected automatically.', 'muted', True)
        layout.addWidget(self.destination_hint)
        return frame

    def result_card(self):
        frame, layout = self.card()
        grid = QGridLayout()
        self.result_title = label('Ready for your first sheet', 'resultTitle')
        self.result_summary = label('Your installed sheet ID will appear here.', 'muted')
        grid.addWidget(self.result_title, 0, 0)
        grid.addWidget(self.result_summary, 1, 0)
        right = QHBoxLayout()
        self.code = QLineEdit()
        self.code.setObjectName('code')
        self.code.setReadOnly(True)
        self.code.setPlaceholderText('LOCAL SHEET CODE')
        self.code.setMinimumWidth(285)
        right.addWidget(self.code)
        self.copy_button = button('Copy code', self.copy_code)
        self.copy_button.setEnabled(False)
        right.addWidget(self.copy_button)
        grid.addLayout(right, 0, 1, 2, 1)
        self.output_path = label('No file created yet.', 'muted', True)
        self.output_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(self.output_path, 2, 0, 1, 2)
        actions = QHBoxLayout()
        self.open_folder_button = button('Open GuitarNotes', self.open_target_folder, 'subtle')
        self.details_button = button('Conversion details', self.show_details, 'subtle')
        self.open_folder_button.setEnabled(False)
        self.details_button.setEnabled(False)
        actions.addWidget(self.open_folder_button)
        actions.addWidget(self.details_button)
        actions.addStretch()
        grid.addLayout(actions, 3, 0, 1, 2)
        layout.addLayout(grid)
        layout.addWidget(label('Local sheet ID · This app does not register online share codes. In-game loading depends on NTE accepting the local cache. Use NTE’s own share feature for an online code.', 'muted', True))
        return frame

    def run_job(self, function, done, message):
        if self.jobs:
            return
        worker = Worker(function)
        self.jobs.add(worker)
        self.create_button.setEnabled(False)
        self.tabs.setEnabled(False)
        self.progress.show()
        self.status.setText(message)
        worker.signals.done.connect(done)
        worker.signals.failed.connect(self.job_error)
        worker.signals.finished.connect(lambda: self.job_finished(worker))
        self.pool.start(worker)

    def job_finished(self, worker):
        self.jobs.discard(worker)
        self.create_button.setEnabled(True)
        self.tabs.setEnabled(True)
        self.progress.hide()

    def job_error(self, message):
        self.status.setText('Could not finish. Check the input and try again.')
        QMessageBox.warning(self, 'Could not create the sheet', message)

    def browse_midi(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose a MIDI file', '', 'MIDI files (*.mid *.midi);;All files (*)', options=QFileDialog.Option.DontUseNativeDialog)
        if path:
            self.load_midi(path)

    def load_midi(self, path):
        if self.jobs:
            return
        source = Path(path)
        sustain = self.sustain.isChecked()

        def loaded(song):
            self.song, self.midi_path = song, source
            self.populate_tracks(song)
            minutes, seconds = divmod(round(song.duration), 60)
            self.file_label.setText(f'{source.name}  ·  {minutes}:{seconds:02d}  ·  {len(song.parts)} parts  ·  {len(song.tempos)} tempo segments')
            self.file_label.setToolTip(str(source))
            if not self.sheet_title.text().strip():
                self.sheet_title.setText(source.stem)
            self.status.setText('MIDI loaded. Choose tracks, then create your sheet.')
        self.run_job(lambda: read_midi(source, sustain), loaded, 'Reading MIDI and analyzing tracks…')

    def reload_midi(self):
        if self.midi_path:
            self.load_midi(self.midi_path)

    def populate_tracks(self, song):
        self.track_table.setRowCount(len(song.parts))
        for row, part in enumerate(song.parts):
            use = QTableWidgetItem()
            use.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            use.setCheckState(Qt.CheckState.Unchecked if part.percussion else Qt.CheckState.Checked)
            if part.percussion:
                use.setFlags(Qt.ItemFlag.NoItemFlags)
            self.track_table.setItem(row, 0, use)
            values = [part.name + (' · percussion' if part.percussion else ''), str(part.channel + 1),
                      f'{len(part.notes):,}', f'{pitch_name(min(n.pitch for n in part.notes))}–{pitch_name(max(n.pitch for n in part.notes))}']
            for col, value in enumerate(values, 1):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.track_table.setItem(row, col, item)
            role = QComboBox()
            for name, priority in [('Lead', 100), ('Normal', 0), ('Background', -50)]:
                role.addItem(name, priority)
            role.setCurrentIndex(0 if any(word in part.name.lower() for word in ('vocal', 'melody', 'lead')) else 1)
            role.setEnabled(not part.percussion)
            self.track_table.setCellWidget(row, 5, role)
            self.track_table.setRowHeight(row, 39)

    def select_parts(self, selected):
        if not self.song:
            return
        for row, part in enumerate(self.song.parts):
            if not part.percussion:
                self.track_table.item(row, 0).setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)

    def current_mapping(self):
        return PRESETS.get(self.layout_combo.currentText(), self.custom_mapping)

    def edit_mapping(self):
        dialog = MappingDialog(self.current_mapping(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.custom_mapping = dialog.mapping
            self.layout_combo.setCurrentText('Custom key mapping')
            self.settings.setValue('custom_mapping', json.dumps(self.custom_mapping))

    def insert_example(self):
        if self.text_input.toPlainText().strip():
            if QMessageBox.question(self, 'Replace text?', 'Replace the current text with the example?') != QMessageBox.StandardButton.Yes:
                return
        self.layout_combo.setCurrentIndex(0)
        self.text_input.setPlainText(DEMO)

    def show_syntax(self):
        box = QMessageBox(self)
        box.setWindowTitle('Text sheet syntax')
        box.setText('Choose the keyboard layout that matches your source sheet.')
        box.setInformativeText(
            'a b c: consecutive notes; each note takes one step.\n'
            '[abc] or {abc}: notes played together.\n'
            '(abc): a fast roll; each note takes half a step.\n'
            '([ab]c): a chord followed by a note in a fast roll.\n'
            '- or |: one rest step.  _: two rest steps.\n'
            'Spaces and line breaks are separators, not extra time.\n'
            '// starts a comment until the end of the line.\n'
            'Use a backslash for literal reserved keys: \\[ \\] \\- \\(\n\n'
            'Virtual Piano: lowercase = white keys; uppercase and shifted symbols = black keys.\n'
            'Genshin: Z–M = C3–B3, A–J = C4–B4, Q–U = C5–B5.\n'
            'NTE: A–Enter = E3–D#4, Q–] = E4–D#5, 1–= = E5–D#6. Use ~ for Enter.\n\n'
            'Letter sheets do not contain exact original timings. BPM, steps per beat and note length define the rhythm here. '
            'Grouping conventions differ between websites; adjust your text to this guide.'
        )
        box.exec()

    def refresh_destinations(self):
        if not hasattr(self, 'destination_combo'):
            return
        previous = self.destination.text().strip()
        found = detect_destinations()
        self.destination_combo.blockSignals(True)
        self.destination_combo.clear()
        self.destination_combo.addItem('Select a detected folder…', None)
        for label_, path in found:
            self.destination_combo.addItem(f'{label_} · {path.parent.name}', str(path))
            self.destination_combo.setItemData(self.destination_combo.count() - 1, str(path), Qt.ItemDataRole.ToolTipRole)
        saved = previous or self.settings.value('destination', '')
        match = self.destination_combo.findData(saved)
        if match > 0:
            self.destination_combo.setCurrentIndex(match)
            self.destination.setText(saved)
        elif saved:
            self.destination.setText(saved)
        elif len(found) == 1:
            self.destination_combo.setCurrentIndex(1)
            self.destination.setText(str(found[0][1]))
        else:
            self.destination.clear()
        self.destination_combo.blockSignals(False)
        if not found:
            self.destination_hint.setText('No NTE cache found. Launch NTE once, or choose GuitarNotes inside the game’s Windows/Proton profile.')
        elif len(found) > 1:
            self.destination_hint.setText('Multiple game profiles found. Select the folder used by your current installation.')
        else:
            self.destination_hint.setText('NTE cache detected. Check the path before installing.')

    def destination_selected(self, index):
        path = self.destination_combo.itemData(index)
        if path:
            self.destination.setText(path)

    def browse_destination(self):
        path = QFileDialog.getExistingDirectory(self, 'Choose the GuitarNotes folder', self.destination.text(), options=QFileDialog.Option.DontUseNativeDialog)
        if path:
            target = Path(path)
            if target.name != 'GuitarNotes':
                target /= 'GuitarNotes'
            self.destination.setText(str(target))
            self.destination_combo.setCurrentIndex(0)

    def create_sheet(self):
        if self.jobs:
            return
        try:
            title = self.sheet_title.text().strip() or 'Untitled sheet'
            destination = self.destination.text().strip()
            if not destination:
                raise SheetError('Choose your GuitarNotes destination folder before creating a sheet.')
            if not Path(destination).expanduser().is_absolute():
                raise SheetError('Enter an absolute destination path.')
            options = Options(tone=self.tone.currentText(), transpose=self.transpose.value(),
                              speed=self.speed.value() if self.tabs.currentIndex() == 0 else 1,
                              max_voices=self.voices.value(), range_mode=self.range_mode.currentText(),
                              trim_lead=self.trim_lead.isChecked())
            source_duration = None
            warnings = []
            if self.tabs.currentIndex() == 0:
                if not self.song:
                    raise SheetError('Choose a MIDI file first.')
                notes, chosen = [], []
                for row, part in enumerate(self.song.parts):
                    if not part.percussion and self.track_table.item(row, 0).checkState() == Qt.CheckState.Checked:
                        priority = self.track_table.cellWidget(row, 5).currentData()
                        notes.extend(replace(n, priority=priority) for n in part.notes)
                        chosen.append(part.name)
                if not notes:
                    raise SheetError('Select at least one non-percussion track.')
                metadata = {'source_type': 'MIDI', 'source_file': str(self.midi_path),
                            'selected_tracks': chosen, 'tempo_segments': self.song.tempos,
                            'read_sustain': self.sustain.isChecked()}
                warnings = list(self.song.warnings)
            else:
                text = self.text_input.toPlainText()
                mapping = dict(self.current_mapping())
                # Parsing is done in the worker too, keeping long pastes responsive.
                notes = None
                bpm, steps, gate = self.bpm.value(), self.steps.currentData(), self.gate.value() / 100
                metadata = {'source_type': 'Text', 'layout': self.layout_combo.currentText(),
                            'bpm': bpm, 'steps_per_beat': steps, 'note_length': gate,
                            'mapping': mapping, 'source_text': text}
            self.settings.setValue('destination', destination)
            self.settings.setValue('tone', options.tone)
            self.settings.setValue('text_layout', self.layout_combo.currentText())

            def work():
                source_notes, duration_ = notes, source_duration
                if source_notes is None:
                    source_notes, duration_ = parse_text(text, mapping, bpm, steps, gate)
                doc, report = convert(source_notes, options, source_duration=duration_)
                report.update(metadata)
                report['warnings'] = warnings
                return install_sheet(doc, report, title, destination)
            self.run_job(work, self.conversion_finished, 'Converting notes, validating JSON and installing…')
        except (SheetError, OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Check your input', str(exc))

    def conversion_finished(self, result):
        self.last_result = result
        self.code.setText(result['code'])
        self.result_title.setText('Installed · ' + result['title'])
        self.result_title.setObjectName('success')
        check = result['report']['validation']
        minutes, seconds = divmod(round(check['duration_seconds']), 60)
        stats = result['report']['statistics']
        self.result_summary.setText(f"{minutes}:{seconds:02d}  ·  {check['notes']:,} notes  ·  {result['report']['options']['tone']}")
        self.output_path.setText(result['target'])
        self.copy_button.setEnabled(True)
        self.open_folder_button.setEnabled(True)
        self.details_button.setEnabled(True)
        changes = []
        if stats['folded_notes']:
            changes.append(f"{stats['folded_notes']:,} notes octave-fitted")
        dropped = sum(stats[k] for k in ('out_of_range_dropped', 'short_notes_dropped', 'polyphony_dropped'))
        if dropped:
            changes.append(f'{dropped:,} notes omitted; see conversion details')
        warnings = result['report'].get('warnings', [])
        if warnings:
            changes.append('MIDI repairs reported in conversion details')
        self.status.setText('Installed and verified.' + (' ' + ' · '.join(changes) if changes else ' Code ready to copy.'))

    def copy_code(self):
        if self.last_result:
            QApplication.clipboard().setText(self.last_result['code'])
            self.status.setText('Local sheet code copied to the clipboard.')

    def open_target_folder(self):
        if self.last_result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.last_result['target']).parent)))

    def show_details(self):
        if not self.last_result:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Conversion details')
        dialog.resize(740, 600)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('The installed JSON and export backup were verified byte for byte.', 'muted', True))
        text = QPlainTextEdit(json.dumps(self.last_result, indent=2, ensure_ascii=False))
        text.setReadOnly(True)
        text.setFont(QFont('DejaVu Sans Mono', 10))
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def closeEvent(self, event):
        if self.jobs:
            QMessageBox.information(self, 'Conversion in progress', 'Please wait for the current operation to finish before closing.')
            event.ignore()
            return
        self.settings.sync()
        event.accept()


def main():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName('NTE Local Music Sheet Creator')
    app.setOrganizationName('NTE Local Music Sheet Creator')
    app.setStyle('Fusion')
    set_dark_palette(app)
    window = StudioWindow()
    window.show()
    return app.exec()


def set_dark_palette(app):
    palette = QPalette()
    for role, color in [(QPalette.ColorRole.Window, '#10151f'), (QPalette.ColorRole.WindowText, '#e9edf5'),
                        (QPalette.ColorRole.Base, '#101722'), (QPalette.ColorRole.Text, '#e9edf5'),
                        (QPalette.ColorRole.Button, '#253247'), (QPalette.ColorRole.ButtonText, '#e9edf5'),
                        (QPalette.ColorRole.Highlight, '#356751'), (QPalette.ColorRole.HighlightedText, '#ffffff'),
                        (QPalette.ColorRole.ToolTipBase, '#243247'), (QPalette.ColorRole.ToolTipText, '#ffffff')]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
