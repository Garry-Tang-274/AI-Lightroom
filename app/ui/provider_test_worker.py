from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.ai.errors import error_from_exception
from app.ai.provider_registry import provider_registry


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
        try:
            provider = provider_registry.create(self.config, self.api_key, system_prompt=self.system_prompt)
            self.signals.succeeded.emit(provider.test_connection())
        except Exception as exc:
            self.signals.failed.emit(error_from_exception(exc, model=self.config.model, request_sent=bool(self.api_key), provider=self.config.display_name))
