from __future__ import annotations


# A neutral workspace keeps the photograph, rather than the chrome, in focus.
APP_STYLESHEET = """
QWidget { background: #202327; color: #dce0e5; font-family: "Segoe UI", "Microsoft YaHei UI"; font-size: 10pt; }
QMainWindow, QMenuBar, QMenu { background: #191c20; }
QMenuBar { padding: 3px 8px; }
QMenuBar::item { padding: 4px 10px; background: transparent; }
QMenuBar::item:selected, QMenu::item:selected { background: #303c48; }
QMenu { border: 1px solid #414850; padding: 6px; }
QMenu::item { padding: 7px 24px; }
QToolBar { background: #20252b; border: none; border-bottom: 1px solid #343b43; spacing: 5px; padding: 7px; }
QToolBar::separator { width: 1px; background: #3a424b; margin: 4px 7px; }
QToolButton, QPushButton { background: #2b323a; border: 1px solid #414b56; border-radius: 5px; padding: 6px 11px; }
QToolButton:hover, QPushButton:hover { background: #384551; border-color: #6086a5; }
QToolButton:pressed, QPushButton:pressed, QToolButton:checked, QPushButton:checked { background: #214560; border-color: #6eafd8; }
QToolButton:disabled, QPushButton:disabled { color: #68717b; background: #24292f; border-color: #30363d; }
QPushButton#accentButton, QToolButton#accentButton { background: #287db4; border-color: #449ed4; color: #ffffff; font-weight: 600; }
QPushButton#accentButton:hover, QToolButton#accentButton:hover { background: #3295cd; }
QPushButton#accentButton:disabled { background: #273b49; border-color: #324955; color: #7e929f; }
QSplitter::handle { background: #14171b; }
QSplitter::handle:hover { background: #477b9b; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #20252b; color: #9ea9b6; padding: 10px 17px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #f2f7fb; border-bottom-color: #69b7e6; background: #282f37; }
QTabBar::tab:hover { color: #e9f0f5; background: #2b333c; }
QGroupBox { border: 1px solid #353e47; border-radius: 5px; margin-top: 13px; padding: 12px 7px 7px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #ecf0f4; }
QSlider::groove:horizontal { background: #424d59; height: 3px; border-radius: 1px; }
QSlider::sub-page:horizontal { background: #6ca6cf; }
QSlider::handle:horizontal { background: #e1edf5; border: 1px solid #a6bfce; width: 11px; margin: -5px 0; border-radius: 6px; }
QSlider::handle:horizontal:hover { background: white; border-color: #74c9ff; }
QLineEdit, QTextEdit, QTextBrowser, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #181d23; border: 1px solid #3b4652; border-radius: 5px; padding: 6px; selection-background-color: #33678c;
}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #65abd8; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled { color: #697581; }
QComboBox { padding-right: 22px; min-height: 21px; }
QComboBox QAbstractItemView { background: #222a33; selection-background-color: #325872; }
QScrollArea { border: none; }
QScrollBar:vertical { background: #20252b; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #495663; min-height: 30px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #71889c; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QStatusBar { background: #181d23; color: #a5b2bf; padding: 3px; }
QStatusBar::item { border: none; }
QListWidget { background: #1c2127; border: none; outline: none; }
QListWidget::item { padding: 9px 8px; border-radius: 4px; }
QListWidget::item:hover { background: #2b353f; }
QListWidget::item:selected { background: #28475d; color: #edf7ff; }
QLabel#sectionTitle { font-size: 12pt; font-weight: 600; color: #f0f4f8; }
QLabel#muted { color: #a3afbb; }
QLabel#mutedLabel { color: #a3afbb; }
QLabel#panelTitle { font-size: 12pt; font-weight: 600; }
QToolButton#sectionHeader { background: transparent; border: none; border-bottom: 1px solid #343e48; border-radius: 0; text-align: left; padding: 10px 5px; font-weight: 600; }
QToolButton#sectionHeader:hover { background: #2c3540; }
QLabel#canvasInfo { color: #b0bdc8; background: transparent; padding: 7px 10px; }
QWidget#canvasHeader { background: #1c2229; border-bottom: 1px solid #303942; }
QToolTip { background: #263747; color: #f4f7fa; border: 1px solid #54728a; padding: 5px; }
"""
