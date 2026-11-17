"""Frozen entry point: surface startup failures without hanging release checks."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import traceback


def launch() -> int:
    try:
        from app.main import main

        return main()
    except Exception:
        # Qt itself may be unavailable. Keep this handler standard-library-only
        # and never open an error dialog during unattended package validation.
        log_path = Path(os.environ.get("AI_LIGHTROOM_STARTUP_LOG") or (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) /
            "AI Lightroom" / "logs" / "startup-error.log"
        ))
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            if sys.stderr is not None:
                traceback.print_exc()
        unattended = any(arg == "--package-self-check" or arg.startswith("--smoke-test") for arg in sys.argv)
        if not unattended and sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                f"AI Lightroom 无法启动。请重新安装完整版本。\n\n诊断日志：\n{log_path}",
                "AI Lightroom — 启动失败", 0x10,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(launch())
