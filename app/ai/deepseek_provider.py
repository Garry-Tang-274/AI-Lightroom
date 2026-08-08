from __future__ import annotations

from app.ai.capabilities import ProviderCapabilities
from app.ai.openai_compatible_provider import OpenAICompatibleProvider


DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


class DeepSeekProvider(OpenAICompatibleProvider):
    """Text/state provider only until a selected DeepSeek model exposes vision."""

    id = "deepseek"
    name = "DeepSeek"
    capabilities = ProviderCapabilities(
        supports_vision=False, supports_structured_output=True,
        supports_text_chat=True, supports_streaming=True, supports_custom_base_url=True,
    )

    def __init__(self, api_key: str, model: str = "deepseek-chat", base_url: str = DEEPSEEK_DEFAULT_BASE_URL, **kwargs) -> None:
        super().__init__(api_key, model, base_url, provider_id=self.id, display_name=self.name, capabilities=self.capabilities, **kwargs)
