from __future__ import annotations

import builtins
import runpy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ENTRY = Path(__file__).parents[1] / "build_tools" / "frozen_entry.py"


@pytest.mark.parametrize("flag", ["--package-self-check", "--smoke-test"])
def test_import_failure_in_unattended_package_check_exits_and_logs(tmp_path, monkeypatch, flag):
    original_import = builtins.__import__

    def broken_import(name, *args, **kwargs):
        if name == "app.main":
            raise ImportError("QtCore DLL procedure missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)
    monkeypatch.setattr(sys, "argv", ["AI Lightroom.exe", flag])
    log = tmp_path / "startup.log"
    monkeypatch.setenv("AI_LIGHTROOM_STARTUP_LOG", str(log))
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(ENTRY), run_name="__main__")
    assert exit_info.value.code == 1
    assert "QtCore DLL procedure missing" in log.read_text(encoding="utf-8")


def test_frozen_entry_preserves_application_exit_status(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.main", SimpleNamespace(main=lambda: 2))
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(ENTRY), run_name="__main__")
    assert exit_info.value.code == 2
