from __future__ import annotations

import json
import shutil
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image
from platformdirs import user_data_path
from PySide6.QtCore import QSettings

from app.core.editor_state import WatermarkLayer


SUPPORTED_WATERMARKS = {".png", ".jpg", ".jpeg", ".webp"}


class WatermarkLibrary:
    def __init__(self, store: QSettings | None = None) -> None:
        self.store = store or QSettings("AI Lightroom", "AI Lightroom")
        self.directory = user_data_path("AI Lightroom", "AI Lightroom") / "watermarks"
        self.directory.mkdir(parents=True, exist_ok=True)

    def entries(self) -> list[dict]:
        try:
            entries = json.loads(str(self.store.value("watermarks/library", "[]")))
        except (TypeError, ValueError):
            return []
        return [entry for entry in entries if isinstance(entry, dict) and (self.directory / entry.get("filename", "")).is_file()]

    def add(self, source: str | Path, name: str | None = None) -> dict:
        source = Path(source)
        if source.suffix.lower() not in SUPPORTED_WATERMARKS:
            raise ValueError("水印仅支持 PNG、JPG 或 WEBP")
        asset_id = str(uuid4())
        filename = f"{asset_id}{source.suffix.lower()}"
        shutil.copy2(source, self.directory / filename)
        entry = {"id": asset_id, "filename": filename, "name": name or source.stem}
        entries = self.entries()
        entries.append(entry)
        self._save(entries)
        return entry

    def rename(self, asset_id: str, name: str) -> None:
        entries = self.entries()
        for entry in entries:
            if entry["id"] == asset_id:
                entry["name"] = name.strip() or entry["name"]
        self._save(entries)

    def delete(self, asset_id: str) -> None:
        entries = self.entries()
        retained = [entry for entry in entries if entry["id"] != asset_id]
        for entry in entries:
            if entry["id"] == asset_id:
                path = self.directory / entry["filename"]
                if path.is_file():
                    path.unlink()
        self._save(retained)

    def set_default(self, asset_id: str) -> None:
        if self.path_for(asset_id):
            self.store.setValue("watermarks/default_id", asset_id)
            self.store.sync()

    def default(self) -> dict | None:
        target = str(self.store.value("watermarks/default_id", ""))
        return next((entry for entry in self.entries() if entry["id"] == target), None)

    def path_for(self, asset_id: str) -> Path | None:
        return next((self.directory / entry["filename"] for entry in self.entries() if entry["id"] == asset_id), None)

    def _save(self, entries: list[dict]) -> None:
        self.store.setValue("watermarks/library", json.dumps(entries, ensure_ascii=False))
        self.store.sync()


def composite_watermarks(image: np.ndarray, layers: list[WatermarkLayer], library: WatermarkLibrary | None = None) -> np.ndarray:
    if not layers:
        return image
    library = library or WatermarkLibrary()
    result = Image.fromarray(image, "RGB").convert("RGBA")
    for layer in layers:
        if not layer.enabled or layer.opacity <= 0:
            continue
        path = library.path_for(layer.asset_id)
        if path is None or not path.is_file():
            continue
        overlay = _load_overlay(str(path), layer.scale, result.size)
        if overlay is None:
            continue
        if layer.opacity < 1:
            alpha = overlay.getchannel("A").point(lambda value: round(value * layer.opacity))
            overlay.putalpha(alpha)
        result.alpha_composite(overlay, _position(layer, result.size, overlay.size))
    return np.asarray(result.convert("RGB"), dtype=np.uint8)


@lru_cache(maxsize=24)
def _load_overlay(path: str, scale: float, target_size: tuple[int, int]) -> Image.Image | None:
    try:
        with Image.open(path) as opened:
            overlay = opened.convert("RGBA")
    except (OSError, ValueError):
        return None
    longest = max(target_size)
    desired_longest = max(8, round(longest * max(0.01, min(1.0, scale))))
    ratio = min(1.0, desired_longest / max(overlay.size))
    size = (max(1, round(overlay.width * ratio)), max(1, round(overlay.height * ratio)))
    return overlay.resize(size, Image.Resampling.LANCZOS)


def _position(layer: WatermarkLayer, image_size: tuple[int, int], overlay_size: tuple[int, int]) -> tuple[int, int]:
    width, height = image_size
    overlay_width, overlay_height = overlay_size
    margin = max(0, round(min(width, height) * layer.margin))
    anchors = {
        "top_left": (margin, margin), "top_right": (width - overlay_width - margin, margin),
        "bottom_left": (margin, height - overlay_height - margin),
        "bottom_right": (width - overlay_width - margin, height - overlay_height - margin),
        "center": ((width - overlay_width) // 2, (height - overlay_height) // 2),
        "custom": (round((width - overlay_width) * layer.x), round((height - overlay_height) * layer.y)),
    }
    x, y = anchors.get(layer.position, anchors["bottom_right"])
    return max(0, min(width - overlay_width, x)), max(0, min(height - overlay_height, y))
