from __future__ import annotations

import numpy as np
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget


class HistogramWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(132)
        self._histograms: list[np.ndarray] = []
        self._clip_high = 0.0
        self._clip_low = 0.0
        self.caption = QToolButton()
        self.caption.setText("RGB 直方图")
        self.caption.setCheckable(True)
        self.caption.setChecked(True)
        self.caption.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.caption.setArrowType(Qt.ArrowType.DownArrow)
        self.caption.setStyleSheet("border:none; background:transparent; text-align:left; padding:3px;")
        self.caption.setToolTip("点击收起 / 展开。高光：任一通道达到255；黑位：全部通道为0。基于预览采样。")
        self.caption.toggled.connect(self._toggle)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.addWidget(self.caption)
        layout.addStretch(1)

    def _toggle(self, expanded: bool) -> None:
        self.setFixedHeight(132 if expanded else 36)
        self.caption.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.update()

    def set_image(self, pixels: np.ndarray | None) -> None:
        if pixels is None or pixels.size == 0:
            self._histograms = []
            self._clip_high = self._clip_low = 0.0
            self.caption.setText("RGB 直方图")
            self.update()
            return
        sample = pixels[::max(1, (pixels.shape[0] + 239) // 240), ::max(1, (pixels.shape[1] + 359) // 360)]
        self._histograms = [np.bincount(sample[..., channel].ravel(), minlength=256).astype(float) for channel in range(3)]
        self._clip_high = float((sample == 255).any(axis=2).mean() * 100)
        self._clip_low = float((sample == 0).all(axis=2).mean() * 100)
        self.caption.setText(f"RGB · 高光 {self._clip_high:.1f}% · 黑位 {self._clip_low:.1f}%")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self.caption.isChecked():
            return
        painter = QPainter(self)
        area = QRectF(self.contentsRect().adjusted(12, 35, -12, -25))
        painter.fillRect(area, QColor("#151719"))
        if not self._histograms:
            painter.setPen(QColor("#95a4b3"))
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, "打开照片后显示色调分布")
            return
        painter.setPen(QPen(QColor("#2e3740"), 1))
        for fraction in (.25, .5, .75):
            x = area.left() + area.width() * fraction
            painter.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
        maximum = max(1.0, max(hist.max() for hist in self._histograms))
        for histogram, color in zip(self._histograms, (QColor(230, 90, 90, 175), QColor(95, 195, 120, 175), QColor(95, 145, 235, 175))):
            path = QPainterPath()
            for index, count in enumerate(histogram):
                x = area.left() + index / 255 * area.width()
                y = area.bottom() - count / maximum * area.height()
                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.setPen(QPen(color, 1.2))
            painter.drawPath(path)
            path.lineTo(area.right(), area.bottom())
            path.lineTo(area.left(), area.bottom())
            path.closeSubpath()
            color.setAlpha(38)
            painter.fillPath(path, color)
        painter.setPen(QColor("#95a4b3"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for text, alignment in (("暗部", Qt.AlignmentFlag.AlignLeft), ("中间调", Qt.AlignmentFlag.AlignHCenter), ("高光", Qt.AlignmentFlag.AlignRight)):
            painter.drawText(QRectF(area.left(), area.bottom() + 3, area.width(), 20), alignment | Qt.AlignmentFlag.AlignVCenter, text)
