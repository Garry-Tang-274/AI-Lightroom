from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.core.editor_state import EditorState
from app.ui.adjustment_panel import NoWheelComboBox, ParameterSlider, SliderSpec


class WatermarkPanel(QWidget):
    import_requested = Signal()
    remove_requested = Signal(str)
    property_changed = Signal(str, str, object)
    library_rename_requested = Signal(str)
    library_delete_requested = Signal(str)
    library_default_requested = Signal(str)
    default_add_requested = Signal()
    interaction_started = Signal(str)
    interaction_finished = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state = EditorState()
        self._selected_id: str | None = None
        self._updating = False
        self.import_button = QPushButton("导入水印")
        self.import_button.setToolTip("导入 PNG / JPG / WEBP 并添加为图层")
        self.import_button.setObjectName("accentButton")
        self.remove_button = QPushButton("移除图层")
        self.rename_button = QPushButton("重命名")
        self.default_button = QPushButton("设为默认")
        self.delete_library_button = QPushButton("从库删除")
        self.add_default_button = QPushButton("添加默认")
        self.remove_button.setEnabled(False)
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(72)
        self.list_widget.setMaximumHeight(180)
        self.empty = QLabel("导入 PNG、JPG 或 WEBP 水印。水印以非破坏式图层显示，并在导出时叠加。")
        self.empty.setWordWrap(True)
        self.enabled = QCheckBox("显示水印")
        self.position = NoWheelComboBox()
        for label, value in (("左上", "top_left"), ("右上", "top_right"), ("左下", "bottom_left"), ("右下", "bottom_right"), ("居中", "center"), ("自定义", "custom")):
            self.position.addItem(label, value)
        self.scale_control = ParameterSlider(SliderSpec("scale", "大小", 1, 100, 100, 0.18, 100, "%"))
        self.opacity_control = ParameterSlider(SliderSpec("opacity", "不透明度", 0, 100, 100, 1.0, 100, "%"))
        self.margin_control = ParameterSlider(SliderSpec("margin", "边距", 0, 25, 100, 0.03, 100, "%"))
        self.x_control = ParameterSlider(SliderSpec("x", "水平位置", 0, 100, 100, 1.0, 100, "%"))
        self.y_control = ParameterSlider(SliderSpec("y", "垂直位置", 0, 100, 100, 1.0, 100, "%"))
        self.scale = self.scale_control.slider
        self.opacity = self.opacity_control.slider
        self.margin = self.margin_control.slider
        self.properties = QWidget()
        properties_layout = QVBoxLayout(self.properties)
        properties_layout.setContentsMargins(0, 4, 0, 0)
        form = QFormLayout()
        form.addRow(self.enabled)
        form.addRow("位置", self.position)
        properties_layout.addLayout(form)
        for control in (self.x_control, self.y_control, self.scale_control, self.opacity_control, self.margin_control):
            properties_layout.addWidget(control)
            control.value_changed.connect(self._changed)
            control.interaction_started.connect(lambda _key: self.interaction_started.emit("调整水印"))
            control.interaction_finished.connect(lambda _key: self.interaction_finished.emit("调整水印"))
        properties_layout.addStretch()
        self.x_control.hide()
        self.y_control.hide()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.properties)
        buttons = QHBoxLayout()
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.remove_button)
        library_buttons = QGridLayout()
        library_buttons.addWidget(self.add_default_button, 0, 0)
        library_buttons.addWidget(self.default_button, 0, 1)
        library_buttons.addWidget(self.rename_button, 1, 0)
        library_buttons.addWidget(self.delete_library_button, 1, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(buttons)
        layout.addLayout(library_buttons)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self.empty)
        layout.addWidget(scroll, 2)
        self.import_button.clicked.connect(self.import_requested)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self._selected_id) if self._selected_id else None)
        self.rename_button.clicked.connect(lambda: self.library_rename_requested.emit(self._selected_asset_id()) if self._selected_asset_id() else None)
        self.default_button.clicked.connect(lambda: self.library_default_requested.emit(self._selected_asset_id()) if self._selected_asset_id() else None)
        self.delete_library_button.clicked.connect(lambda: self.library_delete_requested.emit(self._selected_asset_id()) if self._selected_asset_id() else None)
        self.add_default_button.clicked.connect(self.default_add_requested)
        self.list_widget.currentItemChanged.connect(self._select)
        self.enabled.toggled.connect(lambda value: self._changed("enabled", value))
        self.position.currentIndexChanged.connect(self._position_changed)
        self._set_selection_enabled(False)

    def set_state(self, state: EditorState) -> None:
        selected = self._selected_id
        self._state = state.snapshot()
        self._updating = True
        self.list_widget.clear()
        selected_item = None
        for layer in self._state.watermarks:
            item = QListWidgetItem(layer.name)
            item.setData(Qt.ItemDataRole.UserRole, layer.id)
            self.list_widget.addItem(item)
            if layer.id == selected:
                selected_item = item
        self.empty.setVisible(not self._state.watermarks)
        self._updating = False
        if selected_item:
            self.list_widget.setCurrentItem(selected_item)
        elif self.list_widget.count():
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)
        else:
            self._selected_id = None
            self._set_selection_enabled(False)

    def _select(self, current, previous) -> None:
        if self._updating:
            return
        self._selected_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        layer = next((item for item in self._state.watermarks if item.id == self._selected_id), None)
        self._set_selection_enabled(layer is not None)
        if layer is None:
            return
        self._updating = True
        self.enabled.setChecked(layer.enabled)
        self.position.setCurrentIndex(max(0, self.position.findData(layer.position)))
        self.scale_control.set_value(layer.scale)
        self.opacity_control.set_value(layer.opacity)
        self.margin_control.set_value(layer.margin)
        self.x_control.set_value(layer.x)
        self.y_control.set_value(layer.y)
        self.x_control.setVisible(layer.position == "custom")
        self.y_control.setVisible(layer.position == "custom")
        self._updating = False

    def _changed(self, key: str, value) -> None:
        if not self._updating and self._selected_id:
            layer = next((item for item in self._state.watermarks if item.id == self._selected_id), None)
            if layer is not None:
                setattr(layer, key, value)
            self.property_changed.emit(self._selected_id, key, value)

    def _position_changed(self) -> None:
        position = self.position.currentData()
        self.x_control.setVisible(position == "custom")
        self.y_control.setVisible(position == "custom")
        self._changed("position", position)

    def _set_selection_enabled(self, enabled: bool) -> None:
        for widget in (self.properties, self.remove_button, self.rename_button, self.default_button, self.delete_library_button):
            widget.setEnabled(enabled)

    def _selected_asset_id(self) -> str | None:
        layer = next((item for item in self._state.watermarks if item.id == self._selected_id), None)
        return layer.asset_id if layer else None
