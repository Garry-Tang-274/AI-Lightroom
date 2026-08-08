from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import APP_STYLESHEET
from app.utils.logging_setup import configure_logging, install_exception_hook
from app.utils.paths import resource_path


def create_application(argv: list[str] | None = None) -> QApplication:
    QApplication.setOrganizationName("AI Lightroom")
    QApplication.setApplicationName("AI Lightroom")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv if argv is not None else sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    icon_path = resource_path("assets/app.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(APP_STYLESHEET)
    return app


def main() -> int:
    log_path = configure_logging()
    app = create_application()
    install_exception_hook(log_path)
    window = MainWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        index = sys.argv.index("--smoke-test")
        screenshot = sys.argv[index + 1] if index + 1 < len(sys.argv) else "ai-lightroom-smoke.png"

        def finish_smoke_test() -> None:
            try:
                # Exercise the active provider credential backend without exposing a key.
                window.settings_manager.provider_api_key(window.runtime_settings.provider)
                success = window.grab().save(screenshot)
            except Exception:
                success = False
            app.exit(0 if success else 2)

        QTimer.singleShot(800, finish_smoke_test)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
