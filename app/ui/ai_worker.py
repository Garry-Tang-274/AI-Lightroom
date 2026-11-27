from __future__ import annotations

from threading import Event

import numpy as np
from PySide6.QtCore import QObject, QRunnable, QSettings, Signal, Slot

from app.ai.errors import AIRequestError, error_from_exception
from app.ai.orchestrator import AIOrchestrator
from app.ai.progress import AIProgress
from app.ai.provider_registry import provider_registry
from app.ai.usage import AIUsageManager, CloudRequestTracker
from app.core.editor_state import EditorState
from app.utils.config import RuntimeSettings
from app.utils.io_utils import make_preview


class AIWorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)
    progress = Signal(object)


class AIEditWorker(QRunnable):
    def __init__(self, instruction: str, source_pixels: np.ndarray, state: EditorState, history_summary: list[str], settings: RuntimeSettings, api_key: str, selected_mask_id: str | None) -> None:
        super().__init__()
        self.instruction = instruction
        # Keep the original image pixels in the worker only.  The UI can stay
        # responsive on a low-quality working preview while this worker creates
        # the separately configured image sent to an AI provider.
        self.source_pixels = source_pixels
        self.state = state.snapshot()
        self.history_summary = list(history_summary)
        self.settings = settings
        self.api_key = api_key
        self.selected_mask_id = selected_mask_id
        self.signals = AIWorkerSignals()
        self._cancelled = Event()
        self._request_number = 0
        self._request_sent = False
        self._cloud = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self) -> None:
        if self._cancelled.is_set():
            return
        self._cancelled.set()
        message = "已请求取消；正在等待当前步骤安全结束，不会应用结果。"
        if self._request_sent:
            message = ("已请求取消；云端请求已发出，仍可能计费，不会应用返回结果。" if self._cloud else
                       "已请求取消；本地模型可能仍在运行，不会应用返回结果。")
        self._emit_progress("cancelling", message)

    def _emit_progress(self, stage: str, message: str) -> None:
        if self._cancelled.is_set() and stage not in {"cancelling", "cancelled"}:
            return
        self.signals.progress.emit(AIProgress(stage, message, self._request_number, self._request_sent, self._cloud))

    def _cancellation_error(self) -> AIRequestError:
        message = "已取消本次编辑，照片未修改。"
        if self._request_sent:
            message += "已发出的云端请求仍计入本地调用记录，并可能计费。" if self._cloud else "本地推理请求已发出，模型可能仍在运行。"
        else:
            message += "未发送推理请求。"
        return AIRequestError("已取消本地等待", message, provider=self.settings.provider_config.display_name,
                              model=self.settings.active_model, request_sent=self._request_sent)

    def _check_cancelled(self) -> None:
        if self._cancelled.is_set():
            raise self._cancellation_error()

    @Slot()
    def run(self) -> None:
        config = self.settings.provider_config
        descriptor = provider_registry.descriptor(config.provider_id)
        use_cloud = descriptor.requires_api_key and bool(self.api_key)
        self._cloud = use_cloud
        provider_name = config.display_name
        model = config.model
        usage = AIUsageManager(QSettings("AI Lightroom", "AI Lightroom"))
        tracker = CloudRequestTracker(usage, provider_name, model, cloud=use_cloud, cancelled=self._cancelled.is_set)

        def request_started() -> None:
            self._check_cancelled()
            tracker.started()
            self._request_number += 1
            self._request_sent = True
            if use_cloud:
                self._emit_progress("waiting_cloud", f"{provider_name} 请求已发出，正在等待调色方案…")
            else:
                self._emit_progress("waiting_local", "本地模型正在分析当前预览；高分辨率推理可能需要数分钟…")

        try:
            self._check_cancelled()
            self._emit_progress("checking_provider", "正在检查 AI 配置与连接状态…")
            provider = provider_registry.create(
                config, self.api_key,
                system_prompt=self.settings.system_prompt,
                on_request_started=request_started,
                on_result=tracker.result,
            )
            if hasattr(provider, "set_execution_hooks"):
                provider.set_execution_hooks(on_stage=self._emit_progress, check_cancelled=self._check_cancelled)
            self._check_cancelled()
            self._emit_progress("preparing_preview", "正在准备当前照片预览…")
            analysis_source = make_preview(self.source_pixels, self.settings.active_ai_preview_size)
            orchestrator = AIOrchestrator(
                provider, preview_size=self.settings.active_ai_preview_size,
                reinspection_enabled=self.settings.ai_reinspection,
                max_vision_calls=self.settings.max_vision_calls,
                check_cancelled=self._check_cancelled,
                on_stage=self._emit_progress,
            )
            result = orchestrator.process(self.instruction, analysis_source, self.state, self.history_summary, self.selected_mask_id)
            self._check_cancelled()
        except Exception as exc:
            # A transport timeout after Cancel must not turn into a retryable
            # failure or accidentally apply a late response.
            error = self._cancellation_error() if self._cancelled.is_set() else error_from_exception(
                exc, model=model, request_sent=self._request_sent, provider=provider_name, secrets=(self.api_key,))
            error.request_sent = error.request_sent or self._request_sent
            tracker.result(error.category)
            self._emit_progress("cancelled" if self._cancelled.is_set() else "failed", "已取消，照片未修改。" if self._cancelled.is_set() else "本次未完成，照片未修改。")
            self.signals.failed.emit(error)
            return
        self._emit_progress("completed", "调色方案已校验并渲染完成。" if result.has_changes else "方案已检查，当前参数无需改变。")
        self.signals.finished.emit(result)
