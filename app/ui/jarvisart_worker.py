from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.ai.jarvisart.service import JarvisArtServiceManager


class JarvisArtControlSignals(QObject):
    finished = Signal(object)


class JarvisArtControlWorker(QRunnable):
    def __init__(self, root: str, endpoint: str, action: str) -> None:
        super().__init__()
        self.root = root
        self.endpoint = endpoint
        self.action = action
        self.signals = JarvisArtControlSignals()

    @Slot()
    def run(self) -> None:
        manager = JarvisArtServiceManager(self.root, self.endpoint)
        result = manager.start() if self.action == "start" else manager.stop_owned()
        self.signals.finished.emit(result)
