from __future__ import annotations

import os
import argparse
import sys
from pathlib import Path

# Support both ``python -m app.main`` and the documented
# ``python app/main.py`` source-entry command. PyInstaller supplies its own
# import path, so this only affects direct source execution.
if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import APP_STYLESHEET
from app.utils.logging_setup import configure_logging, install_exception_hook
from app.utils.paths import resource_path


from app import __version__


def package_self_check() -> int:
    """Cheap executable-level contract check used by the release build."""
    from app.ai.schemas import LocalAdjustmentValues
    from app.core.editor_state import LocalAdjustments

    return 0 if set(LocalAdjustments.model_fields) == set(LocalAdjustmentValues.model_fields) else 2


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
    parser = argparse.ArgumentParser(description="AI Lightroom photo editor")
    parser.add_argument("photo", nargs="?", help="JPG or PNG to open")
    parser.add_argument("--package-self-check", action="store_true")
    parser.add_argument("--smoke-test", nargs="?", const="ai-lightroom-smoke.png")
    args = parser.parse_args()
    if args.package_self_check:
        return package_self_check()
    log_path = configure_logging()
    app = create_application()
    install_exception_hook(log_path)
    window = MainWindow()
    if args.smoke_test:
        # Capture the actual Windows rendering without displaying a window or
        # taking focus from another application during background validation.
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    if args.photo:
        QTimer.singleShot(0, lambda: window.open_image_async(args.photo))
    if args.smoke_test:
        screenshot = args.smoke_test

        def finish_smoke_test() -> None:
            if window._loading or window._render_in_flight:
                QTimer.singleShot(100, finish_smoke_test)
                return
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
