from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError
from PySide6.QtCore import QSettings

from app.ai.errors import AIRequestError, error_from_exception
from app.ai.executor import apply_editing_plan
from app.ai.gemini_provider import GeminiProvider
from app.ai.jarvisart.adapter import JarvisArtAdapter
from app.ai.jarvisart.runtime import parse_jarvisart_lua
from app.ai.jarvisart.service import JarvisArtServiceManager, JarvisArtServiceStatus
from app.ai.openai_provider import OpenAIProvider
from app.ai.openai_compatible_provider import OpenAICompatibleProvider
from app.ai.orchestrator import AIOrchestrator
from app.ai.prompt_builder import build_prompt
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.provider_registry import provider_registry
from app.ai.schemas import EditingPlan, GlobalAdjustment, GLOBAL_ADJUSTMENT_RANGES
from app.ai.usage import AIUsageManager, CloudRequestTracker
from app.core.editor_state import EditorState, MaskLayer, MaskType, WatermarkLayer
from app.ui.ai_worker import AIEditWorker
from app.ui.provider_test_worker import ProviderConnectionWorker
from app.utils.config import RuntimeSettings


def plan(**updates) -> EditingPlan:
    return EditingPlan.model_validate({
        "summary": "Light edit", "reasoning_summary": "Preserve the subject.",
        "global_adjustments": [{"tool": "set_contrast", "value": 10}],
        "confidence": 0.9, **updates,
    })


def pixels():
    return np.full((40, 60, 3), 130, dtype=np.uint8)


class StubProvider(AIProvider):
    name = "Test provider"

    def __init__(self, result=None, on_call=lambda: None):
        self.result = result or plan()
        self.on_call = on_call
        self.calls = 0

    def plan(self, request):
        self.on_call()
        self.calls += 1
        return self.result


@pytest.mark.parametrize("curve", [
    "{0, 0, 64, 50, 192, 215, 255, 255}",
    "{[1]=0, [2]=0, [3]=64, [4]=50, [5]=192, [6]=215, [7]=255, [8]=255}",
    "{[7]=255, [0]=0, [1]=0, [2]=64, [3]=50, [4]=192, [5]=215, [6]=255}",
    "{[0]=0, [64]=50, [192]=215, [255]=255}",
])
def test_native_indexed_and_flat_curves_are_identical(curve):
    native = parse_jarvisart_lua("return {ToneCurvePV2012=" + curve + "}")
    assert [(point.x, point.y) for point in native.curves[0].points] == [
        (0, 0), (64, 50), (192, 215), (255, 255),
    ]


@pytest.mark.parametrize("content", [
    "return {Exposure2012=-0.5",
    'return {Exposure2012=-0.5, Name="truncated}',
    "return {Exposure2012=-0.5, ToneCurvePV2012={0,0,255,255}",
    "return {Exposure2012=-0.5} dangerous_code()",
    "return {Exposure2012=-0.5, Exposure2012=0.3}",
    "return {Exposure2012='not a number'}",
    "return {Exposure2012=}",
    "return {ToneCurvePV2012={0,0,255}}",
    "return {ToneCurvePV2012={0,0,255,280}}",
    "return {ToneCurvePV2012={0,0,0,255}}",
])
def test_native_invalid_table_is_rejected_instead_of_partial_application(content):
    with pytest.raises(AIRequestError, match="."):
        parse_jarvisart_lua(content)


def test_unknown_nested_and_string_native_operations_remain_visible():
    native = parse_jarvisart_lua(
        'return {Exposure2012=-.2, GenerativeRemove={enabled=true}, Mystery="foo", ProcessVersion="15.4"}'
    )
    result = JarvisArtAdapter().adapt(native)
    assert any("GenerativeRemove" in item for item in result.unsupported_operations)
    assert any("Mystery" in item for item in result.unsupported_operations)
    assert not any("ProcessVersion" in item for item in result.unsupported_operations)
    assert result.plan.global_adjustments[0].value == -0.2


def test_openai_sdk_is_explicitly_no_retry_with_finite_deadline(monkeypatch):
    options = {}
    monkeypatch.setattr("app.ai.openai_provider.OpenAI", lambda **kwargs: options.update(kwargs) or object())
    OpenAIProvider("test-key", "test-model")
    assert options["max_retries"] == 0
    assert options["timeout"] == 120.0


@pytest.mark.parametrize("provider_class", [GeminiProvider, OpenAIProvider])
def test_cloud_connection_test_is_one_small_request(provider_class):
    calls, started, results = [], [], []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text="OK", output_text="OK")

    client = SimpleNamespace(models=SimpleNamespace(generate_content=create),
                             responses=SimpleNamespace(create=create))
    provider = provider_class("", "test", client=client,
                              on_request_started=lambda: started.append(True),
                              on_result=lambda *args: results.append(args))
    assert "文字连接测试通过" in provider.test_connection()
    assert len(calls) == len(started) == len(results) == 1
    assert "model" in calls[0]
    if provider_class is GeminiProvider:
        assert calls[0]["config"].http_options.retry_options.attempts == 1


def test_error_details_never_echo_key_or_validation_input():
    secret = "synthetic-private-token-123"
    error = error_from_exception(ValueError("api_key=" + secret + " invalid"), model="m",
                                 request_sent=True, secrets=(secret,))
    assert secret not in error.details()
    with pytest.raises(ValidationError) as raised:
        GlobalAdjustment(tool="set_exposure", value="private-user-input")
    error = error_from_exception(raised.value, model="m", request_sent=True)
    assert "private-user-input" not in error.details()
    assert "value" in error.validation_summary()
    assert all(set(item) == {"loc", "type", "msg"} for item in error.validation_errors)


def test_compatible_provider_error_redacts_the_exact_configured_key():
    secret = "this-is-not-a-standard-vendor-token"

    def fail(**kwargs):
        raise RuntimeError("rejected credential " + secret)

    provider = OpenAICompatibleProvider(
        secret, "m", "https://example.invalid/v1",
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail))),
    )
    with pytest.raises(AIRequestError) as raised:
        provider.plan(PlanningRequest("edit", EditorState(), None, []))
    assert secret not in raised.value.details()


def test_budget_enforces_limit_at_request_boundary_and_tracks_out_of_order_results(tmp_path):
    usage = AIUsageManager(QSettings(str(tmp_path / "budget.ini"), QSettings.Format.IniFormat))
    first = usage.record_started_request("Gemini", "m")
    second = usage.record_started_request("Gemini", "m")
    usage.record_result("Gemini", "m", "second", request_id=second, total_tokens=31)
    usage.record_result("Gemini", "m", "first", request_id=first, total_tokens=13)
    assert [entry["result"] for entry in usage.recent_events()] == ["second", "first"]
    for _ in range(18):
        usage.record_started_request("Gemini", "m")
    with pytest.raises(AIRequestError, match="每日"):
        usage.record_started_request("Gemini", "m")
    assert usage.status().today_count == 20
    usage.store.setValue("ai/usage_date", "2000-01-01")
    usage.record_started_request("Gemini", "m")
    assert usage.status().today_count == 1


def test_reinspection_cannot_bypass_budget(tmp_path):
    usage = AIUsageManager(QSettings(str(tmp_path / "budget.ini"), QSettings.Format.IniFormat))
    for _ in range(19):
        usage.record_started_request("test", "m")
    tracker = CloudRequestTracker(usage, "test", "m", cloud=True)
    provider = StubProvider(plan(needs_reinspection=True), on_call=tracker.started)
    original = EditorState()
    with pytest.raises(AIRequestError, match="每日"):
        AIOrchestrator(provider, reinspection_enabled=True).process("edit", pixels(), original, [])
    assert provider.calls == 1
    assert usage.status().today_count == 20
    assert original.is_pristine()


def test_cancellation_blocks_first_request_and_optional_second_request():
    cancelled = False

    def check():
        if cancelled:
            raise AIRequestError("已取消本地等待", "cancelled")

    def after_request():
        nonlocal cancelled
        cancelled = True

    provider = StubProvider(plan(needs_reinspection=True), on_call=after_request)
    orchestrator = AIOrchestrator(provider, reinspection_enabled=True, check_cancelled=check)
    with pytest.raises(AIRequestError, match="cancelled"):
        orchestrator.process("edit", pixels(), EditorState(), [])
    assert provider.calls == 1
    with pytest.raises(AIRequestError, match="cancelled"):
        orchestrator.process("edit", pixels(), EditorState(), [])
    assert provider.calls == 1


def test_default_orchestrator_never_automatically_reinspects():
    provider = StubProvider(plan(needs_reinspection=True))
    result = AIOrchestrator(provider).process("edit", pixels(), EditorState(), [])
    assert provider.calls == 1
    assert result.preview_pixels.shape == pixels().shape
    assert result.has_changes


def test_text_request_with_max_calls_one_cannot_trigger_a_second_request():
    provider = StubProvider(plan(needs_reinspection=True))
    AIOrchestrator(provider, reinspection_enabled=True, max_vision_calls=1).process(
        "退一点", pixels(), EditorState(), [],
    )
    assert provider.calls == 1


def test_unchanged_plan_has_no_fake_changes():
    provider = StubProvider(plan(global_adjustments=[{"tool": "set_exposure", "value": 0}]))
    result = AIOrchestrator(provider).process("edit", pixels(), EditorState(), [])
    assert not result.has_changes
    assert not result.changed_fields
    assert np.array_equal(result.preview_pixels, pixels())


def test_invalid_final_render_aborts_transaction(monkeypatch):
    def render(source, state):
        if not state.is_pristine():
            raise ValueError("render failed")
        return source.copy()

    monkeypatch.setattr("app.ai.orchestrator.render_image", render)
    state = EditorState()
    provider = StubProvider()
    with pytest.raises(AIRequestError) as raised:
        AIOrchestrator(provider).process("edit", pixels(), state, [])
    assert raised.value.category == "本地图像处理错误"
    assert state.is_pristine() and provider.calls == 1


def test_rejected_semantic_mask_is_reported_as_warning_not_applied_change(monkeypatch):
    monkeypatch.setattr("app.ai.orchestrator.mask_confidence", lambda *args: 0)
    provider = StubProvider(plan(
        global_adjustments=[],
        requested_masks=[{"tool": "create_sky_mask", "ref": "s", "name": "Sky"}],
        local_adjustments=[{"mask_ref": "s", "adjustments": {"exposure": -0.5}}],
    ))
    result = AIOrchestrator(provider).process("edit", pixels(), EditorState(), [])
    assert result.state.is_pristine()
    assert not result.has_changes and not result.changed_fields and not result.created_masks
    assert len(result.warnings) == 1 and "Sky" in result.warnings[0]


def test_duplicate_mask_reference_aborts_without_mutating_original_state():
    state = EditorState()
    proposed = plan(requested_masks=[
        {"tool": "create_sky_mask", "ref": "same", "name": "Sky 1"},
        {"tool": "create_sky_mask", "ref": "same", "name": "Sky 2"},
    ])
    with pytest.raises(ValueError, match="duplicate"):
        apply_editing_plan(state, proposed)
    assert state.is_pristine()


@pytest.mark.parametrize("endpoint", ["https://example.invalid", "http://127.0.0.1@evil.invalid", "file:///temp", "http://127.0.0.1:8765?secret=x"])
def test_local_provider_rejects_non_loopback_endpoints_without_sending(endpoint):
    calls = []
    manager = JarvisArtServiceManager(endpoint=endpoint, opener=lambda *args, **kwargs: calls.append(True))
    assert manager.status().state == "Error"
    assert not calls


def test_prompt_uses_actual_ranges_and_omits_private_watermark_assets():
    state = EditorState()
    state.watermarks = [WatermarkLayer(asset_id="private-watermark-asset", name="Private Logo")]
    request = PlanningRequest("edit", state, None, [])
    prompt = build_prompt(request)
    assert "private-watermark-asset" not in prompt
    assert '"set_color_grade_shadow_hue":[0.0,360.0]' in prompt
    for tool, (minimum, maximum) in GLOBAL_ADJUSTMENT_RANGES.items():
        GlobalAdjustment(tool=tool, value=minimum)
        GlobalAdjustment(tool=tool, value=maximum)
        with pytest.raises(ValidationError):
            GlobalAdjustment(tool=tool, value=maximum + 1)


def test_connection_worker_budget_blocks_before_sdk(monkeypatch, tmp_path, qtbot):
    store = QSettings(str(tmp_path / "budget.ini"), QSettings.Format.IniFormat)
    store.setValue("ai/budget_mode", "disabled")
    monkeypatch.setattr("app.ui.provider_test_worker.QSettings", lambda *args: store)
    calls = []

    def factory(config, key, **kwargs):
        def test():
            kwargs["on_request_started"]()
            calls.append(True)
            return "OK"
        return SimpleNamespace(test_connection=test)

    monkeypatch.setattr(provider_registry, "create", factory)
    worker = ProviderConnectionWorker(provider_registry.make_config("gemini"), "fake", "system")
    errors = []
    worker.signals.failed.connect(errors.append)
    worker.run()
    assert len(errors) == 1 and not errors[0].request_sent
    assert not calls and AIUsageManager(store).status().today_count == 0


def test_worker_cancelled_before_start_does_not_create_provider(monkeypatch, tmp_path, qtbot):
    store = QSettings(str(tmp_path / "budget.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("app.ui.ai_worker.QSettings", lambda *args: store)
    calls = []
    monkeypatch.setattr(provider_registry, "create", lambda *args, **kwargs: calls.append(True))
    worker = AIEditWorker("edit", pixels(), EditorState(), [], RuntimeSettings(), "fake", None)
    errors = []
    worker.signals.failed.connect(errors.append)
    worker.cancel()
    worker.run()
    assert len(errors) == 1 and not errors[0].request_sent
    assert not calls and AIUsageManager(store).status().today_count == 0


def test_failed_schema_response_stays_counted_once(monkeypatch, tmp_path, qtbot):
    store = QSettings(str(tmp_path / "budget.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("app.ui.ai_worker.QSettings", lambda *args: store)

    def factory(config, key, **kwargs):
        def fail():
            kwargs["on_request_started"]()
            raise AIRequestError("Pydantic schema 校验错误", "bad plan", request_sent=True)
        return StubProvider(on_call=fail)

    monkeypatch.setattr(provider_registry, "create", factory)
    worker = AIEditWorker("edit", pixels(), EditorState(), [], RuntimeSettings(), "fake", None)
    errors = []
    worker.signals.failed.connect(errors.append)
    worker.run()
    usage = AIUsageManager(store)
    assert usage.status().today_count == 1
    assert len(usage.recent_events()) == 1
    assert usage.recent_events()[0]["result"] == "Pydantic schema 校验错误"
    assert errors[0].request_sent


def test_local_launcher_uses_file_capture_not_inherited_child_pipes(monkeypatch, tmp_path):
    root = tmp_path / "JarvisArt"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "launch_services.ps1").write_text("# test", encoding="utf-8")
    manager = JarvisArtServiceManager(str(root))
    statuses = iter([JarvisArtServiceStatus("Offline", "offline"), JarvisArtServiceStatus("Ready", "ready")])
    monkeypatch.setattr(manager, "status", lambda: next(statuses))
    monkeypatch.setattr(manager, "_listener_pids", lambda: set())
    calls = []

    def run(command, **kwargs):
        calls.append(kwargs)
        assert "capture_output" not in kwargs
        kwargs["stdout"].write("launcher ready\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("app.ai.jarvisart.service.subprocess.run", run)
    assert manager.start().state == "Ready"
    assert len(calls) == 1 and calls[0]["timeout"] == 180.0
