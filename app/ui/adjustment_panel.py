from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QToolButton,
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
    default: float = 0.0
    display_multiplier: float = 1.0
    suffix: str = ""


BASIC_SPECS = (
    SliderSpec("exposure", "曝光", -500, 500, 100),
    SliderSpec("contrast", "对比度", -100, 100),
    SliderSpec("highlights", "高光", -100, 100),
    SliderSpec("shadows", "阴影", -100, 100),
    SliderSpec("whites", "白色色阶", -100, 100),
    SliderSpec("blacks", "黑色色阶", -100, 100),
    SliderSpec("temperature", "色温", -100, 100),
    SliderSpec("tint", "色调", -100, 100),
    SliderSpec("saturation", "饱和度", -100, 100),
    SliderSpec("vibrance", "自然饱和度", -100, 100),
    SliderSpec("clarity", "清晰度", -100, 100),
    SliderSpec("texture", "纹理", -100, 100),
    SliderSpec("dehaze", "去朦胧", -100, 100),
    SliderSpec("sharpen", "锐化", 0, 100),
    SliderSpec("vignette", "暗角", -100, 100),
)

DETAIL_SPECS = (
    SliderSpec("sharpen_radius", "锐化半径", 30, 300, 100, 0.8),
    SliderSpec("sharpen_detail", "锐化细节", 0, 100, default=25),
    SliderSpec("sharpen_masking", "锐化蒙版", 0, 100),
    SliderSpec("luminance_noise_reduction", "明度降噪", 0, 100),
    SliderSpec("luminance_noise_reduction_detail", "明度细节", 0, 100, default=50),
    SliderSpec("luminance_noise_reduction_contrast", "明度对比", 0, 100),
    SliderSpec("color_noise_reduction", "颜色降噪", 0, 100),
    SliderSpec("color_noise_reduction_detail", "颜色细节", 0, 100, default=50),
    SliderSpec("color_noise_reduction_smoothness", "颜色平滑度", 0, 100, default=50),
)

EFFECTS_SPECS = (
    SliderSpec("vignette_midpoint", "暗角中点", 0, 100, default=50),
    SliderSpec("vignette_roundness", "暗角圆度", -100, 100),
    SliderSpec("vignette_feather", "暗角羽化", 0, 100, default=50),
    SliderSpec("vignette_highlights", "暗角高光", 0, 100),
    SliderSpec("curve_refine_saturation", "曲线后饱和度", -100, 100),
    SliderSpec("grain_amount", "颗粒数量", 0, 100),
    SliderSpec("grain_size", "颗粒大小", 0, 100, default=25),
    SliderSpec("grain_roughness", "颗粒粗糙度", 0, 100, default=50),
)

OPTICS_SPECS = (
    SliderSpec("defringe_purple_amount", "紫边校正", 0, 100),
    SliderSpec("defringe_purple_hue_low", "紫边色相下限", 0, 100, default=30),
    SliderSpec("defringe_purple_hue_high", "紫边色相上限", 0, 100, default=70),
    SliderSpec("defringe_green_amount", "绿边校正", 0, 100),
    SliderSpec("defringe_green_hue_low", "绿边色相下限", 0, 100, default=40),
    SliderSpec("defringe_green_hue_high", "绿边色相上限", 0, 100, default=60),
)

TRANSFORM_SPECS = (
    SliderSpec("vertical", "垂直", -100, 100),
    SliderSpec("horizontal", "水平", -100, 100),
    SliderSpec("rotate", "旋转", -4500, 4500, 100),
    SliderSpec("scale", "缩放", 50, 150, default=100),
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
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseDoubleClickEvent(event)
        self.sliderPressed.emit()
        self.setValue(getattr(self, "reset_value", 0))
        self.sliderReleased.emit()
        event.accept()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class CollapsibleSection(QWidget):
    """A compact disclosure row; collapsing changes layout, never edit state."""

    def __init__(self, title: str, keywords: str, expanded: bool = False, parent=None):
        super().__init__(parent)
        self.keywords = f"{title} {keywords}".casefold()
        self.header = QToolButton()
        self.header.setObjectName("sectionHeader")
        self.header.setText(title)
        self.header.setToolTip(keywords)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setCheckable(True)
        self.header.setSizePolicy(self.sizePolicy().Policy.Expanding, self.sizePolicy().Policy.Fixed)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(4, 6, 4, 10)
        self.body_layout.setSpacing(8)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.body)
        self.header.toggled.connect(self.set_expanded)
        self.set_expanded(expanded)

    def set_expanded(self, expanded: bool) -> None:
        self.header.setChecked(expanded)
        self.header.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.body.setVisible(expanded)


class ParameterSlider(QWidget):
    value_changed = Signal(str, float)
    interaction_started = Signal(str)
    interaction_finished = Signal(str)

    def __init__(self, spec: SliderSpec, parent=None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.label = QLabel(spec.label)
        self.value_label = NoWheelDoubleSpinBox()
        self.value_label.setRange(spec.minimum / spec.scale * spec.display_multiplier, spec.maximum / spec.scale * spec.display_multiplier)
        self.value_label.setDecimals(2 if spec.scale / spec.display_multiplier != 1 else 0)
        self.value_label.setSingleStep(spec.display_multiplier / spec.scale)
        self.value_label.setSuffix(spec.suffix)
        self.value_label.setMinimumWidth(76)
        self.value_label.setMaximumWidth(88)
        self.value_label.setKeyboardTracking(False)
        self.value_label.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.slider = NoWheelSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(spec.minimum, spec.maximum)
        self.slider.reset_value = round(spec.default * spec.scale)
        self.slider.setValue(self.slider.reset_value)
        self.value_label.setValue(spec.default * spec.display_multiplier)
        self.setToolTip(f"{spec.label} / {spec.key.replace('_', ' ').title()}\n双击滑块恢复默认值 {spec.default * spec.display_multiplier:g}{spec.suffix}")
        self.label.setBuddy(self.value_label)
        self.slider.setAccessibleName(spec.label)
        self.value_label.setAccessibleName(f"{spec.label}数值")
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
        self.value_label.setValue(value * self.spec.display_multiplier)
        self.value_label.blockSignals(False)
        self.value_changed.emit(self.spec.key, self.slider.value() / self.spec.scale)

    def _spin_value_changed(self, value: float) -> None:
        value /= self.spec.display_multiplier
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
        self.value_label.setValue(value * self.spec.display_multiplier)
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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._sections: list[CollapsibleSection] = []
        self._section_controls: dict[CollapsibleSection, list[ParameterSlider]] = {}
        self._saved_expansion: list[bool] | None = None
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("编辑")
        title.setObjectName("panelTitle")
        title.setStyleSheet("font-size: 13pt; font-weight: 600;")
        reset = QPushButton("重置")
        reset.setToolTip("重置当前照片的所有调整 · Ctrl+R")
        reset.clicked.connect(self.reset_requested)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(reset)
        layout.addLayout(header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索调整… 如曝光、HSL、Grain")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("搜索调整参数")
        layout.addWidget(self.search)
        self.no_results = QLabel("没有匹配的调整")
        self.no_results.setObjectName("mutedLabel")
        self.no_results.hide()
        layout.addWidget(self.no_results)

        self.controls: dict[str, ParameterSlider] = {}
        for title, keywords, keys, expanded in (
            ("明暗", "Light · Exposure / Contrast / Highlights / Shadows", ("exposure", "contrast", "highlights", "shadows", "whites", "blacks"), True),
            ("色彩", "Color · White balance / Saturation", ("temperature", "tint", "saturation", "vibrance"), False),
            ("质感", "Presence · Clarity / Texture / Dehaze", ("clarity", "texture", "dehaze"), False),
        ):
            section = self._section(layout, title, keywords, expanded)
            for spec in BASIC_SPECS:
                if spec.key in keys:
                    self._add_basic_control(section, spec)

        hsl_group = self._section(layout, "颜色混合 · HSL", "Color mixer · Hue / Saturation / Luminance")
        hsl_layout = hsl_group.body_layout
        self.hsl_selector = NoWheelComboBox()
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
            self._section_controls[hsl_group].append(control)
        self.hsl_selector.currentIndexChanged.connect(self._show_selected_hsl)

        curve_group = self._section(layout, "曲线", "Tone curves · RGB / Red / Green / Blue")
        curve_layout = curve_group.body_layout
        self.curve_panel = CurvePanel()
        self.curve_panel.curve_changed.connect(self.curve_changed)
        self.curve_panel.interaction_started.connect(lambda: self.interaction_started.emit("调整曲线"))
        self.curve_panel.interaction_finished.connect(lambda: self.interaction_finished.emit("调整曲线"))
        curve_layout.addWidget(self.curve_panel)

        grading_group = self._section(layout, "色彩分级", "Color grading · Shadows / Midtones / Highlights")
        grading_layout = grading_group.body_layout
        self.grading_selector = NoWheelComboBox()
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
            self._section_controls[grading_group].append(control)
        self.grading_selector.currentIndexChanged.connect(self._show_selected_grading)

        self.advanced_controls: dict[str, dict[str, ParameterSlider]] = {}
        detail_group = self._section(layout, "细节", "Detail · Sharpening / Noise reduction")
        self._add_basic_control(detail_group, next(spec for spec in BASIC_SPECS if spec.key == "sharpen"))
        self._add_advanced_controls(detail_group, "detail", DETAIL_SPECS)
        effects_group = self._section(layout, "效果", "Effects · Vignette / Film grain")
        effects_layout = effects_group.body_layout
        self._add_basic_control(effects_group, next(spec for spec in BASIC_SPECS if spec.key == "vignette"))
        self._add_advanced_controls(effects_group, "effects", EFFECTS_SPECS)
        self.vignette_style = NoWheelComboBox()
        self.vignette_style.addItem("暗角样式：绘制叠加", 0)
        self.vignette_style.addItem("暗角样式：高光优先", 1)
        self.vignette_style.addItem("暗角样式：颜色优先", 2)
        self.vignette_style.addItem("暗角样式：保留", 3)
        self.vignette_style.currentIndexChanged.connect(
            lambda _index: self.advanced_adjustment_changed.emit("effects", "vignette_style", self.vignette_style.currentData())
        )
        effects_layout.addWidget(self.vignette_style)

        optics_group = self._section(layout, "光学", "Optics · Chromatic aberration / Defringe")
        optics_layout = optics_group.body_layout
        self.remove_chromatic_aberration = QCheckBox("自动去色边（紫 / 绿）")
        self.remove_chromatic_aberration.toggled.connect(
            lambda checked: self.advanced_adjustment_changed.emit("optics", "remove_chromatic_aberration", checked)
        )
        optics_layout.addWidget(self.remove_chromatic_aberration)
        self._add_advanced_controls(optics_group, "optics", OPTICS_SPECS)

        self._add_advanced_group(layout, "几何", "transform", TRANSFORM_SPECS, "Geometry · Perspective / Rotate / Scale")
        self._add_advanced_group(layout, "相机校准", "calibration", CALIBRATION_SPECS, "Calibration · Red / Green / Blue primaries")
        layout.addStretch()
        self.setWidget(container)
        self._state = EditorState()
        self.search.textChanged.connect(self._filter_controls)
        self.set_state(self._state)

    def _section(self, layout: QVBoxLayout, title: str, keywords: str, expanded: bool = False) -> CollapsibleSection:
        section = CollapsibleSection(title, keywords, expanded)
        self._sections.append(section)
        self._section_controls[section] = []
        layout.addWidget(section)
        return section

    def _add_basic_control(self, section: CollapsibleSection, spec: SliderSpec) -> None:
        control = ParameterSlider(spec)
        control.value_changed.connect(self.adjustment_changed)
        control.interaction_started.connect(lambda _key, label=spec.label: self.interaction_started.emit(label))
        control.interaction_finished.connect(lambda _key, label=spec.label: self.interaction_finished.emit(label))
        self.controls[spec.key] = control
        self._section_controls[section].append(control)
        section.body_layout.addWidget(control)

    def _filter_controls(self, query: str) -> None:
        query = query.strip().casefold()
        if query and self._saved_expansion is None:
            self._saved_expansion = [section.header.isChecked() for section in self._sections]
        matches = 0
        for index, section in enumerate(self._sections):
            section_match = query in section.keywords
            controls = self._section_controls[section]
            any_control = False
            for control in controls:
                terms = f"{control.spec.label} {control.spec.key} {control.spec.key.replace('_', ' ')}".casefold()
                visible = not query or section_match or query in terms
                control.setVisible(visible)
                any_control |= visible
            visible = not query or section_match or any_control
            section.setVisible(visible)
            matches += int(visible)
            if query and visible:
                section.set_expanded(True)
            elif not query and self._saved_expansion is not None:
                section.set_expanded(self._saved_expansion[index])
        self.no_results.setVisible(matches == 0)
        if not query:
            self._saved_expansion = None
        self.vignette_style.setVisible(not query or query in "效果 effects 暗角样式 vignette style")
        self.remove_chromatic_aberration.setVisible(not query or query in "光学 optics 移除色差 chromatic aberration")

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

    def _add_advanced_group(self, parent: QVBoxLayout, title: str, section: str, specs: tuple[SliderSpec, ...], keywords: str) -> None:
        group = self._section(parent, title, keywords)
        self._add_advanced_controls(group, section, specs)

    def _add_advanced_controls(self, group: CollapsibleSection, section: str, specs: tuple[SliderSpec, ...]) -> None:
        controls = self.advanced_controls.setdefault(section, {})
        for spec in specs:
            control = ParameterSlider(spec)
            control.value_changed.connect(
                lambda key, value, section_name=section: self.advanced_adjustment_changed.emit(section_name, key, value)
            )
            control.interaction_started.connect(
                lambda _key, title=group.header.text(): self.interaction_started.emit(f"调整{title}")
            )
            control.interaction_finished.connect(
                lambda _key, title=group.header.text(): self.interaction_finished.emit(f"调整{title}")
            )
            controls[spec.key] = control
            group.body_layout.addWidget(control)
            self._section_controls[group].append(control)

    def _show_selected_hsl(self) -> None:
        color = HSLColor(self.hsl_selector.currentData())
        values = self._state.hsl[color]
        for key, control in self.hsl_controls.items():
            control.set_value(getattr(values, key))

    def _hsl_value_changed(self, key: str, value: float) -> None:
        color = self.hsl_selector.currentData()
        setattr(self._state.hsl[HSLColor(color)], key, value)
        self.hsl_changed.emit(color, key, value)

    def _show_selected_grading(self) -> None:
        region = self.grading_selector.currentData()
        values = getattr(self._state.color_grading, region)
        for key, control in self.grading_controls.items():
            control.set_value(getattr(values, key))

    def _grading_value_changed(self, key: str, value: float) -> None:
        setattr(getattr(self._state.color_grading, self.grading_selector.currentData()), key, value)
        self.color_grading_changed.emit(self.grading_selector.currentData(), key, value)
