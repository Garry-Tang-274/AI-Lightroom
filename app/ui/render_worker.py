from __future__ import annotations

import traceback

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from app.core.editor_state import EditorState
from app.core.image_processor import render_image


class RenderSignals(QObject):
    finished = Signal(object, int)
    failed = Signal(str, int)


class PreviewRenderWorker(QRunnable):
    def __init__(self, source: np.ndarray, state: EditorState, generation: int) -> None:
        super().__init__()
        self.source = source
        self.state = state.snapshot()
        self.generation = generation
        self.signals = RenderSignals()

    @Slot()
    def run(self) -> None:
        try:
            rendered = render_image(self.source, self.state)
        except Exception:
            self.signals.failed.emit(traceback.format_exc(), self.generation)
            return
        self.signals.finished.emit(rendered, self.generation)

