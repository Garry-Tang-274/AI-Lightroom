from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget


class PromptEdit(QPlainTextEdit):
    submit_requested = Signal()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self.submit_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class AIPanel(QWidget):
    prompt_submitted = Signal(str)
    details_requested = Signal()
    cancel_requested = Signal()
    usage_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        title = QLabel("AI Assistant")
        title.setStyleSheet("font-size: 12pt; font-weight: 600;")
        self.provider_label = QLabel("AI：Offline Mock（未配置 API Key）")
        self.provider_label.setStyleSheet("color: #858b92; font-size: 9pt;")
        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setPlaceholderText("打开一张照片后，用自然语言描述希望得到的效果。")
        self.input = PromptEdit()
        self.input.setPlaceholderText("例如：天空压暗一点，但地面不要变。\nCtrl+Enter 发送，Enter 换行")
        self.input.setMinimumHeight(96)
        self.input.setMaximumHeight(180)
        self.input.textChanged.connect(self._resize_input)
        self.send_button = QPushButton("发送")
        self.send_button.setObjectName("accentButton")
        self.cancel_button = QPushButton("取消等待")
        self.cancel_button.setEnabled(False)
        self.details_button = QPushButton("查看调整详情")
        self.details_button.setEnabled(False)
        self.usage_button = QPushButton("AI 使用记录")
        self.hint = QLabel("Ctrl+Enter 发送 · Enter 换行")
        self.hint.setStyleSheet("color: #858b92; font-size: 9pt;")
        self.input.submit_requested.connect(self._submit)
        self.send_button.clicked.connect(self._submit)
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.details_button.clicked.connect(self.details_requested)
        self.usage_button.clicked.connect(self.usage_requested)

        action_row = QHBoxLayout()
        action_row.addWidget(self.details_button)
        action_row.addWidget(self.usage_button)
        action_row.addStretch()
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.send_button)
        layout.addWidget(title)
        layout.addWidget(self.provider_label)
        layout.addWidget(self.transcript, 1)
        layout.addWidget(self.input)
        layout.addWidget(self.hint)
        layout.addLayout(action_row)

    def _resize_input(self) -> None:
        lines = min(8, max(4, self.input.document().blockCount()))
        height = self.input.fontMetrics().lineSpacing() * lines + 24
        self.input.setFixedHeight(min(180, max(96, height)))

    def _submit(self) -> None:
        prompt = self.input.toPlainText().strip()
        if not prompt or not self.input.isEnabled():
            return
        self.transcript.append(f"<b>你</b><br>{html.escape(prompt).replace(chr(10), '<br>')}")
        self.input.clear()
        self.prompt_submitted.emit(prompt)

    def add_assistant_message(self, text: str) -> None:
        self.transcript.append(f"<br><b>AI Lightroom</b><br>{html.escape(text).replace(chr(10), '<br>')}")

    def set_ready(self, ready: bool) -> None:
        self.input.setEnabled(ready)
        self.send_button.setEnabled(ready)

    def set_busy(self, busy: bool) -> None:
        self.set_ready(not busy)
        self.cancel_button.setEnabled(busy)
        self.send_button.setText("分析中…" if busy else "发送")

    def set_provider_status(self, text: str) -> None:
        self.provider_label.setText(f"AI：{text}")

    def set_result_info(self, provider: str, has_details: bool) -> None:
        self.set_provider_status(f"本次规划：{provider}")
        self.details_button.setEnabled(has_details)

    def set_details_available(self, available: bool) -> None:
        self.details_button.setEnabled(available)
