from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.core.editor_state import CurvePoint, EditorState, ToneCurve


CHANNEL_LABELS = {
    "rgb": "RGB",
    "red": "红色",
    "green": "绿色",
    "blue": "蓝色",
}

CHANNEL_COLORS = {
    "rgb": QColor("#e6e7e8"),
    "red": QColor("#e35b62"),
    "green": QColor("#66c77a"),
    "blue": QColor("#5f95e8"),
}


class CurveEditor(QWidget):
    curve_changed = Signal(object)
    interaction_started = Signal()
    interaction_finished = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(170)
        self.setMinimumWidth(210)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("色调曲线")
        self.setToolTip("点击添加控制点，拖动调整；右键删除中间控制点。")
        self._curve = ToneCurve()
        self._channel = "rgb"
        self._drag_index: int | None = None
        self._selected_index: int | None = None

    def set_channel(self, channel: str) -> None:
        self._channel = channel
        self.update()

    def set_curve(self, curve: ToneCurve) -> None:
        self._curve = curve.model_copy(deep=True)
        self._drag_index = None
        self._selected_index = None
        self.update()

    def curve(self) -> ToneCurve:
        return self._curve.model_copy(deep=True)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        area = self._plot_rect()
        painter.fillRect(area, QColor("#151719"))
        painter.setPen(QPen(QColor("#34393e"), 1))
        for step in range(5):
            ratio = step / 4
            x = area.left() + ratio * area.width()
            y = area.top() + ratio * area.height()
            painter.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
            painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
        painter.setPen(QPen(QColor("#4a4f55"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(area.bottomLeft(), area.topRight())

        points = [self._to_widget(point) for point in self._curve.points]
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        painter.setPen(QPen(CHANNEL_COLORS[self._channel], 2))
        painter.drawPath(path)
        painter.setBrush(QColor("#202225"))
        painter.setPen(QPen(CHANNEL_COLORS[self._channel], 2))
        for point in points:
            painter.drawEllipse(point, 4.5, 4.5)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if not self._plot_rect().contains(event.position()):
            return
        nearest, distance = self._nearest(event.position())
        if event.button() == Qt.MouseButton.RightButton:
            if nearest not in (0, len(self._curve.points) - 1) and distance < 14:
                points = self._curve.points.copy()
                points.pop(nearest)
                self.interaction_started.emit()
                self._set_points(points)
                self._selected_index = None
                self.interaction_finished.emit()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.interaction_started.emit()
        if distance < 14:
            self._drag_index = nearest
        else:
            new_point = self._from_widget(event.position())
            # Clicking vertically above an existing point must move it, not
            # construct duplicate x values rejected by the shared curve model.
            same_x = next((index for index, point in enumerate(self._curve.points)
                           if abs(point.x - new_point.x) < 0.002), None)
            if same_x is not None:
                self._drag_index = same_x
                self.mouseMoveEvent(event)
                self._selected_index = same_x
                return
            points = self._curve.points + [new_point]
            points.sort(key=lambda point: point.x)
            self._set_points(points)
            self._drag_index = min(range(len(points)), key=lambda index: abs(points[index].x - new_point.x))
        self._selected_index = self._drag_index

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if self._drag_index is None:
            return
        point = self._from_widget(event.position())
        points = self._curve.points.copy()
        index = self._drag_index
        if index == 0:
            point.x = 0.0
        elif index == len(points) - 1:
            point.x = 1.0
        else:
            point.x = max(points[index - 1].x + 0.002, min(point.x, points[index + 1].x - 0.002))
        points[index] = point
        self._set_points(points)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if self._drag_index is None or event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        self._drag_index = None
        self.interaction_finished.emit()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        index = self._selected_index
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and index is not None and 0 < index < len(self._curve.points) - 1:
            self.interaction_started.emit()
            points = self._curve.points.copy()
            points.pop(index)
            self._set_points(points)
            self._selected_index = None
            self.interaction_finished.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _plot_rect(self) -> QRectF:
        return QRectF(8, 8, max(1, self.width() - 16), max(1, self.height() - 16))

    def _to_widget(self, point: CurvePoint) -> QPointF:
        area = self._plot_rect()
        return QPointF(area.left() + point.x * area.width(), area.bottom() - point.y * area.height())

    def _from_widget(self, position: QPointF) -> CurvePoint:
        area = self._plot_rect()
        x = min(1.0, max(0.0, (position.x() - area.left()) / area.width()))
        y = min(1.0, max(0.0, (area.bottom() - position.y()) / area.height()))
        return CurvePoint(x=x, y=y)

    def _nearest(self, position: QPointF) -> tuple[int, float]:
        distances = [((self._to_widget(point) - position).manhattanLength()) for point in self._curve.points]
        index = min(range(len(distances)), key=distances.__getitem__)
        return index, distances[index]

    def _set_points(self, points: list[CurvePoint]) -> None:
        self._curve = ToneCurve(points=points)
        self.update()
        self.curve_changed.emit(self.curve())


class CurveChannelSelector(QComboBox):
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class CurvePanel(QWidget):
    curve_changed = Signal(str, object)
    interaction_started = Signal()
    interaction_finished = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.channel = CurveChannelSelector()
        for key, label in CHANNEL_LABELS.items():
            self.channel.addItem(label, key)
        self.reset_button = QPushButton("重置")
        self.reset_button.setToolTip("重置当前通道曲线")
        self.editor = CurveEditor()

        top = QHBoxLayout()
        top.addWidget(QLabel("通道"))
        top.addWidget(self.channel, 1)
        top.addWidget(self.reset_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self.editor)
        hint = QLabel("点击加点 · 拖动调整 · 右键删点")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._state = EditorState()
        self.channel.currentIndexChanged.connect(self._channel_selected)
        self.reset_button.clicked.connect(self._reset)
        self.editor.curve_changed.connect(self._curve_edited)
        self.editor.interaction_started.connect(self.interaction_started)
        self.editor.interaction_finished.connect(self.interaction_finished)

    def set_state(self, state: EditorState) -> None:
        self._state = state.snapshot()
        self._show_current_curve()

    def _channel_selected(self) -> None:
        self._show_current_curve()

    def _show_current_curve(self) -> None:
        key = self.channel.currentData()
        self.editor.set_channel(key)
        self.editor.set_curve(getattr(self._state.curves, key))

    def _curve_edited(self, curve: ToneCurve) -> None:
        key = self.channel.currentData()
        setattr(self._state.curves, key, curve)
        self.curve_changed.emit(key, curve)

    def _reset(self) -> None:
        self.interaction_started.emit()
        curve = ToneCurve()
        self.editor.set_curve(curve)
        self._curve_edited(curve)
        self.interaction_finished.emit()
