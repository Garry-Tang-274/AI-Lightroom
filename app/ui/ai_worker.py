from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, QRunnable, QSettings, Signal, Slot

from app.ai.errors import AIRequestError, error_from_exception
from app.ai.gemini_provider import GeminiProvider
from app.ai.mock_provider import MockProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.orchestrator import AIOrchestrator
from app.ai.usage import AIUsageManager
from app.core.editor_state import EditorState
from app.utils.config import RuntimeSettings


class AIWorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)


class AIEditWorker(QRunnable):
    def __init__(self, instruction: str, source_preview: np.ndarray, state: EditorState, history_summary: list[str], settings: RuntimeSettings, gemini_api_key: str, openai_api_key: str, selected_mask_id: str | None) -> None:
        super().__init__()
        self.instruction = instruction
        self.source_preview = source_preview
        self.state = state.snapshot()
        self.history_summary = history_summary
        self.settings = settings
        self.gemini_api_key = gemini_api_key
        self.openai_api_key = openai_api_key
        self.selected_mask_id = selected_mask_id
        self.signals = AIWorkerSignals()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        provider_key = self.gemini_api_key if self.settings.provider == "gemini" else self.openai_api_key
        use_cloud = self.settings.provider in {"gemini", "openai"} and bool(provider_key)
        provider_name = "Gemini" if self.settings.provider == "gemini" else "OpenAI"
        model = self.settings.active_model
        usage = AIUsageManager(QSettings("AI Lightroom", "AI Lightroom"))
        try:
            if self.settings.provider == "gemini" and use_cloud:
                provider = GeminiProvider(
                    self.gemini_api_key, self.settings.gemini_model,
                    system_prompt=self.settings.system_prompt,
                    on_request_started=lambda: usage.record_started_request("Gemini", self.settings.gemini_model),
                    on_result=lambda result, input_tokens, output_tokens, total_tokens: usage.record_result(
                        "Gemini", self.settings.gemini_model, result,
                        input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
                    ),
                )
            elif self.settings.provider == "openai" and use_cloud:
                provider = OpenAIProvider(
                    self.openai_api_key, self.settings.openai_model,
                    system_prompt=self.settings.system_prompt,
                    on_request_started=lambda: usage.record_started_request("OpenAI", self.settings.openai_model),
                    on_result=lambda result, input_tokens, output_tokens, total_tokens: usage.record_result(
                        "OpenAI", self.settings.openai_model, result,
                        input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
                    ),
                )
            else:
                provider = MockProvider()
            orchestrator = AIOrchestrator(
                provider, preview_size=self.settings.preview_size,
                reinspection_enabled=self.settings.ai_reinspection,
                max_vision_calls=self.settings.max_vision_calls,
            )
            result = orchestrator.process(self.instruction, self.source_preview, self.state, self.history_summary, self.selected_mask_id)
            if self._cancelled:
                raise AIRequestError("已取消本地等待", "取消只停止本地等待；已发出的云端请求可能仍计入调用。", provider=provider_name, model=model, request_sent=use_cloud)
        except Exception as exc:
            error = error_from_exception(exc, model=model, request_sent=use_cloud, provider=provider_name)
            if use_cloud and error.request_sent:
                usage.record_result(provider_name, model, error.category)
            self.signals.failed.emit(error)
            return
        self.signals.finished.emit(result)
