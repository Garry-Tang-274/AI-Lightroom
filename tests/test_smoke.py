from __future__ import annotations

import numpy as np
from PIL import Image

from app.ui.main_window import MainWindow
from app.utils.io_utils import load_image, make_preview
from app.utils.config import RuntimeSettings


def test_load_image_and_preview(tmp_path):
    source = tmp_path / "中文 测试.png"
    Image.new("RGB", (2400, 1200), (12, 34, 56)).save(source)
    loaded = load_image(source)
    preview = make_preview(loaded.pixels, 800)
    assert loaded.width == 2400
    assert loaded.height == 1200
    assert preview.shape == (400, 800, 3)
    assert preview.dtype == np.uint8


def test_main_window_starts(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "AI Lightroom"
    assert not window.export_action.isEnabled()


def test_manual_slider_updates_the_shared_editor_state(qtbot, tmp_path):
    source = tmp_path / "sample.jpg"
    Image.new("RGB", (320, 200), (80, 100, 120)).save(source)
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_image(str(source))
    window.adjustments.controls["exposure"].slider.setValue(35)
    assert window.state.basic.exposure == 0.35
    assert window.preview_source.shape == (200, 320, 3)
    window._flush_history()
    window.undo()
    assert window.state.basic.exposure == 0
    window.redo()
    assert window.state.basic.exposure == 0.35


def test_mask_layer_ui_and_state_stay_synchronized(qtbot, tmp_path):
    source = tmp_path / "mask-source.png"
    Image.new("RGB", (300, 180), (90, 140, 200)).save(source)
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_image(str(source))
    window._create_mask("sky")
    assert len(window.state.masks) == 1
    layer = window.state.masks[0]
    assert window.mask_panel.selected_mask_id == layer.id
    window._set_local_adjustment(layer.id, "exposure", -0.4)
    assert window.state.masks[0].adjustments.exposure == -0.4


def test_offline_ai_command_updates_visible_state(qtbot, tmp_path, monkeypatch):
    source = tmp_path / "ai-source.jpg"
    pixels = np.zeros((180, 300, 3), dtype=np.uint8)
    pixels[:90] = (80, 145, 220)
    pixels[90:] = (95, 85, 60)
    Image.fromarray(pixels).save(source)
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_image(str(source))
    monkeypatch.setattr(window.settings_manager, "runtime", lambda: RuntimeSettings(provider="mock"))
    monkeypatch.setattr(window.settings_manager, "gemini_api_key", lambda: "")
    window._run_ai_edit("做出轻微电影感，天空压一点，但不要把地面搞暗")
    qtbot.waitUntil(lambda: window._ai_worker is None, timeout=5000)
    assert window.state.basic.contrast > 0
    assert any(layer.type.value == "sky" for layer in window.state.masks)
    assert window.adjustments.controls["contrast"].slider.value() > 0
