from __future__ import annotations

import html

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
    details_requested = Signal()

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
        self.details_button = QPushButton("查看调整详情")
        self.details_button.setEnabled(False)
        self.provider_label = QLabel("未配置 API Key 时自动使用离线 Mock")
        self.provider_label.setStyleSheet("color: #858b92; font-size: 9pt;")
        self.input.returnPressed.connect(self._submit)
        self.send_button.clicked.connect(self._submit)
        self.details_button.clicked.connect(self.details_requested)

        row = QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(self.send_button)
        layout.addWidget(title)
        layout.addWidget(self.provider_label)
        layout.addWidget(self.transcript, 1)
        layout.addWidget(self.details_button)
        layout.addLayout(row)

    def _submit(self) -> None:
        prompt = self.input.text().strip()
        if not prompt:
            return
        self.transcript.append(f"<b>你</b><br>{html.escape(prompt)}")
        self.input.clear()
        self.prompt_submitted.emit(prompt)

    def add_assistant_message(self, text: str) -> None:
        self.transcript.append(f"<br><b>AI Lightroom</b><br>{html.escape(text)}")

    def set_ready(self, ready: bool) -> None:
        self.input.setEnabled(ready)
        self.send_button.setEnabled(ready)

    def set_busy(self, busy: bool) -> None:
        self.set_ready(not busy)
        self.send_button.setText("分析中…" if busy else "应用")

    def set_result_info(self, provider: str, has_details: bool) -> None:
        self.provider_label.setText(f"本次规划：{provider}")
        self.details_button.setEnabled(has_details)
