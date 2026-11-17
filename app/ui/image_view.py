from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class ImageView(QGraphicsView):
    zoom_changed = Signal(float)
    brush_stroke_finished = Signal(object, float)
    open_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        self._mask_overlay_item = QGraphicsPixmapItem()
        self._mask_overlay_item.setZValue(10)
        self._scene.addItem(self._mask_overlay_item)
        self.setScene(self._scene)
        self.setBackgroundBrush(QColor("#13171c"))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._has_image = False
        self._fit_on_resize = True
        self._brush_mode = False
        self._editing_enabled = True
        self._brush_size = 0.08
        self._brush_points: list[tuple[float, float]] = []
        self._brush_path: QPainterPath | None = None
        self._brush_preview: QGraphicsPathItem | None = None
        self._logical_size = None
        self._comparison_pixmap = QPixmap()
        self._comparison_enabled = False
        self._split_fraction = 0.5
        self._dragging_split = False

    def set_image(self, pixels: np.ndarray, logical_size: tuple[int, int] | None = None) -> None:
        contiguous = np.ascontiguousarray(pixels)
        height, width, channels = contiguous.shape
        if channels != 3:
            raise ValueError("ImageView expects an RGB image")
        image = QImage(contiguous.data, width, height, contiguous.strides[0], QImage.Format.Format_RGB888).copy()
        old_size = self._logical_size
        self._logical_size = logical_size or (width, height)
        self._pixmap_item.setPixmap(QPixmap.fromImage(image))
        self._pixmap_item.setScale(self._logical_size[0] / width)
        self._scene.setSceneRect(QRectF(0, 0, *self._logical_size))
        self._has_image = True
        if self._fit_on_resize and old_size != self._logical_size:
            self.fit_to_view()
        self.viewport().update()

    def clear_image(self) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._mask_overlay_item.setPixmap(QPixmap())
        self._has_image = False
        self._logical_size = None
        self._comparison_pixmap = QPixmap()
        self.viewport().update()

    def set_comparison(self, original: np.ndarray | None, enabled: bool) -> None:
        self._comparison_enabled = enabled
        if original is not None:
            pixels = np.ascontiguousarray(original)
            h, w = pixels.shape[:2]
            self._comparison_pixmap = QPixmap.fromImage(QImage(pixels.data, w, h, pixels.strides[0], QImage.Format.Format_RGB888).copy())
        self.viewport().update()

    def drawForeground(self, painter, rect) -> None:  # noqa: N802
        super().drawForeground(painter, rect)
        if not self._has_image:
            painter.save()
            painter.resetTransform()
            area = self.viewport().rect()
            painter.setPen(QColor("#e0ebf4"))
            painter.setFont(QFont("Microsoft YaHei UI", 22))
            painter.drawText(area.adjusted(12, -60, -12, -60), Qt.AlignmentFlag.AlignCenter, "让照片成为主角")
            painter.setPen(QColor("#93a4b5"))
            painter.setFont(QFont("Microsoft YaHei UI", 11))
            painter.drawText(area.adjusted(12, 40, -12, 40), Qt.AlignmentFlag.AlignCenter, "拖入 JPG / PNG，或按 Ctrl+O 打开\n手动调色 · 本地 AI · 全尺寸导出")
            painter.restore()
        elif self._comparison_enabled and not self._comparison_pixmap.isNull():
            bounds = self._scene.sceneRect()
            split = bounds.width() * self._split_fraction
            painter.save()
            painter.setClipRect(QRectF(0, 0, split, bounds.height()))
            painter.drawPixmap(bounds, self._comparison_pixmap, QRectF(self._comparison_pixmap.rect()))
            painter.restore()
            pen = QPen(QColor("#d3e8f8"), 2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(QPointF(split, 0), QPointF(split, bounds.height()))
            painter.save()
            painter.resetTransform()
            painter.setFont(QFont("Microsoft YaHei UI", 10))
            for label, x in (("原图", 14), ("调整后", self.viewport().width() - 85)):
                box = QRectF(x, 12, 68, 26)
                painter.fillRect(box, QColor(20, 28, 36, 220))
                painter.drawText(box, Qt.AlignmentFlag.AlignCenter, label)
            painter.restore()

    def set_mask_overlay(self, mask: np.ndarray | None) -> None:
        if mask is None:
            self._mask_overlay_item.setPixmap(QPixmap())
            return
        alpha = np.clip(mask * 120, 0, 120).astype(np.uint8)
        rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        rgba[..., 0] = 235
        rgba[..., 1] = 48
        rgba[..., 2] = 54
        rgba[..., 3] = alpha
        image = QImage(np.ascontiguousarray(rgba).data, rgba.shape[1], rgba.shape[0], rgba.strides[0], QImage.Format.Format_RGBA8888).copy()
        self._mask_overlay_item.setPixmap(QPixmap.fromImage(image))

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
        self._update_brush_interaction()

    def set_editing_enabled(self, enabled: bool) -> None:
        """Suspend painting during an AI transaction; keep pan/zoom available."""
        self._editing_enabled = enabled
        if not enabled:
            if self._brush_preview is not None:
                self._scene.removeItem(self._brush_preview)
            self._brush_preview = None
            self._brush_path = None
            self._brush_points = []
        self._update_brush_interaction()

    def _update_brush_interaction(self) -> None:
        painting = self._brush_mode and self._editing_enabled
        self.setDragMode(QGraphicsView.DragMode.NoDrag if painting else QGraphicsView.DragMode.ScrollHandDrag)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor if painting else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._comparison_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._dragging_split = True
            self._move_split(event.position())
            event.accept()
            return
        if not self._editing_enabled or not self._brush_mode or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        point = self._normalized_image_point(event.position())
        if point is None:
            return
        scene_point = self.mapToScene(event.position().toPoint())
        self._brush_points = [point]
        self._brush_path = QPainterPath(scene_point)
        self._brush_preview = QGraphicsPathItem(self._brush_path)
        width = self._brush_size * min(self._scene.sceneRect().width(), self._scene.sceneRect().height())
        self._brush_preview.setPen(QPen(QColor(90, 170, 255, 150), max(2.0, width), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self._scene.addItem(self._brush_preview)
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._dragging_split:
            self._move_split(event.position())
            event.accept()
            return
        if not self._editing_enabled or not self._brush_mode or self._brush_path is None:
            return super().mouseMoveEvent(event)
        point = self._normalized_image_point(event.position())
        if point is None:
            return
        self._brush_points.append(point)
        self._brush_path.lineTo(self.mapToScene(event.position().toPoint()))
        self._brush_preview.setPath(self._brush_path)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._dragging_split:
            self._dragging_split = False
            event.accept()
            return
        if not self._editing_enabled or not self._brush_mode or self._brush_path is None:
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

    def _move_split(self, position) -> None:
        width = self._scene.sceneRect().width()
        if width:
            self._split_fraction = max(0.02, min(0.98, self.mapToScene(position.toPoint()).x() / width))
            self.viewport().update()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if not self._has_image:
            self.open_requested.emit()
            return
        if not self._brush_mode and not self._comparison_enabled:
            self.actual_size() if self._fit_on_resize else self.fit_to_view()
            return
        super().mouseDoubleClickEvent(event)

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
