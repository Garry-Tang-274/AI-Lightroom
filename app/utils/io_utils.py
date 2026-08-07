from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@dataclass(slots=True)
class LoadedImage:
    pixels: np.ndarray
    path: Path
    width: int
    height: int
    mode: str
    file_size: int

    @property
    def description(self) -> str:
        megapixels = (self.width * self.height) / 1_000_000
        size_mb = self.file_size / (1024 * 1024)
        return f"{self.width} × {self.height}  •  {megapixels:.1f} MP  •  {size_mb:.1f} MB  •  {self.mode}"


def load_image(path: str | Path) -> LoadedImage:
    source = Path(path)
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("当前版本仅支持 JPG 和 PNG 图片。")

    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        original_mode = image.mode
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (24, 24, 24))
            background.paste(image, mask=image.getchannel("A"))
            image = background
        elif image.mode != "RGB":
            image = _to_srgb(image)
        pixels = np.asarray(image, dtype=np.uint8).copy()

    height, width = pixels.shape[:2]
    return LoadedImage(
        pixels=pixels,
        path=source,
        width=width,
        height=height,
        mode=original_mode,
        file_size=source.stat().st_size,
    )


def _to_srgb(image: Image.Image) -> Image.Image:
    try:
        profile = image.info.get("icc_profile")
        if profile:
            source_profile = ImageCms.ImageCmsProfile(profile)
            target_profile = ImageCms.createProfile("sRGB")
            return ImageCms.profileToProfile(image, source_profile, target_profile, outputMode="RGB")
    except (ImageCms.PyCMSError, OSError, TypeError):
        pass
    return image.convert("RGB")


def make_preview(pixels: np.ndarray, max_edge: int = 1600) -> np.ndarray:
    height, width = pixels.shape[:2]
    scale = min(1.0, max_edge / max(height, width))
    if scale >= 1.0:
        return pixels.copy()
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return np.asarray(Image.fromarray(pixels).resize(new_size, Image.Resampling.LANCZOS), dtype=np.uint8)

