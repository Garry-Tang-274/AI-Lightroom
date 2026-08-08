from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.ai.capabilities import ProviderCapabilities
from app.ai.errors import AIRequestError
from app.ai.executor import apply_editing_plan
from app.ai.jarvisart.adapter import JarvisArtAdapter
from app.ai.jarvisart.provider import JarvisArtProvider
from app.ai.jarvisart.runtime import RealJarvisArtRuntimeStub
from app.ai.jarvisart.runtime import LocalJarvisArtRuntime, parse_jarvisart_lua
from app.ai.jarvisart.service import JarvisArtServiceManager
from app.ai.jarvisart.schemas import JarvisArtNativePlan
from app.ai.provider import PlanningRequest
from app.ai.provider_registry import provider_registry
from app.ai.orchestrator import AIOrchestrator
from app.core.editor_state import EditorState, HSLColor
from app.core.history import HistoryManager
from app.core.image_processor import render_image


FIXTURES = Path(__file__).parent / "fixtures" / "jarvisart_native_output"


def native_fixture(name: str) -> JarvisArtNativePlan:
    return JarvisArtNativePlan.model_validate(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def test_global_fixture_adapts_to_only_supported_editing_plan_tools():
    result = JarvisArtAdapter().adapt(native_fixture("global.json"))
    assert [(item.tool, item.value) for item in result.plan.global_adjustments] == [
        ("set_exposure", -0.35), ("set_contrast", 14.0), ("set_highlights", -18.0), ("set_vibrance", -6.0),
    ]
    assert not result.unsupported_operations


def test_hsl_and_native_255_curves_are_normalized():
    plan = JarvisArtAdapter().adapt(native_fixture("hsl_curves.json")).plan
    assert plan.hsl_adjustments[0].color is HSLColor.BLUE
    assert plan.curve_adjustments[0].points[1].x == pytest.approx(64 / 255)
    assert plan.curve_adjustments[1].tool == "set_blue_curve"


def test_local_regions_map_to_real_masks_and_only_affect_their_layers():
    plan = JarvisArtAdapter().adapt(native_fixture("road_vehicle_sky.json")).plan
    result = apply_editing_plan(EditorState(), plan)
    masks = {mask.name: mask for mask in result.state.masks}
    assert set(masks) == {"Sky", "Road", "Vehicle"}
    assert masks["Sky"].adjustments.exposure == -0.3
    assert masks["Road"].adjustments.clarity == 13
    assert masks["Vehicle"].adjustments.whites == 8
    assert result.state.basic.exposure == 0


def test_unsupported_native_operations_are_never_silently_dropped():
    result = JarvisArtAdapter().adapt(native_fixture("unsupported.json"))
    assert [(item.tool, item.value) for item in result.plan.global_adjustments] == [("set_exposure", -0.2)]
    assert any("LensBlur" in message for message in result.unsupported_operations)
    assert any("CameraCalibration" in message for message in result.unsupported_operations)
    assert any("Temperature" in message for message in result.unsupported_operations)


def test_native_fixture_rejects_unknown_fields_instead_of_guessing():
    payload = native_fixture("global.json").model_dump()
    payload["invented_lightroom_control"] = 1
    with pytest.raises(Exception, match="Extra inputs are not permitted"):
        JarvisArtNativePlan.model_validate(payload)


def test_invalid_mock_native_output_has_a_specific_local_error_category():
    class BrokenRuntime:
        @property
        def status(self):
            return type("Status", (), {"state": "Mock Native Ready"})()

        def infer(self, preview_jpeg, instruction, state):
            return JarvisArtNativePlan.model_validate({"bad": True})

    provider = JarvisArtProvider(provider_registry.make_config("jarvisart_local"), runtime=BrokenRuntime())
    with pytest.raises(AIRequestError) as raised:
        provider.plan(PlanningRequest("test", EditorState(), None, []))
    assert raised.value.category == "JarvisArt fixture parse failed"
    assert not raised.value.request_sent


def test_mock_runtime_drives_adapter_renderer_without_network_or_budget_callbacks():
    started: list[bool] = []
    config = provider_registry.make_config("jarvisart_local", local_mode="mock")
    provider = JarvisArtProvider(config, on_request_started=lambda: started.append(True))
    plan = provider.plan(PlanningRequest("荒漠公路冷峻", EditorState(), b"local preview", []))
    state = apply_editing_plan(EditorState(), plan).state
    pixels = np.full((32, 48, 3), 150, dtype=np.uint8)
    assert not np.array_equal(render_image(pixels, state), pixels)
    assert not started


def test_mock_provider_pipeline_returns_local_status_and_never_uses_cloud_budget():
    provider = JarvisArtProvider(provider_registry.make_config("jarvisart_local", local_mode="mock"))
    pixels = np.zeros((96, 160, 3), dtype=np.uint8)
    pixels[:45] = (90, 160, 220)
    pixels[45:] = (112, 99, 73)
    result = AIOrchestrator(provider, reinspection_enabled=False).process("荒漠公路", pixels, EditorState(), [])
    assert result.provider_name.endswith("Mock Native Ready")
    assert result.vision_calls == 1
    assert result.state.basic.contrast == 10
    assert not result.unsupported_operations


def test_real_runtime_stub_reports_not_installed_without_cloud_fallback():
    config = provider_registry.make_config("jarvisart_local", local_mode="real")
    provider = JarvisArtProvider(config, runtime=RealJarvisArtRuntimeStub())
    assert provider.runtime_status.state == "Real Model Not Installed"
    with pytest.raises(AIRequestError, match="官方 JarvisArt") as raised:
        provider.plan(PlanningRequest("test", EditorState(), None, []))
    assert not raised.value.request_sent


def test_registry_exposes_local_provider_without_api_key_and_atomic_history_is_one_step():
    descriptor = provider_registry.descriptor("jarvisart_local")
    assert not descriptor.requires_api_key and descriptor.capabilities.supports_vision
    state = EditorState()
    history = HistoryManager()
    history.reset(state)
    plan = JarvisArtAdapter().adapt(native_fixture("road_vehicle_sky.json")).plan
    state = apply_editing_plan(state, plan).state
    history.push(state, "AI：JarvisArt transaction")
    assert len(history.entries) == 2
    restored = history.undo()
    assert restored is not None and restored.is_pristine()


def test_real_jarvisart_lua_is_parsed_into_supported_parameters_and_visible_unsupported_operations():
    plan = parse_jarvisart_lua('return { Exposure2012 = -0.35, Contrast2012 = 12, HueAdjustmentBlue = -5, LensBlur = 10 }')
    result = JarvisArtAdapter().adapt(plan)
    assert [(item.tool, item.value) for item in result.plan.global_adjustments] == [("set_exposure", -0.35), ("set_contrast", 12.0)]
    assert result.plan.hsl_adjustments[0].color == HSLColor.BLUE
    assert any("LensBlur" in item for item in result.unsupported_operations)


def test_local_service_status_reports_ready_from_a_health_response(tmp_path):
    root = tmp_path / "JarvisArt"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "launch_services.ps1").write_text("# launcher", encoding="utf-8")

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"status":"ok","model_status":"online","model":"qwen2_vl"}'

    manager = JarvisArtServiceManager(str(root), opener=lambda request, timeout: Response())
    status = manager.status()
    assert status.state == "Ready"
    assert status.model == "qwen2_vl"
