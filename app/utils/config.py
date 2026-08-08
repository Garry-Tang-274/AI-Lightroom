from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv
from PySide6.QtCore import QSettings

from app.ai.provider_registry import provider_registry
from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT
from app.utils.secure_store import WindowsCredentialStore


GEMINI_CREDENTIAL_TARGET = "AI Lightroom/Gemini API Key"
OPENAI_CREDENTIAL_TARGET = "AI Lightroom/OpenAI API Key"


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    # Generic active-provider fields. The legacy model keys are migrated on read.
    provider: str = "gemini"
    model: str = ""
    base_url: str = ""
    custom_provider_name: str = ""
    custom_supports_vision: bool = True
    custom_supports_structured_output: bool = True
    custom_organization: str = ""
    custom_headers: str = ""
    # Real mode is the user-supplied local GGUF/native runtime. The
    # fixture-backed Mock mode is deliberately opt-in and clearly labelled in
    # the UI because it cannot inspect a user's photograph.
    jarvisart_mode: str = "real"
    jarvisart_root: str = ""
    jarvisart_endpoint: str = "http://127.0.0.1:8765"
    jarvisart_auto_start: bool = True
    # ``preview_size`` remains the low-resolution maximum edge for backward
    # compatibility with 1.0.1 settings.  High quality is intentionally kept
    # separate so a cloud provider can remain economical by default.
    preview_size: int = 1536
    high_preview_size: int = 3072
    preview_quality: str = "auto"  # auto, low, high
    ai_preview_quality: str = "follow_preview"  # follow_preview, low, high
    ai_reinspection: bool = False
    max_vision_calls: int = 2
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    export_jpeg_quality: int = 92
    performance_mode: str = "balanced"

    @property
    def worker_threads(self) -> int:
        return {"battery": 1, "balanced": 2, "performance": 4}.get(self.performance_mode, 2)

    @property
    def active_model(self) -> str:
        return self.model or provider_registry.descriptor(self.provider).default_model

    @property
    def effective_preview_quality(self) -> str:
        """Resolve the visible working-preview quality without guessing cost."""
        if self.preview_quality in {"low", "high"}:
            return self.preview_quality
        # The user-supplied local JarvisArt GGUF runtime has no per-request
        # cloud cost, so the useful default is a larger analysis and working
        # preview. All cloud APIs stay on the economical low setting until the
        # user opts in.
        if self.provider == "jarvisart_local" and self.jarvisart_mode == "real":
            return "high"
        return "low"

    @property
    def active_preview_size(self) -> int:
        return self.high_preview_size if self.effective_preview_quality == "high" else self.preview_size

    @property
    def effective_ai_preview_quality(self) -> str:
        if self.ai_preview_quality in {"low", "high"}:
            return self.ai_preview_quality
        return self.effective_preview_quality

    @property
    def active_ai_preview_size(self) -> int:
        return self.high_preview_size if self.effective_ai_preview_quality == "high" else self.preview_size

    @property
    def provider_config(self):
        return provider_registry.make_config(
            self.provider, self.active_model, self.base_url, self.custom_provider_name,
            custom_vision=self.custom_supports_vision,
            custom_structured_output=self.custom_supports_structured_output,
            local_mode=self.jarvisart_mode,
            custom_organization=self.custom_organization,
            custom_headers=self.custom_headers,
            jarvisart_root=self.jarvisart_root,
            jarvisart_endpoint=self.jarvisart_endpoint,
            jarvisart_auto_start=self.jarvisart_auto_start,
        )


class SettingsManager:
    def __init__(self) -> None:
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=False)
        self.store = QSettings("AI Lightroom", "AI Lightroom")
        self._credentials: dict[str, WindowsCredentialStore] = {}

    def runtime(self) -> RuntimeSettings:
        provider = str(self.store.value("ai/active_provider", self.store.value("ai/provider", "gemini")))
        if provider == "auto":
            provider = "gemini"
        descriptor = provider_registry.descriptor(provider)
        legacy_model = self.store.value(f"ai/{provider}_model", "") if provider in {"gemini", "openai"} else ""
        model_env_name = {"gemini": "GEMINI_MODEL", "openai": "OPENAI_MODEL", "qwen": "QWEN_MODEL", "deepseek": "DEEPSEEK_MODEL", "custom": "AI_LIGHTROOM_CUSTOM_MODEL"}.get(provider)
        base_url_env_name = {"qwen": "QWEN_BASE_URL", "deepseek": "DEEPSEEK_BASE_URL", "custom": "AI_LIGHTROOM_CUSTOM_BASE_URL"}.get(provider)
        environment_model = os.getenv(model_env_name, "") if model_env_name else ""
        environment_base_url = os.getenv(base_url_env_name, "") if base_url_env_name else ""
        model = str(environment_model or self.store.value("ai/provider_model", legacy_model or descriptor.default_model))
        base_url = str(environment_base_url or self.store.value("ai/provider_base_url", descriptor.default_base_url))
        return RuntimeSettings(
            provider=descriptor.id,
            model=model,
            base_url=base_url,
            custom_provider_name=str(self.store.value("ai/custom_provider_name", "")),
            custom_supports_vision=_as_bool(self.store.value("ai/custom_supports_vision", True)),
            custom_supports_structured_output=_as_bool(self.store.value("ai/custom_supports_structured_output", True)),
            custom_organization=str(self.store.value("ai/custom_organization", "")),
            custom_headers=str(self.store.value("ai/custom_headers", "")),
            jarvisart_mode=_choice(self.store.value("ai/jarvisart_mode", "real"), {"mock", "real"}, "real"),
            jarvisart_root=str(self.store.value("ai/jarvisart_root", "")),
            jarvisart_endpoint=str(self.store.value("ai/jarvisart_endpoint", "http://127.0.0.1:8765")),
            jarvisart_auto_start=_as_bool(self.store.value("ai/jarvisart_auto_start", True)),
            preview_size=_bounded_int(self.store.value("performance/preview_size", 1536), 640, 2048, 1536),
            high_preview_size=_bounded_int(self.store.value("performance/high_preview_size", 3072), 2048, 4096, 3072),
            preview_quality=_choice(self.store.value("performance/preview_quality", "auto"), {"auto", "low", "high"}, "auto"),
            ai_preview_quality=_choice(self.store.value("ai/preview_quality", "follow_preview"), {"follow_preview", "low", "high"}, "follow_preview"),
            ai_reinspection=_as_bool(self.store.value("ai/reinspection", False)),
            max_vision_calls=_bounded_int(self.store.value("ai/max_vision_calls", 2), 1, 2, 2),
            system_prompt=str(self.store.value("ai/system_prompt", DEFAULT_SYSTEM_PROMPT) or DEFAULT_SYSTEM_PROMPT),
            export_jpeg_quality=_bounded_int(self.store.value("export/jpeg_quality", 92), 1, 100, 92),
            performance_mode=str(self.store.value("performance/mode", "balanced")),
        )

    def provider_api_key(self, provider_id: str) -> str:
        descriptor = provider_registry.descriptor(provider_id)
        if not descriptor.requires_api_key:
            return ""
        if descriptor.api_key_environment:
            environment_key = os.getenv(descriptor.api_key_environment, "").strip()
            if environment_key:
                return environment_key
        try:
            return self._credential_store(descriptor.id).get().strip()
        except OSError:
            return ""

    def has_provider_key(self, provider_id: str) -> bool:
        return bool(self.provider_api_key(provider_id))

    # Compatibility accessors retain existing installations and old tests.
    def gemini_api_key(self) -> str:
        return self.provider_api_key("gemini")

    def openai_api_key(self) -> str:
        return self.provider_api_key("openai")

    def save(self, settings: RuntimeSettings, api_key: str) -> None:
        self.store.setValue("ai/active_provider", settings.provider)
        self.store.setValue("ai/provider", settings.provider)  # legacy readers
        self.store.setValue("ai/provider_model", settings.active_model)
        self.store.setValue("ai/provider_base_url", settings.base_url)
        self.store.setValue("ai/custom_provider_name", settings.custom_provider_name)
        self.store.setValue("ai/custom_supports_vision", settings.custom_supports_vision)
        self.store.setValue("ai/custom_supports_structured_output", settings.custom_supports_structured_output)
        self.store.setValue("ai/custom_organization", settings.custom_organization)
        self.store.setValue("ai/custom_headers", settings.custom_headers)
        self.store.setValue("ai/jarvisart_mode", settings.jarvisart_mode)
        self.store.setValue("ai/jarvisart_root", settings.jarvisart_root)
        self.store.setValue("ai/jarvisart_endpoint", settings.jarvisart_endpoint)
        self.store.setValue("ai/jarvisart_auto_start", settings.jarvisart_auto_start)
        self.store.setValue("performance/preview_size", settings.preview_size)
        self.store.setValue("performance/high_preview_size", settings.high_preview_size)
        self.store.setValue("performance/preview_quality", settings.preview_quality)
        self.store.setValue("ai/preview_quality", settings.ai_preview_quality)
        self.store.setValue("ai/reinspection", settings.ai_reinspection)
        self.store.setValue("ai/max_vision_calls", settings.max_vision_calls)
        self.store.setValue("ai/system_prompt", settings.system_prompt)
        self.store.setValue("export/jpeg_quality", settings.export_jpeg_quality)
        self.store.setValue("performance/mode", settings.performance_mode)
        self.store.sync()
        descriptor = provider_registry.descriptor(settings.provider)
        if descriptor.requires_api_key and not os.getenv(descriptor.api_key_environment):
            try:
                store = self._credential_store(descriptor.id)
                if api_key.strip():
                    store.set(api_key.strip())
                else:
                    store.delete()
            except OSError as exc:
                raise RuntimeError("无法写入 API Key 到系统凭据管理器，请改用 .env 配置。") from exc

    def _credential_store(self, provider_id: str) -> WindowsCredentialStore:
        if provider_id not in self._credentials:
            target = {
                "gemini": GEMINI_CREDENTIAL_TARGET,
                "openai": OPENAI_CREDENTIAL_TARGET,
            }.get(provider_id, f"AI Lightroom/Provider/{provider_id} API Key")
            self._credentials[provider_id] = WindowsCredentialStore(target)
        return self._credentials[provider_id]


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _bounded_int(value, minimum: int, maximum: int, default: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default


def _choice(value, allowed: set[str], default: str) -> str:
    text = str(value).strip().lower()
    return text if text in allowed else default
