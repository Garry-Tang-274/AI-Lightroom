from __future__ import annotations

from app.ai.capabilities import ProviderCapabilities
from app.ai.errors import AIRequestError
from app.ai.openai_compatible_provider import OpenAICompatibleProvider
from app.ai.schemas import EditingPlan


QWEN_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# Qwen visual structured output is a heavier request than a small text
# connection probe.  Give it a realistic local deadline without ever retrying.
QWEN_VISION_TIMEOUT_SECONDS = 120.0


class QwenProvider(OpenAICompatibleProvider):
    """Alibaba Cloud Model Studio Qwen adapter using its official compatible API."""

    id = "qwen"
    name = "阿里云百炼 / Qwen"
    capabilities = ProviderCapabilities(
        supports_vision=True, supports_multiple_images=True,
        supports_structured_output=True, supports_text_chat=True,
        supports_streaming=True, supports_custom_base_url=True,
    )

    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.7-plus",
        base_url: str = QWEN_DEFAULT_BASE_URL,
        *,
        timeout_seconds: float = QWEN_VISION_TIMEOUT_SECONDS,
        **kwargs,
    ) -> None:
        super().__init__(
            api_key, model, base_url, provider_id=self.id, display_name=self.name,
            capabilities=self.capabilities, timeout_seconds=timeout_seconds, **kwargs,
        )

    def _request_options(self) -> dict[str, object]:
        # Qwen3.7-plus is hybrid-thinking by default.  Alibaba Cloud documents
        # visual structured JSON for non-thinking mode; disabling it also keeps
        # latency bounded for an interactive photo-editing request.
        return {"extra_body": {"enable_thinking": False}}

    def _plan_request_options(self) -> dict[str, object]:
        # One forced function call is a single Chat Completions request, not an
        # agent loop.  It gives Qwen the actual nested EditingPlan schema rather
        # than asking JSON mode to infer it from prose.
        return {
            **self._request_options(),
            "tools": [self._editing_plan_tool()],
            "tool_choice": "required",
        }

    def _plan_response_format(self) -> dict[str, object]:
        # Function arguments are already JSON.  Do not combine Qwen JSON mode
        # with a forced tool call, because they are two competing output paths.
        return {}

    def _plan_response_text(self, response) -> str:
        choices = getattr(response, "choices", None) or []
        message = getattr(choices[0], "message", None) if choices else None
        tool_calls = getattr(message, "tool_calls", None) or []
        if len(tool_calls) != 1:
            raise AIRequestError(
                "Qwen structured tool output 错误",
                "Qwen 没有返回唯一的 submit_editing_plan 调用；照片未发生任何修改。",
                provider=self.name,
                model=self.model,
                request_sent=True,
            )
        function = getattr(tool_calls[0], "function", None)
        if getattr(function, "name", "") != "submit_editing_plan":
            raise AIRequestError(
                "Qwen structured tool output 错误",
                "Qwen 返回了未授权的结构化操作；照片未发生任何修改。",
                provider=self.name,
                model=self.model,
                request_sent=True,
            )
        return str(getattr(function, "arguments", "") or "")

    @staticmethod
    def _editing_plan_tool() -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": "submit_editing_plan",
                "description": "Submit one complete AI Lightroom EditingPlan. This is the only allowed action.",
                "parameters": EditingPlan.model_json_schema(),
            },
        }
