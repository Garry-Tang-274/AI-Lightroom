from __future__ import annotations

from pathlib import Path
import os
import tempfile

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
    source_path: str | Path | None = None,
) -> Path:
    path = Path(destination)
    suffix = path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("导出格式必须是 JPG 或 PNG。")
    if not 1 <= jpeg_quality <= 100:
        raise ValueError("JPG 质量必须在 1 到 100 之间。")
    if not path.parent.exists():
        raise FileNotFoundError(f"导出文件夹不存在：{path.parent}")
    if source_path is not None:
        original = Path(source_path)
        if path.resolve() == original.resolve() or (
            path.exists() and original.exists() and path.samefile(original)
        ):
            raise ValueError("不能覆盖原始照片，请选择其他导出文件名。")

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
        image_format = "JPEG"
    else:
        options.update(compress_level=6)
        image_format = "PNG"
    # Encode beside the destination, then replace atomically. A failed encode
    # or full disk must not truncate a previously exported photograph.
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{path.stem[:40]}-", suffix=".tmp", dir=path.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            image.save(temporary, format=image_format, **options)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return path

