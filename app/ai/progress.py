from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AIProgress:
    """Observed work stages, never an estimated percentage or token count."""

    stage: str
    message: str
    request_number: int = 0
    request_sent: bool = False
    cloud: bool = False
