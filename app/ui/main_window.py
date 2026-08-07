from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QThreadPool, QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.adjustment_panel import AdjustmentPanel
from app.ui.ai_panel import AIPanel
from app.ui.image_view import ImageView
from app.ui.render_worker import PreviewRenderWorker
from app.core.editor_state import EditorState
from app.utils.io_utils import LoadedImage, load_image, make_preview


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Lightroom")
        self.resize(1480, 920)
        self.setMinimumSize(1050, 680)
        self.settings = QSettings("AI Lightroom", "AI Lightroom")
        self.loaded_image: LoadedImage | None = None
        self.state = EditorState()
        self.preview_source = None
        self._render_generation = 0
        self._render_pool = QThreadPool(self)
        self._render_pool.setMaxThreadCount(2)
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(75)
        self._render_timer.timeout.connect(self._start_preview_render)
        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_workspace()
        self.statusBar().showMessage("就绪 — 打开 JPG 或 PNG 开始编辑")
        self.adjustments.set_enabled_for_image(False)
        self.ai_panel.set_ready(False)

    def _build_actions(self) -> None:
        self.open_action = QAction("打开图片…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_image_dialog)
        self.export_action = QAction("导出…", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self._not_available_yet)
        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        self.fit_action = QAction("适合窗口", self)
        self.fit_action.setShortcut(QKeySequence("F"))
        self.fit_action.triggered.connect(lambda: self.image_view.fit_to_view())
        self.actual_action = QAction("100%", self)
        self.actual_action.triggered.connect(lambda: self.image_view.actual_size())

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        edit_menu = self.menuBar().addMenu("编辑")
        edit_menu.addAction("撤销").setEnabled(False)
        edit_menu.addAction("重做").setEnabled(False)
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.fit_action)
        view_menu.addAction(self.actual_action)
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
        self.addToolBar(toolbar)

    def _build_workspace(self) -> None:
        self.image_view = ImageView()
        self.adjustments = AdjustmentPanel()
        self.ai_panel = AIPanel()
        self.ai_panel.prompt_submitted.connect(self._ai_placeholder)
        self.adjustments.adjustment_changed.connect(self._set_basic_adjustment)
        self.adjustments.reset_requested.connect(self.reset_edits)

        left_tabs = QTabWidget()
        history = QListWidget()
        history.addItem("打开图片后显示历史记录")
        masks = QListWidget()
        masks.addItem("尚无蒙版")
        left_tabs.addTab(history, "历史")
        left_tabs.addTab(masks, "蒙版")
        self.history_list = history
        self.mask_list = masks

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.addWidget(self.adjustments)
        vertical.addWidget(self.ai_panel)
        vertical.setSizes([590, 270])
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
            preview = make_preview(loaded.pixels)
        except Exception as exc:  # user-facing boundary
            QMessageBox.critical(self, "无法打开图片", str(exc))
            return
        self.loaded_image = loaded
        self.state = EditorState()
        self.preview_source = preview
        self.adjustments.set_state(self.state)
        self.image_view.set_image(preview)
        self.settings.setValue("last_open_dir", str(loaded.path.parent))
        self.setWindowTitle(f"{loaded.path.name} — AI Lightroom")
        self.statusBar().showMessage(loaded.description)
        self.history_list.clear()
        self.history_list.addItem(f"打开：{loaded.path.name}")
        self.adjustments.set_enabled_for_image(True)
        self.ai_panel.set_ready(True)
        self.export_action.setEnabled(True)

    def _set_basic_adjustment(self, key: str, value: float) -> None:
        if self.preview_source is None:
            return
        try:
            self.state.basic = self.state.basic.with_value(key, value)
        except (KeyError, ValueError):
            return
        self._render_generation += 1
        self._render_timer.start()

    def reset_edits(self) -> None:
        if self.preview_source is None:
            return
        self.state = EditorState()
        self.adjustments.set_state(self.state)
        self._render_generation += 1
        self._render_timer.stop()
        self._start_preview_render()

    def _start_preview_render(self) -> None:
        if self.preview_source is None:
            return
        generation = self._render_generation
        worker = PreviewRenderWorker(self.preview_source, self.state, generation)
        worker.signals.finished.connect(self._preview_rendered)
        worker.signals.failed.connect(self._preview_failed)
        self._render_pool.start(worker)

    def _preview_rendered(self, pixels, generation: int) -> None:
        if generation != self._render_generation:
            return
        self.image_view.set_image(pixels)
        self.statusBar().showMessage(f"{self.loaded_image.description}  •  已编辑")

    def _preview_failed(self, details: str, generation: int) -> None:
        if generation != self._render_generation:
            return
        self.statusBar().showMessage("预览渲染失败；已保留当前参数")

    def _ai_placeholder(self, prompt: str) -> None:
        self.ai_panel.add_assistant_message("AI 编辑引擎将在下一开发阶段接入；当前图片已准备好。")

    def _not_available_yet(self) -> None:
        QMessageBox.information(self, "即将可用", "全分辨率导出正在接入。")

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 AI Lightroom",
            "AI Lightroom 0.1\n非破坏式桌面照片编辑器",
        )
