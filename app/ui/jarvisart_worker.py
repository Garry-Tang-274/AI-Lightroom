from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.ai.jarvisart.service import JarvisArtServiceManager, JarvisArtServiceStatus


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
        try:
            manager = JarvisArtServiceManager(self.root, self.endpoint)
            if self.action == "start":
                result = manager.start()
            elif self.action == "stop":
                result = manager.stop_owned()
            else:
                result = manager.status()
        except Exception as exc:
            result = JarvisArtServiceStatus("Error", f"JarvisArt 服务操作失败：{type(exc).__name__}", endpoint=self.endpoint)
        self.signals.finished.emit(result)
