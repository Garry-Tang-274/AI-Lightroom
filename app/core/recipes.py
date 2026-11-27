"""User-named photographic looks. A recipe contains parameters, never pixels."""
from __future__ import annotations

import json
from PySide6.QtCore import QSettings

from app.core.editor_state import EditorState


# Geometry, lens corrections, masks and overlays belong to the target photograph.
LOOK_FIELDS = {"basic", "hsl", "curves", "color_grading", "detail", "effects", "calibration"}


class RecipeLibrary:
    key = "recipes/v1"

    def __init__(self, settings: QSettings) -> None:
        self.settings = settings

    def _read(self) -> dict:
        items = json.loads(str(self.settings.value(self.key, "{}")))
        if not isinstance(items, dict):
            raise ValueError("无法读取本机配方库，原有内容未改变。")
        return items

    def _write(self, items: dict) -> None:
        self.settings.setValue(self.key, json.dumps(items, ensure_ascii=False, separators=(",", ":")))
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            raise OSError("未能将配方写入本机设置。")

    def names(self) -> list[str]:
        return sorted(self._read(), key=str.casefold)

    def save(self, name: str, state: EditorState, *, replace: bool = False) -> None:
        name = name.strip()
        if not name or len(name) > 64:
            raise ValueError("配方名称须为 1–64 个字符。")
        items = self._read()
        if name in items and not replace:
            raise ValueError("已有同名配方。")
        items[name] = state.model_dump(mode="json", include=LOOK_FIELDS)
        self._write(items)

    def apply(self, name: str, target: EditorState) -> EditorState:
        look = self._read()[name]
        if not isinstance(look, dict) or set(look) != LOOK_FIELDS:
            raise ValueError("此配方不完整，未应用。")
        state = EditorState.model_validate({**target.model_dump(), **look})
        if state.hsl.keys() != target.hsl.keys():
            raise ValueError("配方 HSL 通道不完整，未应用。")
        return state

    def remove(self, name: str) -> None:
        items = self._read()
        del items[name]
        self._write(items)
