from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_SRGB_PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))


@dataclass(slots=True)
class LoadedImage:
    pixels: np.ndarray
    path: Path
    width: int
    height: int
    mode: str
    file_size: int
    icc_profile: bytes | None = None
    exif: bytes | None = None
    dpi: tuple[float, float] | None = None

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
        exif = image.info.get("exif")
        dpi = image.info.get("dpi")
        # The renderer uses sRGB transfer functions. Tagged RGB images need
        # conversion too (e.g. Display P3 / Adobe RGB), not just CMYK/LAB.
        image = _to_srgb(image)
        icc_profile = _SRGB_PROFILE.tobytes()
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (24, 24, 24))
            background.paste(image, mask=image.getchannel("A"))
            image = background
        pixels = np.asarray(image, dtype=np.uint8).copy()

    height, width = pixels.shape[:2]
    return LoadedImage(
        pixels=pixels,
        path=source,
        width=width,
        height=height,
        mode=original_mode,
        file_size=source.stat().st_size,
        icc_profile=icc_profile,
        exif=exif,
        dpi=dpi,
    )


def _to_srgb(image: Image.Image) -> Image.Image:
    has_alpha = "A" in image.getbands() or "transparency" in image.info
    alpha = image.convert("RGBA").getchannel("A") if has_alpha else None
    profile = image.info.get("icc_profile")
    try:
        if profile:
            source_profile = ImageCms.ImageCmsProfile(BytesIO(profile))
            profile_space = source_profile.profile.xcolor_space.strip()
            input_mode = {"RGB": "RGB", "GRAY": "L", "CMYK": "CMYK", "Lab": "LAB"}.get(profile_space, image.mode)
            color_image = image.convert(input_mode) if image.mode != input_mode else image
            converted = ImageCms.profileToProfile(color_image, source_profile, _SRGB_PROFILE, outputMode="RGB")
        else:
            converted = image.convert("RGB")
    except (ImageCms.PyCMSError, OSError, TypeError) as exc:
        raise ValueError("无法读取照片的 ICC 色彩配置。请先将照片转换为 sRGB 后重新打开。") from exc
    if alpha is not None:
        converted.putalpha(alpha)
    return converted


def make_preview(pixels: np.ndarray, max_edge: int = 1600) -> np.ndarray:
    if pixels.dtype != np.uint8 or pixels.ndim != 3 or pixels.shape[2] != 3:
        raise ValueError("pixels must be an RGB uint8 image")
    if max_edge < 1 or not pixels.shape[0] or not pixels.shape[1]:
        raise ValueError("Preview dimensions must be positive")
    height, width = pixels.shape[:2]
    scale = min(1.0, max_edge / max(height, width))
    if scale >= 1.0:
        return pixels.copy()
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return np.asarray(Image.fromarray(pixels).resize(new_size, Image.Resampling.LANCZOS), dtype=np.uint8)
