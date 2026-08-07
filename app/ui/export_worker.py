from __future__ import annotations

import traceback
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.core.editor_state import EditorState
from app.core.exporter import export_image


class ExportSignals(QObject):
    finished = Signal(str)
    failed = Signal(str)


class ExportWorker(QRunnable):
    def __init__(
        self,
        source: np.ndarray,
        state: EditorState,
        destination: str,
        jpeg_quality: int,
        metadata: dict,
    ) -> None:
        super().__init__()
        self.source = source
        self.state = state.snapshot()
        self.destination = destination
        self.jpeg_quality = jpeg_quality
        self.metadata = metadata
        self.signals = ExportSignals()

    @Slot()
    def run(self) -> None:
        try:
            path = export_image(
                self.source,
                self.state,
                self.destination,
                jpeg_quality=self.jpeg_quality,
                **self.metadata,
            )
        except Exception:
            self.signals.failed.emit(traceback.format_exc())
            return
        self.signals.finished.emit(str(path))

