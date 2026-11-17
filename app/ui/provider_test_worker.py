from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QSettings, Signal, Slot

from app.ai.errors import error_from_exception
from app.ai.provider_registry import provider_registry
from app.ai.usage import AIUsageManager, CloudRequestTracker


class ProviderTestSignals(QObject):
    succeeded = Signal(str)
    failed = Signal(object)


class ProviderConnectionWorker(QRunnable):
    def __init__(self, config, api_key: str, system_prompt: str) -> None:
        super().__init__()
        self.config = config
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.signals = ProviderTestSignals()

    @Slot()
    def run(self) -> None:
        tracker = CloudRequestTracker(
            AIUsageManager(QSettings("AI Lightroom", "AI Lightroom")),
            self.config.display_name, self.config.model,
            cloud=provider_registry.descriptor(self.config.provider_id).requires_api_key,
        )
        try:
            provider = provider_registry.create(self.config, self.api_key, system_prompt=self.system_prompt,
                                                on_request_started=tracker.started, on_result=tracker.result)
            self.signals.succeeded.emit(provider.test_connection())
        except Exception as exc:
            error = error_from_exception(exc, model=self.config.model, request_sent=tracker.request_sent,
                                         provider=self.config.display_name, secrets=(self.api_key,))
            tracker.result(error.category)
            self.signals.failed.emit(error)
