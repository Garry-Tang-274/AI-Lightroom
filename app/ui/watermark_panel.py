from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSlider, QVBoxLayout, QWidget

from app.core.editor_state import EditorState


class WatermarkPanel(QWidget):
    import_requested = Signal()
    remove_requested = Signal(str)
    property_changed = Signal(str, str, object)
    library_rename_requested = Signal(str)
    library_delete_requested = Signal(str)
    library_default_requested = Signal(str)
    default_add_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state = EditorState()
        self._selected_id: str | None = None
        self._updating = False
        self.import_button = QPushButton("导入水印并添加")
        self.import_button.setObjectName("accentButton")
        self.remove_button = QPushButton("移除图层")
        self.rename_button = QPushButton("重命名库项目")
        self.default_button = QPushButton("设为默认")
        self.delete_library_button = QPushButton("删除库项目")
        self.add_default_button = QPushButton("添加默认水印")
        self.remove_button.setEnabled(False)
        self.list_widget = QListWidget()
        self.empty = QLabel("导入 PNG、JPG 或 WEBP 水印。水印以非破坏式图层显示，并在导出时叠加。")
        self.empty.setWordWrap(True)
        self.enabled = QPushButton("显示")
        self.enabled.setCheckable(True)
        self.position = QComboBox()
        for label, value in (("左上", "top_left"), ("右上", "top_right"), ("左下", "bottom_left"), ("右下", "bottom_right"), ("居中", "center"), ("自定义", "custom")):
            self.position.addItem(label, value)
        self.scale = QSlider(Qt.Orientation.Horizontal)
        self.scale.setRange(1, 100)
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.margin = QSlider(Qt.Orientation.Horizontal)
        self.margin.setRange(0, 25)
        form = QFormLayout()
        form.addRow("显示", self.enabled)
        form.addRow("位置", self.position)
        form.addRow("大小", self.scale)
        form.addRow("不透明度", self.opacity)
        form.addRow("边距", self.margin)
        buttons = QHBoxLayout()
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.remove_button)
        library_buttons = QHBoxLayout()
        library_buttons.addWidget(self.add_default_button)
        library_buttons.addWidget(self.rename_button)
        library_buttons.addWidget(self.default_button)
        library_buttons.addWidget(self.delete_library_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(buttons)
        layout.addLayout(library_buttons)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self.empty)
        layout.addLayout(form)
        self.import_button.clicked.connect(self.import_requested)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self._selected_id) if self._selected_id else None)
        self.rename_button.clicked.connect(lambda: self.library_rename_requested.emit(self._selected_asset_id()) if self._selected_asset_id() else None)
        self.default_button.clicked.connect(lambda: self.library_default_requested.emit(self._selected_asset_id()) if self._selected_asset_id() else None)
        self.delete_library_button.clicked.connect(lambda: self.library_delete_requested.emit(self._selected_asset_id()) if self._selected_asset_id() else None)
        self.add_default_button.clicked.connect(self.default_add_requested)
        self.list_widget.currentItemChanged.connect(self._select)
        self.enabled.toggled.connect(lambda value: self._changed("enabled", value))
        self.position.currentIndexChanged.connect(lambda _index: self._changed("position", self.position.currentData()))
        self.scale.valueChanged.connect(lambda value: self._changed("scale", value / 100.0))
        self.opacity.valueChanged.connect(lambda value: self._changed("opacity", value / 100.0))
        self.margin.valueChanged.connect(lambda value: self._changed("margin", value / 100.0))

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
            self.remove_button.setEnabled(False)

    def _select(self, current, previous) -> None:
        if self._updating:
            return
        self._selected_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        layer = next((item for item in self._state.watermarks if item.id == self._selected_id), None)
        self.remove_button.setEnabled(layer is not None)
        if layer is None:
            return
        self._updating = True
        self.enabled.setChecked(layer.enabled)
        self.position.setCurrentIndex(max(0, self.position.findData(layer.position)))
        self.scale.setValue(round(layer.scale * 100))
        self.opacity.setValue(round(layer.opacity * 100))
        self.margin.setValue(round(layer.margin * 100))
        self._updating = False

    def _changed(self, key: str, value) -> None:
        if not self._updating and self._selected_id:
            self.property_changed.emit(self._selected_id, key, value)

    def _selected_asset_id(self) -> str | None:
        layer = next((item for item in self._state.watermarks if item.id == self._selected_id), None)
        return layer.asset_id if layer else None
