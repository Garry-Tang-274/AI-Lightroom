from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime

from PySide6.QtCore import QSettings


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    mode: str
    daily_limit: int
    today_count: int
    month_count: int

    @property
    def cloud_enabled(self) -> bool:
        return self.mode != "disabled"

    @property
    def can_request(self) -> bool:
        return self.cloud_enabled and self.today_count < self.daily_limit


class AIUsageManager:
    """Local accounting; it never claims to know Google's live quota."""

    def __init__(self, store: QSettings) -> None:
        self.store = store

    def status(self) -> BudgetStatus:
        self._rollover()
        mode = str(self.store.value("ai/budget_mode", "free"))
        limit = 20 if mode == "free" else self._as_int(self.store.value("ai/custom_daily_limit", 20), 20)
        if mode == "disabled":
            limit = 0
        return BudgetStatus(mode, max(0, limit), self._as_int(self.store.value("ai/usage_today_count", 0), 0), self._as_int(self.store.value("ai/usage_month_count", 0), 0))

    def record_started_request(self, provider: str, model: str) -> None:
        self._rollover()
        self.store.setValue("ai/usage_today_count", self._as_int(self.store.value("ai/usage_today_count", 0), 0) + 1)
        self.store.setValue("ai/usage_month_count", self._as_int(self.store.value("ai/usage_month_count", 0), 0) + 1)
        self._append_event(provider, model, "请求已发出")
        self.store.sync()

    def record_result(self, provider: str, model: str, result: str, *, input_tokens: int | None = None, output_tokens: int | None = None, total_tokens: int | None = None) -> None:
        self._append_event(provider, model, result, input_tokens, output_tokens, total_tokens)
        self.store.sync()

    def recent_events(self, limit: int = 12) -> list[dict]:
        try:
            events = json.loads(str(self.store.value("ai/usage_events", "[]")))
        except (TypeError, ValueError):
            return []
        return events[-max(1, limit) :][::-1] if isinstance(events, list) else []

    def _append_event(self, provider: str, model: str, result: str, input_tokens: int | None = None, output_tokens: int | None = None, total_tokens: int | None = None) -> None:
        try:
            events = json.loads(str(self.store.value("ai/usage_events", "[]")))
        except (TypeError, ValueError):
            events = []
        if events and events[-1].get("result") == "请求已发出" and result != "请求已发出":
            events[-1].update({"result": result, "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens})
        else:
            events.append({"time": datetime.now().strftime("%H:%M"), "provider": provider, "model": model, "result": result, "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens})
        self.store.setValue("ai/usage_events", json.dumps(events[-100:], ensure_ascii=False))

    def _rollover(self) -> None:
        today = date.today().isoformat()
        month = today[:7]
        if str(self.store.value("ai/usage_date", "")) != today:
            self.store.setValue("ai/usage_date", today)
            self.store.setValue("ai/usage_today_count", 0)
        if str(self.store.value("ai/usage_month", "")) != month:
            self.store.setValue("ai/usage_month", month)
            self.store.setValue("ai/usage_month_count", 0)

    @staticmethod
    def _as_int(value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
