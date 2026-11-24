"""NTE Guitar Sheet Studio desktop interface."""
from dataclasses import replace
import json
from pathlib import Path

from PySide6.QtCore import (QObject, QRunnable, QSettings, QThreadPool, QTimer, Qt, Signal, Slot,
                            QUrl, QSize, QFileSystemWatcher)
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPalette
from PySide6.QtWidgets import (QApplication, QAbstractItemView, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSlider, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

from . import __version__
from .audio import MidiPlayer
from .convert import convert
from .i18n import LANGUAGES, translate
from .library import midi_files, read_collection
from .midi import read_midi
from .model import Options, SheetError, pitch_name
from .storage import detect_destinations, install_sheet
from .text_sheet import PRESETS, load_mapping, parse_text, tempo_for_duration

APP_NAME = 'NTE Guitar Sheet Studio'
DEMO = '[tuo] - t y u - [yip] -- (tyu) [tuo]'
ASSETS = Path(__file__).parent / 'assets'


def style(theme):
    bg, card, field, fg, muted, border, button, selected = (
        ('#1A1A1E', '#242429', '#1d1d22', '#f0f0f5', '#b2b4c2', '#3c3c47', '#343440', '#334f49')
        if theme == 'dark' else
        ('#f3f3f6', '#ffffff', '#f8f8fb', '#202129', '#5f6270', '#c8cbd5', '#e8eaf1', '#d3e9df'))
    return f'''
QWidget {{ background: {bg}; color: {fg}; font-family: "Segoe UI", "Noto Sans", "DejaVu Sans"; font-size: 13px; }}
QLabel {{ background: transparent; }}
QLabel#muted {{ color: {muted}; }}
QLabel#section {{ color: {muted}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
QLabel#shareTitle {{ font-size: 14px; font-weight: 700; }}
QFrame#card {{ background: {card}; border: 1px solid {border}; border-radius: 12px; }}
QFrame#card QWidget {{ background-color: transparent; }}
QTabWidget::pane {{ border: 1px solid {border}; border-radius: 9px; }}
QTabBar::tab {{ color: {muted}; padding: 12px 22px; border-bottom: 2px solid {border}; font-weight: 600; }}
QTabBar::tab:selected {{ color: {fg}; border-bottom: 2px solid #83dcb4; }}
QPushButton {{ background: {button}; border: 1px solid {border}; border-radius: 7px; padding: 9px 12px; font-weight: 600; }}
QPushButton:hover {{ border-color: #78b69a; }}
QPushButton:disabled {{ color: {muted}; }}
QPushButton#primary {{ color: #11271e; background: #94e2bd; padding: 13px 14px; font-size: 14px; border: none; }}
QPushButton#primary:hover {{ background: #b0f0d1; }}
QPushButton#primary:disabled {{ background: {button}; color: {muted}; }}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {field}; color: {fg}; border: 1px solid {border}; border-radius: 6px; padding: 8px; selection-background-color: {selected}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border-color: #83bf9f; }}
QLineEdit#code {{ color: {fg}; font-family: "DejaVu Sans Mono", "Consolas"; font-size: 11px; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {card}; color: {fg}; selection-background-color: {selected}; }}
QTableWidget, QListWidget {{ background: {field}; alternate-background-color: {card}; border: 1px solid {border}; border-radius: 7px; gridline-color: {border}; }}
QTableWidget::item, QListWidget::item {{ padding: 6px; }}
QTableWidget::item:selected, QListWidget::item:selected {{ background: {selected}; }}
QHeaderView::section {{ background: {button}; color: {muted}; border: none; padding: 9px 5px; font-size: 11px; font-weight: 600; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {muted}; border-radius: 4px; }}
QCheckBox::indicator:checked {{ background: #83cfa8; border: 3px solid #4b7e65; }}
QSlider::groove:horizontal {{ height: 5px; background: {border}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 12px; height: 12px; margin: -4px 0; background: #83cfa8; border-radius: 6px; }}
QProgressBar {{ border: none; background: {border}; max-height: 4px; }}
QProgressBar::chunk {{ background: #83cfa8; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: {field}; width: 9px; }}
QScrollBar::handle:vertical {{ background: {border}; min-height: 28px; border-radius: 4px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QToolTip {{ background: {card}; color: {fg}; border: 1px solid {border}; padding: 6px; }}
QComboBox::down-arrow {{ image: url("{(ASSETS / 'chevron-down.svg').as_posix()}"); width: 12px; height: 8px; }}
'''


class Toggle(QCheckBox):
    """Keyboard-accessible two-state slider switch."""
    def sizeHint(self):
        return QSize(44, 26)

    def hitButton(self, position):
        return self.rect().contains(position)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#80cfa7' if self.isChecked() else '#626574'))
        painter.drawRoundedRect(1, 3, 40, 21, 10, 10)
        painter.setBrush(QColor('#ffffff'))
        painter.drawEllipse(24 if self.isChecked() else 4, 6, 15, 15)
        if self.hasFocus():
            painter.setPen(QColor('#a2bde4'))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(0, 1, 43, 24, 11, 11)

    def currentText(self):
        return 'Distortion' if self.isChecked() else 'Clean'

    def setCurrentText(self, text):
        self.setChecked(text == 'Distortion')


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
            value = self.function()
        except Exception as exc:
            self.signals.failed.emit(str(exc) or type(exc).__name__)
        else:
            self.signals.done.emit(value)
        finally:
            self.signals.finished.emit()


class SettingsDialog(QDialog):
    def __init__(self, studio):
        super().__init__(studio)
        self.studio = studio
        self.setWindowTitle(studio.t('settings'))
        self.resize(650, 660)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(QLabel(studio.t('language')))
        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        self.language.setCurrentIndex(self.language.findData(studio.language))
        layout.addWidget(self.language)
        notice = QLabel(studio.t('ai_notice')); notice.setWordWrap(True); notice.setObjectName('muted')
        layout.addWidget(notice)
        row = QHBoxLayout()
        row.addWidget(QLabel(studio.t('dark')))
        self.light = Toggle(); self.light.setChecked(studio.theme == 'light')
        self.light.setAccessibleName(studio.t('appearance'))
        row.addWidget(self.light); row.addWidget(QLabel(studio.t('light'))); row.addStretch()
        layout.addLayout(row)
        layout.addWidget(QLabel(studio.t('destination')))
        self.detected = QComboBox(); self.detected.addItem(studio.t('destination_hint'), '')
        for name, path in detect_destinations():
            self.detected.addItem(f'{name} · {path}', str(path))
        layout.addWidget(self.detected)
        self.destination = QLineEdit(studio.destination_path)
        self.destination.setPlaceholderText(studio.t('destination_hint'))
        layout.addWidget(self.destination)
        self.detected.currentIndexChanged.connect(lambda i: self.destination.setText(self.detected.itemData(i)) if self.detected.itemData(i) else None)
        choose = QPushButton(studio.t('folder'))
        choose.clicked.connect(lambda: self.choose(self.destination, True))
        layout.addWidget(choose)
        layout.addWidget(QLabel(studio.t('library')))
        self.library = QLineEdit(studio.library_path)
        layout.addWidget(self.library)
        choose = QPushButton(studio.t('folder'))
        choose.clicked.connect(lambda: self.choose(self.library, False))
        layout.addWidget(choose)
        layout.addStretch()
        hint = QLabel(studio.t('settings_hint')); hint.setObjectName('muted'); hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox()
        buttons.addButton(studio.t('save'), QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(studio.t('cancel'), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose(self, field, guitar):
        folder = QFileDialog.getExistingDirectory(self, self.studio.t('folder'), field.text())
        if folder:
            path = Path(folder)
            if guitar and path.name != 'GuitarNotes':
                path /= 'GuitarNotes'
            field.setText(str(path))

    def save(self):
        for field in (self.destination, self.library):
            if field.text().strip() and not Path(field.text().strip()).expanduser().is_absolute():
                QMessageBox.warning(self, self.studio.t('error'), self.studio.t('need_folder'))
                return
        self.studio.apply_settings(self.language.currentData(), 'light' if self.light.isChecked() else 'dark',
                                      self.destination.text().strip(), self.library.text().strip())
        self.accept()


class StudioWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings(APP_NAME, APP_NAME)
        if settings is None and not self.settings.contains('migrated'):
            for old in ('NTE Local Music Sheet Creator', 'NTE Sheet Studio'):
                previous = QSettings(old, old)
                for key in previous.allKeys():
                    if not self.settings.contains(key):
                        self.settings.setValue(key, previous.value(key))
            self.settings.setValue('migrated', True)
        self.language = str(self.settings.value('language', 'en'))
        if self.language not in LANGUAGES: self.language = 'en'
        self.theme = str(self.settings.value('theme', 'dark'))
        self.destination_path = str(self.settings.value('destination', ''))
        self.library_path = str(self.settings.value('midi_library', ''))
        if not self.destination_path:
            found = detect_destinations()
            if len(found) == 1: self.destination_path = str(found[0][1])
        self.song = self.midi_path = self.last_result = None
        self.collection_entries, self.collection_warnings = [], []
        self.bindings = []
        self.pool, self.jobs = QThreadPool(self), set()
        self.player = MidiPlayer(self)
        self.custom_mapping = dict(PRESETS[next(iter(PRESETS))])
        try:
            saved = self.settings.value('custom_mapping', '')
            if saved: self.custom_mapping = load_mapping(saved)
        except SheetError: pass
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(ASSETS / 'icon.png')))
        self.resize(1320, 1080)
        self.setMinimumSize(1020, 760)
        self.setStyleSheet(style(self.theme))
        self.text_timing_timer = QTimer(self)
        self.text_timing_timer.setSingleShot(True); self.text_timing_timer.setInterval(180)
        self.text_timing_timer.timeout.connect(self.update_text_timing)
        outer = QWidget(); self.setCentralWidget(outer)
        page = QVBoxLayout(outer); page.setContentsMargins(24, 14, 24, 16); page.setSpacing(12)
        top = QHBoxLayout(); top.addStretch()
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(str(ASSETS / 'settings.svg')))
        self.settings_button.setIconSize(QSize(23, 23)); self.settings_button.setFixedSize(42, 38)
        self.settings_button.clicked.connect(self.show_settings)
        self.bind(self.settings_button.setToolTip, 'settings')
        self.bind(self.settings_button.setAccessibleName, 'settings')
        top.addWidget(self.settings_button); page.addLayout(top)
        body = QHBoxLayout(); body.setSpacing(18)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.scroll_tab(self.midi_tab()), '')
        self.tabs.addTab(self.scroll_tab(self.text_tab()), '')
        self.tabs.addTab(self.collection_tab(), '')
        for index, key in enumerate(('midi', 'text', 'collection')):
            self.bind(lambda value, index=index: self.tabs.setTabText(index, value), key)
        body.addWidget(self.tabs, 1)
        sidebar = QWidget(); sidebar.setFixedWidth(350)
        side = QVBoxLayout(sidebar); side.setContentsMargins(0, 0, 0, 0); side.setSpacing(14)
        side.addWidget(self.settings_card())
        self.create_button = self.B('create', self.create_sheet, 'primary'); self.create_button.setMinimumHeight(48)
        side.addWidget(self.create_button)
        self.code = QLineEdit(); self.code.setReadOnly(True); self.code.setObjectName('code')
        self.bind(self.code.setPlaceholderText, 'code'); side.addWidget(self.code)
        self.copy_button = self.B('copy', self.copy_code); self.copy_button.setEnabled(False); side.addWidget(self.copy_button)
        self.install_status = self.L('ready', 'muted', True); self.install_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        side.addWidget(self.install_status); side.addStretch()
        side_scroll = QScrollArea(); side_scroll.setWidgetResizable(True); side_scroll.setWidget(sidebar); side_scroll.setFixedWidth(362)
        body.addWidget(side_scroll)
        page.addLayout(body, 1)
        frame, share = self.card()
        share.addWidget(self.L('sharing_title', 'shareTitle'))
        self.sharing_notice = self.L('sharing', 'muted', True)
        self.sharing_notice.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        share.addWidget(self.sharing_notice)
        page.addWidget(frame)
        self.status = self.L('ready', 'muted'); footer = QHBoxLayout(); footer.addWidget(self.status, 1)
        footer.addWidget(QLabel(f'v{__version__}')); page.addLayout(footer)
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.setTextVisible(False); self.progress.hide(); page.addWidget(self.progress)
        self.player.changed.connect(self.update_preview_controls)
        self.player.failed.connect(self.job_error)
        self.tabs.currentChanged.connect(lambda index: self.refresh_collection() if index == 2 else None)
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self.folder_changed)
        self.update_watches(); self.refresh_library(); self.update_preview_controls(); self.update_text_timing()

    def t(self, key, **values):
        return translate(self.language, key, **values)

    def bind(self, setter, key):
        self.bindings.append((setter, key)); setter(self.t(key))

    def L(self, key, name=None, wrap=False):
        widget = QLabel(); widget.setWordWrap(wrap)
        if name: widget.setObjectName(name)
        self.bind(widget.setText, key); return widget

    def B(self, key, action, name=None):
        widget = QPushButton()
        if name: widget.setObjectName(name)
        self.bind(lambda value: widget.setText(value.replace('&', '&&')), key); widget.clicked.connect(action); return widget

    def set_status(self, key, **values):
        self.status.setText(self.t(key, **values))

    def card(self):
        frame = QFrame(); frame.setObjectName('card')
        layout = QVBoxLayout(frame); layout.setContentsMargins(17, 17, 17, 17); layout.setSpacing(12)
        return frame, layout

    def scroll_tab(self, widget):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(widget); return scroll

    def midi_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(18, 18, 18, 18); layout.setSpacing(12)
        row = QHBoxLayout(); row.addWidget(self.L('library', 'section')); row.addStretch()
        row.addWidget(self.B('refresh', self.refresh_library)); row.addWidget(self.B('browse', self.browse_midi)); layout.addLayout(row)
        self.library_hint = self.L('library_hint', 'muted', True); layout.addWidget(self.library_hint)
        self.library_list = QListWidget(); self.library_list.setMinimumHeight(105); self.library_list.setMaximumHeight(170)
        self.library_list.itemActivated.connect(lambda item: self.load_midi(item.data(Qt.ItemDataRole.UserRole)))
        self.library_list.itemClicked.connect(lambda item: self.load_midi(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.library_list)
        self.file_label = self.L('no_midi', 'muted', True); layout.addWidget(self.file_label)
        row = QHBoxLayout(); row.addWidget(self.L('tracks', 'section')); row.addStretch()
        row.addWidget(self.B('all', lambda: self.select_parts(True))); row.addWidget(self.B('clear', lambda: self.select_parts(False))); layout.addLayout(row)
        self.track_table = QTableWidget(0, 6)
        for column, key in enumerate(('use', 'track', 'channel', 'notes', 'range', 'role')):
            self.track_table.setHorizontalHeaderItem(column, QTableWidgetItem())
            self.bind(lambda text, column=column: self.track_table.horizontalHeaderItem(column).setText(text), key)
        self.track_table.verticalHeader().hide(); self.track_table.setAlternatingRowColors(True)
        self.track_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.track_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column, width in ((0, 62), (2, 45), (3, 62), (4, 100), (5, 118)): self.track_table.setColumnWidth(column, width)
        self.track_table.setMinimumHeight(510)
        self.track_table.itemChanged.connect(self.preview_selection_changed)
        layout.addWidget(self.track_table, 1); layout.addWidget(self.L('tracks_hint', 'muted', True))
        row = QHBoxLayout(); self.sustain = QCheckBox(); self.bind(self.sustain.setText, 'sustain'); self.sustain.setChecked(True)
        self.sustain.toggled.connect(self.reload_midi); row.addWidget(self.sustain); row.addStretch(); row.addWidget(self.L('speed', 'muted'))
        self.speed = QDoubleSpinBox(); self.speed.setRange(.25, 4); self.speed.setValue(1); self.speed.setSingleStep(.05); self.speed.setSuffix('×')
        self.speed.valueChanged.connect(self.player.set_speed); row.addWidget(self.speed); layout.addLayout(row)
        row = QHBoxLayout(); self.play_button = QPushButton(); self.play_button.clicked.connect(self.toggle_preview)
        self.stop_button = self.B('stop', self.player.stop); row.addWidget(self.play_button); row.addWidget(self.stop_button)
        self.preview_seek = QSlider(Qt.Orientation.Horizontal); self.preview_seek.setRange(0, 0)
        self.preview_seek.sliderReleased.connect(lambda: self.player.seek(self.preview_seek.value() / 1000))
        row.addWidget(self.preview_seek, 1); self.preview_time = QLabel(); row.addWidget(self.preview_time); layout.addLayout(row)
        row = QHBoxLayout(); row.addWidget(self.L('volume', 'muted')); self.preview_volume = QSlider(Qt.Orientation.Horizontal)
        self.preview_volume.setRange(0, 100); self.preview_volume.setValue(70); self.preview_volume.setMaximumWidth(160)
        self.preview_volume.valueChanged.connect(lambda value: self.player.set_volume(value / 100)); row.addWidget(self.preview_volume); row.addStretch(); layout.addLayout(row)
        controls = [layout.takeAt(7).layout() for _ in range(3)]
        for i, control in enumerate(controls): layout.insertLayout(4 + i, control)
        return page

    def text_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(18, 18, 18, 18); layout.setSpacing(14)
        row = QHBoxLayout(); self.layout_combo = QComboBox()
        for key in PRESETS: self.layout_combo.addItem(key, key)
        self.layout_combo.addItem(self.t('custom_mapping'), 'custom')
        saved = self.settings.value('text_layout', '')
        index = self.layout_combo.findData(saved)
        if index >= 0: self.layout_combo.setCurrentIndex(index)
        row.addWidget(self.layout_combo, 1); row.addWidget(self.B('mapping', self.edit_mapping)); row.addWidget(self.B('syntax', self.show_syntax)); layout.addLayout(row)
        self.custom_mapping = dict(PRESETS[next(iter(PRESETS))])
        try:
            if self.settings.value('custom_mapping'): self.custom_mapping = load_mapping(self.settings.value('custom_mapping'))
        except SheetError: pass
        self.text_input = QPlainTextEdit(); self.text_input.setFont(QFont('DejaVu Sans Mono', 12)); self.text_input.setMinimumHeight(260)
        self.bind(self.text_input.setPlaceholderText, 'text_hint'); layout.addWidget(self.text_input, 1)
        grid = QGridLayout()
        for col, key in enumerate(('tempo', 'steps', 'gate')): grid.addWidget(self.L(key, 'muted'), 0, col)
        self.bpm = QDoubleSpinBox(); self.bpm.setRange(20, 400); self.bpm.setDecimals(3); self.bpm.setValue(120)
        self.steps = QComboBox()
        for number, key in ((1, 'quarter'), (2, 'eighth'), (4, 'sixteenth'), (8, 'thirtysecond')): self.steps.addItem(self.t(key), number)
        self.steps.setCurrentIndex(1)
        self.gate = QSpinBox(); self.gate.setRange(10, 100); self.gate.setValue(85); self.gate.setSuffix('%')
        for col, widget in enumerate((self.bpm, self.steps, self.gate)): grid.addWidget(widget, 1, col)
        layout.addLayout(grid); self.fit_length = QCheckBox(); self.bind(self.fit_length.setText, 'fit'); layout.addWidget(self.fit_length)
        row = QHBoxLayout(); row.addWidget(self.L('target', 'muted'))
        self.length_minutes = QSpinBox(); self.length_minutes.setRange(0, 999); self.length_minutes.setValue(3); self.length_minutes.setSuffix(' min')
        self.length_seconds = QDoubleSpinBox(); self.length_seconds.setDecimals(3); self.length_seconds.setRange(0, 59.999); self.length_seconds.setSuffix(' s')
        row.addWidget(self.length_minutes); row.addWidget(self.length_seconds); row.addStretch(); layout.addLayout(row)
        self.timing_hint = QLabel(); self.timing_hint.setWordWrap(True); self.timing_hint.setObjectName('muted'); layout.addWidget(self.timing_hint)
        layout.addWidget(self.L('fit_hint', 'muted', True)); layout.addWidget(self.B('example', self.insert_example), alignment=Qt.AlignmentFlag.AlignLeft)
        for signal in (self.text_input.textChanged, self.layout_combo.currentIndexChanged, self.steps.currentIndexChanged,
                       self.gate.valueChanged, self.bpm.valueChanged, self.length_minutes.valueChanged, self.length_seconds.valueChanged):
            signal.connect(lambda *_: self.text_timing_timer.start())
        self.fit_length.toggled.connect(self.update_text_timing)
        return page

    def settings_card(self):
        frame, layout = self.card(); layout.addWidget(self.L('fine_tuning', 'section'))
        self.sheet_title = QLineEdit(); self.bind(self.sheet_title.setPlaceholderText, 'sheet_title'); self.sheet_title.setMaxLength(120); layout.addWidget(self.sheet_title)
        layout.addWidget(self.L('tone', 'muted'))
        row = QHBoxLayout(); row.addWidget(self.L('clean')); self.tone = Toggle(); self.tone.setAccessibleName(self.t('tone'))
        self.tone.setCurrentText(self.settings.value('tone', 'Clean')); row.addWidget(self.tone); row.addWidget(self.L('distortion')); row.addStretch(); layout.addLayout(row)
        grid = QGridLayout(); grid.addWidget(self.L('transpose', 'muted'), 0, 0); grid.addWidget(self.L('voices', 'muted'), 0, 1)
        self.transpose = QSpinBox(); self.transpose.setRange(-48, 48); self.transpose.setSuffix(' st')
        self.voices = QSpinBox(); self.voices.setRange(1, 5); self.voices.setValue(5)
        grid.addWidget(self.transpose, 1, 0); grid.addWidget(self.voices, 1, 1); layout.addLayout(grid)
        layout.addWidget(self.L('range', 'muted')); self.range_mode = QComboBox()
        for key, mode in (('fold', 'Octave fold'), ('drop', 'Drop outside range'), ('reject', 'Reject outside range')): self.range_mode.addItem(self.t(key), mode)
        layout.addWidget(self.range_mode); self.trim_lead = QCheckBox(); self.bind(self.trim_lead.setText, 'trim'); self.trim_lead.setChecked(True); layout.addWidget(self.trim_lead)
        return frame

    def collection_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(18, 18, 18, 18)
        row = QHBoxLayout(); self.collection_search = QLineEdit(); self.bind(self.collection_search.setPlaceholderText, 'search'); self.collection_search.textChanged.connect(self.filter_collection)
        row.addWidget(self.collection_search, 1); row.addWidget(self.B('refresh', self.refresh_collection)); row.addWidget(self.B('open_folder', self.open_target_folder)); layout.addLayout(row)
        layout.addWidget(self.L('collection_hint', 'muted', True)); self.collection_table = QTableWidget(0, 4)
        self.collection_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.collection_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.collection_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.collection_table.verticalHeader().hide()
        self.collection_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.collection_table.setColumnWidth(1, 75); self.collection_table.setColumnWidth(2, 100); self.collection_table.setColumnWidth(3, 270)
        for col, key in enumerate(('song', 'length', 'tone', 'code')):
            self.collection_table.setHorizontalHeaderItem(col, QTableWidgetItem())
            self.bind(lambda value, col=col: self.collection_table.horizontalHeaderItem(col).setText(value), key)
        self.collection_table.itemDoubleClicked.connect(lambda _: self.copy_collection_code())
        layout.addWidget(self.collection_table, 1); self.collection_summary = self.L('no_sheets', 'muted', True); layout.addWidget(self.collection_summary)
        layout.addWidget(self.B('copy', self.copy_collection_code), alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    def show_settings(self):
        SettingsDialog(self).exec()

    def apply_settings(self, language, theme, destination, library):
        self.language, self.theme = language, theme
        self.destination_path, self.library_path = destination, library
        for key, value in (('language', language), ('theme', theme), ('destination', destination), ('midi_library', library)):
            self.settings.setValue(key, value)
        self.settings.sync(); self.setStyleSheet(style(theme)); set_palette(QApplication.instance(), theme)
        for setter, key in self.bindings: setter(self.t(key))
        for i, key in enumerate(('fold', 'drop', 'reject')): self.range_mode.setItemText(i, self.t(key))
        for i, key in enumerate(('quarter', 'eighth', 'sixteenth', 'thirtysecond')): self.steps.setItemText(i, self.t(key))
        self.layout_combo.setItemText(self.layout_combo.count() - 1, self.t('custom_mapping'))
        if self.song:
            selected = self.selected_part_keys(); priorities = [self.track_table.cellWidget(i, 5).currentData() for i in range(len(self.song.parts))]
            self.populate_tracks(self.song, selected, priorities)
        self.update_watches(); self.refresh_library(); self.update_preview_controls(); self.update_text_timing(); self.set_status('ready')
        if self.tabs.currentIndex() == 2: self.refresh_collection()

    def update_watches(self):
        if self.watcher.directories(): self.watcher.removePaths(self.watcher.directories())
        paths = [value for value in (self.destination_path, self.library_path) if value and Path(value).is_dir()]
        if paths: self.watcher.addPaths(list(dict.fromkeys(paths)))

    def folder_changed(self, path):
        if path == self.library_path: self.refresh_library()
        if path == self.destination_path and self.tabs.currentIndex() == 2 and not self.jobs: self.refresh_collection()

    def refresh_library(self):
        self.library_list.clear()
        try: files = midi_files(self.library_path)
        except OSError: files = []
        for path in files:
            item = QListWidgetItem(path.stem); item.setData(Qt.ItemDataRole.UserRole, str(path)); item.setToolTip(str(path)); self.library_list.addItem(item)
        self.library_hint.setText(self.library_path if files else self.t('library_empty' if self.library_path else 'library_hint'))

    def run_job(self, function, done, message):
        if self.jobs: return
        worker = Worker(function); self.jobs.add(worker); self.create_button.setEnabled(False); self.tabs.setEnabled(False); self.settings_button.setEnabled(False)
        self.progress.show(); self.set_status(message)
        worker.signals.done.connect(done); worker.signals.failed.connect(self.job_error); worker.signals.finished.connect(lambda: self.job_finished(worker)); self.pool.start(worker)

    def job_finished(self, worker):
        self.jobs.discard(worker); self.create_button.setEnabled(True); self.tabs.setEnabled(True); self.settings_button.setEnabled(True); self.progress.hide()

    def job_error(self, message):
        self.set_status('input_error')
        box = QMessageBox(QMessageBox.Icon.Warning, self.t('error'), self.t('input_error'), parent=self)
        box.setDetailedText(message); box.exec()

    def browse_midi(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t('choose_midi'), self.library_path, 'MIDI (*.mid *.midi)')
        if path: self.load_midi(path)

    def load_midi(self, path, preserve_title=False):
        if self.jobs: return
        source = Path(path); sustain = self.sustain.isChecked(); self.player.stop()
        def loaded(song):
            self.song, self.midi_path = song, source; self.populate_tracks(song); self.player.load(song, self.selected_part_keys(), self.speed.value())
            self.file_label.setText(self.t('file_info', name=source.name, time=self.clock(song.duration), parts=len(song.parts))); self.file_label.setToolTip(str(source))
            if not preserve_title: self.sheet_title.setText(source.stem)
            self.set_status('loaded')
        self.run_job(lambda: read_midi(source, sustain), loaded, 'reading')

    def reload_midi(self):
        if self.midi_path: self.load_midi(self.midi_path, preserve_title=True)

    def populate_tracks(self, song, selected=None, priorities=None):
        self.track_table.blockSignals(True); self.track_table.setRowCount(len(song.parts))
        for row, part in enumerate(song.parts):
            use = QTableWidgetItem(); use.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            checked = not part.percussion and (selected is None or part.key in selected)
            use.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            if part.percussion: use.setFlags(Qt.ItemFlag.NoItemFlags)
            self.track_table.setItem(row, 0, use)
            values = [part.name + (' · ' + self.t('percussion') if part.percussion else ''), str(part.channel + 1),
                      f'{len(part.notes):,}', f'{pitch_name(min(n.pitch for n in part.notes))}–{pitch_name(max(n.pitch for n in part.notes))}']
            for col, value in enumerate(values, 1): self.track_table.setItem(row, col, QTableWidgetItem(value))
            role = QComboBox()
            for key, priority in (('lead', 100), ('normal', 0), ('background', -50)): role.addItem(self.t(key), priority)
            role.setCurrentIndex(role.findData(priorities[row]) if priorities else (0 if any(word in part.name.lower() for word in ('lead', 'vocal', 'melody')) else 1))
            role.setEnabled(not part.percussion); self.track_table.setCellWidget(row, 5, role); self.track_table.setRowHeight(row, 39)
        self.track_table.blockSignals(False)

    def selected_part_keys(self):
        return {p.key for row, p in enumerate(self.song.parts) if not p.percussion and self.track_table.item(row, 0).checkState() == Qt.CheckState.Checked} if self.song else set()

    def select_parts(self, selected):
        if not self.song: return
        self.track_table.blockSignals(True)
        for row, part in enumerate(self.song.parts):
            if not part.percussion: self.track_table.item(row, 0).setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
        self.track_table.blockSignals(False); self.preview_selection_changed()

    def preview_selection_changed(self, item=None):
        if item is None or item.column() == 0: self.player.select(self.selected_part_keys())

    def toggle_preview(self):
        self.player.pause() if self.player.state == 'playing' else self.player.play()

    @staticmethod
    def clock(seconds):
        minutes, seconds = divmod(max(0, int(seconds)), 60); return f'{minutes}:{seconds:02d}'

    def update_preview_controls(self):
        self.play_button.setText(self.t('pause' if self.player.state == 'playing' else 'play'))
        self.play_button.setEnabled(bool(self.song and self.player.selected_keys)); self.stop_button.setEnabled(bool(self.song))
        self.preview_seek.setEnabled(bool(self.song)); self.preview_seek.setMaximum(round(self.player.duration * 1000))
        if not self.preview_seek.isSliderDown(): self.preview_seek.setValue(round(self.player.position * 1000))
        self.preview_time.setText(f'{self.clock(self.player.position)} / {self.clock(self.player.duration)}')

    def current_mapping(self):
        return PRESETS.get(self.layout_combo.currentData(), self.custom_mapping)

    def target_text_duration(self):
        return self.length_minutes.value() * 60 + self.length_seconds.value()

    def update_text_timing(self):
        fitted = self.fit_length.isChecked(); self.bpm.setEnabled(not fitted); self.length_minutes.setEnabled(fitted); self.length_seconds.setEnabled(fitted)
        try:
            text, mapping, steps, gate = self.text_input.toPlainText(), self.current_mapping(), self.steps.currentData(), self.gate.value() / 100
            if fitted:
                bpm = tempo_for_duration(text, mapping, self.target_text_duration(), steps, gate)
                self.bpm.blockSignals(True); self.bpm.setValue(bpm); self.bpm.blockSignals(False)
                self.timing_hint.setText(self.t('auto_tempo', bpm=f'{bpm:.3f}', steps=steps))
            elif text.strip():
                _, duration = parse_text(text, mapping, self.bpm.value(), steps, gate)
                self.timing_hint.setText(self.t('text_duration', seconds=f'{duration:.3f}'))
            else: self.timing_hint.setText('')
        except SheetError:
            self.timing_hint.setText(self.t('timing_error'))

    def insert_example(self):
        if self.text_input.toPlainText().strip() and QMessageBox.question(self, self.t('example'), self.t('replace_text')) != QMessageBox.StandardButton.Yes: return
        self.layout_combo.setCurrentIndex(0); self.text_input.setPlainText(DEMO)

    def edit_mapping(self):
        dialog = QDialog(self); dialog.setWindowTitle(self.t('mapping')); dialog.resize(580, 560); layout = QVBoxLayout(dialog)
        editor = QPlainTextEdit(json.dumps(self.current_mapping(), indent=2, ensure_ascii=False)); layout.addWidget(editor)
        buttons = QDialogButtonBox(); buttons.addButton(self.t('save'), QDialogButtonBox.ButtonRole.AcceptRole); buttons.addButton(self.t('cancel'), QDialogButtonBox.ButtonRole.RejectRole)
        def save():
            try: self.custom_mapping = load_mapping(editor.toPlainText())
            except SheetError as exc: self.job_error(str(exc)); return
            self.settings.setValue('custom_mapping', json.dumps(self.custom_mapping)); self.layout_combo.setCurrentIndex(self.layout_combo.count() - 1); self.update_text_timing(); dialog.accept()
        buttons.accepted.connect(save); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons); dialog.exec()

    def show_syntax(self):
        QMessageBox.information(self, self.t('syntax'), self.t('syntax_text'))

    def create_sheet(self):
        if self.jobs: return
        try:
            if not self.destination_path or not Path(self.destination_path).expanduser().is_absolute(): raise SheetError(self.t('need_folder'))
            if self.tabs.currentIndex() == 2: self.tabs.setCurrentIndex(0)
            options = Options(tone=self.tone.currentText(), transpose=self.transpose.value(), speed=self.speed.value() if self.tabs.currentIndex() == 0 else 1,
                              max_voices=self.voices.value(), range_mode=self.range_mode.currentData(), trim_lead=self.trim_lead.isChecked())
            title, destination = self.sheet_title.text().strip() or self.t('untitled'), self.destination_path
            warnings, target_duration = [], None
            if self.tabs.currentIndex() == 0:
                if not self.song: raise SheetError(self.t('no_midi'))
                selected = self.selected_part_keys(); notes, names = [], []
                for row, part in enumerate(self.song.parts):
                    if part.key in selected:
                        notes.extend(replace(n, priority=self.track_table.cellWidget(row, 5).currentData()) for n in part.notes); names.append(part.name)
                if not notes: raise SheetError(self.t('select_tracks'))
                metadata = {'source_type': 'MIDI', 'source_file': str(self.midi_path), 'selected_tracks': names, 'tempo_segments': self.song.tempos, 'read_sustain': self.sustain.isChecked()}
                warnings = list(self.song.warnings)
            else:
                notes = None; text = self.text_input.toPlainText(); mapping = dict(self.current_mapping())
                bpm, steps, gate = self.bpm.value(), self.steps.currentData(), self.gate.value() / 100
                target_duration = self.target_text_duration() if self.fit_length.isChecked() else None
                if target_duration is not None: bpm = tempo_for_duration(text, mapping, target_duration, steps, gate)
                metadata = {'source_type': 'Text', 'layout': self.layout_combo.currentData(), 'bpm': bpm, 'steps_per_beat': steps,
                            'note_length': gate, 'mapping': mapping, 'source_text': text, 'target_duration_seconds': target_duration}
            self.settings.setValue('tone', options.tone); self.settings.setValue('text_layout', self.layout_combo.currentData())
            def work():
                source_notes, duration = (notes, None) if notes is not None else parse_text(text, mapping, bpm, steps, gate, target_duration)
                doc, report = convert(source_notes, options, source_duration=duration); report.update(metadata); report['warnings'] = warnings
                return install_sheet(doc, report, title, destination)
            self.run_job(work, self.conversion_finished, 'converting')
        except (SheetError, OSError, ValueError) as exc: self.job_error(str(exc))

    def conversion_finished(self, result):
        self.last_result = result; self.code.setText(result['code']); self.copy_button.setEnabled(True)
        self.install_status.setText(self.t('installed', title=result['title'])); self.install_status.setToolTip(result['target']); self.set_status('installed', title=result['title'])
        self.update_watches()

    def copy_code(self):
        if self.code.text(): QApplication.clipboard().setText(self.code.text()); self.set_status('copied')

    def refresh_collection(self):
        if self.jobs: return
        folder = self.destination_path
        def loaded(result):
            entries, warnings = result; self.entries = entries; self.collection_table.setRowCount(len(entries))
            for row, entry in enumerate(entries):
                name = entry.title or self.t('unnamed', code=entry.code[:8])
                for col, value in enumerate((name, self.clock(entry.duration), self.t('distortion' if entry.tone == 'Distortion' else 'clean'), entry.code)):
                    item = QTableWidgetItem(value); item.setToolTip(str(entry.path)); self.collection_table.setItem(row, col, item)
            self.filter_collection(); self.collection_summary.setText(self.t('collection_count', count=len(entries), warnings=len(warnings)) if entries else self.t('no_sheets'))
            self.collection_summary.setToolTip('\n'.join(warnings[:20])); self.set_status('ready')
        self.run_job(lambda: read_collection(folder) if folder else ([], []), loaded, 'reading_collection')

    def filter_collection(self):
        query = self.collection_search.text().casefold()
        for row in range(self.collection_table.rowCount()):
            self.collection_table.setRowHidden(row, query not in ' '.join(self.collection_table.item(row, col).text().casefold() for col in range(4)))

    def copy_collection_code(self):
        row = self.collection_table.currentRow()
        if row >= 0: QApplication.clipboard().setText(self.collection_table.item(row, 3).text()); self.set_status('copied')

    def open_target_folder(self):
        if self.destination_path: QDesktopServices.openUrl(QUrl.fromLocalFile(self.destination_path))

    def closeEvent(self, event):
        if self.jobs: QMessageBox.information(self, APP_NAME, self.t('wait')); event.ignore(); return
        self.player.stop(); self.settings.sync(); event.accept()


def set_palette(app, theme='dark'):
    palette = QPalette()
    bg, fg, field = ('#1A1A1E', '#f0f0f5', '#1d1d22') if theme == 'dark' else ('#f3f3f6', '#202129', '#ffffff')
    for role, color in ((QPalette.ColorRole.Window, bg), (QPalette.ColorRole.WindowText, fg), (QPalette.ColorRole.Base, field),
                        (QPalette.ColorRole.Text, fg), (QPalette.ColorRole.Button, bg), (QPalette.ColorRole.ButtonText, fg),
                        (QPalette.ColorRole.Highlight, '#578c74'), (QPalette.ColorRole.HighlightedText, '#ffffff')):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)


set_dark_palette = set_palette


def main():
    app = QApplication.instance() or QApplication([]); app.setApplicationName(APP_NAME); app.setOrganizationName(APP_NAME); app.setStyle('Fusion')
    window = StudioWindow(); set_palette(app, window.theme); window.show(); return app.exec()
