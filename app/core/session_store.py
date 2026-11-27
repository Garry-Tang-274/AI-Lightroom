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
        self._active: tuple[Path, str] | None = None

    def bind(self, path: Path, file_size: int, modified_ns: int | None) -> None:
        # Keep the identity of the decoded file, not whatever later occupies
        # that path while the photographer is editing or switching photos.
        resolved = path.resolve()
        self._active = (resolved, self._fingerprint(resolved, file_size, modified_ns)
                        if modified_ns is not None else self._disk_key(resolved))

    def save(self, path: Path, state: EditorState, history: HistoryManager) -> None:
        key = self._key(path)
        if len(history.entries) == 1 and state.is_pristine():
            # Merely browsing a photograph isn't an edit. Clearing an old
            # session here also honours an explicit "start from original".
            address = f"sessions/{key}"
            if self.settings.contains(address):
                self.settings.remove(address)
                self._sync()
            return
        # Keep the active cursor inside the retained window, including its redo branch.
        start = max(0, min(history.cursor - 25, len(history.entries) - 50))
        entries = history.entries[start:start + 50]
        payload = {
            "version": 2,
            "state": state.model_dump(mode="json"),
            "cursor": history.cursor - start,
            "history": [{"label": entry.label, "state": entry.state.model_dump(mode="json")} for entry in entries],
        }
        self.settings.setValue(f"sessions/{key}", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        self._sync()

    def _sync(self) -> None:
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            raise OSError("无法保存照片的编辑记录。")

    def load(self, path: Path) -> dict | None:
        try:
            payload = json.loads(str(self.settings.value(f"sessions/{self._key(path)}", "")))
        except (TypeError, ValueError, OSError):
            return None
        if not isinstance(payload, dict):
            return None
        # Older versions also stored one untouched state for every opened file.
        entries = payload.get("history")
        if isinstance(entries, list) and len(entries) == 1 and payload.get("state") == EditorState().model_dump(mode="json"):
            return None
        return payload

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

    def _key(self, path: Path) -> str:
        resolved = path.resolve()
        if self._active and self._active[0] == resolved:
            return self._active[1]
        return self._disk_key(resolved)

    @classmethod
    def _disk_key(cls, path: Path) -> str:
        stat = path.stat()
        return cls._fingerprint(path, stat.st_size, stat.st_mtime_ns)

    @staticmethod
    def _fingerprint(path: Path, size: int, modified_ns: int) -> str:
        source = f"{path}|{size}|{modified_ns}".encode("utf-8")
        return hashlib.sha256(source).hexdigest()
