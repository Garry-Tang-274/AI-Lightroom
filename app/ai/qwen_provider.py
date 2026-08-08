from __future__ import annotations

from app.ai.capabilities import ProviderCapabilities
from app.ai.openai_compatible_provider import OpenAICompatibleProvider


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
