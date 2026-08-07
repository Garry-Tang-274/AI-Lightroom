from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from app.core.editor_state import EditorState
from app.core.exporter import export_image


def test_export_uses_full_resolution_for_jpeg_and_png(tmp_path):
    source = np.full((137, 251, 3), (70, 100, 140), dtype=np.uint8)
    state = EditorState()
    state.basic.exposure = 0.25
    for suffix in ("jpg", "png"):
        path = tmp_path / f"中文 导出.{suffix}"
        export_image(source, state, path, jpeg_quality=95)
        with Image.open(path) as exported:
            assert exported.size == (251, 137)


def test_export_rejects_invalid_target(tmp_path):
    source = np.zeros((10, 10, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        export_image(source, EditorState(), tmp_path / "bad.webp")
    with pytest.raises(FileNotFoundError):
        export_image(source, EditorState(), tmp_path / "missing" / "bad.png")
