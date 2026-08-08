from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PySide6.QtCore import QSettings

from app.core.editor_state import EditorState
from app.core.history import HistoryManager


class SessionStore:
    """Stores lightweight recoverable edit sessions in app settings, never beside user photos."""

    def __init__(self, settings: QSettings) -> None:
        self.settings = settings

    def save(self, path: Path, state: EditorState, history: HistoryManager) -> None:
        key = self._key(path)
        payload = {
            "state": state.model_dump(mode="json"),
            "history": [{"label": entry.label, "state": entry.state.model_dump(mode="json")} for entry in history.entries[-50:]],
        }
        self.settings.setValue(f"sessions/{key}", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        self.settings.sync()

    def load(self, path: Path) -> dict | None:
        try:
            payload = json.loads(str(self.settings.value(f"sessions/{self._key(path)}", "")))
        except (TypeError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _key(path: Path) -> str:
        stat = path.stat()
        source = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
        return hashlib.sha256(source).hexdigest()
