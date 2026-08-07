from __future__ import annotations

import os

import psutil
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.utils.config import RuntimeSettings, SettingsManager


class SettingsDialog(QDialog):
    def __init__(self, manager: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("AI Lightroom 设置")
        self.resize(560, 430)
        runtime = manager.runtime()

        tabs = QTabWidget()
        ai_tab = QWidget()
        ai_form = QFormLayout(ai_tab)
        self.provider = QComboBox()
        self.provider.addItem("自动（有 Key 用 Gemini，否则离线 Mock）", "auto")
        self.provider.addItem("Gemini", "gemini")
        self.provider.addItem("离线 Mock", "mock")
        self.provider.setCurrentIndex(max(0, self.provider.findData(runtime.provider)))
        self.api_key = QLineEdit(manager.gemini_api_key())
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("未配置时使用离线 Mock")
        if os.getenv("GEMINI_API_KEY"):
            self.api_key.setEnabled(False)
            self.api_key.setToolTip("当前由 GEMINI_API_KEY 环境变量提供")
        self.model = QLineEdit(runtime.gemini_model)
        self.reinspection = QCheckBox("允许 AI 在必要时复查渲染结果")
        self.reinspection.setChecked(runtime.ai_reinspection)
        self.max_calls = QSpinBox()
        self.max_calls.setRange(1, 2)
        self.max_calls.setValue(runtime.max_vision_calls)
        ai_form.addRow("AI Provider", self.provider)
        ai_form.addRow("Gemini API Key", self.api_key)
        ai_form.addRow("Gemini Model", self.model)
        ai_form.addRow("视觉复查", self.reinspection)
        ai_form.addRow("单次命令最多视觉调用", self.max_calls)

        performance_tab = QWidget()
        performance_form = QFormLayout(performance_tab)
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
        performance_form.addRow("预览最长边", self.preview_size)
        performance_form.addRow("默认 JPEG 质量", self.jpeg_quality)
        performance_form.addRow("性能模式", self.performance)
        performance_form.addRow("硬件", hardware)

        tabs.addTab(ai_tab, "AI")
        tabs.addTab(performance_tab, "性能与导出")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _save(self) -> None:
        runtime = RuntimeSettings(
            provider=self.provider.currentData(),
            gemini_model=self.model.text().strip() or "gemini-3.6-flash",
            preview_size=self.preview_size.value(),
            ai_reinspection=self.reinspection.isChecked(),
            max_vision_calls=self.max_calls.value(),
            export_jpeg_quality=self.jpeg_quality.value(),
            performance_mode=self.performance.currentData(),
        )
        try:
            self.manager.save(runtime, self.api_key.text())
        except RuntimeError as exc:
            QMessageBox.critical(self, "无法保存设置", str(exc))
            return
        self.accept()

