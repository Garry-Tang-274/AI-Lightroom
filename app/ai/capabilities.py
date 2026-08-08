from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    supports_vision: bool = False
    supports_multiple_images: bool = False
    supports_structured_output: bool = False
    supports_text_chat: bool = True
    supports_image_generation: bool = False
    supports_image_editing: bool = False
    supports_streaming: bool = False
    supports_custom_base_url: bool = False


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    id: str
    display_name: str
    default_model: str
    default_base_url: str = ""
    requires_api_key: bool = True
    api_key_environment: str = ""
    capabilities: ProviderCapabilities = ProviderCapabilities()
    is_custom: bool = False


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    provider_id: str
    model: str
    base_url: str = ""
    display_name: str = ""
    capabilities: ProviderCapabilities = ProviderCapabilities()

