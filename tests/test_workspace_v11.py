from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings, Qt

from app.core.editor_state import EditorState
from app.core.history import HistoryManager
from app.core.session_store import SessionStore
from app.ui.ai_panel import AIPanel
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog
from app.utils.config import SettingsManager, RuntimeSettings
from app.ai.provider_registry import provider_registry


def opened(qtbot, tmp_path):
    source = tmp_path / "photo.png"
    Image.new("RGB", (640, 420), (80, 110, 140)).save(source)
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_image(str(source))
    return window


def test_session_restores_undo_cursor_and_redo(tmp_path):
    history = HistoryManager()
    state = EditorState()
    history.reset(state)
    state.basic.exposure = 1
    history.push(state, "first")
    state.basic.contrast = 20
    history.push(state, "second")
    current = history.undo()
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"test")
    store = SessionStore(QSettings(str(tmp_path / "sessions.ini"), QSettings.Format.IniFormat))
    store.save(source, current, history)
    restored = HistoryManager()
    result = store.restore(store.load(source), restored)
    assert restored.cursor == 1
    assert result.basic.exposure == 1 and result.basic.contrast == 0
    assert restored.redo().basic.contrast == 20


def test_cursorless_session_migrates_active_state():
    history = HistoryManager()
    original = EditorState()
    edited = EditorState()
    edited.basic.exposure = 1
    payload = {"state": original.model_dump(), "history": [
        {"state": original.model_dump(), "label": "original"},
        {"state": edited.model_dump(), "label": "edit"}]}
    SessionStore.restore(payload, history)
    assert history.cursor == 0 and history.can_redo


def test_completed_render_does_not_hide_before(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    window._show_before()
    before = window.image_view._pixmap_item.pixmap().toImage()
    window._preview_rendered(np.full_like(window.preview_source, 180), window._render_generation)
    assert window._showing_before
    assert window.image_view._pixmap_item.pixmap().toImage() == before
    window._show_after()
    assert window.current_preview.mean() == 180


def test_completed_drag_frame_is_displayed_before_release(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    window._begin_interaction("Exposure")
    window._set_basic_adjustment("exposure", 1)
    window._preview_rendered(np.full_like(window.preview_source, 160), window._render_generation - 1)
    assert window.current_preview.mean() == 160
    assert len(window.history.entries) == 1
    window._finish_interaction("Exposure")
    assert len(window.history.entries) == 2


def test_delayed_ai_cannot_overwrite_changed_state(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    window._ai_document = window._document_generation
    window._ai_before_state = window.state.snapshot()
    window.state.basic.exposure = .7
    window._ai_worker = object()
    window._ai_finished(SimpleNamespace(state=EditorState()))
    assert window.state.basic.exposure == .7
    assert "未覆盖" in window.ai_panel.transcript.toPlainText()


def test_busy_actions_protect_transaction(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    window.image_view.set_brush_mode(True)
    window._ai_worker = object()
    try:
        window._sync_actions()
        assert not window.adjustments.isEnabled()
        assert not window.open_action.isEnabled()
        assert not window.history_list.isEnabled()
        assert window.before_action.isEnabled()
        assert not window.image_view._editing_enabled
        assert window.image_view._brush_mode
    finally:
        window._ai_worker = None
        window._sync_actions()
    assert window.image_view._editing_enabled


def test_ai_prevalidated_preview_is_immediately_displayed(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    window._ai_document = window._document_generation
    window._ai_before_state = window.state.snapshot()
    after = window.state.snapshot()
    after.basic.exposure = .5
    pixels = np.full_like(window.preview_source, 140)
    result = SimpleNamespace(state=after, final_plan=SimpleNamespace(summary="exposure", reasoning_summary="lighten"),
                             provider_name="test", vision_calls=1, analysis_preview_max_edge=1280,
                             changed_fields=["exposure"], created_masks=[], unsupported_operations=[],
                             has_changes=True, warnings=[], preview_pixels=pixels)
    window._ai_finished(result)
    assert window.current_preview is pixels
    assert window.state.basic.exposure == .5 and len(window.history.entries) == 2
    window.undo()
    assert window.state.basic.exposure == 0


def test_split_comparison_and_adaptive_pixel_scale(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    window.split_action.setChecked(True)
    assert window.image_view._comparison_enabled
    window.image_view.set_image(np.full((210, 320, 3), 120, np.uint8), (640, 420))
    assert window.image_view._scene.sceneRect().width() == 640
    assert window.image_view._pixmap_item.scale() == 2


def test_noop_ai_does_not_add_history(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    window._ai_document = window._document_generation
    window._ai_before_state = window.state.snapshot()
    result = SimpleNamespace(state=window.state.snapshot(), final_plan=SimpleNamespace(summary="nothing", reasoning_summary="none"),
                             provider_name="test", vision_calls=0, analysis_preview_max_edge=1280,
                             changed_fields=[], created_masks=[], unsupported_operations=[], has_changes=False, warnings=[])
    window._ai_finished(result)
    assert len(window.history.entries) == 1
    assert "未改变" in window.ai_panel.transcript.toPlainText()


def test_prompt_enter_newline_and_busy_dedup(qtbot):
    panel = AIPanel()
    qtbot.addWidget(panel)
    panel.set_ready(True)
    panel.input.setPlainText("中文第一行")
    qtbot.keyClick(panel.input, Qt.Key.Key_End)
    qtbot.keyClick(panel.input, Qt.Key.Key_Return)
    assert "\n" in panel.input.toPlainText()
    sent = []
    panel.prompt_submitted.connect(sent.append)
    panel.set_busy(True)
    qtbot.keyClick(panel.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert not sent
    panel.set_busy(False)
    qtbot.keyClick(panel.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert len(sent) == 1


def test_settings_show_only_selected_provider(qtbot):
    manager = SettingsManager()
    dialog = SettingsDialog(manager)
    qtbot.addWidget(dialog)
    dialog.provider.setCurrentIndex(dialog.provider.findData("qwen"))
    assert dialog.custom_name.isHidden() and dialog.jarvisart_root.isHidden()
    dialog.provider.setCurrentIndex(dialog.provider.findData("custom"))
    assert not dialog.custom_name.isHidden()
    assert dialog.jarvisart_root.isHidden()


def test_provider_connection_preferences_survive_switch():
    manager = SettingsManager()
    manager.save(RuntimeSettings(provider="qwen", model="my-qwen", base_url="https://example.test/v1"), "test-only")
    manager.save(RuntimeSettings(provider="gemini", model="my-gemini"), "another-test")
    config = manager.saved_provider_config("qwen")
    assert config.model == "my-qwen" and config.base_url == "https://example.test/v1"
    assert "test-only" not in str(manager.store.value("ai/providers/qwen/config"))


def test_open_image_worker_keeps_ui_responsive(qtbot, tmp_path):
    window = MainWindow()
    qtbot.addWidget(window)
    source = tmp_path / "async.png"
    Image.new("RGB", (500, 350), (80, 100, 120)).save(source)
    window.open_image_async(str(source))
    qtbot.waitUntil(lambda: window.loaded_image is not None and not window._loading, timeout=5000)
    assert window.loaded_image.path.name == "async.png"


def test_fast_drag_does_not_starve_render_timer(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    starts = []
    window._render_timer.timeout.connect(lambda: starts.append(True))
    window._begin_interaction("曝光")
    for index in range(12):
        window._set_basic_adjustment("exposure", index / 20)
        qtbot.wait(5)
    assert starts, "Fast pointer updates must not continually reset the frame deadline"
    window._finish_interaction("曝光")
    assert len(window.history.entries) == 2


def test_new_edit_before_redo_creates_a_new_branch(qtbot, tmp_path):
    window = opened(qtbot, tmp_path)
    window._set_basic_adjustment("exposure", .5)
    window._flush_history()
    window.undo()
    window._set_basic_adjustment("contrast", 20)
    window.redo()
    assert window.state.basic.contrast == 20 and window.state.basic.exposure == 0
    assert not window.history.can_redo


def test_test_environment_never_uses_native_preferences():
    manager = SettingsManager()
    assert manager.store.format() == QSettings.Format.IniFormat
    assert "pytest" in manager.store.fileName()


def test_performance_modes_actually_change_interaction_resolution():
    assert RuntimeSettings(performance_mode="battery").interaction_preview_size == 768
    assert RuntimeSettings(performance_mode="balanced").interaction_preview_size == 1280
    assert RuntimeSettings(performance_mode="performance").interaction_preview_size == 1600
