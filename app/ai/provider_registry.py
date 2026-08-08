from __future__ import annotations

from collections.abc import Callable

from app.ai.capabilities import ProviderCapabilities, ProviderConfig, ProviderDescriptor
from app.ai.gemini_provider import GeminiProvider
from app.ai.jarvisart.provider import JarvisArtProvider
from app.ai.mock_provider import MockProvider
from app.ai.openai_compatible_provider import OpenAICompatibleProvider
from app.ai.openai_provider import OpenAIProvider
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

    def make_config(self, provider_id: str, model: str = "", base_url: str = "", display_name: str = "", *, custom_vision: bool = True, custom_structured_output: bool = True, local_mode: str = "mock") -> ProviderConfig:
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
            local_mode=local_mode if local_mode in {"mock", "real"} else "mock",
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
        display_name=config.display_name, capabilities=config.capabilities, **kwargs,
    )


def _mock(config, api_key, **kwargs):
    return MockProvider()


def _jarvisart(config, api_key, **kwargs):
    return JarvisArtProvider(config, **kwargs)


VISION_STRUCTURED = ProviderCapabilities(
    supports_vision=True, supports_multiple_images=True,
    supports_structured_output=True, supports_text_chat=True,
    supports_streaming=True,
)

provider_registry = ProviderRegistry()
provider_registry.register(ProviderDescriptor("gemini", "Google Gemini", "gemini-3.6-flash", api_key_environment="GEMINI_API_KEY", capabilities=VISION_STRUCTURED), _gemini)
provider_registry.register(ProviderDescriptor("openai", "OpenAI（高质量 AI 模式）", "gpt-5.6-terra", api_key_environment="OPENAI_API_KEY", capabilities=VISION_STRUCTURED), _openai)
provider_registry.register(ProviderDescriptor("qwen", "阿里云百炼 / Qwen", "qwen3.7-plus", QWEN_DEFAULT_BASE_URL, api_key_environment="DASHSCOPE_API_KEY", capabilities=ProviderCapabilities(supports_vision=True, supports_multiple_images=True, supports_structured_output=True, supports_text_chat=True, supports_streaming=True, supports_custom_base_url=True)), _qwen)
provider_registry.register(ProviderDescriptor("custom", "Custom / OpenAI-compatible API", "", "", api_key_environment="AI_LIGHTROOM_CUSTOM_API_KEY", capabilities=ProviderCapabilities(supports_vision=True, supports_multiple_images=True, supports_structured_output=True, supports_text_chat=True, supports_streaming=True, supports_custom_base_url=True), is_custom=True), _compatible)
provider_registry.register(ProviderDescriptor("mock", "离线 Mock", "offline", requires_api_key=False, capabilities=ProviderCapabilities(supports_vision=True, supports_structured_output=True, supports_text_chat=True)), _mock)
provider_registry.register(ProviderDescriptor("jarvisart_local", "JarvisArt Local", "JarvisArt-1208", requires_api_key=False, capabilities=ProviderCapabilities(supports_vision=True, supports_structured_output=True, supports_text_chat=True)), _jarvisart)
