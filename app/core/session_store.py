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
        # Keep the active cursor inside the retained window, including its redo branch.
        start = max(0, history.cursor - 25)
        entries = history.entries[start:start + 50]
        payload = {
            "version": 2,
            "state": state.model_dump(mode="json"),
            "cursor": history.cursor - start,
            "history": [{"label": entry.label, "state": entry.state.model_dump(mode="json")} for entry in entries],
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
    def restore(payload: dict, history: HistoryManager) -> EditorState:
        """Recover the active state and redo branch; migrate cursor-less v1 sessions."""
        state = EditorState.model_validate(payload["state"])
        entries = payload.get("history", [])
        if not entries:
            history.reset(state, "恢复编辑")
            return state
        validated = [(EditorState.model_validate(item["state"]), str(item.get("label", "编辑"))) for item in entries]
        history.reset(validated[0][0], validated[0][1])
        for saved, label in validated[1:]:
            history.push(saved, label)
        cursor = payload.get("cursor")
        if not isinstance(cursor, int) or not 0 <= cursor < len(history.entries):
            cursor = next((i for i, entry in enumerate(history.entries) if entry.state == state), -1)
        if cursor >= 0 and history.entries[cursor].state == state:
            history.restore(cursor)
        else:
            history.push(state, "恢复编辑")
        return state

    @staticmethod
    def _key(path: Path) -> str:
        stat = path.stat()
        source = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
        return hashlib.sha256(source).hexdigest()
