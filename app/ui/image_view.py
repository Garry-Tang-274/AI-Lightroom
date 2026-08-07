from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class ImageView(QGraphicsView):
    zoom_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        self.setScene(self._scene)
        self.setBackgroundBrush(Qt.GlobalColor.black)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._has_image = False
        self._fit_on_resize = True

    def set_image(self, pixels: np.ndarray) -> None:
        contiguous = np.ascontiguousarray(pixels)
        height, width, channels = contiguous.shape
        if channels != 3:
            raise ValueError("ImageView expects an RGB image")
        image = QImage(contiguous.data, width, height, contiguous.strides[0], QImage.Format.Format_RGB888).copy()
        self._pixmap_item.setPixmap(QPixmap.fromImage(image))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._has_image = True
        if self._fit_on_resize:
            self.fit_to_view()

    def clear_image(self) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._has_image = False

    def fit_to_view(self) -> None:
        if not self._has_image:
            return
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._fit_on_resize = True
        self.zoom_changed.emit(self.transform().m11())

    def actual_size(self) -> None:
        if not self._has_image:
            return
        self.resetTransform()
        self._fit_on_resize = False
        self.centerOn(self._pixmap_item)
        self.zoom_changed.emit(1.0)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API
        if not self._has_image:
            return super().wheelEvent(event)
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        current = self.transform().m11()
        next_zoom = current * factor
        if 0.03 <= next_zoom <= 16:
            self.scale(factor, factor)
            self._fit_on_resize = False
            self.zoom_changed.emit(next_zoom)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        if self._fit_on_resize and self._has_image:
            self.fit_to_view()

