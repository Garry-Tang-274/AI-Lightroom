from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from app.core.editor_state import EditorState
from app.core.image_processor import render_image


def export_image(
    source: np.ndarray,
    state: EditorState,
    destination: str | Path,
    *,
    jpeg_quality: int = 92,
    icc_profile: bytes | None = None,
    exif: bytes | None = None,
    dpi: tuple[float, float] | None = None,
) -> Path:
    path = Path(destination)
    suffix = path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("导出格式必须是 JPG 或 PNG。")
    if not 1 <= jpeg_quality <= 100:
        raise ValueError("JPG 质量必须在 1 到 100 之间。")
    if not path.parent.exists():
        raise FileNotFoundError(f"导出文件夹不存在：{path.parent}")

    rendered = render_image(source, state)
    image = Image.fromarray(rendered, "RGB")
    options: dict[str, object] = {}
    if icc_profile:
        options["icc_profile"] = icc_profile
    if exif:
        options["exif"] = exif
    if dpi:
        options["dpi"] = dpi
    if suffix in {".jpg", ".jpeg"}:
        options.update(quality=jpeg_quality, subsampling=0, optimize=True)
        image.save(path, format="JPEG", **options)
    else:
        options.update(compress_level=6)
        image.save(path, format="PNG", **options)
    return path

