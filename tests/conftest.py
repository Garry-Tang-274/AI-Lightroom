"""Tests must not write a developer's photo sessions, provider settings or vault."""
from __future__ import annotations

import pytest
import sys
import PySide6.QtCore as QtCore
from PySide6.QtCore import QSettings
from app.utils.config import SettingsManager


@pytest.fixture(autouse=True)
def isolated_app_settings(tmp_path, monkeypatch):
    previous = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "user"))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(tmp_path / "system"))
    secrets = {}

    class IsolatedQSettings(QSettings):
        def __init__(self, *args, **kwargs):
            if not args or args[:2] == ("AI Lightroom", "AI Lightroom"):
                super().__init__(str(tmp_path / "application.ini"), QSettings.Format.IniFormat)
            else:
                super().__init__(*args, **kwargs)

    # The explicit organization/application constructor always uses Windows
    # native settings; setDefaultFormat alone does NOT isolate that overload.
    monkeypatch.setattr(QtCore, "QSettings", IsolatedQSettings)
    for name, module in tuple(sys.modules.items()):
        if name.startswith("app.") and getattr(module, "QSettings", None) is QSettings:
            monkeypatch.setattr(module, "QSettings", IsolatedQSettings)

    class TestCredential:
        def __init__(self, provider):
            self.provider = provider

        def get(self):
            return secrets.get(self.provider, "")

        def set(self, value):
            secrets[self.provider] = value

        def delete(self):
            secrets.pop(self.provider, None)

    monkeypatch.setattr(SettingsManager, "_credential_store", lambda self, provider: TestCredential(provider))
    yield
    QSettings.setDefaultFormat(previous)
