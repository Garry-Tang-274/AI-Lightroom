from __future__ import annotations

import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings

from app.core.editor_state import WatermarkLayer
from app.core.watermarks import WatermarkLibrary, composite_watermarks


def test_transparent_watermark_is_library_backed_and_non_destructive(tmp_path):
    source_file = tmp_path / "mark.png"
    overlay = Image.new("RGBA", (40, 20), (255, 20, 20, 0))
    overlay.paste((255, 20, 20, 220), (0, 0, 20, 20))
    overlay.save(source_file)
    store = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    library = WatermarkLibrary(store)
    library.directory = tmp_path / "library"
    library.directory.mkdir()
    entry = library.add(source_file)
    source = np.full((100, 160, 3), 40, dtype=np.uint8)
    result = composite_watermarks(source, [WatermarkLayer(asset_id=entry["id"], name="mark", position="top_left", scale=0.25, margin=0)], library)
    assert np.array_equal(source, np.full((100, 160, 3), 40, dtype=np.uint8))
    assert result[:20, :20, 0].mean() > source[:20, :20, 0].mean()
    assert np.array_equal(result[-10:, -10:], source[-10:, -10:])
