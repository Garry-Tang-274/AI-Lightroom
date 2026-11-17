from __future__ import annotations

import json
import re
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import ValidationError


@dataclass(slots=True)
class AIRequestError(Exception):
    category: str
    message: str
    provider: str = "Gemini"
    model: str = ""
    http_status: int | None = None
    provider_code: str = ""
    retry_after: str = ""
    request_id: str = ""
    local_exception: str = ""
    validation_errors: list[dict[str, Any]] | None = None
    request_sent: bool = False

    def __post_init__(self) -> None:
        self.message = redact_secrets(self.message)
        if self.validation_errors:
            self.validation_errors = safe_validation_errors(self.validation_errors)

    def __str__(self) -> str:
        return self.message

    def details(self) -> str:
        lines = [
            f"时间：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}",
            f"类型：{self.category}",
            f"Provider：{self.provider}",
        ]
        if self.model:
            lines.append(f"模型：{self.model}")
        if self.http_status is not None:
            lines.append(f"HTTP：{self.http_status}")
        if self.provider_code:
            lines.append(f"Provider code：{self.provider_code}")
        if self.retry_after:
            lines.append(f"Retry-After：{self.retry_after}")
        if self.request_id:
            lines.append(f"Request ID：{self.request_id}")
        lines.append(f"说明：{self.message}")
        if self.local_exception:
            lines.append(f"本地异常：{self.local_exception}")
        if self.validation_errors:
            lines.append("校验字段：" + json.dumps(self.validation_errors, ensure_ascii=False))
        lines.append("照片未发生任何修改。")
        return "\n".join(lines)

    def validation_summary(self, limit: int = 3) -> str:
        """A short, safe explanation suitable for the compact AI transcript."""
        if not self.validation_errors:
            return ""
        summary: list[str] = []
        for item in self.validation_errors[:limit]:
            location = ".".join(str(part) for part in item.get("loc", ())) or "response"
            message = str(item.get("msg", "invalid value"))
            summary.append(f"{location}: {message}")
        suffix = "；…" if len(self.validation_errors) > limit else ""
        return "；".join(summary) + suffix


def error_from_exception(exc: Exception, *, model: str, request_sent: bool, provider: str = "Gemini", secrets: tuple[str, ...] = ()) -> AIRequestError:
    if isinstance(exc, AIRequestError):
        exc.message = redact_secrets(exc.message, secrets)
        return exc
    if isinstance(exc, ValidationError):
        return AIRequestError(
            category="Pydantic schema 校验错误", message=f"{provider} 返回内容不符合 EditingPlan schema。",
            provider=provider, model=model, local_exception=type(exc).__name__, validation_errors=safe_validation_errors(exc),
            request_sent=request_sent,
        )
    if isinstance(exc, socket.gaierror):
        return AIRequestError("DNS 错误", f"无法解析 {provider} 服务地址。", provider=provider, model=model, local_exception=type(exc).__name__, request_sent=request_sent)
    if isinstance(exc, ssl.SSLError):
        return AIRequestError("TLS/SSL 错误", f"与 {provider} 服务建立安全连接失败。", provider=provider, model=model, local_exception=type(exc).__name__, request_sent=request_sent)
    if isinstance(exc, TimeoutError):
        return AIRequestError("请求超时", f"{provider} 请求超时。", provider=provider, model=model, local_exception=type(exc).__name__, request_sent=request_sent)
    status = _status_from_exception(exc)
    message = redact_secrets(_message_from_exception(exc), secrets)
    return AIRequestError(
        category=_category_for_status(status, message, provider), message=message, provider=provider, model=model, http_status=status,
        provider_code=str(getattr(exc, "code", "") or ""), retry_after=_header_value(exc, "retry-after"),
        request_id=_header_value(exc, "x-request-id") or _header_value(exc, "x-goog-request-id"),
        local_exception=type(exc).__name__, request_sent=request_sent,
    )


def redact_secrets(text: str, secrets: tuple[str, ...] = ()) -> str:
    """Keep provider diagnostics useful without echoing authorization material."""
    result = str(text)
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    result = re.sub(r"(?i)\bBearer\s+[^\s\"',;}]+", "Bearer [REDACTED]", result)
    result = re.sub(r"(?i)(\b(?:api[_-]?key|x-goog-api-key|authorization)\b[\"']?\s*[:=]\s*[\"']?)[^\s\"'&,;}]+", r"\1[REDACTED]", result)
    result = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{8,}|AIza[A-Za-z0-9_-]{20,})\b", "[REDACTED]", result)
    return result


def safe_validation_errors(errors: ValidationError | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Omit echoed inputs and exception context from UI and log diagnostics."""
    if isinstance(errors, ValidationError):
        errors = errors.errors(include_url=False, include_input=False, include_context=False)
    return [
        {"loc": tuple(redact_secrets(str(part)) if isinstance(part, str) else part for part in item.get("loc", ())),
         "type": str(item.get("type", "validation_error")),
         "msg": redact_secrets(str(item.get("msg", "invalid value")))}
        for item in errors
    ]


def _status_from_exception(exc: Exception) -> int | None:
    for value in (getattr(exc, "status_code", None), getattr(exc, "code", None), getattr(getattr(exc, "response", None), "status_code", None)):
        try:
            status = int(value)
        except (TypeError, ValueError):
            continue
        if 100 <= status <= 599:
            return status
    return None


def _header_value(exc: Exception, name: str) -> str:
    headers = getattr(getattr(exc, "response", None), "headers", None) or getattr(exc, "headers", None)
    try:
        return str(headers.get(name, "")) if headers else ""
    except AttributeError:
        return ""


def _message_from_exception(exc: Exception) -> str:
    text = str(exc).strip()
    return text[:1600] if text else "AI Provider 请求出现未知错误。"


def _category_for_status(status: int | None, message: str, provider: str) -> str:
    lowered = message.lower()
    if status == 401:
        return "API Key 无效（HTTP 401）"
    if status == 403:
        return "API Key 权限不足（HTTP 403）"
    if status == 429:
        return f"{provider} API 配额或 Rate Limit（HTTP 429）"
    if status is not None and status >= 500:
        return f"{provider} 服务器错误（5xx）"
    if "quota" in lowered:
        return f"{provider} API 配额耗尽"
    if "rate" in lowered and "limit" in lowered:
        return f"{provider} Rate Limit"
    if "token" in lowered and ("limit" in lowered or "too" in lowered):
        return "Token 限制"
    if "timeout" in lowered or "timed out" in lowered:
        return "请求超时"
    if "dns" in lowered or "name resolution" in lowered:
        return "DNS 错误"
    if "ssl" in lowered or "tls" in lowered:
        return "TLS/SSL 错误"
    if "connect" in lowered or "network" in lowered:
        return "网络不可用"
    return f"{provider} 请求错误"
