from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from app.ai.orchestrator import AIOrchestrator
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import EditingPlan
from app.core.editor_state import EditorState
from app.ui.main_window import MainWindow
from app.utils.config import RuntimeSettings


class CapturingVisionProvider(AIProvider):
    name = "Capture Vision"
    requires_visual_input = True

    def __init__(self) -> None:
        self.preview_jpeg: bytes | None = None

    def plan(self, request: PlanningRequest) -> EditingPlan:
        self.preview_jpeg = request.preview_jpeg
        return EditingPlan(
            summary="No-op",
            reasoning_summary="Test only.",
            confidence=1.0,
        )


def test_auto_quality_defaults_high_only_for_real_local_jarvisart():
    cloud = RuntimeSettings(provider="qwen", preview_quality="auto", ai_preview_quality="follow_preview")
    local = RuntimeSettings(provider="jarvisart_local", jarvisart_mode="real", preview_quality="auto", ai_preview_quality="follow_preview")
    mock = RuntimeSettings(provider="jarvisart_local", jarvisart_mode="mock", preview_quality="auto", ai_preview_quality="follow_preview")

    assert (cloud.effective_preview_quality, cloud.active_preview_size) == ("low", 1536)
    assert (local.effective_preview_quality, local.active_preview_size) == ("high", 3072)
    assert local.active_ai_preview_size == 3072
    assert (mock.effective_preview_quality, mock.active_preview_size) == ("low", 1536)


def test_explicit_ai_quality_can_differ_from_working_preview():
    settings = RuntimeSettings(
        provider="qwen", preview_quality="low", ai_preview_quality="high",
        preview_size=1024, high_preview_size=3072,
    )
    assert settings.active_preview_size == 1024
    assert settings.active_ai_preview_size == 3072


def test_high_quality_visual_request_encodes_a_high_resolution_jpeg_preview():
    provider = CapturingVisionProvider()
    pixels = np.zeros((2200, 3600, 3), dtype=np.uint8)
    pixels[:, :, 0] = 80
    AIOrchestrator(provider, preview_size=3072, reinspection_enabled=False).process(
        "Inspect the photo", pixels, EditorState(), []
    )
    assert provider.preview_jpeg is not None
    with Image.open(BytesIO(provider.preview_jpeg)) as encoded:
        assert max(encoded.size) == 3072


def test_rebuilding_visible_preview_changes_only_the_working_copy(qtbot, tmp_path):
    source = tmp_path / "large.jpg"
    pixels = np.full((1200, 2200, 3), 90, dtype=np.uint8)
    Image.fromarray(pixels).save(source)
    window = MainWindow()
    qtbot.addWidget(window)
    window.runtime_settings = RuntimeSettings(preview_quality="low", preview_size=800, high_preview_size=1600)
    window.open_image(str(source))
    assert max(window.preview_source.shape[:2]) == 800
    original = window.loaded_image.pixels.copy()

    window.runtime_settings = RuntimeSettings(preview_quality="high", preview_size=800, high_preview_size=1600)
    window._rebuild_visible_preview_source()

    assert max(window.preview_source.shape[:2]) == 1600
    assert np.array_equal(window.loaded_image.pixels, original)


def test_jarvisart_mock_mode_is_blocked_before_a_worker_can_start(qtbot, tmp_path, monkeypatch):
    source = tmp_path / "mock.jpg"
    Image.new("RGB", (240, 160), (80, 100, 120)).save(source)
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_image(str(source))
    monkeypatch.setattr(window.settings_manager, "runtime", lambda: RuntimeSettings(provider="jarvisart_local", jarvisart_mode="mock"))
    called: list[bool] = []
    monkeypatch.setattr(window, "_show_jarvisart_mock_notice", lambda: called.append(True))

    window._run_ai_edit("make this cooler")

    assert called == [True]
    assert window._ai_worker is None
    assert window.state.is_pristine()
