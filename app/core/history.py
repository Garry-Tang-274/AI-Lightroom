from __future__ import annotations

from dataclasses import dataclass

from app.core.editor_state import EditorState


@dataclass(slots=True)
class HistoryEntry:
    label: str
    state: EditorState


class HistoryManager:
    def __init__(self, limit: int = 100) -> None:
        self.limit = max(2, limit)
        self._entries: list[HistoryEntry] = []
        self._cursor = -1

    @property
    def entries(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._entries)

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return 0 <= self._cursor < len(self._entries) - 1

    def reset(self, state: EditorState, label: str = "打开图片") -> None:
        self._entries = [HistoryEntry(label, state.snapshot())]
        self._cursor = 0

    def push(self, state: EditorState, label: str) -> bool:
        snapshot = state.snapshot()
        if self._cursor >= 0 and self._entries[self._cursor].state == snapshot:
            return False
        del self._entries[self._cursor + 1 :]
        self._entries.append(HistoryEntry(label, snapshot))
        if len(self._entries) > self.limit:
            overflow = len(self._entries) - self.limit
            del self._entries[:overflow]
        self._cursor = len(self._entries) - 1
        return True

    def undo(self) -> EditorState | None:
        if not self.can_undo:
            return None
        self._cursor -= 1
        return self._entries[self._cursor].state.snapshot()

    def redo(self) -> EditorState | None:
        if not self.can_redo:
            return None
        self._cursor += 1
        return self._entries[self._cursor].state.snapshot()

    def restore(self, index: int) -> EditorState | None:
        if not 0 <= index < len(self._entries):
            return None
        self._cursor = index
        return self._entries[index].state.snapshot()

