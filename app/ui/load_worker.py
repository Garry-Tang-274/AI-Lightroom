from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from app.utils.io_utils import load_image, make_preview


class LoadSignals(QObject):
    finished = Signal(object, object, int)
    failed = Signal(str, int)


class ImageLoadWorker(QRunnable):
    def __init__(self, filename: str, edge: int, request_id: int) -> None:
        super().__init__()
        self.filename, self.edge, self.request_id = filename, edge, request_id
        self.signals = LoadSignals()

    @Slot()
    def run(self) -> None:
        try:
            loaded = load_image(self.filename)
            preview = make_preview(loaded.pixels, self.edge)
            self.signals.finished.emit(loaded, preview, self.request_id)
        except Exception as exc:
            self.signals.failed.emit(str(exc), self.request_id)
