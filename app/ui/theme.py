from __future__ import annotations


APP_STYLESHEET = """
QWidget {
    background: #202225;
    color: #d8dadd;
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 10pt;
}
QMainWindow, QMenuBar, QMenu { background: #1b1d1f; }
QMenuBar::item:selected, QMenu::item:selected { background: #3a3e43; }
QToolBar { background: #24272a; border-bottom: 1px solid #111; spacing: 6px; }
QToolButton, QPushButton {
    background: #34383d;
    border: 1px solid #484d53;
    border-radius: 4px;
    padding: 5px 10px;
}
QToolButton:hover, QPushButton:hover { background: #41464c; }
QToolButton:pressed, QPushButton:pressed { background: #2a2d31; }
QPushButton#accentButton { background: #246fa8; border-color: #3188c7; }
QSplitter::handle { background: #111315; }
QTabWidget::pane { border: 1px solid #303338; }
QTabBar::tab { background: #292c30; padding: 7px 12px; }
QTabBar::tab:selected { background: #35393e; color: white; }
QGroupBox {
    border: 1px solid #363a3f;
    border-radius: 4px;
    margin-top: 9px;
    padding-top: 7px;
    font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QSlider::groove:horizontal { background: #43484e; height: 4px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #4a91c7; }
QSlider::handle:horizontal { background: #e5e7e9; width: 12px; margin: -5px 0; border-radius: 6px; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #17191b;
    border: 1px solid #3c4146;
    border-radius: 4px;
    padding: 4px;
    selection-background-color: #246fa8;
}
QScrollBar:vertical { background: #202225; width: 10px; }
QScrollBar::handle:vertical { background: #4a4f55; min-height: 24px; border-radius: 4px; }
QStatusBar { background: #181a1c; color: #aeb3b8; }
QListWidget { background: #191b1e; border: none; }
QListWidget::item { padding: 6px; }
QListWidget::item:selected { background: #2d5d7d; }
"""
