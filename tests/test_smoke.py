from __future__ import annotations

import numpy as np
from PIL import Image

from app.ui.main_window import MainWindow
from app.utils.io_utils import load_image, make_preview


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

