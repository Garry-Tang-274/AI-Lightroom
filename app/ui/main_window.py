from __future__ import annotations

from pathlib import Path
import logging
import platform
import subprocess
import time

from PySide6.QtCore import QSettings, QThreadPool, QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.adjustment_panel import AdjustmentPanel
from app.ui.ai_panel import AIPanel
from app.ui.ai_worker import AIEditWorker
from app.ui.image_view import ImageView
from app.ui.mask_panel import MaskPanel
from app.ui.render_worker import PreviewRenderWorker
from app.ui.load_worker import ImageLoadWorker
from app.ui.jarvisart_worker import JarvisArtControlWorker
from app.ui.settings_dialog import SettingsDialog
from app.ui.usage_dialog import AIUsageDialog
from app.ui.watermark_panel import WatermarkPanel
from app.ui.histogram_widget import HistogramWidget
from app.ui.export_worker import ExportWorker
from app.core.editor_state import (
    BrushPoint,
    BrushStroke,
    ColorGrading,
    ColorWheel,
    EditorState,
    HSLAdjustment,
    HSLColor,
    MaskLayer,
    MaskType,
    WatermarkLayer,
)
from app.core.history import HistoryManager
from app.core.recipes import RecipeLibrary
from app.utils.io_utils import LoadedImage, SUPPORTED_EXTENSIONS, load_image, make_preview
from app.utils.config import SettingsManager
from app.ai.errors import AIRequestError
from app.ai.progress import AIProgress
from app.ai.usage import AIUsageManager
from app.ai.provider_registry import provider_registry
from app.core.watermarks import WatermarkLibrary
from app.core.session_store import SessionStore
from app.core.masks import generate_mask, mask_confidence
from app.core.image_processor import prepare_mask_source
from app.utils.logging_setup import configure_logging


from app import __version__ as APP_VERSION


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Lightroom")
        self.resize(1480, 920)
        self.setMinimumSize(1080, 700)
        self.setAcceptDrops(True)
        self.settings_manager = SettingsManager()
        self.runtime_settings = self.settings_manager.runtime()
        self.settings = self.settings_manager.store
        self.usage_manager = AIUsageManager(self.settings)
        self.watermark_library = WatermarkLibrary(self.settings)
        self.session_store = SessionStore(self.settings)
        self.recipes = RecipeLibrary(self.settings)
        self.photo_set: tuple[Path, ...] = ()
        self._photo_index = -1
        self._visited_photos: set[Path] = set()
        self._pending_selection = None
        self._session_write_failed = False
        self.loaded_image: LoadedImage | None = None
        self.state = EditorState()
        self.history = HistoryManager()
        self.preview_source = None
        self.current_preview = None
        self._render_generation = 0
        self._document_generation = 0
        self._load_generation = 0
        self._loading = False
        self._closing = False
        self._close_when_idle = False
        self._ai_before_state = None
        self._ai_document = None
        self._provider_health_worker = None
        self._provider_health = "正在检查服务…"
        self._interactive_source = None
        self._render_started_at = 0.0
        self._render_pool = QThreadPool(self)
        self._render_pool.setMaxThreadCount(1)
        self._task_pool = QThreadPool(self)
        self._task_pool.setMaxThreadCount(2)
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
        self._restore_workspace_layout()
        self.statusBar().showMessage("就绪 — 打开 JPG 或 PNG 开始编辑")
        self.adjustments.set_enabled_for_image(False)
        self.ai_panel.set_ready(False)
        self._refresh_ai_status()
        self._sync_actions()

    def _build_actions(self) -> None:
        self.open_action = QAction("打开图片…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_image_dialog)
        self.open_action.setToolTip("打开一张或多张 JPG / PNG（Ctrl+O）")
        self.previous_photo = QAction("上一张", self)
        self.previous_photo.setShortcut(QKeySequence("Alt+Left"))
        self.previous_photo.triggered.connect(lambda: self._navigate_set(self._photo_index - 1))
        self.next_photo = QAction("下一张", self)
        self.next_photo.setShortcut(QKeySequence("Alt+Right"))
        self.next_photo.triggered.connect(lambda: self._navigate_set(self._photo_index + 1))
        self.export_action = QAction("导出…", self)
        self.export_action.setShortcut(QKeySequence.StandardKey.Save)
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self.export_image_dialog)
        self.export_as_action = QAction("另存/导出…", self)
        self.export_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.export_as_action.setEnabled(False)
        self.export_as_action.triggered.connect(self.export_image_dialog)
        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        self.fit_action = QAction("适合窗口", self)
        self.fit_action.setShortcut(QKeySequence("F"))
        self.fit_action.triggered.connect(lambda: self.image_view.fit_to_view())
        self.actual_action = QAction("100%", self)
        self.actual_action.setShortcut(QKeySequence("1"))
        self.actual_action.triggered.connect(lambda: self.image_view.actual_size())
        self.undo_action = QAction("撤销", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.undo)
        self.redo_action = QAction("重做", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.redo)
        self.reset_action = QAction("重置所有调整", self)
        self.reset_action.setShortcut(QKeySequence("Ctrl+R"))
        self.reset_action.triggered.connect(self.reset_edits)
        self.settings_action = QAction("设置…", self)
        self.settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self.settings_action.triggered.connect(self.open_settings)
        self.before_action = QAction("原图对比", self)
        self.before_action.setShortcut(QKeySequence("\\"))
        self.before_action.triggered.connect(self._toggle_before_after)
        self.split_action = QAction("左右对比", self)
        self.split_action.setCheckable(True)
        self.split_action.setShortcut(QKeySequence("C"))
        self.split_action.toggled.connect(self._toggle_split_comparison)
        self.focus_action = QAction("专注模式", self)
        self.focus_action.setCheckable(True)
        self.focus_action.setShortcut(QKeySequence("Ctrl+Tab"))
        self.focus_action.toggled.connect(self._toggle_focus_mode)
        self.copy_adjustments_action = QAction("复制调整", self)
        self.copy_adjustments_action.setShortcut(QKeySequence("Ctrl+Alt+C"))
        self.copy_adjustments_action.triggered.connect(self.copy_adjustments)
        self.paste_adjustments_action = QAction("粘贴调整", self)
        self.paste_adjustments_action.setShortcut(QKeySequence("Ctrl+Alt+V"))
        self.paste_adjustments_action.triggered.connect(self.paste_adjustments)
        self.preview_quality_menu = QMenu("预览质量", self)
        self.preview_quality_group = QActionGroup(self)
        self.preview_quality_group.setExclusive(True)
        self.preview_quality_actions: dict[str, QAction] = {}
        for mode, label in (
            ("auto", "自动（本地 JarvisArt GGUF 默认高清；云端默认低清）"),
            ("low", "低清预览"),
            ("high", "高清预览"),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, selected=mode: self._set_preview_quality(selected))
            self.preview_quality_group.addAction(action)
            self.preview_quality_menu.addAction(action)
            self.preview_quality_actions[mode] = action
        self._update_preview_quality_actions()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.export_action)
        file_menu.addAction(self.export_as_action)
        self.recent_menu = file_menu.addMenu("最近文件")
        self._refresh_recent_menu()
        file_menu.addAction(self.previous_photo)
        file_menu.addAction(self.next_photo)
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
        self.recipe_menu = edit_menu.addMenu("调色配方")
        self.recipe_menu.aboutToShow.connect(self._populate_recipes)
        edit_menu.addSeparator()
        edit_menu.addAction(self.reset_action)
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.fit_action)
        view_menu.addAction(self.actual_action)
        view_menu.addAction(self.before_action)
        view_menu.addAction(self.split_action)
        view_menu.addAction(self.focus_action)
        view_menu.addSeparator()
        view_menu.addMenu(self.preview_quality_menu)
        help_menu = self.menuBar().addMenu("帮助")
        open_logs = help_menu.addAction("打开日志文件夹")
        open_logs.triggered.connect(self._open_logs_folder)
        diagnostic = help_menu.addAction("复制诊断信息")
        diagnostic.triggered.connect(self._copy_diagnostic_info)
        help_menu.addSeparator()
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
        self.preview_quality_button = QToolButton(self)
        self.preview_quality_button.setMenu(self.preview_quality_menu)
        self.preview_quality_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(self.preview_quality_button)
        toolbar.addSeparator()
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)
        toolbar.addSeparator()
        self.before_button = QToolButton()
        self.before_button.setText("按住原图")
        self.before_button.pressed.connect(self._show_before)
        self.before_button.released.connect(self._show_after)
        toolbar.addWidget(self.before_button)
        toolbar.addAction(self.split_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        self.recipe_button = QToolButton()
        self.recipe_button.setText("配方")
        self.recipe_button.setToolTip("保存当前调色，或将已有配方应用到这张照片")
        self.recipe_button.setMenu(self.recipe_menu)
        self.recipe_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(self.recipe_button)
        toolbar.addAction(self.settings_action)
        toolbar.widgetForAction(self.export_action).setObjectName("accentButton")
        self.addToolBar(toolbar)
        self._update_preview_quality_actions()

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
        self.ai_panel.settings_requested.connect(self.open_settings)
        self.image_view.open_requested.connect(self.open_image_dialog)
        self.adjustments.adjustment_changed.connect(self._set_basic_adjustment)
        self.adjustments.hsl_changed.connect(self._set_hsl_adjustment)
        self.adjustments.curve_changed.connect(self._set_curve)
        self.adjustments.color_grading_changed.connect(self._set_color_grading)
        self.adjustments.advanced_adjustment_changed.connect(self._set_advanced_adjustment)
        self.adjustments.reset_requested.connect(self.reset_edits)
        self.adjustments.interaction_started.connect(self._begin_interaction)
        self.adjustments.interaction_finished.connect(self._finish_interaction)

        left_tabs = QTabWidget()
        self.left_tabs = left_tabs
        left_tabs.setMinimumWidth(245)
        left_tabs.setMaximumWidth(420)
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
        self.watermark_panel.interaction_started.connect(self._begin_interaction)
        self.watermark_panel.interaction_finished.connect(self._finish_interaction)

        right = QWidget()
        self.right_panel = right
        right.setMinimumWidth(330)
        right.setMaximumWidth(560)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.histogram.setFixedHeight(132)
        right_layout.addWidget(self.histogram)
        self.editor_tabs = QTabWidget()
        self.editor_tabs.addTab(self.adjustments, "调色")
        self.editor_tabs.addTab(self.ai_panel, "AI 助手")
        right_layout.addWidget(self.editor_tabs, 1)

        canvas = QWidget()
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        canvas_header = QWidget()
        canvas_header.setObjectName("canvasHeader")
        header_layout = QHBoxLayout(canvas_header)
        header_layout.setContentsMargins(0, 0, 8, 0)
        self.photo_label = QLabel("照片工作区")
        self.photo_label.setObjectName("canvasInfo")
        self.photo_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.zoom_label = QLabel("适合窗口")
        self.zoom_label.setObjectName("muted")
        self.zoom_label.setToolTip("百分比相对工作预览；导出始终为原始尺寸。")
        self.image_view.zoom_changed.connect(lambda zoom: self.zoom_label.setText(f"{zoom:.0%} · 预览"))
        header_layout.addWidget(self.photo_label, 1)
        self.set_nav = QWidget()
        nav = QHBoxLayout(self.set_nav)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(2)
        for action in (self.previous_photo, self.next_photo):
            button = QToolButton()
            button.setDefaultAction(action)
            button.setArrowType(Qt.ArrowType.LeftArrow if action == self.previous_photo else Qt.ArrowType.RightArrow)
            button.setToolTip("上一张（Alt+←）" if action == self.previous_photo else "下一张（Alt+→）")
            nav.addWidget(button)
        self.set_picker = QToolButton()
        self.set_picker.setAccessibleName("照片组：跳转到照片")
        self.set_picker.setToolTip("查看组内照片，点击文件名可直接跳转")
        self.set_menu = QMenu(self.set_picker)
        self.set_menu.aboutToShow.connect(self._populate_photo_set)
        self.set_picker.setMenu(self.set_menu)
        self.set_picker.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        nav.insertWidget(1, self.set_picker)
        header_layout.addWidget(self.set_nav)
        header_layout.addWidget(self.zoom_label)
        canvas_layout.addWidget(canvas_header)
        canvas_layout.addWidget(self.image_view, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter = splitter
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(left_tabs)
        splitter.addWidget(canvas)
        splitter.addWidget(right)
        splitter.setSizes([245, 860, 370])
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)
        self.render_label = QLabel("")
        self.render_label.setObjectName("muted")
        self.statusBar().addPermanentWidget(self.render_label)

    def _restore_workspace_layout(self) -> None:
        geometry = self.settings.value("workspace/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        sizes = self.settings.value("workspace/sizes")
        if isinstance(sizes, list) and len(sizes) == 3:
            self.workspace_splitter.setSizes([max(100, int(v)) for v in sizes])

    def _toggle_focus_mode(self, enabled: bool) -> None:
        self.left_tabs.setVisible(not enabled)
        self.right_panel.setVisible(not enabled)

    def _toggle_split_comparison(self, enabled: bool) -> None:
        self._show_after()
        self.image_view.set_comparison(self.preview_source, enabled)
        if enabled:
            self.image_view.set_mask_overlay(None)
            self.statusBar().showMessage("左右对比：左侧原图，右侧调整后；在画布上拖动分隔线。", 7000)
        else:
            self._update_mask_overlay()

    def _sync_actions(self) -> None:
        ready = self.loaded_image is not None
        editable = ready and self._ai_worker is None and not self._loading
        self.adjustments.setEnabled(editable)
        self.adjustments.set_enabled_for_image(editable)
        self.mask_panel.setEnabled(editable)
        self.image_view.set_editing_enabled(editable)
        self.watermark_panel.setEnabled(editable)
        self.history_list.setEnabled(editable)
        self.open_action.setEnabled(self._ai_worker is None)
        self.recipe_button.setEnabled(editable)
        self.recipe_menu.setEnabled(editable)
        self.set_nav.setVisible(len(self.photo_set) > 1)
        self.set_picker.setEnabled(editable)
        self.previous_photo.setEnabled(editable and self._photo_index > 0)
        self.next_photo.setEnabled(editable and self._photo_index + 1 < len(self.photo_set))
        self.settings_action.setEnabled(self._ai_worker is None and not self._loading)
        for action in (self.reset_action, self.copy_adjustments_action):
            action.setEnabled(editable)
        self.paste_adjustments_action.setEnabled(editable and bool(self._adjustment_clipboard))
        self.undo_action.setEnabled(editable and self.history.can_undo)
        self.redo_action.setEnabled(editable and self.history.can_redo)
        for action in (self.export_action, self.export_as_action):
            action.setEnabled(editable and self._export_worker is None)
        for action in (self.fit_action, self.actual_action, self.before_action, self.split_action):
            action.setEnabled(ready)
        self.before_button.setEnabled(ready)
        self.ai_panel.set_ready(ready and not self._loading)

    def open_image_async(self, filename: str) -> None:
        self.open_photo_set([filename])

    def open_photo_set(self, filenames) -> None:
        paths = tuple(dict.fromkeys(Path(name).absolute() for name in filenames))
        if paths:
            self._start_photo_load(paths, 0, new_set=True)

    def _navigate_set(self, index: int) -> None:
        if not self._loading and 0 <= index < len(self.photo_set) and index != self._photo_index:
            self._start_photo_load(self.photo_set, index, new_set=False)

    def _populate_photo_set(self) -> None:
        self.set_menu.clear()
        for index, path in enumerate(self.photo_set):
            action = self.set_menu.addAction(f"{index + 1}   {path.name.replace('&', '&&')}")
            action.setToolTip(str(path))
            action.setCheckable(True)
            action.setChecked(index == self._photo_index)
            action.triggered.connect(lambda _checked=False, i=index: self._navigate_set(i))

    def _start_photo_load(self, paths: tuple[Path, ...], index: int, *, new_set: bool) -> None:
        if self._ai_worker is not None:
            self.statusBar().showMessage("请先等待 AI 完成，或取消当前请求。", 5000)
            return
        self._flush_history()
        if self._session_write_failed and not self._save_session():
            self.statusBar().showMessage("当前编辑未能保存，已保留照片。请先导出，或恢复本机设置的写入权限。")
            return
        self._load_generation += 1
        self._pending_selection = (paths, index, new_set)
        self._loading = True
        self._sync_actions()
        self.statusBar().showMessage(f"正在读取 {paths[index].name}…")
        worker = ImageLoadWorker(str(paths[index]), self.runtime_settings.active_preview_size, self._load_generation)
        worker.signals.finished.connect(self._image_loaded)
        worker.signals.failed.connect(self._image_load_failed)
        self._task_pool.start(worker)

    def _image_loaded(self, loaded, preview, request_id: int) -> None:
        if request_id != self._load_generation:
            return
        self._loading = False
        paths, index, new_set = self._pending_selection
        self._pending_selection = None
        if self._close_when_idle:
            self._finish_pending_close()
            return
        resume = not new_set and paths[index] in self._visited_photos
        if new_set:
            self._visited_photos.clear()
        self.photo_set, self._photo_index = paths, index
        self.set_picker.setText(f"{index + 1} / {len(paths)}")
        self._visited_photos.add(paths[index])
        self._install_loaded_image(loaded, preview, resume=resume)
        if new_set and index:
            self.statusBar().showMessage(f"开头 {index} 张照片未能读取；已打开 {loaded.path.name}。", 8000)
        self._sync_actions()
        self._finish_pending_close()

    def _image_load_failed(self, message: str, request_id: int) -> None:
        if request_id != self._load_generation:
            return
        paths, index, new_set = self._pending_selection
        self._pending_selection = None
        if new_set and not self._close_when_idle and index + 1 < len(paths):
            self._start_photo_load(paths, index + 1, new_set=True)
            return
        self._loading = False
        self._sync_actions()
        if not self._close_when_idle:
            QMessageBox.critical(self, "无法打开图片", message)
        self._finish_pending_close()

    def open_image_dialog(self) -> None:
        start = self.settings.value("last_open_dir", str(Path.home()))
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "打开照片（可多选）",
            start,
            "图片 (*.jpg *.jpeg *.png);;所有文件 (*)",
        )
        if filenames:
            self.open_photo_set(filenames)

    def open_image(self, filename: str) -> None:
        """Synchronous API retained for integrations; interactive entrypoints use a worker."""
        if self._ai_worker is not None:
            return
        try:
            loaded = load_image(filename)
            preview = make_preview(loaded.pixels, self.runtime_settings.active_preview_size)
        except Exception as exc:  # user-facing boundary
            QMessageBox.critical(self, "无法打开图片", str(exc))
            return
        self._load_generation += 1
        self._loading = False
        self._pending_selection = None
        self.photo_set, self._photo_index = (loaded.path.absolute(),), 0
        self._visited_photos = set(self.photo_set)
        self._install_loaded_image(loaded, preview)

    def _install_loaded_image(self, loaded, preview, *, resume: bool = False) -> None:
        self._flush_history()
        self._document_generation += 1
        self._render_generation += 1
        self._render_timer.stop()
        self._history_timer.stop()
        self._active_interaction = False
        self._showing_before = False
        self._last_ai_prompt = ""
        self._ai_details = ""
        self._last_ai_error = None
        self.ai_panel.clear_session()
        self.split_action.setChecked(False)
        self.image_view.clear_image()
        self.image_view._fit_on_resize = True
        self.loaded_image = loaded
        self.session_store.bind(loaded.path, loaded.file_size, loaded.modified_ns)
        self.state = EditorState()
        self.history.reset(self.state, f"打开：{loaded.path.name}")
        recovered = self.session_store.load(loaded.path)
        if recovered and recovered.get("state"):
            answer = QMessageBox.StandardButton.Yes if resume else QMessageBox.question(
                self, "恢复编辑", "发现这张照片的已保存编辑。是否恢复？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                try:
                    self.state = self.session_store.restore(recovered, self.history)
                except (KeyError, TypeError, ValueError):
                    self.state = EditorState()
                    self.history.reset(self.state, f"打开：{loaded.path.name}")
        self.preview_source = preview
        self._interactive_source = make_preview(preview, self.runtime_settings.interaction_preview_size)
        self.current_preview = preview.copy()
        self.adjustments.set_state(self.state)
        self.mask_panel.set_state(self.state)
        self.watermark_panel.set_state(self.state)
        self.image_view.set_image(preview)
        self.histogram.set_image(preview)
        self.settings.setValue("last_open_dir", str(loaded.path.parent))
        self.setWindowTitle(f"{loaded.path.name} — AI Lightroom")
        self.photo_label.setText(loaded.path.name)
        self.photo_label.setToolTip(str(loaded.path))
        self.statusBar().showMessage(loaded.description)
        self._refresh_history_ui()
        self.adjustments.set_enabled_for_image(True)
        self.ai_panel.set_ready(True)
        self.export_action.setEnabled(True)
        self.export_as_action.setEnabled(True)
        self._add_recent_file(loaded.path)
        self._refresh_ai_status()
        self._sync_actions()
        if not self.state.is_pristine():
            self._queue_preview_render()

    def _preview_quality_label(self, quality: str | None = None) -> str:
        resolved = quality or self.runtime_settings.effective_preview_quality
        return "高清" if resolved == "high" else "低清"

    def _update_preview_quality_actions(self) -> None:
        if not hasattr(self, "preview_quality_actions"):
            return
        selected = self.runtime_settings.preview_quality
        action = self.preview_quality_actions.get(selected, self.preview_quality_actions["auto"])
        action.setChecked(True)
        if hasattr(self, "preview_quality_button"):
            visible = self._preview_quality_label()
            self.preview_quality_button.setText(f"{visible}预览")
            self.preview_quality_button.setToolTip(
                f"当前：{visible}（最长边 {self.runtime_settings.active_preview_size}px）。点击切换预览质量。"
            )

    def _rebuild_visible_preview_source(self) -> None:
        """Rebuild only the working preview; original pixels stay untouched."""
        if self.loaded_image is None:
            return
        self._render_generation += 1
        self._render_timer.stop()
        self.preview_source = make_preview(self.loaded_image.pixels, self.runtime_settings.active_preview_size)
        self._interactive_source = make_preview(self.preview_source, self.runtime_settings.interaction_preview_size)
        self.current_preview = self.preview_source.copy()
        self.image_view.set_image(self.preview_source)
        self.histogram.set_image(self.preview_source)
        self.image_view.set_comparison(self.preview_source, self.split_action.isChecked())
        self._update_mask_overlay()
        if not self.state.is_pristine():
            self._queue_preview_render()

    def _set_preview_quality(self, mode: str) -> None:
        if mode not in {"auto", "low", "high"}:
            return
        if self._ai_worker is not None:
            self.statusBar().showMessage("AI 正在处理中；完成后再切换预览质量。", 5000)
            self._update_preview_quality_actions()
            return
        previous_edge = self.runtime_settings.active_preview_size
        self.settings.setValue("performance/preview_quality", mode)
        self.settings.sync()
        self.runtime_settings = self.settings_manager.runtime()
        self._update_preview_quality_actions()
        if self.loaded_image is not None and previous_edge != self.runtime_settings.active_preview_size:
            self._rebuild_visible_preview_source()
        self.statusBar().showMessage(
            f"已切换到{self._preview_quality_label()}预览（最长边 {self.runtime_settings.active_preview_size}px）。"
            "AI 图像质量可在 设置 → 性能与导出 中单独设置。",
            7000,
        )

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if any(url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS for url in urls):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        paths = [url.toLocalFile() for url in event.mimeData().urls()
                 if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS]
        if paths and self._ai_worker is None:
            self.open_photo_set(paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _recent_files(self) -> list[str]:
        stored = self.settings.value("recent_files", [])
        values = [str(item) for item in (stored if isinstance(stored, list) else [stored]) if item]
        return [path for path in values if Path(path).is_file()][:10]

    def _add_recent_file(self, path: Path) -> None:
        ordered = [str(path.resolve())] + [item for item in self._recent_files() if Path(item).resolve() != path.resolve()]
        self.settings.setValue("recent_files", ordered[:10])
        self.settings.sync()
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        recent = self._recent_files()
        if not recent:
            action = self.recent_menu.addAction("暂无最近文件")
            action.setEnabled(False)
            return
        for filename in recent:
            action = self.recent_menu.addAction(Path(filename).name)
            action.setToolTip(filename)
            action.triggered.connect(lambda _checked=False, value=filename: self.open_image_async(value))

    def _set_basic_adjustment(self, key: str, value: float) -> None:
        if self.preview_source is None:
            return
        try:
            self.state.basic = self.state.basic.with_value(key, value)
        except (KeyError, ValueError):
            return
        self._queue_preview_render()
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

    def _set_advanced_adjustment(self, section: str, key: str, value) -> None:
        if self.preview_source is None:
            return
        try:
            values = getattr(self.state, section)
            if section == "color_grading" and key in {"blending", "balance"}:
                self.state.color_grading = ColorGrading.model_validate({**values.model_dump(), key: value})
            else:
                setattr(self.state, section, values.with_value(key, value))
        except (AttributeError, KeyError, ValueError):
            return
        self._queue_preview_render()
        self._schedule_history(f"调整{section}")
        if section == "transform":
            self._update_mask_overlay()

    def _queue_preview_render(self) -> None:
        self._render_generation += 1
        if not self._render_timer.isActive():
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
        self._queue_preview_render()

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
            confidence = mask_confidence(generate_mask(prepare_mask_source(self.preview_source, self.state), layer), semantic_label or mask_type.value)
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
        self._schedule_history(f"局部调整：{layer.name}")

    def _set_mask_property(self, mask_id: str, key: str, value) -> None:
        layer = self._mask_by_id(mask_id)
        if layer is None or key not in {"enabled", "inverted", "opacity", "feather", "parameters"}:
            return
        setattr(layer, key, value)
        self._queue_preview_render()
        self._update_mask_overlay()
        self._schedule_history(f"更新蒙版：{layer.name}")

    def _add_brush_stroke(self, points, size: float) -> None:
        if self._ai_worker is not None or self._loading:
            return
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
        self._update_mask_overlay()
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
        if layer is None or key not in {"enabled", "position", "scale", "opacity", "margin", "x", "y"}:
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
        if self.preview_source is None or self._showing_before or self.split_action.isChecked() or not self.mask_panel.preview_button.isChecked():
            self.image_view.set_mask_overlay(None)
            return
        layer = self._mask_by_id(self.mask_panel.selected_mask_id or "")
        if layer is None:
            self.image_view.set_mask_overlay(None)
            return
        try:
            self.image_view.set_mask_overlay(generate_mask(prepare_mask_source(self.preview_source, self.state), layer))
        except ValueError:
            self.image_view.set_mask_overlay(None)

    def reset_edits(self) -> None:
        if self.preview_source is None:
            return
        self._flush_history()
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
        self._history_timer.stop()
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
        self._flush_history()
        state = self.history.redo()
        if state is not None:
            self._restore_state(state)

    def _history_row_selected(self, row: int) -> None:
        if row < 0 or row == self.history.cursor or self.preview_source is None:
            return
        entries = self.history.entries
        if row >= len(entries):
            return
        requested = entries[row]
        # A numeric edit can still be inside its merge interval. Preserve it as
        # a redo step before jumping, even if adding it trims the history.
        self._flush_history()
        index = next((i for i, entry in enumerate(self.history.entries) if entry is requested), -1)
        state = self.history.restore(index)
        if state is not None:
            self._restore_state(state)

    def _restore_state(self, state: EditorState) -> None:
        self._history_timer.stop()
        self._active_interaction = False
        self.state = state
        self.adjustments.set_state(state)
        self.mask_panel.set_state(state)
        self.watermark_panel.set_state(state)
        self._update_mask_overlay()
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
        self._sync_actions()
        if self.loaded_image is not None:
            self._save_session()

    def _save_session(self) -> bool:
        if self.loaded_image is None:
            return True
        try:
            self.session_store.save(self.loaded_image.path, self.state, self.history)
            self._session_write_failed = False
        except (OSError, ValueError):
            self._session_write_failed = True
            logging.getLogger(__name__).exception("Could not save edit session")
            self.statusBar().showMessage("编辑仍在内存中，但自动保存失败；请导出成片。", 7000)
        return not self._session_write_failed

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._ai_worker is not None or self._export_worker is not None or self._loading:
            self._close_when_idle = True
            if self._ai_worker is not None:
                self._ai_worker.cancel()
            self.statusBar().showMessage("正在等待后台任务安全结束，完成后自动关闭…")
            event.ignore()
            return
        self._closing = True
        self._render_timer.stop()
        self._flush_history()
        self._save_session()
        self.settings.setValue("workspace/geometry", self.saveGeometry())
        if not self.focus_action.isChecked():
            self.settings.setValue("workspace/sizes", self.workspace_splitter.sizes())
        self.settings.sync()
        self._render_pool.clear()
        self._render_pool.waitForDone()
        # A local bridge may also be serving Lightroom Classic. Closing this
        # client is not permission to stop that shared service.
        super().closeEvent(event)

    def _finish_pending_close(self) -> None:
        if self._close_when_idle and self._ai_worker is None and self._export_worker is None and not self._loading:
            QTimer.singleShot(0, self.close)

    def export_image_dialog(self) -> None:
        if self._export_worker is not None or self._ai_worker is not None or self._loading:
            return
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
        if self._is_source_photo(path):
            QMessageBox.warning(self, "请保留原图", "导出不能覆盖当前照片或组内其他原图。请选择其他文件名。")
            return
        quality = self.runtime_settings.export_jpeg_quality
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            quality, accepted = QInputDialog.getInt(self, "JPEG 质量", "质量（1–100）", quality, 1, 100)
            if not accepted:
                return
        self.export_action.setEnabled(False)
        self.export_as_action.setEnabled(False)
        self.statusBar().showMessage("正在以原始分辨率导出…")
        metadata = {
            "icc_profile": self.loaded_image.icc_profile,
            "exif": self.loaded_image.exif if self.runtime_settings.export_keep_exif else None,
            "dpi": self.loaded_image.dpi,
        }
        worker = ExportWorker(self.loaded_image.pixels, self.state, str(path), quality, metadata, source_path=self.loaded_image.path)
        self._export_worker = worker
        worker.signals.finished.connect(self._export_finished)
        worker.signals.failed.connect(self._export_failed)
        self._task_pool.start(worker)

    def _is_source_photo(self, path: Path) -> bool:
        target = path.resolve()
        sources = self.photo_set or (self.loaded_image.path,)
        if target in sources:
            return True
        if not target.exists():
            return False
        return any(source.exists() and target.samefile(source) for source in sources)

    def _export_finished(self, filename: str) -> None:
        self.export_action.setEnabled(True)
        self.export_as_action.setEnabled(True)
        self._export_worker = None
        self._sync_actions()
        self.statusBar().showMessage(f"已导出：{filename}", 8000)
        self._finish_pending_close()

    def _export_failed(self, details: str) -> None:
        self.export_action.setEnabled(True)
        self.export_as_action.setEnabled(True)
        self._export_worker = None
        self._sync_actions()
        self.statusBar().showMessage("导出失败")
        last_line = next((line for line in reversed(details.splitlines()) if line.strip()), "未知错误")
        QMessageBox.critical(self, "导出失败", last_line)
        self._finish_pending_close()

    def _start_preview_render(self) -> None:
        if self.preview_source is None or self._closing:
            return
        if self._render_in_flight:
            self._render_dirty = True
            return
        generation = self._render_generation
        fast = self._active_interaction and self._interactive_source is not None
        source = self._interactive_source if fast else self.preview_source
        worker = PreviewRenderWorker(source, self.state, generation)
        self._render_document = self._document_generation
        self._render_started_at = time.perf_counter()
        worker.signals.finished.connect(self._preview_rendered)
        worker.signals.failed.connect(self._preview_failed)
        self._render_in_flight = True
        self._render_pool.start(worker)

    def _preview_rendered(self, pixels, generation: int) -> None:
        self._render_in_flight = False
        if self._closing:
            return
        stale = generation != self._render_generation
        same_document = getattr(self, "_render_document", self._document_generation) == self._document_generation
        # Publish completed frames during dragging rather than starving the canvas
        # until the mouse stops. Never publish a previous photograph's result.
        if same_document and (not stale or self._active_interaction):
            self.current_preview = pixels
            if not self._showing_before:
                self.image_view.set_image(pixels, (self.preview_source.shape[1], self.preview_source.shape[0]))
                self.histogram.set_image(pixels)
            elapsed = (time.perf_counter() - self._render_started_at) * 1000
            label = "交互预览" if self._active_interaction else "精细预览"
            self.render_label.setText(f"{label} · {elapsed:.0f} ms")
        if self._render_dirty or stale:
            self._render_dirty = False
            self._render_timer.start()
        if same_document and not self._showing_before and self._ai_worker is None and self._export_worker is None:
            status = "正在调整" if self._active_interaction else ("原始状态" if self.state.is_pristine() else "参数已更新")
            self.statusBar().showMessage(f"{self.loaded_image.description}  ·  {status}")

    def _preview_failed(self, details: str, generation: int) -> None:
        self._render_in_flight = False
        if self._closing:
            return
        if generation != self._render_generation:
            self._render_dirty = False
            self._render_timer.start()
            return
        self.statusBar().showMessage("预览渲染失败；已保留当前参数")
        logging.getLogger(__name__).error("Preview rendering failed: %s", details)
        self.render_label.setText("预览失败 · 可撤回重试")
        if self._render_dirty:
            self._render_dirty = False
            self._render_timer.start()

    def _show_before(self) -> None:
        if self.preview_source is not None:
            self._showing_before = True
            self.image_view.set_comparison(None, False)
            self.image_view.set_mask_overlay(None)
            self.image_view.set_image(self.preview_source)
            self.histogram.set_image(self.preview_source)
            self.statusBar().showMessage("正在显示原图")

    def _show_after(self) -> None:
        if self._showing_before:
            self._showing_before = False
            if self.current_preview is not None:
                self.image_view.set_image(self.current_preview, (self.preview_source.shape[1], self.preview_source.shape[0]))
                self.histogram.set_image(self.current_preview)
            self.image_view.set_comparison(self.preview_source, self.split_action.isChecked())
            self._update_mask_overlay()
            self.statusBar().showMessage("已恢复编辑结果")

    def _toggle_before_after(self) -> None:
        if self._showing_before:
            self._show_after()
        else:
            self._show_before()

    def _populate_recipes(self) -> None:
        menu = self.recipe_menu
        menu.clear()
        try:
            names = self.recipes.names()
        except (ValueError, OSError):
            menu.addAction("无法读取本机配方库").setEnabled(False)
            return
        menu.addAction("将当前调色存为配方…", self._save_recipe)
        menu.addSeparator()
        if names:
            for name in names:
                menu.addAction(name.replace("&", "&&"), lambda _checked=False, n=name: self._apply_recipe(n))
            menu.addSeparator()
            submenu = menu.addMenu("删除配方")
            for name in names:
                submenu.addAction(name.replace("&", "&&"), lambda _checked=False, n=name: self._delete_recipe(n))
        else:
            menu.addAction("尚无已保存的配方").setEnabled(False)

    def _save_recipe(self) -> None:
        name, ok = QInputDialog.getText(self, "保存调色配方",
            "名称（保留色调与细节，不复制光学、几何、蒙版或水印）：")
        if not ok or not name.strip():
            return
        name = name.strip()
        try:
            replace = name in self.recipes.names()
            if replace and QMessageBox.question(self, "替换配方", f"要替换已有配方「{name}」吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
                    ) != QMessageBox.StandardButton.Yes:
                return
            self.recipes.save(name, self.state, replace=replace)
            self.statusBar().showMessage(f"已保存配方「{name}」，切换照片后可继续使用。", 6000)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "无法保存配方", str(exc))

    def _apply_recipe(self, name: str) -> None:
        if self.loaded_image is None or self._ai_worker is not None or self._loading:
            return
        try:
            after = self.recipes.apply(name, self.state)
        except (ValueError, OSError, KeyError) as exc:
            QMessageBox.warning(self, "无法应用配方", str(exc))
            return
        if after == self.state:
            self.statusBar().showMessage(f"当前调色已与「{name}」一致。", 4000)
            return
        self._flush_history()
        self.history.push(after, f"配方：{name}")
        self._restore_state(after)
        self.statusBar().showMessage(f"已应用「{name}」· 可撤销", 5000)

    def _delete_recipe(self, name: str) -> None:
        if QMessageBox.question(self, "删除配方", f"删除「{name}」？已编辑的照片不会改变。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                self.recipes.remove(name)
            except (KeyError, ValueError, OSError) as exc:
                QMessageBox.warning(self, "无法删除配方", str(exc))

    def copy_adjustments(self) -> None:
        if self.preview_source is None:
            return
        self._adjustment_clipboard = {
            "basic": self.state.basic.model_dump(mode="json"),
            "hsl": {key.value: value.model_dump(mode="json") for key, value in self.state.hsl.items()},
            "curves": self.state.curves.model_dump(mode="json"),
            "color_grading": self.state.color_grading.model_dump(mode="json"),
            "detail": self.state.detail.model_dump(mode="json"),
            "effects": self.state.effects.model_dump(mode="json"),
            "optics": self.state.optics.model_dump(mode="json"),
            "transform": self.state.transform.model_dump(mode="json"),
            "calibration": self.state.calibration.model_dump(mode="json"),
        }
        self.statusBar().showMessage("已复制全局、细节、效果、光学、几何、校准、HSL 和曲线调整（不含蒙版和水印）", 5000)
        self._sync_actions()

    def paste_adjustments(self) -> None:
        if self.preview_source is None or not self._adjustment_clipboard:
            return
        self._flush_history()
        payload = self.state.model_dump(mode="json")
        payload.update(self._adjustment_clipboard)
        try:
            self.state = EditorState.model_validate(payload)
        except ValueError:
            return
        self.adjustments.set_state(self.state)
        self._queue_preview_render()
        self._update_mask_overlay()
        self.history.push(self.state, "粘贴调整")
        self._refresh_history_ui()

    def _run_ai_edit(self, prompt: str) -> None:
        if self._loading or self._closing or not prompt.strip():
            return
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
        if provider_config.provider_id == "mock":
            self._show_offline_mock_notice()
            return
        if provider_config.provider_id == "jarvisart_local" and provider_config.local_mode == "mock":
            self._show_jarvisart_mock_notice()
            return
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
        history_summary = [entry.label for entry in self.history.entries[:self.history.cursor + 1][-8:]]
        worker = AIEditWorker(
            prompt,
            self.loaded_image.pixels if self.loaded_image is not None else self.preview_source,
            self.state,
            history_summary,
            self.runtime_settings,
            api_key,
            self.mask_panel.selected_mask_id,
        )
        self._ai_worker = worker
        self._ai_before_state = self.state.snapshot()
        self._ai_document = self._document_generation
        worker.signals.progress.connect(self._ai_progress)
        worker.signals.finished.connect(self._ai_finished)
        worker.signals.failed.connect(self._ai_failed)
        self.ai_panel.set_busy(True)
        self.editor_tabs.setCurrentWidget(self.ai_panel)
        self._sync_actions()
        self._last_ai_error = None
        self.ai_panel.set_retry_available(False)
        ai_quality = self._preview_quality_label(self.runtime_settings.effective_ai_preview_quality)
        self.statusBar().showMessage(
            f"AI 正在分析当前画面和编辑状态… 视觉分析将使用{ai_quality} JPEG 预览（最长边 {self.runtime_settings.active_ai_preview_size}px）。"
        )
        self._task_pool.start(worker)

    def _show_jarvisart_mock_notice(self) -> None:
        """Never let a fixed fixture masquerade as visual inference."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("JarvisArt Mock 不能执行真实调色")
        box.setText("当前选择的是离线 Mock 测试模式。它只会返回固定演示参数，不会读取或分析当前照片。")
        box.setInformativeText("为了避免“看起来已完成、实际没有理解指令”的误导，本次没有执行任何编辑。请切换到 Local GGUF（主力本地推理）或已配置的云端 AI Provider。")
        settings_button = box.addButton("打开设置", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        self.ai_panel.add_assistant_message(
            "已阻止离线 Mock 测试模式执行：它不会分析图片，因此不会用于真实调色。当前照片未发生任何修改。"
        )
        self.statusBar().showMessage("离线 Mock 不会执行真实调色；请在设置中选择 Local GGUF 或云端 Provider。", 9000)
        self._refresh_ai_status()
        if box.clickedButton() is settings_button:
            self.open_settings()

    def _show_offline_mock_notice(self) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Offline Mock 不能执行真实调色")
        box.setText("当前选择的是 Offline Mock。它只用于开发测试，不会读取、理解或分析当前照片。")
        box.setInformativeText("为了避免固定演示参数被误当成真实 AI 结果，本次没有执行任何编辑。请在设置中选择 Local GGUF 或已配置的云端 Provider。")
        settings_button = box.addButton("打开设置", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        self.ai_panel.add_assistant_message(
            "已阻止 Offline Mock 执行：它不会分析图片，因此不会用于真实调色。当前照片未发生任何修改。"
        )
        self.statusBar().showMessage("Offline Mock 仅用于开发测试；请在设置中选择 Local GGUF 或云端 Provider。", 9000)
        self._refresh_ai_status()
        if box.clickedButton() is settings_button:
            self.open_settings()

    def _ai_progress(self, progress) -> None:
        worker = self._ai_worker
        if worker is not None and self.sender() is worker.signals and self._ai_document == self._document_generation:
            self.ai_panel.set_progress(progress)

    def _finish_cancelled_ai(self, message: str) -> None:
        self._ai_worker = None
        self.ai_panel.set_progress(AIProgress("cancelled", "已取消，本次结果未应用。"))
        self.ai_panel.set_busy(False)
        self.ai_panel.set_retry_available(False)
        self.ai_panel.set_details_available(False)
        self.ai_panel.add_assistant_message(message)
        self._ai_details = ""
        self._last_ai_error = None
        self._sync_actions()
        self.statusBar().showMessage("AI 编辑已取消，照片保持不变。", 6000)
        self._finish_pending_close()

    def _ai_finished(self, result) -> None:
        if getattr(self._ai_worker, "is_cancelled", False):
            self._finish_cancelled_ai("结果已返回，但你已取消，本次没有应用调整。")
            return
        self._ai_worker = None
        self.ai_panel.set_busy(False)
        if self._ai_document != self._document_generation or self._ai_before_state != self.state or self._close_when_idle:
            self.ai_panel.add_assistant_message("当前照片或调整已变化；旧请求的结果未覆盖当前编辑。")
            self._sync_actions()
            self._finish_pending_close()
            return
        self.state = result.state
        self.adjustments.set_state(self.state)
        self.mask_panel.set_state(self.state)
        self.watermark_panel.set_state(self.state)
        self._update_mask_overlay()
        self.history.push(self.state, f"AI：{result.final_plan.summary}")
        self._refresh_history_ui()
        self._render_generation += 1
        self._render_timer.stop()
        pixels = getattr(result, "preview_pixels", None)
        if pixels is not None:
            self.current_preview = pixels
            if not self._showing_before:
                self.image_view.set_image(pixels, (self.preview_source.shape[1], self.preview_source.shape[0]))
                self.histogram.set_image(pixels)
        if pixels is None or pixels.shape != self.preview_source.shape:
            self._start_preview_render()
        self.ai_panel.set_result_info(result.provider_name, True)
        self._refresh_ai_status(result.provider_name)
        self.ai_panel.add_assistant_message(result.final_plan.summary if getattr(result, "has_changes", True) else "方案未改变当前调整。可换一个更具体的要求，或直接手动调整。")
        for warning in getattr(result, "warnings", []):
            self.ai_panel.add_assistant_message(warning)
        details = [
            f"方案：{result.final_plan.summary}",
            f"依据：{result.final_plan.reasoning_summary}",
            f"Provider：{result.provider_name}",
            f"视觉调用：{result.vision_calls}",
            f"视觉预览上限：{result.analysis_preview_max_edge}px",
        ]
        if result.changed_fields:
            details.append("\n参数与局部调整：\n- " + "\n- ".join(result.changed_fields))
        if result.created_masks:
            details.append("\n创建蒙版：\n- " + "\n- ".join(result.created_masks))
        if getattr(result, "warnings", []):
            details.append("\n未执行的区域：\n- " + "\n- ".join(result.warnings))
        if result.unsupported_operations:
            warning = f"有 {len(result.unsupported_operations)} 项原生 Lightroom 操作无法应用，详见调整详情。其他有效操作已执行。"
            self.ai_panel.add_assistant_message(warning)
            details.append("\n未支持的 JarvisArt 操作：\n- " + "\n- ".join(result.unsupported_operations))
        self._ai_details = "\n".join(details)
        self._sync_actions()
        self._finish_pending_close()

    def _ai_failed(self, traceback_text: str) -> None:
        if getattr(self._ai_worker, "is_cancelled", False):
            message = (traceback_text.message if isinstance(traceback_text, AIRequestError)
                       and traceback_text.category == "已取消本地等待" else "已取消本次编辑，照片保持不变。")
            self._finish_cancelled_ai(message)
            return
        self._ai_worker = None
        self.ai_panel.set_busy(False)
        error = traceback_text if isinstance(traceback_text, AIRequestError) else AIRequestError(
            "未知错误", str(traceback_text), model=self.runtime_settings.active_model
        )
        self._last_ai_error = error
        self._ai_details = error.details()
        self.ai_panel.set_details_available(True)
        self.ai_panel.set_retry_available(bool(self._last_ai_prompt))
        visible_error = (
            f"AI 请求失败\n类型：{error.category}\n模型：{error.model or self.runtime_settings.active_model}\n说明：{error.message}\n照片未发生任何修改。"
        )
        if error.validation_errors:
            visible_error += f"\n字段：{error.validation_summary()}"
        self.ai_panel.add_assistant_message(visible_error)
        self.statusBar().showMessage(f"AI 请求失败：{error.category}；当前编辑未改变", 10000)
        self._refresh_ai_status()
        self._sync_actions()
        self._finish_pending_close()

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
        if self._ai_worker is not None or self._loading:
            return
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec():
            previous_edge = self.runtime_settings.active_preview_size
            self.runtime_settings = self.settings_manager.runtime()
            if self.preview_source is not None:
                self._interactive_source = make_preview(self.preview_source, self.runtime_settings.interaction_preview_size)
            self._update_preview_quality_actions()
            if self.loaded_image is not None and previous_edge != self.runtime_settings.active_preview_size:
                self._rebuild_visible_preview_source()
            self._refresh_ai_status()

    def _cancel_ai_request(self) -> None:
        if self._ai_worker is not None:
            self._ai_worker.cancel()
            self.statusBar().showMessage("正在等待当前 AI 请求安全结束…", 5000)

    def _retry_ai_request(self) -> None:
        if self._last_ai_prompt and self._ai_worker is None:
            self._run_ai_edit(self._last_ai_prompt)

    def _show_ai_usage(self) -> None:
        provider = self._provider_status_text()
        AIUsageDialog(self.usage_manager, self.runtime_settings, provider, self).exec()

    def _provider_status_text(self) -> str:
        config = self.runtime_settings.provider_config
        descriptor = provider_registry.descriptor(config.provider_id)
        if not descriptor.requires_api_key:
            if config.provider_id == "jarvisart_local":
                if config.local_mode == "mock":
                    return "⚠ JarvisArt Local · 离线 Mock 测试（不会分析照片）"
                else:
                    state = self._provider_health
                return f"JarvisArt Local GGUF · {state} · 本地，无云端费用 · {self._preview_quality_label()}预览"
            if config.provider_id == "mock":
                return "⚠ Offline Mock（仅开发测试；不会分析照片）"
            return descriptor.display_name
        budget = self.usage_manager.status()
        if budget.mode == "disabled":
            return "Cloud disabled"
        if self.settings_manager.has_provider_key(config.provider_id):
            return f"{config.display_name} · {config.model}"
        return "尚未配置 AI Provider（可在设置中启用云端服务或 JarvisArt Local）"

    def _cloud_provider_configured(self) -> bool:
        descriptor = provider_registry.descriptor(self.runtime_settings.provider)
        return descriptor.requires_api_key and self.settings_manager.has_provider_key(descriptor.id)

    def _refresh_ai_status(self, completed_provider: str | None = None) -> None:
        if completed_provider:
            self.ai_panel.set_provider_status(f"本次规划：{completed_provider} · {self.runtime_settings.active_model}")
        else:
            self.ai_panel.set_provider_status(self._provider_status_text())
        config = self.runtime_settings.provider_config
        if config.provider_id == "jarvisart_local" and config.local_mode == "real" and self._provider_health_worker is None:
            worker = JarvisArtControlWorker(config.jarvisart_root, config.jarvisart_endpoint, "status")
            self._provider_health_worker = worker
            worker.signals.finished.connect(self._provider_health_received)
            self._task_pool.start(worker)

    def _provider_health_received(self, status) -> None:
        self._provider_health_worker = None
        self._provider_health = status.state
        if not self._closing and self.runtime_settings.provider == "jarvisart_local":
            self.ai_panel.set_provider_status(self._provider_status_text())

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 AI Lightroom",
            f"AI Lightroom {APP_VERSION}\n\n"
            "一个支持传统非破坏式照片编辑与可选 AI 调色计划的桌面应用。\n"
            "License: MIT\n"
            "JarvisArt 是独立可选组件，遵循其自身许可证；AI Lightroom 不隶属于 Adobe。\n"
            "https://github.com/Garry-Tang-274/AI-Lightroom",
        )

    def _open_logs_folder(self) -> None:
        log_path = configure_logging()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path.parent)))

    def _copy_diagnostic_info(self) -> None:
        provider = self.runtime_settings.provider_config
        gpu = "Unavailable"
        try:
            gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"], text=True, timeout=3).strip() or gpu
        except (OSError, subprocess.SubprocessError):
            pass
        lines = [
            f"AI Lightroom {APP_VERSION}",
            f"OS: {platform.system()} {platform.release()}",
            f"Python: {platform.python_version()}",
            f"Provider: {provider.display_name}",
            f"Model: {provider.model}",
            f"GPU: {gpu}",
        ]
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText("\n".join(lines))
        self.statusBar().showMessage("已复制不含密钥、指令和照片路径的诊断信息。", 5000)
