from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QThreadPool, QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.adjustment_panel import AdjustmentPanel
from app.ui.ai_panel import AIPanel
from app.ui.ai_worker import AIEditWorker
from app.ui.image_view import ImageView
from app.ui.mask_panel import MaskPanel
from app.ui.render_worker import PreviewRenderWorker
from app.ui.settings_dialog import SettingsDialog
from app.ui.usage_dialog import AIUsageDialog
from app.ui.watermark_panel import WatermarkPanel
from app.ui.histogram_widget import HistogramWidget
from app.ui.export_worker import ExportWorker
from app.core.editor_state import (
    BrushPoint,
    BrushStroke,
    ColorWheel,
    EditorState,
    HSLAdjustment,
    HSLColor,
    MaskLayer,
    MaskType,
    WatermarkLayer,
)
from app.core.history import HistoryManager
from app.utils.io_utils import LoadedImage, load_image, make_preview
from app.utils.config import SettingsManager
from app.ai.errors import AIRequestError
from app.ai.usage import AIUsageManager
from app.ai.provider_registry import provider_registry
from app.core.watermarks import WatermarkLibrary
from app.core.session_store import SessionStore
from app.core.masks import generate_mask, mask_confidence


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Lightroom")
        self.resize(1480, 920)
        self.setMinimumSize(1050, 680)
        self.settings_manager = SettingsManager()
        self.runtime_settings = self.settings_manager.runtime()
        self.settings = self.settings_manager.store
        self.usage_manager = AIUsageManager(self.settings)
        self.watermark_library = WatermarkLibrary(self.settings)
        self.session_store = SessionStore(self.settings)
        self.loaded_image: LoadedImage | None = None
        self.state = EditorState()
        self.history = HistoryManager()
        self.preview_source = None
        self.current_preview = None
        self._render_generation = 0
        self._render_pool = QThreadPool(self)
        self._render_pool.setMaxThreadCount(self.runtime_settings.worker_threads)
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(16)
        self._render_timer.timeout.connect(self._start_preview_render)
        self._history_timer = QTimer(self)
        self._history_timer.setSingleShot(True)
        self._history_timer.setInterval(350)
        self._history_timer.timeout.connect(self._flush_history)
        self._pending_history_label = "调整参数"
        self._active_interaction = False
        self._interaction_label = "调整参数"
        self._render_in_flight = False
        self._render_dirty = False
        self._export_worker = None
        self._ai_worker = None
        self._ai_details = ""
        self._last_ai_error: AIRequestError | None = None
        self._last_ai_prompt = ""
        self._adjustment_clipboard: dict | None = None
        self._showing_before = False
        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_workspace()
        self.statusBar().showMessage("就绪 — 打开 JPG 或 PNG 开始编辑")
        self.adjustments.set_enabled_for_image(False)
        self.ai_panel.set_ready(False)
        self._refresh_ai_status()

    def _build_actions(self) -> None:
        self.open_action = QAction("打开图片…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_image_dialog)
        self.export_action = QAction("导出…", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self.export_image_dialog)
        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        self.fit_action = QAction("适合窗口", self)
        self.fit_action.setShortcut(QKeySequence("F"))
        self.fit_action.triggered.connect(lambda: self.image_view.fit_to_view())
        self.actual_action = QAction("100%", self)
        self.actual_action.triggered.connect(lambda: self.image_view.actual_size())
        self.undo_action = QAction("撤销", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.undo)
        self.redo_action = QAction("重做", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.redo)
        self.reset_action = QAction("重置所有调整", self)
        self.reset_action.setShortcut(QKeySequence("Ctrl+R"))
        self.reset_action.triggered.connect(self.reset_edits)
        self.settings_action = QAction("设置…", self)
        self.settings_action.triggered.connect(self.open_settings)
        self.before_action = QAction("原图对比", self)
        self.before_action.setShortcut(QKeySequence("\\"))
        self.before_action.triggered.connect(self._toggle_before_after)
        self.copy_adjustments_action = QAction("复制调整", self)
        self.copy_adjustments_action.setShortcut(QKeySequence("Ctrl+Alt+C"))
        self.copy_adjustments_action.triggered.connect(self.copy_adjustments)
        self.paste_adjustments_action = QAction("粘贴调整", self)
        self.paste_adjustments_action.setShortcut(QKeySequence("Ctrl+Alt+V"))
        self.paste_adjustments_action.triggered.connect(self.paste_adjustments)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        edit_menu = self.menuBar().addMenu("编辑")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.copy_adjustments_action)
        edit_menu.addAction(self.paste_adjustments_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.reset_action)
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.fit_action)
        view_menu.addAction(self.actual_action)
        view_menu.addAction(self.before_action)
        help_menu = self.menuBar().addMenu("帮助")
        about = help_menu.addAction("关于 AI Lightroom")
        about.triggered.connect(self._show_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏", self)
        toolbar.setMovable(False)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.export_action)
        toolbar.addSeparator()
        toolbar.addAction(self.fit_action)
        toolbar.addAction(self.actual_action)
        toolbar.addSeparator()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        toolbar.addSeparator()
        self.before_button = QToolButton()
        self.before_button.setText("按住原图")
        self.before_button.pressed.connect(self._show_before)
        self.before_button.released.connect(self._show_after)
        toolbar.addWidget(self.before_button)
        self.addToolBar(toolbar)

    def _build_workspace(self) -> None:
        self.image_view = ImageView()
        self.adjustments = AdjustmentPanel()
        self.ai_panel = AIPanel()
        self.histogram = HistogramWidget()
        self.ai_panel.prompt_submitted.connect(self._run_ai_edit)
        self.ai_panel.details_requested.connect(self._show_ai_details)
        self.ai_panel.cancel_requested.connect(self._cancel_ai_request)
        self.ai_panel.usage_requested.connect(self._show_ai_usage)
        self.ai_panel.retry_requested.connect(self._retry_ai_request)
        self.adjustments.adjustment_changed.connect(self._set_basic_adjustment)
        self.adjustments.hsl_changed.connect(self._set_hsl_adjustment)
        self.adjustments.curve_changed.connect(self._set_curve)
        self.adjustments.color_grading_changed.connect(self._set_color_grading)
        self.adjustments.reset_requested.connect(self.reset_edits)
        self.adjustments.interaction_started.connect(self._begin_interaction)
        self.adjustments.interaction_finished.connect(self._finish_interaction)

        left_tabs = QTabWidget()
        history = QListWidget()
        history.addItem("打开图片后显示历史记录")
        masks = MaskPanel()
        watermarks = WatermarkPanel()
        left_tabs.addTab(history, "历史")
        left_tabs.addTab(masks, "蒙版")
        left_tabs.addTab(watermarks, "水印")
        self.history_list = history
        self.history_list.currentRowChanged.connect(self._history_row_selected)
        self.mask_panel = masks
        self.watermark_panel = watermarks
        self.mask_panel.create_mask_requested.connect(self._create_mask)
        self.mask_panel.remove_mask_requested.connect(self._remove_mask)
        self.mask_panel.local_adjustment_changed.connect(self._set_local_adjustment)
        self.mask_panel.mask_property_changed.connect(self._set_mask_property)
        self.mask_panel.brush_mode_changed.connect(self.image_view.set_brush_mode)
        self.mask_panel.mask_selected.connect(lambda _mask_id: self._update_mask_overlay())
        self.mask_panel.mask_preview_toggled.connect(lambda _visible: self._update_mask_overlay())
        self.mask_panel.interaction_started.connect(self._begin_interaction)
        self.mask_panel.interaction_finished.connect(self._finish_interaction)
        self.image_view.brush_stroke_finished.connect(self._add_brush_stroke)
        self.watermark_panel.import_requested.connect(self._import_watermark)
        self.watermark_panel.remove_requested.connect(self._remove_watermark)
        self.watermark_panel.property_changed.connect(self._set_watermark_property)
        self.watermark_panel.library_rename_requested.connect(self._rename_watermark_asset)
        self.watermark_panel.library_delete_requested.connect(self._delete_watermark_asset)
        self.watermark_panel.library_default_requested.connect(self._set_default_watermark)
        self.watermark_panel.default_add_requested.connect(self._add_default_watermark)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.addWidget(self.adjustments)
        vertical.addWidget(self.histogram)
        vertical.addWidget(self.ai_panel)
        vertical.setSizes([500, 150, 270])
        right_layout.addWidget(vertical)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_tabs)
        splitter.addWidget(self.image_view)
        splitter.addWidget(right)
        splitter.setSizes([210, 900, 360])
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

    def open_image_dialog(self) -> None:
        start = self.settings.value("last_open_dir", str(Path.home()))
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "打开图片",
            start,
            "图片 (*.jpg *.jpeg *.png);;所有文件 (*)",
        )
        if filename:
            self.open_image(filename)

    def open_image(self, filename: str) -> None:
        try:
            loaded = load_image(filename)
            preview = make_preview(loaded.pixels, self.runtime_settings.preview_size)
        except Exception as exc:  # user-facing boundary
            QMessageBox.critical(self, "无法打开图片", str(exc))
            return
        self._render_generation += 1
        self._render_timer.stop()
        self._history_timer.stop()
        self.loaded_image = loaded
        self.state = EditorState()
        self.history.reset(self.state, f"打开：{loaded.path.name}")
        recovered = self.session_store.load(loaded.path)
        if recovered and recovered.get("state"):
            answer = QMessageBox.question(
                self, "恢复编辑", "发现这张照片的已保存编辑。是否恢复？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                try:
                    self.state = EditorState.model_validate(recovered["state"])
                    history_entries = recovered.get("history", [])
                    if history_entries:
                        first = EditorState.model_validate(history_entries[0]["state"])
                        self.history.reset(first, str(history_entries[0].get("label", "打开图片")))
                        for entry in history_entries[1:]:
                            self.history.push(EditorState.model_validate(entry["state"]), str(entry.get("label", "编辑")))
                except (KeyError, TypeError, ValueError):
                    self.state = EditorState()
                    self.history.reset(self.state, f"打开：{loaded.path.name}")
        self.preview_source = preview
        self.current_preview = preview.copy()
        self.adjustments.set_state(self.state)
        self.mask_panel.set_state(self.state)
        self.watermark_panel.set_state(self.state)
        self.image_view.set_image(preview)
        self.histogram.set_image(preview)
        self.settings.setValue("last_open_dir", str(loaded.path.parent))
        self.setWindowTitle(f"{loaded.path.name} — AI Lightroom")
        self.statusBar().showMessage(loaded.description)
        self._refresh_history_ui()
        self.adjustments.set_enabled_for_image(True)
        self.ai_panel.set_ready(True)
        self.export_action.setEnabled(True)
        self._refresh_ai_status()
        if not self.state.is_pristine():
            self._queue_preview_render()

    def _set_basic_adjustment(self, key: str, value: float) -> None:
        if self.preview_source is None:
            return
        try:
            self.state.basic = self.state.basic.with_value(key, value)
        except (KeyError, ValueError):
            return
        self._render_generation += 1
        self._render_timer.start()
        label = self.adjustments.controls[key].label.text()
        self._schedule_history(f"调整：{label}")

    def _set_hsl_adjustment(self, color: str, key: str, value: float) -> None:
        if self.preview_source is None:
            return
        target = self.state.hsl[HSLColor(color)].model_dump()
        target[key] = value
        self.state.hsl[HSLColor(color)] = HSLAdjustment.model_validate(target)
        self._queue_preview_render()
        self._schedule_history("调整 HSL")

    def _set_curve(self, channel: str, curve) -> None:
        if self.preview_source is None:
            return
        setattr(self.state.curves, channel, curve)
        self._queue_preview_render()
        self._schedule_history("调整曲线")

    def _set_color_grading(self, region: str, key: str, value: float) -> None:
        if self.preview_source is None:
            return
        target = getattr(self.state.color_grading, region).model_dump()
        target[key] = value
        setattr(self.state.color_grading, region, ColorWheel.model_validate(target))
        self._queue_preview_render()
        self._schedule_history("调整色彩分级")

    def _queue_preview_render(self) -> None:
        self._render_generation += 1
        self._render_timer.start()

    def _begin_interaction(self, label: str) -> None:
        if self.preview_source is None or self._active_interaction:
            return
        self._flush_history()
        self._active_interaction = True
        self._interaction_label = label

    def _finish_interaction(self, label: str) -> None:
        if not self._active_interaction:
            return
        self._active_interaction = False
        self._pending_history_label = label or self._interaction_label
        self._flush_history()

    def _create_mask(self, requested_type: str) -> None:
        if self.preview_source is None:
            return
        semantic_label = None
        if requested_type.startswith("semantic:"):
            mask_type = MaskType.SEMANTIC
            semantic_label = requested_type.split(":", 1)[1]
        else:
            mask_type = MaskType(requested_type)
        names = {
            MaskType.LINEAR_GRADIENT: "线性渐变",
            MaskType.RADIAL_GRADIENT: "径向渐变",
            MaskType.LUMINANCE_RANGE: "明度范围",
            MaskType.COLOR_RANGE: "颜色范围",
            MaskType.SKY: "天空",
            MaskType.SUBJECT: "主体",
            MaskType.SEMANTIC: semantic_label or "语义区域",
            MaskType.BRUSH: "画笔",
        }
        parameters: dict[str, float | str | bool] = {}
        if mask_type == MaskType.LINEAR_GRADIENT:
            parameters = {"start_x": 0.5, "start_y": 0.0, "end_x": 0.5, "end_y": 0.65}
        elif mask_type == MaskType.RADIAL_GRADIENT:
            parameters = {"center_x": 0.5, "center_y": 0.5, "radius_x": 0.35, "radius_y": 0.35}
        elif mask_type == MaskType.LUMINANCE_RANGE:
            parameters = {"min": 0.55, "max": 1.0}
        elif mask_type == MaskType.COLOR_RANGE:
            parameters = {"hue": 210.0, "tolerance": 35.0, "min_saturation": 0.08}
        layer = MaskLayer(
            name=f"蒙版 {len(self.state.masks) + 1} — {names[mask_type]}",
            type=mask_type,
            semantic_label=semantic_label,
            parameters=parameters,
        )
        if mask_type in {MaskType.SKY, MaskType.SUBJECT, MaskType.SEMANTIC}:
            confidence = mask_confidence(generate_mask(self.preview_source, layer), semantic_label or mask_type.value)
            if confidence <= 0:
                self.statusBar().showMessage(f"未能可靠识别{names[mask_type]}区域，请手动选择或使用画笔。", 8000)
                return
            layer.parameters["mask_confidence"] = confidence
        self.state.masks.append(layer)
        self.mask_panel.set_state(self.state, layer.id)
        self._update_mask_overlay()
        self._queue_preview_render()
        self.history.push(self.state, f"创建：{names[mask_type]}")
        self._refresh_history_ui()

    def _remove_mask(self, mask_id: str) -> None:
        before = len(self.state.masks)
        self.state.masks = [layer for layer in self.state.masks if layer.id != mask_id]
        if len(self.state.masks) == before:
            return
        self.mask_panel.set_state(self.state)
        self._update_mask_overlay()
        self._queue_preview_render()
        self.history.push(self.state, "删除蒙版")
        self._refresh_history_ui()

    def _set_local_adjustment(self, mask_id: str, key: str, value: float) -> None:
        layer = self._mask_by_id(mask_id)
        if layer is None:
            return
        layer.adjustments = layer.adjustments.with_value(key, value)
        self._queue_preview_render()
        self._update_mask_overlay()
        self._schedule_history(f"局部调整：{layer.name}")

    def _set_mask_property(self, mask_id: str, key: str, value) -> None:
        layer = self._mask_by_id(mask_id)
        if layer is None or key not in {"enabled", "inverted", "opacity", "feather"}:
            return
        setattr(layer, key, value)
        self._queue_preview_render()
        self._update_mask_overlay()
        self._schedule_history(f"更新蒙版：{layer.name}")

    def _add_brush_stroke(self, points, size: float) -> None:
        mask_id = self.mask_panel.selected_mask_id
        layer = self._mask_by_id(mask_id) if mask_id else None
        if layer is None or layer.type != MaskType.BRUSH:
            return
        stroke = BrushStroke(
            points=[BrushPoint(x=x, y=y) for x, y in points], size=size,
            hardness=self.mask_panel.brush_hardness_value,
            opacity=self.mask_panel.brush_opacity_value,
            erase=self.mask_panel.brush_erase_value,
        )
        layer.strokes.append(stroke)
        self._queue_preview_render()
        self.history.push(self.state, f"画笔：{layer.name}")
        self._refresh_history_ui()

    def _import_watermark(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "导入水印", str(Path.home()), "水印 (*.png *.jpg *.jpeg *.webp)")
        if not filename:
            return
        try:
            asset = self.watermark_library.add(filename)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "无法导入水印", str(exc))
            return
        layer = WatermarkLayer(asset_id=asset["id"], name=asset["name"])
        self.state.watermarks.append(layer)
        self.watermark_panel.set_state(self.state)
        self._queue_preview_render()
        self.history.push(self.state, "添加水印")
        self._refresh_history_ui()

    def _remove_watermark(self, layer_id: str) -> None:
        original = len(self.state.watermarks)
        self.state.watermarks = [layer for layer in self.state.watermarks if layer.id != layer_id]
        if len(self.state.watermarks) == original:
            return
        self.watermark_panel.set_state(self.state)
        self._queue_preview_render()
        self.history.push(self.state, "移除水印")
        self._refresh_history_ui()

    def _set_watermark_property(self, layer_id: str, key: str, value) -> None:
        layer = next((item for item in self.state.watermarks if item.id == layer_id), None)
        if layer is None or key not in {"enabled", "position", "scale", "opacity", "margin"}:
            return
        setattr(layer, key, value)
        self._queue_preview_render()
        self._schedule_history("调整水印")

    def _rename_watermark_asset(self, asset_id: str) -> None:
        entry = next((item for item in self.watermark_library.entries() if item["id"] == asset_id), None)
        if entry is None:
            return
        name, accepted = QInputDialog.getText(self, "重命名水印", "名称", text=entry["name"])
        if not accepted or not name.strip():
            return
        self.watermark_library.rename(asset_id, name)
        for layer in self.state.watermarks:
            if layer.asset_id == asset_id:
                layer.name = name.strip()
        self.watermark_panel.set_state(self.state)
        self._queue_preview_render()
        self.history.push(self.state, "重命名水印")
        self._refresh_history_ui()

    def _set_default_watermark(self, asset_id: str) -> None:
        self.watermark_library.set_default(asset_id)
        self.statusBar().showMessage("已设置默认水印", 4000)

    def _add_default_watermark(self) -> None:
        entry = self.watermark_library.default()
        if entry is None:
            self.statusBar().showMessage("尚未设置默认水印", 4000)
            return
        self.state.watermarks.append(WatermarkLayer(asset_id=entry["id"], name=entry["name"]))
        self.watermark_panel.set_state(self.state)
        self._queue_preview_render()
        self.history.push(self.state, "添加默认水印")
        self._refresh_history_ui()

    def _delete_watermark_asset(self, asset_id: str) -> None:
        answer = QMessageBox.question(self, "删除水印库项目", "将从水印库删除该项目，并移除当前照片中使用它的图层。继续吗？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.watermark_library.delete(asset_id)
        self.state.watermarks = [layer for layer in self.state.watermarks if layer.asset_id != asset_id]
        self.watermark_panel.set_state(self.state)
        self._queue_preview_render()
        self.history.push(self.state, "删除水印库项目")
        self._refresh_history_ui()

    def _mask_by_id(self, mask_id: str):
        return next((layer for layer in self.state.masks if layer.id == mask_id), None)

    def _update_mask_overlay(self) -> None:
        if self.preview_source is None or not self.mask_panel.preview_button.isChecked():
            self.image_view.set_mask_overlay(None)
            return
        layer = self._mask_by_id(self.mask_panel.selected_mask_id or "")
        if layer is None:
            self.image_view.set_mask_overlay(None)
            return
        try:
            self.image_view.set_mask_overlay(generate_mask(self.preview_source, layer))
        except ValueError:
            self.image_view.set_mask_overlay(None)

    def reset_edits(self) -> None:
        if self.preview_source is None:
            return
        self._history_timer.stop()
        if self.state.is_pristine():
            return
        self.state = EditorState()
        self.adjustments.set_state(self.state)
        self.mask_panel.set_state(self.state)
        self.watermark_panel.set_state(self.state)
        self._render_generation += 1
        self._render_timer.stop()
        self._start_preview_render()
        self.history.push(self.state, "重置所有调整")
        self._refresh_history_ui()

    def _schedule_history(self, label: str) -> None:
        if self._active_interaction:
            return
        self._pending_history_label = label
        self._history_timer.start()

    def _flush_history(self) -> None:
        if self.preview_source is None:
            return
        if self.history.push(self.state, self._pending_history_label):
            self._refresh_history_ui()

    def undo(self) -> None:
        self._flush_history()
        state = self.history.undo()
        if state is not None:
            self._restore_state(state)

    def redo(self) -> None:
        state = self.history.redo()
        if state is not None:
            self._restore_state(state)

    def _history_row_selected(self, row: int) -> None:
        if row < 0 or row == self.history.cursor or self.preview_source is None:
            return
        self._history_timer.stop()
        state = self.history.restore(row)
        if state is not None:
            self._restore_state(state)

    def _restore_state(self, state: EditorState) -> None:
        self.state = state
        self.adjustments.set_state(state)
        self.mask_panel.set_state(state)
        self.watermark_panel.set_state(state)
        self._render_generation += 1
        self._render_timer.stop()
        self._start_preview_render()
        self._refresh_history_ui()

    def _refresh_history_ui(self) -> None:
        self.history_list.blockSignals(True)
        self.history_list.clear()
        for entry in self.history.entries:
            self.history_list.addItem(entry.label)
        if self.history.cursor >= 0:
            self.history_list.setCurrentRow(self.history.cursor)
        self.history_list.blockSignals(False)
        self.undo_action.setEnabled(self.history.can_undo)
        self.redo_action.setEnabled(self.history.can_redo)
        if self.loaded_image is not None:
            self.session_store.save(self.loaded_image.path, self.state, self.history)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._flush_history()
        if self.loaded_image is not None:
            self.session_store.save(self.loaded_image.path, self.state, self.history)
        super().closeEvent(event)

    def export_image_dialog(self) -> None:
        if self.loaded_image is None:
            QMessageBox.information(self, "没有可导出的图片", "请先打开一张图片。")
            return
        self._flush_history()
        suggested = self.loaded_image.path.with_name(f"{self.loaded_image.path.stem}_edited.jpg")
        filename, selected = QFileDialog.getSaveFileName(
            self,
            "导出全分辨率图片",
            str(suggested),
            "JPEG 图片 (*.jpg *.jpeg);;PNG 图片 (*.png)",
        )
        if not filename:
            return
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix(".png" if selected.startswith("PNG") else ".jpg")
        quality = self.runtime_settings.export_jpeg_quality
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            quality, accepted = QInputDialog.getInt(self, "JPEG 质量", "质量（1–100）", quality, 1, 100)
            if not accepted:
                return
        self.export_action.setEnabled(False)
        self.statusBar().showMessage("正在以原始分辨率导出…")
        metadata = {
            "icc_profile": self.loaded_image.icc_profile,
            "exif": self.loaded_image.exif,
            "dpi": self.loaded_image.dpi,
        }
        worker = ExportWorker(self.loaded_image.pixels, self.state, str(path), quality, metadata)
        self._export_worker = worker
        worker.signals.finished.connect(self._export_finished)
        worker.signals.failed.connect(self._export_failed)
        self._render_pool.start(worker)

    def _export_finished(self, filename: str) -> None:
        self.export_action.setEnabled(True)
        self._export_worker = None
        self.statusBar().showMessage(f"已导出：{filename}", 8000)

    def _export_failed(self, details: str) -> None:
        self.export_action.setEnabled(True)
        self._export_worker = None
        self.statusBar().showMessage("导出失败")
        last_line = next((line for line in reversed(details.splitlines()) if line.strip()), "未知错误")
        QMessageBox.critical(self, "导出失败", last_line)

    def _start_preview_render(self) -> None:
        if self.preview_source is None:
            return
        if self._render_in_flight:
            self._render_dirty = True
            return
        generation = self._render_generation
        worker = PreviewRenderWorker(self.preview_source, self.state, generation)
        worker.signals.finished.connect(self._preview_rendered)
        worker.signals.failed.connect(self._preview_failed)
        self._render_in_flight = True
        self._render_pool.start(worker)

    def _preview_rendered(self, pixels, generation: int) -> None:
        self._render_in_flight = False
        if generation != self._render_generation:
            self._render_dirty = False
            self._render_timer.start()
            return
        self.image_view.set_image(pixels)
        self.current_preview = pixels
        self.histogram.set_image(pixels)
        if self._render_dirty:
            self._render_dirty = False
            self._render_timer.start()
        self.statusBar().showMessage(f"{self.loaded_image.description}  •  已编辑")

    def _preview_failed(self, details: str, generation: int) -> None:
        self._render_in_flight = False
        if generation != self._render_generation:
            self._render_dirty = False
            self._render_timer.start()
            return
        self.statusBar().showMessage("预览渲染失败；已保留当前参数")
        if self._render_dirty:
            self._render_dirty = False
            self._render_timer.start()

    def _show_before(self) -> None:
        if self.preview_source is not None:
            self._showing_before = True
            self.image_view.set_image(self.preview_source)
            self.histogram.set_image(self.preview_source)
            self.statusBar().showMessage("正在显示原图")

    def _show_after(self) -> None:
        if self._showing_before:
            self._showing_before = False
            if self.current_preview is not None:
                self.image_view.set_image(self.current_preview)
                self.histogram.set_image(self.current_preview)
            self.statusBar().showMessage("已恢复编辑结果")

    def _toggle_before_after(self) -> None:
        if self._showing_before:
            self._show_after()
        else:
            self._show_before()

    def copy_adjustments(self) -> None:
        if self.preview_source is None:
            return
        self._adjustment_clipboard = {
            "basic": self.state.basic.model_dump(mode="json"),
            "hsl": {key.value: value.model_dump(mode="json") for key, value in self.state.hsl.items()},
            "curves": self.state.curves.model_dump(mode="json"),
        }
        self.statusBar().showMessage("已复制全局、HSL 和曲线调整（不含蒙版和水印）", 5000)

    def paste_adjustments(self) -> None:
        if self.preview_source is None or not self._adjustment_clipboard:
            return
        payload = self.state.model_dump(mode="json")
        payload.update(self._adjustment_clipboard)
        try:
            self.state = EditorState.model_validate(payload)
        except ValueError:
            return
        self.adjustments.set_state(self.state)
        self._queue_preview_render()
        self.history.push(self.state, "粘贴调整")
        self._refresh_history_ui()

    def _run_ai_edit(self, prompt: str) -> None:
        if self.preview_source is None:
            self.ai_panel.add_assistant_message("请先打开一张图片。")
            return
        if self._ai_worker is not None:
            self.ai_panel.add_assistant_message("上一条指令仍在处理中，请稍候。")
            return
        self._last_ai_prompt = prompt
        self._flush_history()
        self.runtime_settings = self.settings_manager.runtime()
        budget = self.usage_manager.status()
        provider_config = self.runtime_settings.provider_config
        provider_descriptor = provider_registry.descriptor(provider_config.provider_id)
        api_key = self.settings_manager.provider_api_key(provider_config.provider_id)
        use_cloud = provider_descriptor.requires_api_key and bool(api_key)
        if provider_descriptor.requires_api_key and not api_key:
            self.ai_panel.add_assistant_message(f"请先在设置中配置 {provider_descriptor.display_name} 的 API Key；本次未发送请求。")
            self._refresh_ai_status()
            return
        if provider_descriptor.capabilities.supports_custom_base_url and not provider_config.base_url:
            self.ai_panel.add_assistant_message("请先填写 OpenAI-compatible API 的 Base URL；本次未发送请求。")
            self._refresh_ai_status()
            return
        if budget.mode == "disabled" and use_cloud:
            self.ai_panel.add_assistant_message("云端 AI 已在费用保护设置中禁用；本次未发送请求。")
            self._refresh_ai_status()
            return
        if use_cloud and not budget.can_request:
            self.ai_panel.add_assistant_message("已达到 AI Lightroom 设置的每日云端调用上限。为了防止意外费用，云端 AI 已暂停。")
            self._refresh_ai_status()
            return
        history_summary = [entry.label for entry in self.history.entries[-8:]]
        worker = AIEditWorker(
            prompt,
            self.preview_source,
            self.state,
            history_summary,
            self.runtime_settings,
            api_key,
            self.mask_panel.selected_mask_id,
        )
        self._ai_worker = worker
        worker.signals.finished.connect(self._ai_finished)
        worker.signals.failed.connect(self._ai_failed)
        self.ai_panel.set_busy(True)
        self._last_ai_error = None
        self.ai_panel.set_retry_available(False)
        self.statusBar().showMessage("AI 正在分析当前画面和编辑状态…")
        self._render_pool.start(worker)

    def _ai_finished(self, result) -> None:
        self._ai_worker = None
        self.state = result.state
        self.adjustments.set_state(self.state)
        self.mask_panel.set_state(self.state)
        self.history.push(self.state, f"AI：{result.final_plan.summary}")
        self._refresh_history_ui()
        self._render_generation += 1
        self._render_timer.stop()
        self._start_preview_render()
        self.ai_panel.set_busy(False)
        self.ai_panel.set_result_info(result.provider_name, True)
        self._refresh_ai_status(result.provider_name)
        self.ai_panel.add_assistant_message(result.final_plan.summary)
        details = [
            f"方案：{result.final_plan.summary}",
            f"依据：{result.final_plan.reasoning_summary}",
            f"Provider：{result.provider_name}",
            f"视觉调用：{result.vision_calls}",
        ]
        if result.changed_fields:
            details.append("\n参数与局部调整：\n- " + "\n- ".join(result.changed_fields))
        if result.created_masks:
            details.append("\n创建蒙版：\n- " + "\n- ".join(result.created_masks))
        self._ai_details = "\n".join(details)

    def _ai_failed(self, traceback_text: str) -> None:
        self._ai_worker = None
        self.ai_panel.set_busy(False)
        error = traceback_text if isinstance(traceback_text, AIRequestError) else AIRequestError(
            "未知错误", str(traceback_text), model=self.runtime_settings.active_model
        )
        self._last_ai_error = error
        self._ai_details = error.details()
        self.ai_panel.set_details_available(True)
        self.ai_panel.set_retry_available(bool(self._last_ai_prompt))
        self.ai_panel.add_assistant_message(
            f"AI 请求失败\n类型：{error.category}\n模型：{error.model or self.runtime_settings.active_model}\n说明：{error.message}\n照片未发生任何修改。"
        )
        self.statusBar().showMessage(f"AI 请求失败：{error.category}；当前编辑未改变", 10000)
        self._refresh_ai_status()

    def _show_ai_details(self) -> None:
        if self._ai_details:
            box = QMessageBox(self)
            box.setWindowTitle("AI 错误详情" if self._last_ai_error else "AI 调整详情")
            box.setText(self._ai_details)
            if self._last_ai_error:
                copy_button = box.addButton("复制错误详情", QMessageBox.ButtonRole.ActionRole)
                box.addButton(QMessageBox.StandardButton.Close)
                box.exec()
                if box.clickedButton() is copy_button:
                    from PySide6.QtWidgets import QApplication
                    QApplication.clipboard().setText(self._ai_details)
            else:
                box.exec()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec():
            self.runtime_settings = self.settings_manager.runtime()
            self._render_pool.setMaxThreadCount(self.runtime_settings.worker_threads)
            self._refresh_ai_status()

    def _cancel_ai_request(self) -> None:
        if self._ai_worker is not None:
            self._ai_worker.cancel()
            self.ai_panel.add_assistant_message("已请求取消本地等待；已经发出的云端请求可能仍计入调用。")
            self.statusBar().showMessage("正在等待当前 AI 请求安全结束…", 5000)

    def _retry_ai_request(self) -> None:
        if self._last_ai_prompt and self._ai_worker is None:
            self._run_ai_edit(self._last_ai_prompt)

    def _show_ai_usage(self) -> None:
        provider = self._provider_status_text()
        AIUsageDialog(self.usage_manager, self.runtime_settings, provider, self).exec()

    def _provider_status_text(self) -> str:
        budget = self.usage_manager.status()
        if budget.mode == "disabled":
            return "Cloud disabled"
        config = self.runtime_settings.provider_config
        descriptor = provider_registry.descriptor(config.provider_id)
        if not descriptor.requires_api_key:
            return descriptor.display_name
        if self.settings_manager.has_provider_key(config.provider_id):
            return f"{config.display_name} · {config.model}"
        return f"未配置 {config.display_name} API Key"

    def _cloud_provider_configured(self) -> bool:
        descriptor = provider_registry.descriptor(self.runtime_settings.provider)
        return descriptor.requires_api_key and self.settings_manager.has_provider_key(descriptor.id)

    def _refresh_ai_status(self, completed_provider: str | None = None) -> None:
        if completed_provider:
            self.ai_panel.set_provider_status(f"本次规划：{completed_provider} · {self.runtime_settings.active_model}")
        else:
            self.ai_panel.set_provider_status(self._provider_status_text())

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 AI Lightroom",
            "AI Lightroom 0.1\n非破坏式桌面照片编辑器",
        )
