from __future__ import annotations

from app.core.editor_state import EditorState
from app.core.history import HistoryManager


def state_with_exposure(value: float) -> EditorState:
    state = EditorState()
    state.basic.exposure = value
    return state


def test_history_undo_redo_and_branching():
    history = HistoryManager()
    history.reset(EditorState(), "open")
    history.push(state_with_exposure(0.2), "first")
    history.push(state_with_exposure(0.5), "second")
    assert history.undo().basic.exposure == 0.2
    assert history.redo().basic.exposure == 0.5
    assert history.undo().basic.exposure == 0.2
    history.push(state_with_exposure(-0.1), "branch")
    assert not history.can_redo
    assert [entry.label for entry in history.entries] == ["open", "first", "branch"]


def test_history_deduplicates_and_limits_entries():
    history = HistoryManager(limit=3)
    history.reset(EditorState())
    assert not history.push(EditorState(), "duplicate")
    for value in (0.1, 0.2, 0.3):
        history.push(state_with_exposure(value), str(value))
    assert len(history.entries) == 3
    assert history.entries[-1].state.basic.exposure == 0.3

