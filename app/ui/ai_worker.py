from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, QRunnable, QSettings, Signal, Slot

from app.ai.errors import AIRequestError, error_from_exception
from app.ai.orchestrator import AIOrchestrator
from app.ai.provider_registry import provider_registry
from app.ai.usage import AIUsageManager
from app.core.editor_state import EditorState
from app.utils.config import RuntimeSettings
from app.utils.io_utils import make_preview


class AIWorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)


class AIEditWorker(QRunnable):
    def __init__(self, instruction: str, source_pixels: np.ndarray, state: EditorState, history_summary: list[str], settings: RuntimeSettings, api_key: str, selected_mask_id: str | None) -> None:
        super().__init__()
        self.instruction = instruction
        # Keep the original image pixels in the worker only.  The UI can stay
        # responsive on a low-quality working preview while this worker creates
        # the separately configured image sent to an AI provider.
        self.source_pixels = source_pixels
        self.state = state.snapshot()
        self.history_summary = history_summary
        self.settings = settings
        self.api_key = api_key
        self.selected_mask_id = selected_mask_id
        self.signals = AIWorkerSignals()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        config = self.settings.provider_config
        descriptor = provider_registry.descriptor(config.provider_id)
        use_cloud = descriptor.requires_api_key and bool(self.api_key)
        provider_name = config.display_name
        model = config.model
        usage = AIUsageManager(QSettings("AI Lightroom", "AI Lightroom"))
        try:
            provider = provider_registry.create(
                config, self.api_key,
                system_prompt=self.settings.system_prompt,
                on_request_started=lambda: usage.record_started_request(provider_name, model),
                on_result=lambda result, input_tokens, output_tokens, total_tokens: usage.record_result(
                    provider_name, model, result,
                    input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
                ),
            )
            analysis_source = make_preview(self.source_pixels, self.settings.active_ai_preview_size)
            orchestrator = AIOrchestrator(
                provider, preview_size=self.settings.active_ai_preview_size,
                reinspection_enabled=self.settings.ai_reinspection,
                max_vision_calls=self.settings.max_vision_calls,
            )
            result = orchestrator.process(self.instruction, analysis_source, self.state, self.history_summary, self.selected_mask_id)
            if self._cancelled:
                raise AIRequestError("已取消本地等待", "取消只停止本地等待；已发出的云端请求可能仍计入调用。", provider=provider_name, model=model, request_sent=use_cloud)
        except Exception as exc:
            error = error_from_exception(exc, model=model, request_sent=use_cloud, provider=provider_name)
            if use_cloud and error.request_sent:
                usage.record_result(provider_name, model, error.category)
            self.signals.failed.emit(error)
            return
        self.signals.finished.emit(result)
