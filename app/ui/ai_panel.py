from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget, QSizePolicy


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
    retry_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        self._ready = False
        self._busy = False
        title = QLabel("用语言调整照片")
        title.setObjectName("sectionTitle")
        self.provider_label = QLabel("选择 AI 服务后开始")
        self.provider_label.setWordWrap(True)
        self.provider_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.provider_label.setObjectName("muted")
        self.settings_button = QPushButton("设置")
        self.settings_button.clicked.connect(self.settings_requested)
        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setPlaceholderText("描述想要的色调，也告诉 AI 哪些部分要保留。\n\n例如：整体冷一点，天空稍暗，保持地面和白色主体的亮度。")
        self.transcript.document().setMaximumBlockCount(200)
        self.transcript.setMinimumWidth(0)
        self.transcript.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.input = PromptEdit()
        self.input.setPlaceholderText("例如：天空压暗一点，但地面不要变。\nCtrl+Enter 发送，Enter 换行")
        self.input.setMinimumHeight(116)
        self.input.setMaximumHeight(220)
        self.input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.input.textChanged.connect(self._resize_input)
        self.send_button = QPushButton("发送指令")
        self.send_button.setObjectName("accentButton")
        self.cancel_button = QPushButton("取消等待")
        self.cancel_button.setEnabled(False)
        self.retry_button = QPushButton("重新尝试")
        self.retry_button.setEnabled(False)
        self.details_button = QPushButton("调整详情")
        self.details_button.setEnabled(False)
        self.usage_button = QPushButton("使用记录")
        self.hint = QLabel("Ctrl+Enter 发送 · Enter 换行")
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        self.input.submit_requested.connect(self._submit)
        self.send_button.clicked.connect(self._submit)
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.retry_button.clicked.connect(self.retry_requested)
        self.details_button.clicked.connect(self.details_requested)
        self.usage_button.clicked.connect(self.usage_requested)

        action_row = QHBoxLayout()
        title_row = QHBoxLayout()
        title_row.addWidget(title, 1)
        title_row.addWidget(self.settings_button)
        detail_row = QHBoxLayout()
        detail_row.addWidget(self.details_button)
        detail_row.addWidget(self.usage_button)
        detail_row.addStretch()
        action_row.addWidget(self.retry_button)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.send_button, 1)
        layout.addLayout(title_row)
        layout.addWidget(self.provider_label)
        layout.addWidget(self.transcript, 1)
        layout.addLayout(detail_row)
        layout.addWidget(self.input)
        layout.addWidget(self.hint)
        layout.addLayout(action_row)
        self.retry_button.hide()
        self.cancel_button.hide()

    def _resize_input(self) -> None:
        lines = min(8, max(4, self.input.document().blockCount()))
        height = self.input.fontMetrics().lineSpacing() * lines + 24
        self.input.setFixedHeight(min(220, max(116, height)))
        self.send_button.setEnabled(self._ready and not self._busy and bool(self.input.toPlainText().strip()))

    def _submit(self) -> None:
        prompt = self.input.toPlainText().strip()
        if not prompt or not self.input.isEnabled() or self._busy:
            return
        self.transcript.append(f"<b>你</b><br>{html.escape(prompt).replace(chr(10), '<br>')}")
        self.input.clear()
        self.prompt_submitted.emit(prompt)

    def add_assistant_message(self, text: str) -> None:
        self.transcript.append(f"<br><b>AI Lightroom</b><br>{html.escape(text).replace(chr(10), '<br>')}")

    def set_ready(self, ready: bool) -> None:
        self._ready = ready
        self.input.setEnabled(ready and not self._busy)
        self.send_button.setEnabled(ready and not self._busy and bool(self.input.toPlainText().strip()))

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.set_ready(self._ready)
        self.cancel_button.setEnabled(busy)
        self.cancel_button.setVisible(busy)
        self.settings_button.setEnabled(not busy)
        self.retry_button.setEnabled(not busy)
        self.send_button.setText("正在分析…" if busy else "发送指令")

    def set_provider_status(self, text: str) -> None:
        self.provider_label.setText(f"AI：{text}")
        is_warning = "Mock" in text or text.lstrip().startswith("⚠")
        color = "#e7b467" if is_warning else "#a3b8c9"
        self.provider_label.setStyleSheet(f"color: {color};")

    def set_result_info(self, provider: str, has_details: bool) -> None:
        self.set_provider_status(f"本次规划：{provider}")
        self.details_button.setEnabled(has_details)

    def set_details_available(self, available: bool) -> None:
        self.details_button.setEnabled(available)

    def set_retry_available(self, available: bool) -> None:
        self.retry_button.setEnabled(available)
        self.retry_button.setVisible(available)

    def clear_session(self) -> None:
        self.transcript.clear()
        self.set_details_available(False)
        self.set_retry_available(False)
