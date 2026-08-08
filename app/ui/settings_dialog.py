from __future__ import annotations

from dataclasses import replace
import os

import psutil
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.ai.provider_registry import provider_registry
from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT
from app.ai.usage import AIUsageManager
from app.ui.provider_test_worker import ProviderConnectionWorker
from app.ui.jarvisart_worker import JarvisArtControlWorker
from app.utils.config import RuntimeSettings, SettingsManager


class SettingsDialog(QDialog):
    def __init__(self, manager: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.runtime = manager.runtime()
        self.usage = AIUsageManager(manager.store)
        self._drafts: dict[str, tuple[object, str]] = {}
        self._connection_worker = None
        self._jarvisart_worker = None
        self.setWindowTitle("AI Lightroom 设置")
        self.resize(680, 610)

        tabs = QTabWidget()
        tabs.addTab(self._build_ai_tab(), "AI Providers")
        tabs.addTab(self._build_ai_advanced_tab(), "AI Advanced")
        tabs.addTab(self._build_budget_tab(), "API Cost Protection")
        tabs.addTab(self._build_performance_tab(), "Performance & Export")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _build_ai_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()
        self.provider = QComboBox()
        for descriptor in provider_registry.descriptors():
            self.provider.addItem(descriptor.display_name, descriptor.id)
        self.provider.setCurrentIndex(max(0, self.provider.findData(self.runtime.provider)))
        self.provider.currentIndexChanged.connect(self._provider_changed)
        self.provider_description = QLabel()
        self.provider_description.setWordWrap(True)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("使用自己的 API Key；不会写入项目文件")
        self.model = QLineEdit()
        self.custom_name = QLineEdit()
        self.custom_name.setPlaceholderText("例如：本地 Ollama / OpenRouter / 公司网关")
        self.base_url = QLineEdit()
        self.base_url.setPlaceholderText("https://…/v1")
        self.custom_vision = QCheckBox("服务支持 Vision / 图片输入")
        self.custom_structured = QCheckBox("服务支持 JSON structured output")
        self.custom_organization = QLineEdit()
        self.custom_organization.setPlaceholderText("可选：organization / project")
        self.custom_headers = QLineEdit()
        self.custom_headers.setPlaceholderText('可选 JSON，例如 {"X-Client": "AI-Lightroom"}')
        self.jarvisart_mode = QComboBox()
        self.jarvisart_mode.addItem("Local GGUF（主力本地推理）", "real")
        self.jarvisart_mode.addItem("Mock Native（仅开发测试；不会分析图片）", "mock")
        self.jarvisart_status = QLabel()
        self.jarvisart_status.setWordWrap(True)
        self.jarvisart_root = QLineEdit()
        self.jarvisart_root.setPlaceholderText("可选：自动检测相邻 JarvisArt 安装或环境变量")
        self.jarvisart_endpoint = QLineEdit()
        self.jarvisart_endpoint.setPlaceholderText("http://127.0.0.1:8765")
        self.jarvisart_auto_start = QCheckBox("首次 JarvisArt 请求时自动启动本地服务")
        self.jarvisart_start = QPushButton("启动 JarvisArt")
        self.jarvisart_stop = QPushButton("停止并释放显存")
        self.jarvisart_start.clicked.connect(lambda: self._control_jarvisart("start"))
        self.jarvisart_stop.clicked.connect(lambda: self._control_jarvisart("stop"))
        self.reinspection = QCheckBox("AI 自动复检（默认关闭；开启时一次命令最多可能额外调用一次）")
        self.reinspection.setChecked(self.runtime.ai_reinspection)
        self.max_calls = QSpinBox()
        self.max_calls.setRange(1, 2)
        self.max_calls.setValue(self.runtime.max_vision_calls)
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self._test_connection)
        self.capability_label = QLabel()
        self.capability_label.setWordWrap(True)
        form.addRow("AI Provider", self.provider)
        form.addRow("说明", self.provider_description)
        form.addRow("API Key", self.api_key)
        form.addRow("Model ID", self.model)
        form.addRow("Provider 名称（Custom）", self.custom_name)
        form.addRow("Base URL（OpenAI-compatible）", self.base_url)
        form.addRow("Custom 能力", self.custom_vision)
        form.addRow("", self.custom_structured)
        form.addRow("Organization / Project（Custom）", self.custom_organization)
        form.addRow("Custom Headers（JSON）", self.custom_headers)
        form.addRow("JarvisArt 运行模式", self.jarvisart_mode)
        form.addRow("JarvisArt 状态", self.jarvisart_status)
        form.addRow("JarvisArt 根目录", self.jarvisart_root)
        form.addRow("JarvisArt Endpoint", self.jarvisart_endpoint)
        form.addRow("", self.jarvisart_auto_start)
        jarvisart_actions = QWidget()
        jarvisart_actions_layout = QVBoxLayout(jarvisart_actions)
        jarvisart_actions_layout.setContentsMargins(0, 0, 0, 0)
        jarvisart_actions_layout.addWidget(self.jarvisart_start)
        jarvisart_actions_layout.addWidget(self.jarvisart_stop)
        form.addRow("JarvisArt 服务", jarvisart_actions)
        form.addRow("Automatic Reinspection", self.reinspection)
        form.addRow("单次命令最多视觉调用", self.max_calls)
        form.addRow("支持能力", self.capability_label)
        form.addRow("", self.test_button)
        advanced = QGroupBox("Endpoint 与能力说明")
        advanced.setCheckable(True)
        advanced.setChecked(False)
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.addWidget(QLabel("Qwen 默认使用北京 OpenAI-compatible 端点。若你的 Key 属于其他地域或工作空间，请替换为百炼控制台提供的 Base URL。Custom 仅适用于实际兼容 OpenAI Chat Completions 的服务。"))
        layout.addLayout(form)
        layout.addWidget(advanced)
        layout.addStretch()
        self._load_provider_fields()
        return tab

    def _provider_changed(self) -> None:
        self._store_current_draft()
        self._load_provider_fields()

    def _store_current_draft(self) -> None:
        if not hasattr(self, "api_key"):
            return
        previous_id = getattr(self, "_shown_provider_id", "")
        if not previous_id:
            return
        self._drafts[previous_id] = (
            provider_registry.make_config(
                previous_id, self.model.text(), self.base_url.text(), self.custom_name.text(),
                custom_vision=self.custom_vision.isChecked(),
                custom_structured_output=self.custom_structured.isChecked(),
                local_mode=str(self.jarvisart_mode.currentData()),
                custom_organization=self.custom_organization.text(), custom_headers=self.custom_headers.text(),
                jarvisart_root=self.jarvisart_root.text(), jarvisart_endpoint=self.jarvisart_endpoint.text(),
                jarvisart_auto_start=self.jarvisart_auto_start.isChecked(),
            ),
            self.api_key.text(),
        )

    def _load_provider_fields(self) -> None:
        provider_id = str(self.provider.currentData())
        descriptor = provider_registry.descriptor(provider_id)
        config, key = self._drafts.get(provider_id, (None, None))
        if config is None:
            if provider_id == self.runtime.provider:
                config = self.runtime.provider_config
            else:
                config = provider_registry.make_config(provider_id)
            key = self.manager.provider_api_key(provider_id) if descriptor.requires_api_key else ""
        self._shown_provider_id = provider_id
        self.model.setText(config.model)
        self.base_url.setText(config.base_url)
        self.custom_name.setText(config.display_name if descriptor.is_custom else "")
        self.api_key.setText(key or "")
        self.api_key.setEnabled(descriptor.requires_api_key and not bool(descriptor.api_key_environment and os.getenv(descriptor.api_key_environment)))
        if not self.api_key.isEnabled():
            self.api_key.setToolTip(f"当前由 {descriptor.api_key_environment} 环境变量提供")
        self.base_url.setEnabled(descriptor.capabilities.supports_custom_base_url)
        self.custom_name.setEnabled(descriptor.is_custom)
        self.custom_vision.setEnabled(descriptor.is_custom)
        self.custom_structured.setEnabled(descriptor.is_custom)
        self.custom_organization.setEnabled(descriptor.is_custom)
        self.custom_headers.setEnabled(descriptor.is_custom)
        self.custom_vision.setChecked(config.capabilities.supports_vision)
        self.custom_structured.setChecked(config.capabilities.supports_structured_output)
        self.custom_organization.setText(config.custom_organization if descriptor.is_custom else "")
        self.custom_headers.setText(config.custom_headers if descriptor.is_custom else "")
        self.jarvisart_mode.setCurrentIndex(max(0, self.jarvisart_mode.findData(config.local_mode)))
        is_jarvisart = provider_id == "jarvisart_local"
        self.jarvisart_mode.setEnabled(is_jarvisart)
        self.jarvisart_root.setEnabled(is_jarvisart)
        self.jarvisart_endpoint.setEnabled(is_jarvisart)
        self.jarvisart_auto_start.setEnabled(is_jarvisart)
        self.jarvisart_start.setEnabled(is_jarvisart and config.local_mode == "real")
        self.jarvisart_stop.setEnabled(is_jarvisart and config.local_mode == "real")
        self.jarvisart_root.setText(config.jarvisart_root)
        self.jarvisart_endpoint.setText(config.jarvisart_endpoint)
        self.jarvisart_auto_start.setChecked(config.jarvisart_auto_start)
        if is_jarvisart:
            if config.local_mode == "mock":
                status = "离线 Mock 测试模式：仅返回固定 fixture，不会读取、理解或分析当前照片。默认会阻止执行；仅供开发验证时手动确认。"
                self.provider_description.setText("Mock Native 不是 JarvisArt 推理。它不会分析照片，也不会产出可用于验收的调色建议。请选择 Local GGUF 或已配置的云端 Provider。")
            else:
                from app.ai.jarvisart.service import JarvisArtServiceManager
                detected = JarvisArtServiceManager(config.jarvisart_root, config.jarvisart_endpoint).status()
                status = f"{detected.state}：{detected.message}\n模型：{detected.model or 'JarvisArt-1208'}\n本地 GPU · 无云端费用 · 图片不会发送到云端"
                self.provider_description.setText("JarvisArt Local GGUF 使用你已安装的本地 llama.cpp / Qwen2-VL 服务处理图片；不会上传原图，也不使用云端 AI 额度。默认高清预览，可在性能设置中调整。")
            self.jarvisart_status.setText(status)
        else:
            self.provider_description.setText("离线 Provider，不发送照片或网络请求。" if not descriptor.requires_api_key else "使用用户自己的 API Key；仅发送缩小 JPEG Preview 和当前编辑状态。")
            self.jarvisart_status.setText("仅在选择 JarvisArt Local 时可用。")
        caps = config.capabilities
        self.capability_label.setText("Vision：{} · 多图：{} · JSON：{} · 图片生成：{} · 图片编辑：{}".format(*["支持" if value else "不支持" for value in (caps.supports_vision, caps.supports_multiple_images, caps.supports_structured_output, caps.supports_image_generation, caps.supports_image_editing)]))
        self.test_button.setEnabled(descriptor.requires_api_key)

    def _current_config(self):
        return provider_registry.make_config(
            str(self.provider.currentData()), self.model.text(), self.base_url.text(), self.custom_name.text(),
            custom_vision=self.custom_vision.isChecked(), custom_structured_output=self.custom_structured.isChecked(),
            local_mode=str(self.jarvisart_mode.currentData()),
            custom_organization=self.custom_organization.text(), custom_headers=self.custom_headers.text(),
            jarvisart_root=self.jarvisart_root.text(), jarvisart_endpoint=self.jarvisart_endpoint.text(),
            jarvisart_auto_start=self.jarvisart_auto_start.isChecked(),
        )

    def _test_connection(self) -> None:
        config = self._current_config()
        if not self.api_key.text().strip():
            QMessageBox.warning(self, "无法测试连接", "请先填写 API Key。")
            return
        if config.capabilities.supports_custom_base_url and not config.base_url:
            QMessageBox.warning(self, "无法测试连接", "请先填写 Base URL。")
            return
        self.test_button.setEnabled(False)
        self.test_button.setText("正在测试…")
        worker = ProviderConnectionWorker(config, self.api_key.text().strip(), self.system_prompt.toPlainText().strip() or DEFAULT_SYSTEM_PROMPT)
        self._connection_worker = worker
        worker.signals.succeeded.connect(self._connection_succeeded)
        worker.signals.failed.connect(self._connection_failed)
        QThreadPool.globalInstance().start(worker)

    def _control_jarvisart(self, action: str) -> None:
        if self._jarvisart_worker is not None:
            return
        self.jarvisart_start.setEnabled(False)
        self.jarvisart_stop.setEnabled(False)
        worker = JarvisArtControlWorker(self.jarvisart_root.text(), self.jarvisart_endpoint.text(), action)
        self._jarvisart_worker = worker
        worker.signals.finished.connect(self._jarvisart_control_finished)
        QThreadPool.globalInstance().start(worker)

    def _jarvisart_control_finished(self, status) -> None:
        self._jarvisart_worker = None
        self.jarvisart_status.setText(f"{status.state}：{status.message}\n模型：{status.model or 'JarvisArt-1208'}")
        is_real = self.provider.currentData() == "jarvisart_local" and self.jarvisart_mode.currentData() == "real"
        self.jarvisart_start.setEnabled(is_real)
        self.jarvisart_stop.setEnabled(is_real)

    def _connection_succeeded(self, message: str) -> None:
        self._connection_worker = None
        self.test_button.setEnabled(True)
        self.test_button.setText("测试连接")
        QMessageBox.information(self, "连接测试", message)

    def _connection_failed(self, error) -> None:
        self._connection_worker = None
        self.test_button.setEnabled(True)
        self.test_button.setText("测试连接")
        QMessageBox.critical(self, "连接测试失败", error.details() if hasattr(error, "details") else str(error))

    def _build_ai_advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("系统提示词仅定义摄影分析与确定性调色原则；模型只能输出当前 EditingPlan schema 支持的操作。"))
        self.system_prompt = QTextEdit(self.runtime.system_prompt)
        self.system_prompt.setAcceptRichText(False)
        self.system_prompt.setMinimumHeight(280)
        restore = QPushButton("恢复默认")
        restore.clicked.connect(lambda: self.system_prompt.setPlainText(DEFAULT_SYSTEM_PROMPT))
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
        form.addRow("模式", self.budget_mode)
        form.addRow("自定义每日上限", self.custom_daily_limit)
        layout.addLayout(form)
        layout.addWidget(QLabel("这是本地安全上限，不代表各云端服务的实时额度。连接测试是用户主动操作，也可能产生少量服务端用量。"))
        layout.addStretch()
        return tab

    def _build_performance_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.preview_quality = QComboBox()
        self.preview_quality.addItem("自动（本地 JarvisArt GGUF 默认高清；云端默认低清）", "auto")
        self.preview_quality.addItem("低清（响应更快、云端更省流量）", "low")
        self.preview_quality.addItem("高清（画布与 AI 视觉分析都使用更大预览）", "high")
        self.preview_quality.setCurrentIndex(max(0, self.preview_quality.findData(self.runtime.preview_quality)))
        self.preview_size = QSpinBox()
        self.preview_size.setRange(640, 2048)
        self.preview_size.setSingleStep(128)
        self.preview_size.setSuffix(" px")
        self.preview_size.setValue(self.runtime.preview_size)
        self.high_preview_size = QSpinBox()
        self.high_preview_size.setRange(2048, 4096)
        self.high_preview_size.setSingleStep(256)
        self.high_preview_size.setSuffix(" px")
        self.high_preview_size.setValue(self.runtime.high_preview_size)
        self.ai_preview_quality = QComboBox()
        self.ai_preview_quality.addItem("跟随画布预览", "follow_preview")
        self.ai_preview_quality.addItem("始终低清（云端节省流量）", "low")
        self.ai_preview_quality.addItem("始终高清（更精细的视觉分析）", "high")
        self.ai_preview_quality.setCurrentIndex(max(0, self.ai_preview_quality.findData(self.runtime.ai_preview_quality)))
        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(1, 100)
        self.jpeg_quality.setValue(self.runtime.export_jpeg_quality)
        self.performance = QComboBox()
        self.performance.addItem("省电", "battery")
        self.performance.addItem("平衡", "balanced")
        self.performance.addItem("性能", "performance")
        self.performance.setCurrentIndex(max(0, self.performance.findData(self.runtime.performance_mode)))
        form.addRow("预览质量", self.preview_quality)
        form.addRow("低清最长边", self.preview_size)
        form.addRow("高清最长边", self.high_preview_size)
        form.addRow("发送给 AI 的图像质量", self.ai_preview_quality)
        form.addRow("说明", QLabel("高清模式会重建更大的工作预览；需要视觉分析时，AI 收到同等质量的 JPEG 预览。增量文字指令可能不发送图片，以节省云端调用。"))
        form.addRow("默认 JPEG 质量", self.jpeg_quality)
        form.addRow("性能模式", self.performance)
        form.addRow("硬件", QLabel(f"CPU 逻辑线程：{psutil.cpu_count(logical=True) or '未知'}\nAI 请求在后台执行"))
        return tab

    def _save(self) -> None:
        self._store_current_draft()
        config, api_key = self._drafts[str(self.provider.currentData())]
        runtime = replace(
            self.runtime, provider=config.provider_id, model=config.model, base_url=config.base_url,
            custom_provider_name=self.custom_name.text().strip(),
            custom_supports_vision=self.custom_vision.isChecked(),
            custom_supports_structured_output=self.custom_structured.isChecked(),
            jarvisart_mode=str(self.jarvisart_mode.currentData()),
            custom_organization=self.custom_organization.text().strip(), custom_headers=self.custom_headers.text().strip(),
            jarvisart_root=self.jarvisart_root.text().strip(), jarvisart_endpoint=self.jarvisart_endpoint.text().strip() or "http://127.0.0.1:8765",
            jarvisart_auto_start=self.jarvisart_auto_start.isChecked(),
            preview_size=self.preview_size.value(), high_preview_size=self.high_preview_size.value(),
            preview_quality=str(self.preview_quality.currentData()), ai_preview_quality=str(self.ai_preview_quality.currentData()),
            ai_reinspection=self.reinspection.isChecked(), max_vision_calls=self.max_calls.value(),
            system_prompt=self.system_prompt.toPlainText().strip() or DEFAULT_SYSTEM_PROMPT,
            export_jpeg_quality=self.jpeg_quality.value(), performance_mode=self.performance.currentData(),
        )
        try:
            self.manager.save(runtime, api_key)
            self.manager.store.setValue("ai/budget_mode", self.budget_mode.currentData())
            self.manager.store.setValue("ai/custom_daily_limit", self.custom_daily_limit.value())
            self.manager.store.sync()
        except RuntimeError as exc:
            QMessageBox.critical(self, "无法保存设置", str(exc))
            return
        self.accept()
