from __future__ import annotations

import traceback

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.ai.gemini_provider import GeminiProvider
from app.ai.mock_provider import MockProvider
from app.ai.orchestrator import AIOrchestrator
from app.core.editor_state import EditorState
from app.utils.config import RuntimeSettings


class AIWorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class AIEditWorker(QRunnable):
    def __init__(
        self,
        instruction: str,
        source_preview: np.ndarray,
        state: EditorState,
        history_summary: list[str],
        settings: RuntimeSettings,
        api_key: str,
        selected_mask_id: str | None,
    ) -> None:
        super().__init__()
        self.instruction = instruction
        self.source_preview = source_preview
        self.state = state.snapshot()
        self.history_summary = history_summary
        self.settings = settings
        self.api_key = api_key
        self.selected_mask_id = selected_mask_id
        self.signals = AIWorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            use_gemini = self.settings.provider != "mock" and bool(self.api_key)
            provider = (
                GeminiProvider(self.api_key, self.settings.gemini_model)
                if use_gemini
                else MockProvider()
            )
            orchestrator = AIOrchestrator(
                provider,
                preview_size=self.settings.preview_size,
                reinspection_enabled=self.settings.ai_reinspection,
                max_vision_calls=self.settings.max_vision_calls,
            )
            result = orchestrator.process(
                self.instruction,
                self.source_preview,
                self.state,
                self.history_summary,
                self.selected_mask_id,
            )
        except Exception:
            self.signals.failed.emit(traceback.format_exc())
            return
        self.signals.finished.emit(result)
