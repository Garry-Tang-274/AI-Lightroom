from __future__ import annotations

from collections.abc import Callable

from app.ai.capabilities import ProviderCapabilities, ProviderConfig, ProviderDescriptor
from app.ai.gemini_provider import GeminiProvider
from app.ai.jarvisart.provider import JarvisArtProvider
from app.ai.mock_provider import MockProvider
from app.ai.openai_compatible_provider import OpenAICompatibleProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.deepseek_provider import DeepSeekProvider
from app.ai.qwen_provider import QWEN_DEFAULT_BASE_URL, QwenProvider
from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT


ProviderFactory = Callable[..., object]


class ProviderRegistry:
    """Single registration point for provider metadata and adapter construction."""

    def __init__(self) -> None:
        self._descriptors: dict[str, ProviderDescriptor] = {}
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, descriptor: ProviderDescriptor, factory: ProviderFactory) -> None:
        self._descriptors[descriptor.id] = descriptor
        self._factories[descriptor.id] = factory

    def descriptors(self) -> tuple[ProviderDescriptor, ...]:
        return tuple(self._descriptors.values())

    def descriptor(self, provider_id: str) -> ProviderDescriptor:
        return self._descriptors.get(provider_id, self._descriptors["mock"])

    def make_config(self, provider_id: str, model: str = "", base_url: str = "", display_name: str = "", *, custom_vision: bool = True, custom_structured_output: bool = True, local_mode: str = "real", custom_organization: str = "", custom_headers: str = "", jarvisart_root: str = "", jarvisart_endpoint: str = "http://127.0.0.1:8765", jarvisart_auto_start: bool = True) -> ProviderConfig:
        descriptor = self.descriptor(provider_id)
        capabilities = descriptor.capabilities
        if descriptor.is_custom:
            capabilities = ProviderCapabilities(
                supports_vision=custom_vision,
                supports_multiple_images=custom_vision,
                supports_structured_output=custom_structured_output,
                supports_text_chat=True,
                supports_streaming=True,
                supports_custom_base_url=True,
            )
        return ProviderConfig(
            provider_id=descriptor.id,
            model=model.strip() or descriptor.default_model,
            base_url=(base_url.strip() or descriptor.default_base_url).rstrip("/"),
            display_name=display_name.strip() or descriptor.display_name,
            capabilities=capabilities,
            local_mode=local_mode if local_mode in {"mock", "real"} else "real",
            custom_organization=custom_organization.strip(),
            custom_headers=custom_headers.strip(),
            jarvisart_root=jarvisart_root.strip(),
            jarvisart_endpoint=jarvisart_endpoint.strip() or "http://127.0.0.1:8765",
            jarvisart_auto_start=jarvisart_auto_start,
        )

    def create(self, config: ProviderConfig, api_key: str, *, system_prompt: str = DEFAULT_SYSTEM_PROMPT, on_request_started=None, on_result=None, client=None):
        descriptor = self.descriptor(config.provider_id)
        if descriptor.requires_api_key and not api_key:
            raise ValueError(f"{descriptor.display_name} API Key 为空")
        if descriptor.capabilities.supports_custom_base_url and not config.base_url and descriptor.requires_api_key:
            raise ValueError(f"{descriptor.display_name} Base URL 为空")
        return self._factories[descriptor.id](
            config, api_key, system_prompt=system_prompt,
            on_request_started=on_request_started, on_result=on_result, client=client,
        )


def _gemini(config, api_key, **kwargs):
    return GeminiProvider(api_key, config.model, **kwargs)


def _openai(config, api_key, **kwargs):
    return OpenAIProvider(api_key, config.model, **kwargs)


def _qwen(config, api_key, **kwargs):
    return QwenProvider(api_key, config.model, config.base_url, **kwargs)


def _compatible(config, api_key, **kwargs):
    return OpenAICompatibleProvider(
        api_key, config.model, config.base_url, provider_id=config.provider_id,
        display_name=config.display_name, capabilities=config.capabilities,
        organization=config.custom_organization, custom_headers=config.custom_headers, **kwargs,
    )


def _mock(config, api_key, **kwargs):
    return MockProvider()


def _jarvisart(config, api_key, **kwargs):
    return JarvisArtProvider(config, **kwargs)


def _deepseek(config, api_key, **kwargs):
    return DeepSeekProvider(api_key, config.model, config.base_url, **kwargs)


VISION_STRUCTURED = ProviderCapabilities(
    supports_vision=True, supports_multiple_images=True,
    supports_structured_output=True, supports_text_chat=True,
    supports_streaming=True,
)

provider_registry = ProviderRegistry()
provider_registry.register(ProviderDescriptor("gemini", "Google Gemini", "gemini-3.6-flash", api_key_environment="GEMINI_API_KEY", capabilities=VISION_STRUCTURED, cost_type="cloud_api", privacy_type="cloud_preview"), _gemini)
provider_registry.register(ProviderDescriptor("openai", "OpenAI（高质量 AI 模式）", "gpt-5.6-terra", api_key_environment="OPENAI_API_KEY", capabilities=VISION_STRUCTURED, cost_type="cloud_api", privacy_type="cloud_preview"), _openai)
provider_registry.register(ProviderDescriptor("qwen", "阿里云百炼 / Qwen", "qwen3.7-plus", QWEN_DEFAULT_BASE_URL, api_key_environment="DASHSCOPE_API_KEY", capabilities=ProviderCapabilities(supports_vision=True, supports_multiple_images=True, supports_structured_output=True, supports_text_chat=True, supports_streaming=True, supports_custom_base_url=True), cost_type="cloud_api", privacy_type="cloud_preview"), _qwen)
provider_registry.register(ProviderDescriptor("deepseek", "DeepSeek（文本增量调整）", "deepseek-chat", "https://api.deepseek.com/v1", api_key_environment="DEEPSEEK_API_KEY", capabilities=ProviderCapabilities(supports_structured_output=True, supports_text_chat=True, supports_streaming=True, supports_custom_base_url=True), cost_type="cloud_api", privacy_type="text_state_only"), _deepseek)
provider_registry.register(ProviderDescriptor("custom", "Custom / OpenAI-compatible API", "", "", api_key_environment="AI_LIGHTROOM_CUSTOM_API_KEY", capabilities=ProviderCapabilities(supports_vision=True, supports_multiple_images=True, supports_structured_output=True, supports_text_chat=True, supports_streaming=True, supports_custom_base_url=True), is_custom=True, cost_type="user_configured", privacy_type="user_configured"), _compatible)
provider_registry.register(ProviderDescriptor("mock", "Offline Mock（仅开发测试）", "offline", requires_api_key=False, capabilities=ProviderCapabilities(supports_vision=True, supports_structured_output=True, supports_text_chat=True), cost_type="free", privacy_type="local"), _mock)
provider_registry.register(ProviderDescriptor("jarvisart_local", "JarvisArt Local GGUF", "qwen2_vl", requires_api_key=False, capabilities=ProviderCapabilities(supports_vision=True, supports_structured_output=True, supports_text_chat=True), cost_type="free", privacy_type="local"), _jarvisart)
