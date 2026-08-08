from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from PySide6.QtCore import QSettings

from app.utils.secure_store import WindowsCredentialStore
from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT


GEMINI_CREDENTIAL_TARGET = "AI Lightroom/Gemini API Key"
OPENAI_CREDENTIAL_TARGET = "AI Lightroom/OpenAI API Key"


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    provider: str = "gemini"
    gemini_model: str = "gemini-3.6-flash"
    openai_model: str = "gpt-5.6-terra"
    preview_size: int = 1280
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
        return self.openai_model if self.provider == "openai" else self.gemini_model


class SettingsManager:
    def __init__(self) -> None:
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=False)
        self.store = QSettings("AI Lightroom", "AI Lightroom")
        self.gemini_credentials = WindowsCredentialStore(GEMINI_CREDENTIAL_TARGET) if os.name == "nt" else None
        self.openai_credentials = WindowsCredentialStore(OPENAI_CREDENTIAL_TARGET) if os.name == "nt" else None

    def runtime(self) -> RuntimeSettings:
        gemini_model = os.getenv("GEMINI_MODEL") or self.store.value("ai/gemini_model", "gemini-3.6-flash")
        openai_model = os.getenv("OPENAI_MODEL") or self.store.value("ai/openai_model", "gpt-5.6-terra")
        provider = str(self.store.value("ai/provider", "gemini"))
        # Preserve existing installations that stored the former automatic mode.
        if provider == "auto":
            provider = "gemini"
        return RuntimeSettings(
            provider=provider,
            gemini_model=str(gemini_model),
            openai_model=str(openai_model),
            preview_size=_bounded_int(self.store.value("performance/preview_size", 1280), 640, 2048, 1280),
            ai_reinspection=_as_bool(self.store.value("ai/reinspection", False)),
            max_vision_calls=_bounded_int(self.store.value("ai/max_vision_calls", 2), 1, 2, 2),
            system_prompt=str(self.store.value("ai/system_prompt", DEFAULT_SYSTEM_PROMPT) or DEFAULT_SYSTEM_PROMPT),
            export_jpeg_quality=_bounded_int(self.store.value("export/jpeg_quality", 92), 1, 100, 92),
            performance_mode=str(self.store.value("performance/mode", "balanced")),
        )

    def gemini_api_key(self) -> str:
        environment_key = os.getenv("GEMINI_API_KEY", "").strip()
        if environment_key:
            return environment_key
        if self.gemini_credentials is None:
            return ""
        try:
            return self.gemini_credentials.get().strip()
        except OSError:
            return ""

    def openai_api_key(self) -> str:
        environment_key = os.getenv("OPENAI_API_KEY", "").strip()
        if environment_key:
            return environment_key
        if self.openai_credentials is None:
            return ""
        try:
            return self.openai_credentials.get().strip()
        except OSError:
            return ""

    def save(self, settings: RuntimeSettings, gemini_api_key: str, openai_api_key: str) -> None:
        self.store.setValue("ai/provider", settings.provider)
        self.store.setValue("ai/gemini_model", settings.gemini_model)
        self.store.setValue("ai/openai_model", settings.openai_model)
        self.store.setValue("performance/preview_size", settings.preview_size)
        self.store.setValue("ai/reinspection", settings.ai_reinspection)
        self.store.setValue("ai/max_vision_calls", settings.max_vision_calls)
        self.store.setValue("ai/system_prompt", settings.system_prompt)
        self.store.setValue("export/jpeg_quality", settings.export_jpeg_quality)
        self.store.setValue("performance/mode", settings.performance_mode)
        self.store.sync()
        if not os.getenv("GEMINI_API_KEY"):
            try:
                if gemini_api_key.strip():
                    self.gemini_credentials.set(gemini_api_key.strip())
                elif self.gemini_credentials:
                    self.gemini_credentials.delete()
            except OSError as exc:
                raise RuntimeError("无法写入 Gemini API Key 到 Windows 凭据管理器，请改用 .env 配置。") from exc
        if not os.getenv("OPENAI_API_KEY"):
            try:
                if openai_api_key.strip():
                    self.openai_credentials.set(openai_api_key.strip())
                elif self.openai_credentials:
                    self.openai_credentials.delete()
            except OSError as exc:
                raise RuntimeError("无法写入 OpenAI API Key 到 Windows 凭据管理器，请改用 .env 配置。") from exc


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _bounded_int(value, minimum: int, maximum: int, default: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default
