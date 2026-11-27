from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from app.ai.capabilities import ProviderCapabilities
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
    id = "provider"
    name = "AI Provider"
    capabilities = ProviderCapabilities()

    @abstractmethod
    def plan(self, request: PlanningRequest) -> EditingPlan:
        raise NotImplementedError

    def validate_config(self) -> None:
        """Raise a clear error only when this provider's configuration is invalid."""

    def set_execution_hooks(self, *, on_stage: Callable[[str, str], None], check_cancelled: Callable[[], None]) -> None:
        """Optional local-runtime stages; transport request hooks stay separate."""

    def create_editing_plan(self, request: PlanningRequest) -> EditingPlan:
        return self.plan(request)

    def request(self, request: PlanningRequest) -> EditingPlan:
        return self.plan(request)

    def analyze_image(self, request: PlanningRequest) -> EditingPlan:
        return self.plan(request)

    def test_connection(self) -> str:
        """Make one small, explicit user-triggered request and return a safe status."""
        raise NotImplementedError("This provider does not expose a connection test")
