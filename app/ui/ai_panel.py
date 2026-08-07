from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class AIPanel(QWidget):
    prompt_submitted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        title = QLabel("AI Assistant")
        title.setStyleSheet("font-size: 12pt; font-weight: 600;")
        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setPlaceholderText("打开一张照片，然后用自然语言描述你想要的效果。")
        self.input = QLineEdit()
        self.input.setPlaceholderText("例如：天空压暗一点，但地面不要变")
        self.send_button = QPushButton("应用")
        self.send_button.setObjectName("accentButton")
        self.input.returnPressed.connect(self._submit)
        self.send_button.clicked.connect(self._submit)

        row = QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(self.send_button)
        layout.addWidget(title)
        layout.addWidget(self.transcript, 1)
        layout.addLayout(row)

    def _submit(self) -> None:
        prompt = self.input.text().strip()
        if not prompt:
            return
        self.transcript.append(f"<b>你</b><br>{prompt}")
        self.input.clear()
        self.prompt_submitted.emit(prompt)

    def add_assistant_message(self, text: str) -> None:
        self.transcript.append(f"<br><b>AI Lightroom</b><br>{text}")

    def set_ready(self, ready: bool) -> None:
        self.input.setEnabled(ready)
        self.send_button.setEnabled(ready)

