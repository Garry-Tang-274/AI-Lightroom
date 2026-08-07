from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class ImageView(QGraphicsView):
    zoom_changed = Signal(float)
    brush_stroke_finished = Signal(object, float)

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
        self._brush_mode = False
        self._brush_size = 0.08
        self._brush_points: list[tuple[float, float]] = []
        self._brush_path: QPainterPath | None = None
        self._brush_preview: QGraphicsPathItem | None = None

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

    def set_brush_mode(self, enabled: bool, size: float = 0.08) -> None:
        self._brush_mode = enabled
        self._brush_size = size
        self.setDragMode(QGraphicsView.DragMode.NoDrag if enabled else QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if not self._brush_mode or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        point = self._normalized_image_point(event.position())
        if point is None:
            return
        scene_point = self.mapToScene(event.position().toPoint())
        self._brush_points = [point]
        self._brush_path = QPainterPath(scene_point)
        self._brush_preview = QGraphicsPathItem(self._brush_path)
        width = self._brush_size * min(self._pixmap_item.boundingRect().width(), self._pixmap_item.boundingRect().height())
        self._brush_preview.setPen(QPen(QColor(90, 170, 255, 150), max(2.0, width), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self._scene.addItem(self._brush_preview)
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        if not self._brush_mode or self._brush_path is None:
            return super().mouseMoveEvent(event)
        point = self._normalized_image_point(event.position())
        if point is None:
            return
        self._brush_points.append(point)
        self._brush_path.lineTo(self.mapToScene(event.position().toPoint()))
        self._brush_preview.setPath(self._brush_path)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt API
        if not self._brush_mode or self._brush_path is None:
            return super().mouseReleaseEvent(event)
        if self._brush_preview is not None:
            self._scene.removeItem(self._brush_preview)
        points = self._brush_points
        self._brush_points = []
        self._brush_path = None
        self._brush_preview = None
        if points:
            self.brush_stroke_finished.emit(points, self._brush_size)
        event.accept()

    def _normalized_image_point(self, viewport_position: QPointF) -> tuple[float, float] | None:
        if not self._has_image:
            return None
        scene_point = self.mapToScene(viewport_position.toPoint())
        local = self._pixmap_item.mapFromScene(scene_point)
        bounds = self._pixmap_item.boundingRect()
        if not bounds.contains(local):
            return None
        return (local.x() / max(bounds.width(), 1), local.y() / max(bounds.height(), 1))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        if self._fit_on_resize and self._has_image:
            self.fit_to_view()
