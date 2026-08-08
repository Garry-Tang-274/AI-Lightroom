from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, QRunnable, QSettings, Signal, Slot

from app.ai.errors import AIRequestError, error_from_exception
from app.ai.gemini_provider import GeminiProvider
from app.ai.mock_provider import MockProvider
from app.ai.orchestrator import AIOrchestrator
from app.ai.usage import AIUsageManager
from app.core.editor_state import EditorState
from app.utils.config import RuntimeSettings


class AIWorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)


class AIEditWorker(QRunnable):
    def __init__(self, instruction: str, source_preview: np.ndarray, state: EditorState, history_summary: list[str], settings: RuntimeSettings, api_key: str, selected_mask_id: str | None) -> None:
        super().__init__()
        self.instruction = instruction
        self.source_preview = source_preview
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
        use_gemini = self.settings.provider != "mock" and bool(self.api_key)
        usage = AIUsageManager(QSettings("AI Lightroom", "AI Lightroom"))
        try:
            provider = (
                GeminiProvider(
                    self.api_key, self.settings.gemini_model,
                    system_prompt=self.settings.system_prompt,
                    on_request_started=lambda: usage.record_started_request("Gemini", self.settings.gemini_model),
                    on_result=lambda result, input_tokens, output_tokens, total_tokens: usage.record_result(
                        "Gemini", self.settings.gemini_model, result,
                        input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
                    ),
                )
                if use_gemini else MockProvider()
            )
            orchestrator = AIOrchestrator(
                provider, preview_size=self.settings.preview_size,
                reinspection_enabled=self.settings.ai_reinspection,
                max_vision_calls=self.settings.max_vision_calls,
            )
            result = orchestrator.process(self.instruction, self.source_preview, self.state, self.history_summary, self.selected_mask_id)
            if self._cancelled:
                raise AIRequestError("已取消本地等待", "取消只停止本地等待；已发出的云端请求可能仍计入调用。", model=self.settings.gemini_model, request_sent=use_gemini)
        except Exception as exc:
            error = error_from_exception(exc, model=self.settings.gemini_model, request_sent=use_gemini)
            if use_gemini and error.request_sent:
                usage.record_result("Gemini", self.settings.gemini_model, error.category)
            self.signals.failed.emit(error)
            return
        self.signals.finished.emit(result)
