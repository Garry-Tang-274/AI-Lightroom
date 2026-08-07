from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import keyring
from dotenv import find_dotenv, load_dotenv
from PySide6.QtCore import QSettings


KEYRING_SERVICE = "AI Lightroom"
KEYRING_ACCOUNT = "gemini_api_key"


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    provider: str = "auto"
    gemini_model: str = "gemini-3.6-flash"
    preview_size: int = 1280
    ai_reinspection: bool = True
    max_vision_calls: int = 2
    export_jpeg_quality: int = 92
    performance_mode: str = "balanced"

    @property
    def worker_threads(self) -> int:
        return {"battery": 1, "balanced": 2, "performance": 4}.get(self.performance_mode, 2)


class SettingsManager:
    def __init__(self) -> None:
        dotenv_path = find_dotenv(usecwd=True)
        if dotenv_path:
            load_dotenv(dotenv_path, override=False)
        self.store = QSettings("AI Lightroom", "AI Lightroom")

    def runtime(self) -> RuntimeSettings:
        model = os.getenv("GEMINI_MODEL") or self.store.value("ai/gemini_model", "gemini-3.6-flash")
        return RuntimeSettings(
            provider=str(self.store.value("ai/provider", "auto")),
            gemini_model=str(model),
            preview_size=_bounded_int(self.store.value("performance/preview_size", 1280), 640, 2048, 1280),
            ai_reinspection=_as_bool(self.store.value("ai/reinspection", True)),
            max_vision_calls=_bounded_int(self.store.value("ai/max_vision_calls", 2), 1, 2, 2),
            export_jpeg_quality=_bounded_int(self.store.value("export/jpeg_quality", 92), 1, 100, 92),
            performance_mode=str(self.store.value("performance/mode", "balanced")),
        )

    def gemini_api_key(self) -> str:
        environment_key = os.getenv("GEMINI_API_KEY", "").strip()
        if environment_key:
            return environment_key
        try:
            return (keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT) or "").strip()
        except keyring.errors.KeyringError:
            return ""

    def save(self, settings: RuntimeSettings, api_key: str) -> None:
        self.store.setValue("ai/provider", settings.provider)
        self.store.setValue("ai/gemini_model", settings.gemini_model)
        self.store.setValue("performance/preview_size", settings.preview_size)
        self.store.setValue("ai/reinspection", settings.ai_reinspection)
        self.store.setValue("ai/max_vision_calls", settings.max_vision_calls)
        self.store.setValue("export/jpeg_quality", settings.export_jpeg_quality)
        self.store.setValue("performance/mode", settings.performance_mode)
        self.store.sync()
        if not os.getenv("GEMINI_API_KEY"):
            try:
                if api_key.strip():
                    keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, api_key.strip())
                else:
                    existing = keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
                    if existing:
                        keyring.delete_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
            except keyring.errors.KeyringError as exc:
                raise RuntimeError("无法写入 Windows 凭据管理器，请改用 .env 配置 API Key。") from exc


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _bounded_int(value, minimum: int, maximum: int, default: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default

