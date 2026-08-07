from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.ai.schemas import EditingPlan
from app.core.editor_state import EditorState


@dataclass(slots=True)
class PlanningRequest:
    instruction: str
    state: EditorState
    preview_jpeg: bytes | None
    history_summary: list[str]
    is_reinspection: bool = False


class AIProvider(ABC):
    name = "AI Provider"

    @abstractmethod
    def plan(self, request: PlanningRequest) -> EditingPlan:
        raise NotImplementedError

