from __future__ import annotations

import os

import psutil
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT
from app.ai.usage import AIUsageManager
from app.utils.config import RuntimeSettings, SettingsManager


class SettingsDialog(QDialog):
    def __init__(self, manager: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("AI Lightroom 设置")
        self.resize(640, 570)
        runtime = manager.runtime()
        self.usage = AIUsageManager(manager.store)

        tabs = QTabWidget()
        tabs.addTab(self._build_ai_tab(runtime), "AI")
        tabs.addTab(self._build_ai_advanced_tab(runtime), "AI 高级设置")
        tabs.addTab(self._build_budget_tab(), "AI 费用保护")
        tabs.addTab(self._build_performance_tab(runtime), "性能与导出")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _build_ai_tab(self, runtime: RuntimeSettings) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.provider = QComboBox()
        self.provider.addItem("自动（有 Key 使用 Gemini，否则离线 Mock）", "auto")
        self.provider.addItem("Gemini", "gemini")
        self.provider.addItem("离线 Mock", "mock")
        self.provider.setCurrentIndex(max(0, self.provider.findData(runtime.provider)))
        self.api_key = QLineEdit(self.manager.gemini_api_key())
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("未配置时使用离线 Mock")
        if os.getenv("GEMINI_API_KEY"):
            self.api_key.setEnabled(False)
            self.api_key.setToolTip("当前由 GEMINI_API_KEY 环境变量提供")
        self.model = QLineEdit(runtime.gemini_model)
        self.current_model = QLabel(runtime.gemini_model)
        self.reinspection = QCheckBox("AI 自动复检（一次编辑可能产生额外一次云端调用）")
        self.reinspection.setChecked(runtime.ai_reinspection)
        self.max_calls = QSpinBox()
        self.max_calls.setRange(1, 2)
        self.max_calls.setValue(runtime.max_vision_calls)
        form.addRow("AI Provider", self.provider)
        form.addRow("Gemini API Key", self.api_key)
        form.addRow("Gemini Model", self.model)
        form.addRow("当前实际模型", self.current_model)
        form.addRow("Automatic Reinspection", self.reinspection)
        form.addRow("单次命令最多视觉调用", self.max_calls)
        return tab

    def _build_ai_advanced_tab(self, runtime: RuntimeSettings) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        label = QLabel("系统提示词会作为每次 AI 规划的内置摄影原则。普通用户无需修改。")
        label.setWordWrap(True)
        self.system_prompt = QTextEdit(runtime.system_prompt)
        self.system_prompt.setAcceptRichText(False)
        self.system_prompt.setMinimumHeight(280)
        restore = QPushButton("恢复默认")
        restore.clicked.connect(lambda: self.system_prompt.setPlainText(DEFAULT_SYSTEM_PROMPT))
        layout.addWidget(label)
        layout.addWidget(self.system_prompt, 1)
        layout.addWidget(restore)
        return tab

    def _build_budget_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()
        status = self.usage.status()
        self.budget_mode = QComboBox()
        self.budget_mode.addItem("免费保护模式（默认，每日 20 次）", "free")
        self.budget_mode.addItem("自定义本地上限", "custom")
        self.budget_mode.addItem("禁用云端 AI", "disabled")
        self.budget_mode.setCurrentIndex(max(0, self.budget_mode.findData(status.mode)))
        self.custom_daily_limit = QSpinBox()
        self.custom_daily_limit.setRange(1, 10000)
        self.custom_daily_limit.setValue(max(1, status.daily_limit or 20))
        self.usage_label = QLabel(f"今天云端请求：{status.today_count} / {status.daily_limit}\n本月云端请求：{status.month_count}")
        self.usage_label.setWordWrap(True)
        form.addRow("模式", self.budget_mode)
        form.addRow("自定义每日上限", self.custom_daily_limit)
        form.addRow("本地计数", self.usage_label)
        note = QLabel("这是本地安全上限，并不代表 Google 官方实时剩余额度。达到上限后不会自动重试或继续发起云端请求。")
        note.setWordWrap(True)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addStretch()
        return tab

    def _build_performance_tab(self, runtime: RuntimeSettings) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.preview_size = QSpinBox()
        self.preview_size.setRange(640, 2048)
        self.preview_size.setSingleStep(128)
        self.preview_size.setSuffix(" px")
        self.preview_size.setValue(runtime.preview_size)
        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(1, 100)
        self.jpeg_quality.setValue(runtime.export_jpeg_quality)
        self.performance = QComboBox()
        self.performance.addItem("省电", "battery")
        self.performance.addItem("平衡", "balanced")
        self.performance.addItem("性能", "performance")
        self.performance.setCurrentIndex(max(0, self.performance.findData(runtime.performance_mode)))
        hardware = QLabel(f"CPU 逻辑线程：{psutil.cpu_count(logical=True) or '未知'}\n预览渲染：OpenCV / CPU；AI 请求在后台执行")
        hardware.setWordWrap(True)
        form.addRow("预览最长边", self.preview_size)
        form.addRow("默认 JPEG 质量", self.jpeg_quality)
        form.addRow("性能模式", self.performance)
        form.addRow("硬件", hardware)
        return tab

    def _save(self) -> None:
        runtime = RuntimeSettings(
            provider=self.provider.currentData(), gemini_model=self.model.text().strip() or "gemini-3.6-flash",
            preview_size=self.preview_size.value(), ai_reinspection=self.reinspection.isChecked(),
            max_vision_calls=self.max_calls.value(), system_prompt=self.system_prompt.toPlainText().strip() or DEFAULT_SYSTEM_PROMPT,
            export_jpeg_quality=self.jpeg_quality.value(), performance_mode=self.performance.currentData(),
        )
        try:
            self.manager.save(runtime, self.api_key.text())
            self.manager.store.setValue("ai/budget_mode", self.budget_mode.currentData())
            self.manager.store.setValue("ai/custom_daily_limit", self.custom_daily_limit.value())
            self.manager.store.sync()
        except RuntimeError as exc:
            QMessageBox.critical(self, "无法保存设置", str(exc))
            return
        self.accept()
