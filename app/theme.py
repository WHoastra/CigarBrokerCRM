"""Dark professional theme for CigarBrokerCRM - Wood Term / Whoastra style."""

# Palette constants — the single source for code that colors things outside
# the stylesheet (charts, inline labels).
GOLD = "#c9a84c"
BG_DARK = "#1a1a2e"
TEXT_COLOR = "#e0e0e0"
GRID_COLOR = "#2a2a4a"

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #1a1a2e;
    color: #e0e0e0;
}
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", "Consolas", sans-serif;
    font-size: 13px;
}
QLabel {
    color: #e0e0e0;
    background: transparent;
}
QLabel#sectionHeader {
    font-size: 18px;
    font-weight: bold;
    color: #c9a84c;
    padding: 8px 0;
}
QLabel#statLabel {
    font-size: 24px;
    font-weight: bold;
    color: #c9a84c;
}

/* Sidebar */
QListWidget#sidebar {
    background-color: #12122a;
    border: none;
    border-right: 2px solid #c9a84c;
    padding: 5px;
    font-size: 14px;
    outline: none;
}
QListWidget#sidebar::item {
    padding: 14px 20px;
    border-radius: 6px;
    margin: 2px 4px;
    color: #b0b0b0;
}
QListWidget#sidebar::item:selected {
    background-color: #2a2a4a;
    color: #c9a84c;
    font-weight: bold;
}
QListWidget#sidebar::item:hover {
    background-color: #22223a;
    color: #e0e0e0;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #16162e;
    alternate-background-color: #1c1c38;
    gridline-color: #2a2a4a;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    selection-background-color: #3a3a5c;
    selection-color: #c9a84c;
    color: #e0e0e0;
}
QHeaderView::section {
    background-color: #12122a;
    color: #c9a84c;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #c9a84c;
    font-weight: bold;
    font-size: 12px;
}

/* Buttons */
QPushButton {
    background-color: #2a2a4a;
    color: #e0e0e0;
    border: 1px solid #3a3a5c;
    padding: 8px 18px;
    border-radius: 4px;
    font-weight: 500;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #3a3a5c;
    border-color: #c9a84c;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #4a4a6c;
}
QPushButton#primaryBtn {
    background-color: #c9a84c;
    color: #1a1a2e;
    border: none;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #d4b85c;
}
QPushButton#dangerBtn {
    background-color: #8b2252;
    color: #ffffff;
    border: none;
}
QPushButton#dangerBtn:hover {
    background-color: #a52a6a;
}

/* Input fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #12122a;
    color: #e0e0e0;
    border: 1px solid #3a3a5c;
    padding: 8px 12px;
    border-radius: 4px;
    selection-background-color: #c9a84c;
    selection-color: #1a1a2e;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #c9a84c;
}
QLineEdit#searchField {
    padding: 10px 14px;
    font-size: 14px;
    border: 2px solid #3a3a5c;
}
QLineEdit#searchField:focus {
    border-color: #c9a84c;
}

/* ComboBox */
QComboBox {
    background-color: #12122a;
    color: #e0e0e0;
    border: 1px solid #3a3a5c;
    padding: 8px 12px;
    border-radius: 4px;
    min-height: 20px;
}
QComboBox:hover {
    border-color: #c9a84c;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #c9a84c;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #12122a;
    color: #e0e0e0;
    selection-background-color: #3a3a5c;
    selection-color: #c9a84c;
    border: 1px solid #3a3a5c;
}

/* DateEdit */
QDateEdit {
    background-color: #12122a;
    color: #e0e0e0;
    border: 1px solid #3a3a5c;
    padding: 8px 12px;
    border-radius: 4px;
}
QDateEdit:focus {
    border-color: #c9a84c;
}

/* Scrollbar */
QScrollBar:vertical {
    background-color: #12122a;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #3a3a5c;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #c9a84c;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: #12122a;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #3a3a5c;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #c9a84c;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #2a2a4a;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #12122a;
    color: #b0b0b0;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #c9a84c;
    border-bottom: 2px solid #c9a84c;
}
QTabBar::tab:hover {
    color: #e0e0e0;
    background-color: #1c1c38;
}

/* Group Box */
QGroupBox {
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #c9a84c;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* Splitter */
QSplitter::handle {
    background-color: #2a2a4a;
}

/* MessageBox and dialogs */
QMessageBox {
    background-color: #1a1a2e;
}
QMessageBox QLabel {
    color: #e0e0e0;
}

/* Status bar */
QStatusBar {
    background-color: #12122a;
    color: #888;
    border-top: 1px solid #2a2a4a;
}

/* Menu */
QMenuBar {
    background-color: #12122a;
    color: #e0e0e0;
    border-bottom: 1px solid #2a2a4a;
}
QMenuBar::item:selected {
    background-color: #2a2a4a;
    color: #c9a84c;
}
QMenu {
    background-color: #1a1a2e;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
}
QMenu::item:selected {
    background-color: #3a3a5c;
    color: #c9a84c;
}
QMenu::separator {
    height: 1px;
    background-color: #2a2a4a;
    margin: 4px 0;
}

/* ToolTip */
QToolTip {
    background-color: #2a2a4a;
    color: #e0e0e0;
    border: 1px solid #c9a84c;
    padding: 4px 8px;
    border-radius: 3px;
}

/* Progress Bar */
QProgressBar {
    background-color: #12122a;
    border: 1px solid #3a3a5c;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
}
QProgressBar::chunk {
    background-color: #c9a84c;
    border-radius: 3px;
}

/* Calendar popup */
QCalendarWidget {
    background-color: #1a1a2e;
}
QCalendarWidget QToolButton {
    color: #e0e0e0;
    background-color: #2a2a4a;
    border: none;
    padding: 4px;
}
QCalendarWidget QMenu {
    background-color: #1a1a2e;
    color: #e0e0e0;
}
"""
