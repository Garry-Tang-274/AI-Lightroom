from __future__ import annotations

from app.ai.capabilities import ProviderCapabilities
from app.ai.openai_compatible_provider import OpenAICompatibleProvider


QWEN_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class QwenProvider(OpenAICompatibleProvider):
    """Alibaba Cloud Model Studio Qwen adapter using its official compatible API."""

    id = "qwen"
    name = "阿里云百炼 / Qwen"
    capabilities = ProviderCapabilities(
        supports_vision=True, supports_multiple_images=True,
        supports_structured_output=True, supports_text_chat=True,
        supports_streaming=True, supports_custom_base_url=True,
    )

    def __init__(self, api_key: str, model: str = "qwen3.7-plus", base_url: str = QWEN_DEFAULT_BASE_URL, **kwargs) -> None:
        super().__init__(
            api_key, model, base_url, provider_id=self.id, display_name=self.name,
            capabilities=self.capabilities, **kwargs,
        )
