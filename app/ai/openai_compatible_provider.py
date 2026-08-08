from __future__ import annotations

import base64

from openai import OpenAI
from pydantic import ValidationError

from app.ai.capabilities import ProviderCapabilities
from app.ai.errors import AIRequestError, error_from_exception
from app.ai.prompt_builder import build_prompt
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import EditingPlan
from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT


class OpenAICompatibleProvider(AIProvider):
    """Adapter for OpenAI-compatible Chat Completions services.

    It asks only for a JSON EditingPlan. It neither enables tools nor calls an
    image-generation/editing endpoint.
    """

    id = "openai_compatible"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        *,
        provider_id: str = "openai_compatible",
        display_name: str = "OpenAI Compatible",
        capabilities: ProviderCapabilities = ProviderCapabilities(
            supports_vision=True, supports_multiple_images=True,
            supports_structured_output=True, supports_text_chat=True,
            supports_streaming=True, supports_custom_base_url=True,
        ),
        client=None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        on_request_started=None,
        on_result=None,
        timeout_seconds: float = 45.0,
    ) -> None:
        if not api_key and client is None:
            raise ValueError(f"{display_name} API Key 为空")
        if not base_url and client is None:
            raise ValueError(f"{display_name} Base URL 为空")
        self.id = provider_id
        self.name = display_name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.capabilities = capabilities
        # Keep this explicit: the app's cost-safety rule is zero automatic
        # retries, while the provider-specific deadline can accommodate a
        # genuine multimodal inference request.
        self.timeout_seconds = float(timeout_seconds)
        self.client = client or OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            max_retries=0,
        )
        self.system_prompt = system_prompt
        self.on_request_started = on_request_started
        self.on_result = on_result

    def plan(self, request: PlanningRequest) -> EditingPlan:
        user_content: list[dict[str, object]] = [{"type": "text", "text": build_prompt(request, "")}]
        if request.preview_jpeg:
            image_url = "data:image/jpeg;base64," + base64.b64encode(request.preview_jpeg).decode("ascii")
            user_content.append({"type": "image_url", "image_url": {"url": image_url}})
        if request.preview_jpeg and not self.capabilities.supports_vision:
            raise AIRequestError("Provider 不支持视觉输入", "当前 Provider 未声明图片理解能力，未发送请求。", provider=self.name, model=self.model)
        if self.on_request_started:
            self.on_request_started()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt + "\n\nReturn only valid JSON matching the EditingPlan schema."},
                    {"role": "user", "content": user_content},
                ],
                **({"response_format": {"type": "json_object"}} if self.capabilities.supports_structured_output else {}),
                **self._request_options(),
            )
        except Exception as exc:
            error = error_from_exception(exc, model=self.model, request_sent=True, provider=self.name)
            if error.category == "请求超时":
                error.message = (
                    f"{self.name} 的视觉调色请求在 {self.timeout_seconds:.0f} 秒内未完成。"
                    "请求没有自动重试，照片未发生任何修改。"
                )
            raise error from exc
        text = _completion_text(response)
        if not text:
            raise AIRequestError(f"{self.name} 返回空内容", "AI 未返回可执行的 EditingPlan。", provider=self.name, model=self.model, request_sent=True)
        try:
            plan = EditingPlan.model_validate_json(text)
        except ValidationError as exc:
            raise AIRequestError(
                category="Pydantic schema 校验错误",
                message=f"{self.name} 返回 JSON 不符合严格 EditingPlan schema。",
                provider=self.name, model=self.model, local_exception=type(exc).__name__,
                validation_errors=exc.errors(include_url=False), request_sent=True,
            ) from exc
        if self.on_result:
            usage = getattr(response, "usage", None)
            self.on_result("成功", getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None), getattr(usage, "total_tokens", None))
        return plan

    def test_connection(self) -> str:
        if self.on_request_started:
            self.on_request_started()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Return JSON exactly: {\"status\":\"ok\"}"}],
                **({"response_format": {"type": "json_object"}} if self.capabilities.supports_structured_output else {}),
                **self._request_options(),
            )
        except Exception as exc:
            raise error_from_exception(exc, model=self.model, request_sent=True, provider=self.name) from exc
        if not _completion_text(response):
            raise AIRequestError(f"{self.name} 返回空内容", "连接测试没有返回文本。", provider=self.name, model=self.model, request_sent=True)
        if self.on_result:
            usage = getattr(response, "usage", None)
            self.on_result("连接测试成功", getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None), getattr(usage, "total_tokens", None))
        return "连接成功"

    def _request_options(self) -> dict[str, object]:
        """Vendor-neutral extension point for compatible API options."""
        return {}


def _completion_text(response) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    return str(getattr(getattr(choices[0], "message", None), "content", "") or "")
