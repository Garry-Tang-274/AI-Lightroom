from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from app.ai.gemini_provider import GeminiProvider
from app.ai.provider import PlanningRequest
from app.core.editor_state import EditorState
from app.core.masks import generate_mask
from app.ui.main_window import MainWindow
from app.utils.io_utils import load_image, make_preview
from app.utils.secure_store import WindowsCredentialStore


def test_consecutive_images_replace_source_and_invalidate_old_render(qtbot, tmp_path):
    first = tmp_path / "first.jpg"
    second = tmp_path / "第二张 竖图.png"
    Image.new("RGB", (500, 300), (200, 30, 20)).save(first)
    Image.new("RGB", (240, 420), (20, 40, 180)).save(second)
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_image(str(first))
    generation = window._render_generation
    window.adjustments.controls["clarity"].slider.setValue(40)
    window.open_image(str(second))
    assert window._render_generation > generation
    assert window.loaded_image.path == second
    assert window.preview_source.shape == (420, 240, 3)
    assert window.state.is_pristine()


def test_large_jpeg_is_reduced_for_preview_but_original_is_retained(tmp_path):
    source = tmp_path / "large.jpg"
    Image.new("RGB", (5200, 3100), (80, 100, 120)).save(source, quality=88)
    loaded = load_image(source)
    preview = make_preview(loaded.pixels, 1024)
    assert loaded.pixels.shape == (3100, 5200, 3)
    assert max(preview.shape[:2]) == 1024


def test_corrupt_and_unsupported_images_fail_cleanly(tmp_path):
    corrupt = tmp_path / "broken.jpg"
    corrupt.write_bytes(b"not a jpeg")
    with pytest.raises(Exception):
        load_image(corrupt)
    unsupported = tmp_path / "photo.webp"
    unsupported.write_bytes(b"x")
    with pytest.raises(ValueError, match="JPG"):
        load_image(unsupported)


def test_invalid_ai_json_is_rejected_without_partial_state():
    class BrokenModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text='{"summary": "missing fields", nope}')

    provider = GeminiProvider("", "test", client=SimpleNamespace(models=BrokenModels()))
    state = EditorState()
    with pytest.raises(ValidationError):
        provider.plan(PlanningRequest("edit", state, None, []))
    assert state.is_pristine()


def test_mask_engine_rejects_invalid_pixel_input():
    from app.core.editor_state import MaskLayer, MaskType

    with pytest.raises(ValueError, match="RGB uint8"):
        generate_mask(np.zeros((20, 20), dtype=np.uint8), MaskLayer(name="sky", type=MaskType.SKY))


def test_windows_credential_store_round_trip():
    target = f"AI Lightroom/Test/{uuid4()}"
    store = WindowsCredentialStore(target)
    try:
        store.set("temporary-test-secret")
        assert store.get() == "temporary-test-secret"
    finally:
        store.delete()
