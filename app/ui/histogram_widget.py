from __future__ import annotations

import numpy as np
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class HistogramWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(130)
        self._histograms: list[np.ndarray] = []
        self._clip_high = 0.0
        self._clip_low = 0.0
        self.caption = QLabel("RGB Histogram")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.addWidget(self.caption)

    def set_image(self, pixels: np.ndarray | None) -> None:
        if pixels is None or pixels.size == 0:
            self._histograms = []
            self.caption.setText("RGB Histogram")
            self.update()
            return
        sample = pixels[::max(1, pixels.shape[0] // 240), ::max(1, pixels.shape[1] // 360)]
        self._histograms = [np.histogram(sample[..., channel], bins=256, range=(0, 256))[0].astype(float) for channel in range(3)]
        self._clip_high = float((sample >= 250).all(axis=2).mean() * 100)
        self._clip_low = float((sample <= 5).all(axis=2).mean() * 100)
        self.caption.setText(f"RGB Histogram · 高光裁切 {self._clip_high:.1f}% · 阴影裁切 {self._clip_low:.1f}%")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._histograms:
            return
        painter = QPainter(self)
        area = self.contentsRect().adjusted(8, 28, -8, -8)
        painter.fillRect(area, QColor("#151719"))
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
