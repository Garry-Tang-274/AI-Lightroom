from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AIEditSession:
    """Bounded per-photo context reserved for future multi-turn AI editing."""

    photo_id: str
    recent_user_requests: list[str] = field(default_factory=list)
    recent_plan_summaries: list[str] = field(default_factory=list)

    def record(self, request: str, summary: str) -> None:
        self.recent_user_requests = (self.recent_user_requests + [request])[-8:]
        self.recent_plan_summaries = (self.recent_plan_summaries + [summary])[-8:]
