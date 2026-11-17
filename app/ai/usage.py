from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from threading import RLock
from uuid import uuid4

from PySide6.QtCore import QSettings

from app.ai.errors import AIRequestError


_USAGE_LOCK = RLock()


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

    def record_started_request(self, provider: str, model: str) -> str:
        # All cloud entry points (including tests and optional reinspection)
        # pass this boundary immediately before their one SDK request.
        with _USAGE_LOCK:
            self.store.sync()
            status = self.status()
            if not status.can_request:
                message = "云端 AI 已在费用保护设置中禁用。" if not status.cloud_enabled else "已达到 AI Lightroom 设置的每日云端调用上限。为了防止意外费用，云端 AI 已暂停。"
                raise AIRequestError("本地 AI 费用保护", message, provider=provider, model=model)
            self.store.setValue("ai/usage_today_count", status.today_count + 1)
            self.store.setValue("ai/usage_month_count", status.month_count + 1)
            request_id = uuid4().hex
            self._append_event(provider, model, "请求已发出", request_id=request_id)
            self.store.sync()
            return request_id

    def record_result(self, provider: str, model: str, result: str, *, input_tokens: int | None = None, output_tokens: int | None = None, total_tokens: int | None = None, request_id: str | None = None) -> None:
        with _USAGE_LOCK:
            self.store.sync()
            self._append_event(provider, model, result, input_tokens, output_tokens, total_tokens, request_id=request_id)
            self.store.sync()

    def recent_events(self, limit: int = 12) -> list[dict]:
        try:
            events = json.loads(str(self.store.value("ai/usage_events", "[]")))
        except (TypeError, ValueError):
            return []
        return [event for event in events if isinstance(event, dict)][-max(1, limit) :][::-1] if isinstance(events, list) else []

    def _append_event(self, provider: str, model: str, result: str, input_tokens: int | None = None, output_tokens: int | None = None, total_tokens: int | None = None, *, request_id: str | None = None) -> None:
        try:
            events = json.loads(str(self.store.value("ai/usage_events", "[]")))
        except (TypeError, ValueError):
            events = []
        events = [event for event in events if isinstance(event, dict)] if isinstance(events, list) else []
        matching = next((event for event in reversed(events) if (
            event.get("id") == request_id if request_id else
            event.get("provider") == provider and event.get("model") == model and event.get("result") == "请求已发出"
        )), None)
        if matching is not None and result != "请求已发出":
            matching["result"] = result
            for key, value in (("input_tokens", input_tokens), ("output_tokens", output_tokens), ("total_tokens", total_tokens)):
                if value is not None:
                    matching[key] = value
        else:
            events.append({"id": request_id or uuid4().hex, "time": datetime.now().strftime("%H:%M"), "date": date.today().isoformat(), "provider": provider, "model": model, "result": result, "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens})
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


class CloudRequestTracker:
    """Bind accounting to actual SDK attempts rather than possession of a key."""

    def __init__(self, usage: AIUsageManager, provider: str, model: str, *, cloud: bool, cancelled=lambda: False) -> None:
        self.usage, self.provider, self.model = usage, provider, model
        self.cloud, self.cancelled = cloud, cancelled
        self.request_id: str | None = None
        self.request_sent = False

    def started(self) -> None:
        self.request_id = None
        self.check_cancelled()
        if self.cloud:
            self.request_id = self.usage.record_started_request(self.provider, self.model)
            self.request_sent = True

    def result(self, result: str, input_tokens=None, output_tokens=None, total_tokens=None) -> None:
        if self.request_id:
            self.usage.record_result(self.provider, self.model, result, request_id=self.request_id,
                                     input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens)

    def check_cancelled(self) -> None:
        if self.cancelled():
            raise AIRequestError("已取消本地等待", "已取消本次编辑，照片未修改；已发出的请求仍可能计入调用。",
                                 provider=self.provider, model=self.model, request_sent=self.request_sent)
