from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.editor_state import EditorState, MaskType
from app.ui.adjustment_panel import CollapsibleSection, NoWheelComboBox, ParameterSlider, SliderSpec


LOCAL_SPECS = (
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
)


MASK_PARAMETER_SPECS = {
    MaskType.LINEAR_GRADIENT: (
        SliderSpec("start_x", "起点 X", 0, 100, 100, 0.5),
        SliderSpec("start_y", "起点 Y", 0, 100, 100),
        SliderSpec("end_x", "终点 X", 0, 100, 100, 0.5),
        SliderSpec("end_y", "终点 Y", 0, 100, 100, 0.65),
    ),
    MaskType.RADIAL_GRADIENT: (
        SliderSpec("center_x", "中心 X", 0, 100, 100, 0.5),
        SliderSpec("center_y", "中心 Y", 0, 100, 100, 0.5),
        SliderSpec("radius_x", "水平半径", 1, 150, 100, 0.35),
        SliderSpec("radius_y", "垂直半径", 1, 150, 100, 0.35),
        SliderSpec("rotation", "旋转角度", -180, 180),
    ),
    MaskType.LUMINANCE_RANGE: (
        SliderSpec("min", "明度下限", 0, 100, 100, 0.55),
        SliderSpec("max", "明度上限", 0, 100, 100, 1.0),
    ),
    MaskType.COLOR_RANGE: (
        SliderSpec("hue", "目标色相", 0, 360, default=210),
        SliderSpec("tolerance", "色相范围", 1, 180, default=35),
        SliderSpec("min_saturation", "最低饱和度", 0, 100, 100, 0.08),
    ),
}


class MaskPanel(QWidget):
    create_mask_requested = Signal(str)
    remove_mask_requested = Signal(str)
    local_adjustment_changed = Signal(str, str, float)
    mask_property_changed = Signal(str, str, object)
    brush_mode_changed = Signal(bool, float)
    interaction_started = Signal(str)
    interaction_finished = Signal(str)
    mask_selected = Signal(str)
    mask_preview_toggled = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state = EditorState()
        self._updating = False
        self._selected_id: str | None = None

        self.type_selector = NoWheelComboBox()
        for label, key in (
            ("线性渐变", MaskType.LINEAR_GRADIENT.value),
            ("径向渐变", MaskType.RADIAL_GRADIENT.value),
            ("明度范围", MaskType.LUMINANCE_RANGE.value),
            ("颜色范围", MaskType.COLOR_RANGE.value),
            ("天空", MaskType.SKY.value),
            ("主体", MaskType.SUBJECT.value),
            ("植被", "semantic:vegetation"),
            ("地面", "semantic:ground"),
            ("水面", "semantic:water"),
            ("建筑", "semantic:building"),
            ("道路", "semantic:road"),
            ("人物", "semantic:person"),
            ("车辆", "semantic:vehicle"),
            ("前景", "semantic:foreground"),
            ("背景", "semantic:background"),
            ("画笔", MaskType.BRUSH.value),
        ):
            self.type_selector.addItem(label, key)
        self.add_button = QPushButton("添加")
        self.add_button.setObjectName("accentButton")
        self.remove_button = QPushButton("删除")
        self.remove_button.setEnabled(False)
        self.preview_button = QPushButton("显示蒙版")
        self.preview_button.setCheckable(True)
        self.preview_button.setEnabled(False)
        self.list_widget = QListWidget()
        self.empty_label = QLabel("添加局部蒙版后，可单独调整选中区域。")
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: #899098; padding: 6px;")

        add_row = QHBoxLayout()
        add_row.addWidget(self.type_selector, 1)
        add_row.addWidget(self.add_button)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.preview_button)
        button_row.addWidget(self.remove_button)

        self.properties = QWidget()
        properties_layout = QVBoxLayout(self.properties)
        properties_layout.setContentsMargins(0, 4, 0, 0)
        self.enabled_check = QCheckBox("启用蒙版")
        self.enabled_check.setChecked(True)
        self.invert_check = QCheckBox("反转")
        checks = QHBoxLayout()
        checks.addWidget(self.enabled_check)
        checks.addWidget(self.invert_check)
        checks.addStretch()
        properties_layout.addLayout(checks)

        self.opacity_control = ParameterSlider(SliderSpec("opacity", "不透明度", 0, 100, 100, 1.0, 100, "%"))
        self.feather_control = ParameterSlider(SliderSpec("feather", "羽化", 0, 100, 100, 0.5, 100, "%"))
        properties_layout.addWidget(self.opacity_control)
        properties_layout.addWidget(self.feather_control)

        self.range_section = CollapsibleSection("区域与范围", "Mask geometry / range", expanded=True)
        self.parameter_controls: dict[MaskType, dict[str, ParameterSlider]] = {}
        for mask_type, specs in MASK_PARAMETER_SPECS.items():
            controls = self.parameter_controls.setdefault(mask_type, {})
            for spec in specs:
                control = ParameterSlider(spec)
                control.value_changed.connect(self._parameter_changed)
                control.interaction_started.connect(lambda _key: self.interaction_started.emit("调整蒙版范围"))
                control.interaction_finished.connect(lambda _key: self.interaction_finished.emit("调整蒙版范围"))
                self.range_section.body_layout.addWidget(control)
                controls[spec.key] = control
        properties_layout.addWidget(self.range_section)
        self.range_section.hide()

        self.paint_button = QPushButton("在图片上绘制")
        self.paint_button.setCheckable(True)
        self.paint_button.setVisible(False)
        self.brush_size = ParameterSlider(SliderSpec("brush_size", "画笔大小", 1, 40, 100, 0.08, 100, "%"))
        self.brush_size.set_value(0.08)
        self.brush_size.setVisible(False)
        self.brush_hardness = ParameterSlider(SliderSpec("brush_hardness", "画笔硬度", 0, 100, 100, 0.65, 100, "%"))
        self.brush_hardness.set_value(0.65)
        self.brush_hardness.setVisible(False)
        self.brush_opacity = ParameterSlider(SliderSpec("brush_opacity", "画笔不透明度", 1, 100, 100, 1.0, 100, "%"))
        self.brush_opacity.set_value(1.0)
        self.brush_opacity.setVisible(False)
        self.brush_erase = QCheckBox("擦除笔触")
        self.brush_erase.setVisible(False)
        properties_layout.addWidget(self.paint_button)
        properties_layout.addWidget(self.brush_size)
        properties_layout.addWidget(self.brush_hardness)
        properties_layout.addWidget(self.brush_opacity)
        properties_layout.addWidget(self.brush_erase)

        local_title = QLabel("局部参数")
        local_title.setStyleSheet("font-weight: 600; padding-top: 5px;")
        properties_layout.addWidget(local_title)
        self.controls: dict[str, ParameterSlider] = {}
        for spec in LOCAL_SPECS:
            control = ParameterSlider(spec)
            control.value_changed.connect(self._local_changed)
            self.controls[spec.key] = control
            properties_layout.addWidget(control)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.properties)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(add_row)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self.empty_label)
        layout.addLayout(button_row)
        layout.addWidget(scroll, 2)

        self.add_button.clicked.connect(lambda: self.create_mask_requested.emit(self.type_selector.currentData()))
        self.remove_button.clicked.connect(self._remove)
        self.list_widget.currentItemChanged.connect(self._selection_changed)
        self.enabled_check.toggled.connect(lambda value: self._property_changed("enabled", value))
        self.invert_check.toggled.connect(lambda value: self._property_changed("inverted", value))
        self.opacity_control.value_changed.connect(lambda _key, value: self._property_changed("opacity", value))
        self.feather_control.value_changed.connect(lambda _key, value: self._property_changed("feather", value))
        for control in (self.opacity_control, self.feather_control, *self.controls.values()):
            control.interaction_started.connect(lambda _key: self.interaction_started.emit("调整局部蒙版"))
            control.interaction_finished.connect(lambda _key: self.interaction_finished.emit("调整局部蒙版"))
        self.preview_button.toggled.connect(self._preview_toggled)
        self.paint_button.toggled.connect(self._paint_toggled)
        self.brush_size.value_changed.connect(self._brush_size_changed)
        self.properties.setEnabled(False)

    @property
    def selected_mask_id(self) -> str | None:
        return self._selected_id

    @property
    def brush_hardness_value(self) -> float:
        return self.brush_hardness.slider.value() / self.brush_hardness.spec.scale

    @property
    def brush_opacity_value(self) -> float:
        return self.brush_opacity.slider.value() / self.brush_opacity.spec.scale

    @property
    def brush_erase_value(self) -> bool:
        return self.brush_erase.isChecked()

    def set_state(self, state: EditorState, select_id: str | None = None) -> None:
        requested = select_id or self._selected_id
        was_painting = self.paint_button.isChecked() and requested == self._selected_id
        self._state = state.snapshot()
        self._updating = True
        self.list_widget.clear()
        selected_item = None
        for layer in self._state.masks:
            item = QListWidgetItem(layer.name)
            item.setData(Qt.ItemDataRole.UserRole, layer.id)
            if not layer.enabled:
                item.setForeground(Qt.GlobalColor.gray)
            self.list_widget.addItem(item)
            if layer.id == requested:
                selected_item = item
        self.empty_label.setVisible(not self._state.masks)
        self._updating = False
        if selected_item is not None:
            self.list_widget.setCurrentItem(selected_item)
        elif self.list_widget.count():
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)
        else:
            self._selected_id = None
            self.properties.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.preview_button.setEnabled(False)
            self.brush_mode_changed.emit(False, self._brush_size_value())
            self.preview_button.setChecked(False)
            self.mask_selected.emit("")
        if was_painting and self._selected_layer() and self._selected_layer().type == MaskType.BRUSH:
            self.paint_button.setChecked(True)

    def _selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if self._updating:
            return
        self.paint_button.blockSignals(True)
        self.paint_button.setChecked(False)
        self.paint_button.blockSignals(False)
        self.brush_mode_changed.emit(False, self._brush_size_value())
        self._selected_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.mask_selected.emit(self._selected_id or "")
        layer = self._selected_layer()
        self.properties.setEnabled(layer is not None)
        self.remove_button.setEnabled(layer is not None)
        self.preview_button.setEnabled(layer is not None)
        if layer is None:
            return
        self._updating = True
        self.enabled_check.setChecked(layer.enabled)
        self.invert_check.setChecked(layer.inverted)
        self.opacity_control.set_value(layer.opacity)
        self.feather_control.set_value(layer.feather)
        has_range = layer.type in self.parameter_controls
        self.range_section.setVisible(has_range)
        self.feather_control.setVisible(layer.type in {MaskType.RADIAL_GRADIENT, MaskType.LUMINANCE_RANGE, MaskType.COLOR_RANGE})
        for mask_type, controls in self.parameter_controls.items():
            for key, control in controls.items():
                control.setVisible(mask_type == layer.type)
                if mask_type == layer.type:
                    control.set_value(float(layer.parameters.get(key, control.spec.default)))
        for key, control in self.controls.items():
            control.set_value(getattr(layer.adjustments, key))
        is_brush = layer.type == MaskType.BRUSH
        self.paint_button.setVisible(is_brush)
        self.brush_size.setVisible(is_brush)
        self.brush_hardness.setVisible(is_brush)
        self.brush_opacity.setVisible(is_brush)
        self.brush_erase.setVisible(is_brush)
        self._updating = False

    def _selected_layer(self):
        return next((layer for layer in self._state.masks if layer.id == self._selected_id), None)

    def _remove(self) -> None:
        if self._selected_id:
            self.remove_mask_requested.emit(self._selected_id)

    def _local_changed(self, key: str, value: float) -> None:
        if not self._updating and self._selected_id:
            setattr(self._selected_layer().adjustments, key, value)
            self.local_adjustment_changed.emit(self._selected_id, key, value)

    def _property_changed(self, key: str, value) -> None:
        if not self._updating and self._selected_id:
            setattr(self._selected_layer(), key, value)
            self.mask_property_changed.emit(self._selected_id, key, value)

    def _parameter_changed(self, key: str, value: float) -> None:
        if self._updating or not self._selected_id:
            return
        layer = self._selected_layer()
        parameters = dict(layer.parameters)
        parameters[key] = value
        if layer.type == MaskType.LUMINANCE_RANGE:
            other = "max" if key == "min" else "min"
            other_default = 1.0 if other == "max" else 0.55
            other_value = float(parameters.get(other, other_default))
            if (key == "min" and value > other_value) or (key == "max" and value < other_value):
                parameters[other] = value
                self.parameter_controls[layer.type][other].set_value(value)
        layer.parameters = parameters
        self.mask_property_changed.emit(self._selected_id, "parameters", parameters)

    def _preview_toggled(self, visible: bool) -> None:
        self.preview_button.setText("隐藏蒙版" if visible else "显示蒙版")
        self.mask_preview_toggled.emit(visible)

    def _paint_toggled(self, checked: bool) -> None:
        if not self._updating:
            self.brush_mode_changed.emit(checked, self._brush_size_value())

    def _brush_size_changed(self, key: str, value: float) -> None:
        if self.paint_button.isChecked():
            self.brush_mode_changed.emit(True, value)

    def _brush_size_value(self) -> float:
        return self.brush_size.slider.value() / self.brush_size.spec.scale
