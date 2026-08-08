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

DETAIL_SPECS = (
    SliderSpec("sharpen_radius", "锐化半径", 30, 300, 100),
    SliderSpec("sharpen_detail", "锐化细节", 0, 100),
    SliderSpec("sharpen_masking", "锐化蒙版", 0, 100),
    SliderSpec("luminance_noise_reduction", "明度降噪", 0, 100),
    SliderSpec("luminance_noise_reduction_detail", "明度细节", 0, 100),
    SliderSpec("luminance_noise_reduction_contrast", "明度对比", 0, 100),
    SliderSpec("color_noise_reduction", "颜色降噪", 0, 100),
    SliderSpec("color_noise_reduction_detail", "颜色细节", 0, 100),
    SliderSpec("color_noise_reduction_smoothness", "颜色平滑度", 0, 100),
)

EFFECTS_SPECS = (
    SliderSpec("vignette_midpoint", "暗角中点", 0, 100),
    SliderSpec("vignette_roundness", "暗角圆度", -100, 100),
    SliderSpec("vignette_feather", "暗角羽化", 0, 100),
    SliderSpec("vignette_highlights", "暗角高光", 0, 100),
    SliderSpec("curve_refine_saturation", "曲线后饱和度", -100, 100),
    SliderSpec("grain_amount", "颗粒数量", 0, 100),
    SliderSpec("grain_size", "颗粒大小", 0, 100),
    SliderSpec("grain_roughness", "颗粒粗糙度", 0, 100),
)

OPTICS_SPECS = (
    SliderSpec("defringe_purple_amount", "紫边校正", 0, 100),
    SliderSpec("defringe_purple_hue_low", "紫边色相下限", 0, 100),
    SliderSpec("defringe_purple_hue_high", "紫边色相上限", 0, 100),
    SliderSpec("defringe_green_amount", "绿边校正", 0, 100),
    SliderSpec("defringe_green_hue_low", "绿边色相下限", 0, 100),
    SliderSpec("defringe_green_hue_high", "绿边色相上限", 0, 100),
)

TRANSFORM_SPECS = (
    SliderSpec("vertical", "垂直", -100, 100),
    SliderSpec("horizontal", "水平", -100, 100),
    SliderSpec("rotate", "旋转", -4500, 4500, 100),
    SliderSpec("scale", "缩放", 50, 150),
    SliderSpec("offset_x", "水平偏移", -100, 100),
    SliderSpec("offset_y", "垂直偏移", -100, 100),
    SliderSpec("aspect", "宽高比", -100, 100),
)

CALIBRATION_SPECS = (
    SliderSpec("red_primary_hue", "红原色色相", -100, 100),
    SliderSpec("red_primary_saturation", "红原色饱和度", -100, 100),
    SliderSpec("green_primary_hue", "绿原色色相", -100, 100),
    SliderSpec("green_primary_saturation", "绿原色饱和度", -100, 100),
    SliderSpec("blue_primary_hue", "蓝原色色相", -100, 100),
    SliderSpec("blue_primary_saturation", "蓝原色饱和度", -100, 100),
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
    advanced_adjustment_changed = Signal(str, str, object)
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

        self.advanced_controls: dict[str, dict[str, ParameterSlider]] = {}
        self._add_advanced_group(layout, "细节", "detail", DETAIL_SPECS)
        effects_group = QGroupBox("效果")
        effects_layout = QVBoxLayout(effects_group)
        self._add_advanced_controls(effects_layout, "effects", EFFECTS_SPECS)
        self.vignette_style = QComboBox()
        self.vignette_style.addItem("暗角样式：绘制叠加", 0)
        self.vignette_style.addItem("暗角样式：高光优先", 1)
        self.vignette_style.addItem("暗角样式：颜色优先", 2)
        self.vignette_style.addItem("暗角样式：保留", 3)
        self.vignette_style.currentIndexChanged.connect(
            lambda _index: self.advanced_adjustment_changed.emit("effects", "vignette_style", self.vignette_style.currentData())
        )
        effects_layout.addWidget(self.vignette_style)
        layout.addWidget(effects_group)

        optics_group = QGroupBox("光学")
        optics_layout = QVBoxLayout(optics_group)
        from PySide6.QtWidgets import QCheckBox
        self.remove_chromatic_aberration = QCheckBox("移除色差")
        self.remove_chromatic_aberration.toggled.connect(
            lambda checked: self.advanced_adjustment_changed.emit("optics", "remove_chromatic_aberration", checked)
        )
        optics_layout.addWidget(self.remove_chromatic_aberration)
        self._add_advanced_controls(optics_layout, "optics", OPTICS_SPECS)
        layout.addWidget(optics_group)

        self._add_advanced_group(layout, "几何", "transform", TRANSFORM_SPECS)
        self._add_advanced_group(layout, "相机校准", "calibration", CALIBRATION_SPECS)

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
        for section, controls in self.advanced_controls.items():
            values = getattr(state, section)
            for key, control in controls.items():
                control.set_value(getattr(values, key))
        self.remove_chromatic_aberration.blockSignals(True)
        self.remove_chromatic_aberration.setChecked(state.optics.remove_chromatic_aberration)
        self.remove_chromatic_aberration.blockSignals(False)
        self.vignette_style.blockSignals(True)
        self.vignette_style.setCurrentIndex(max(0, self.vignette_style.findData(state.effects.vignette_style)))
        self.vignette_style.blockSignals(False)
        self._show_selected_hsl()
        self._show_selected_grading()

    def _add_advanced_group(self, parent: QVBoxLayout, title: str, section: str, specs: tuple[SliderSpec, ...]) -> None:
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        self._add_advanced_controls(group_layout, section, specs)
        parent.addWidget(group)

    def _add_advanced_controls(self, layout: QVBoxLayout, section: str, specs: tuple[SliderSpec, ...]) -> None:
        controls = self.advanced_controls.setdefault(section, {})
        for spec in specs:
            control = ParameterSlider(spec)
            control.value_changed.connect(
                lambda key, value, section_name=section: self.advanced_adjustment_changed.emit(section_name, key, value)
            )
            control.interaction_started.connect(
                lambda _key, title=section: self.interaction_started.emit(f"调整{title}")
            )
            control.interaction_finished.connect(
                lambda _key, title=section: self.interaction_finished.emit(f"调整{title}")
            )
            controls[spec.key] = control
            layout.addWidget(control)

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
