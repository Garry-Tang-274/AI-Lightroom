from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_dir
from PySide6.QtWidgets import QApplication, QMessageBox


def configure_logging() -> Path:
    directory = Path(user_log_dir("AI Lightroom", "AI Lightroom"))
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "ai-lightroom.log"
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.INFO)
        handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    return log_path


def install_exception_hook(log_path: Path) -> None:
    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger("ai_lightroom").critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        if QApplication.instance() is not None:
            QMessageBox.critical(
                None,
                "AI Lightroom 遇到错误",
                f"程序已记录错误详情。\n\n{exc_value}\n\n日志：{log_path}",
            )

    sys.excepthook = handle_exception

