from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.core.editor_state import EditorState, HSLColor
from app.ui.curve_editor import CurvePanel


@dataclass(frozen=True, slots=True)
class SliderSpec:
    key: str
    label: str
    minimum: int
    maximum: int
    scale: int = 1


BASIC_SPECS = (
    SliderSpec("exposure", "曝光", -500, 500, 100),
    SliderSpec("contrast", "对比度", -100, 100),
    SliderSpec("highlights", "高光", -100, 100),
    SliderSpec("shadows", "阴影", -100, 100),
    SliderSpec("whites", "白色色阶", -100, 100),
    SliderSpec("blacks", "黑色色阶", -100, 100),
    SliderSpec("temperature", "色温", -100, 100),
    SliderSpec("tint", "Tint", -100, 100),
    SliderSpec("saturation", "饱和度", -100, 100),
    SliderSpec("vibrance", "自然饱和度", -100, 100),
    SliderSpec("clarity", "清晰度", -100, 100),
    SliderSpec("texture", "纹理", -100, 100),
    SliderSpec("dehaze", "去朦胧", -100, 100),
    SliderSpec("sharpen", "锐化", 0, 100),
    SliderSpec("vignette", "暗角", -100, 100),
)


class NoWheelSlider(QSlider):
    """Keep the editor scroll wheel for the surrounding panel, never values."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.setValue(0)
        event.accept()


class ParameterSlider(QWidget):
    value_changed = Signal(str, float)
    interaction_started = Signal(str)
    interaction_finished = Signal(str)

    def __init__(self, spec: SliderSpec, parent=None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.label = QLabel(spec.label)
        self.value_label = QDoubleSpinBox()
        self.value_label.setRange(spec.minimum / spec.scale, spec.maximum / spec.scale)
        self.value_label.setDecimals(2 if spec.scale != 1 else 0)
        self.value_label.setSingleStep(0.01 if spec.scale != 1 else 1.0)
        self.value_label.setMinimumWidth(76)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(spec.minimum, spec.maximum)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self._emit_value)
        self.value_label.valueChanged.connect(self._spin_value_changed)
        self.slider.sliderPressed.connect(lambda: self.interaction_started.emit(self.spec.key))
        self.slider.sliderReleased.connect(lambda: self.interaction_finished.emit(self.spec.key))

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.label)
        top.addStretch()
        top.addWidget(self.value_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 4)
        layout.setSpacing(2)
        layout.addLayout(top)
        layout.addWidget(self.slider)

    def _emit_value(self, raw: int) -> None:
        value = raw / self.spec.scale
        self.value_label.blockSignals(True)
        self.value_label.setValue(value)
        self.value_label.blockSignals(False)
        self.value_changed.emit(self.spec.key, value)

    def _spin_value_changed(self, value: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(round(value * self.spec.scale))
        self.slider.blockSignals(False)
        self.value_changed.emit(self.spec.key, value)

    def set_value(self, value: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(round(value * self.spec.scale))
        self.slider.blockSignals(False)
        self._update_label(value)

    def _update_label(self, value: float) -> None:
        self.value_label.blockSignals(True)
        self.value_label.setValue(value)
        self.value_label.blockSignals(False)


class AdjustmentPanel(QScrollArea):
    adjustment_changed = Signal(str, float)
    hsl_changed = Signal(str, str, float)
    curve_changed = Signal(str, object)
    color_grading_changed = Signal(str, str, float)
    reset_requested = Signal()
    interaction_started = Signal(str)
    interaction_finished = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("编辑")
        title.setStyleSheet("font-size: 13pt; font-weight: 600;")
        reset = QPushButton("重置")
        reset.clicked.connect(self.reset_requested)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(reset)
        layout.addLayout(header)

        basic = QGroupBox("基础调整")
        basic_layout = QVBoxLayout(basic)
        self.controls: dict[str, ParameterSlider] = {}
        for spec in BASIC_SPECS:
            control = ParameterSlider(spec)
            control.value_changed.connect(self.adjustment_changed)
            control.interaction_started.connect(lambda _key, label=spec.label: self.interaction_started.emit(label))
            control.interaction_finished.connect(lambda _key, label=spec.label: self.interaction_finished.emit(label))
            self.controls[spec.key] = control
            basic_layout.addWidget(control)
        layout.addWidget(basic)

        hsl_group = QGroupBox("HSL / 颜色")
        hsl_layout = QVBoxLayout(hsl_group)
        self.hsl_selector = QComboBox()
        for color, label in (
            (HSLColor.RED, "红色"),
            (HSLColor.ORANGE, "橙色"),
            (HSLColor.YELLOW, "黄色"),
            (HSLColor.GREEN, "绿色"),
            (HSLColor.AQUA, "青色"),
            (HSLColor.BLUE, "蓝色"),
            (HSLColor.PURPLE, "紫色"),
            (HSLColor.MAGENTA, "洋红"),
        ):
            self.hsl_selector.addItem(label, color.value)
        hsl_layout.addWidget(self.hsl_selector)
        self.hsl_controls: dict[str, ParameterSlider] = {}
        for spec in (
            SliderSpec("hue", "色相", -100, 100),
            SliderSpec("saturation", "饱和度", -100, 100),
            SliderSpec("luminance", "明亮度", -100, 100),
        ):
            control = ParameterSlider(spec)
            control.value_changed.connect(self._hsl_value_changed)
            control.interaction_started.connect(lambda _key: self.interaction_started.emit("调整 HSL"))
            control.interaction_finished.connect(lambda _key: self.interaction_finished.emit("调整 HSL"))
            self.hsl_controls[spec.key] = control
            hsl_layout.addWidget(control)
        self.hsl_selector.currentIndexChanged.connect(self._show_selected_hsl)
        layout.addWidget(hsl_group)

        curve_group = QGroupBox("曲线")
        curve_layout = QVBoxLayout(curve_group)
        self.curve_panel = CurvePanel()
        self.curve_panel.curve_changed.connect(self.curve_changed)
        self.curve_panel.interaction_started.connect(lambda: self.interaction_started.emit("调整曲线"))
        self.curve_panel.interaction_finished.connect(lambda: self.interaction_finished.emit("调整曲线"))
        curve_layout.addWidget(self.curve_panel)
        layout.addWidget(curve_group)

        grading_group = QGroupBox("色彩分级")
        grading_layout = QVBoxLayout(grading_group)
        self.grading_selector = QComboBox()
        self.grading_selector.addItem("阴影", "shadows")
        self.grading_selector.addItem("中间调", "midtones")
        self.grading_selector.addItem("高光", "highlights")
        grading_layout.addWidget(self.grading_selector)
        self.grading_controls: dict[str, ParameterSlider] = {}
        for spec in (
            SliderSpec("hue", "色相", 0, 360),
            SliderSpec("saturation", "饱和度", 0, 100),
            SliderSpec("luminance", "明亮度", -100, 100),
        ):
            control = ParameterSlider(spec)
            control.value_changed.connect(self._grading_value_changed)
            control.interaction_started.connect(lambda _key: self.interaction_started.emit("调整色彩分级"))
            control.interaction_finished.connect(lambda _key: self.interaction_finished.emit("调整色彩分级"))
            self.grading_controls[spec.key] = control
            grading_layout.addWidget(control)
        self.grading_selector.currentIndexChanged.connect(self._show_selected_grading)
        layout.addWidget(grading_group)

        masks_placeholder = QGroupBox("局部调整")
        masks_layout = QFormLayout(masks_placeholder)
        muted = QLabel("渐变、范围和智能蒙版")
        muted.setStyleSheet("color: #858b92;")
        masks_layout.addRow(muted)
        layout.addWidget(masks_placeholder)
        layout.addStretch()
        self.setWidget(container)
        self._state = EditorState()

    def set_enabled_for_image(self, enabled: bool) -> None:
        self.widget().setEnabled(enabled)

    def set_state(self, state: EditorState) -> None:
        self._state = state.snapshot()
        for key, control in self.controls.items():
            control.set_value(getattr(state.basic, key))
        self.curve_panel.set_state(state)
        self._show_selected_hsl()
        self._show_selected_grading()

    def _show_selected_hsl(self) -> None:
        color = HSLColor(self.hsl_selector.currentData())
        values = self._state.hsl[color]
        for key, control in self.hsl_controls.items():
            control.set_value(getattr(values, key))

    def _hsl_value_changed(self, key: str, value: float) -> None:
        color = self.hsl_selector.currentData()
        self.hsl_changed.emit(color, key, value)

    def _show_selected_grading(self) -> None:
        region = self.grading_selector.currentData()
        values = getattr(self._state.color_grading, region)
        for key, control in self.grading_controls.items():
            control.set_value(getattr(values, key))

    def _grading_value_changed(self, key: str, value: float) -> None:
        self.color_grading_changed.emit(self.grading_selector.currentData(), key, value)
