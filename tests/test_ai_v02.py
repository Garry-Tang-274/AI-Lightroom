from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from PySide6.QtCore import QSettings, Qt

from app.ai.errors import AIRequestError, error_from_exception
from app.ai.gemini_provider import GeminiProvider
from app.ai.provider import PlanningRequest
from app.ai.schemas import EditingPlan, gemini_response_schema
from app.ai.usage import AIUsageManager
from app.core.editor_state import EditorState
from app.ui.ai_panel import AIPanel


def valid_plan() -> dict:
    return {
        "summary": "轻微优化层次", "reasoning_summary": "保护高光和主体。",
        "global_adjustments": [{"tool": "set_contrast", "value": 4}],
        "hsl_adjustments": [{"color": "blue", "hue": 0, "saturation": -4, "luminance": -2}],
        "curve_adjustments": [{"tool": "set_rgb_curve", "points": [{"x": 0, "y": 0}, {"x": 1, "y": 1}]}],
        "requested_masks": [{"tool": "create_sky_mask", "ref": "sky_1", "name": "天空"}],
        "local_adjustments": [{"mask_ref": "sky_1", "adjustments": {"exposure": -0.2}}],
        "confidence": 0.82, "needs_reinspection": False,
    }


def test_editing_plan_strict_fixture_cases():
    assert EditingPlan.model_validate(valid_plan()).hsl_adjustments[0].color == "blue"
    extra = valid_plan() | {"unexpected": True}
    with pytest.raises(ValidationError, match="extra_forbidden"):
        EditingPlan.model_validate(extra)
    missing = valid_plan()
    del missing["confidence"]
    with pytest.raises(ValidationError, match="Field required"):
        EditingPlan.model_validate(missing)
    wrong = valid_plan() | {"confidence": "high"}
    with pytest.raises(ValidationError):
        EditingPlan.model_validate(wrong)


def test_schema_error_has_a_compact_field_summary():
    with pytest.raises(ValidationError) as raised:
        EditingPlan.model_validate(valid_plan() | {"analysis": {"scene": "city"}})
    error = AIRequestError(
        "Pydantic schema 校验错误",
        "response did not match",
        validation_errors=raised.value.errors(include_url=False),
    )
    assert "analysis: Extra inputs are not permitted" in error.validation_summary()


def test_gemini_schema_preflight_is_sdk_compatible():
    GeminiProvider.validate_response_schema()
    assert "additionalProperties" not in str(gemini_response_schema())


@pytest.mark.parametrize(
    ("payload", "category"),
    [
        ("", "Gemini 返回空内容"),
        ('{"summary":"truncated"', "Pydantic schema 校验错误"),
        ('{"summary":"x","reasoning_summary":"x","confidence":0.5,"extra":1}', "Pydantic schema 校验错误"),
    ],
)
def test_gemini_provider_rejects_bad_content_without_real_request(payload, category):
    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=payload)
    provider = GeminiProvider("", "test", client=SimpleNamespace(models=FakeModels()))
    with pytest.raises(AIRequestError) as raised:
        provider.plan(PlanningRequest("edit", EditorState(), None, []))
    assert raised.value.category == category
    assert raised.value.request_sent


def test_gemini_provider_does_not_retry_after_failure():
    class FakeModels:
        calls = 0
        def generate_content(self, **kwargs):
            self.calls += 1
            raise TimeoutError("timed out")
    models = FakeModels()
    provider = GeminiProvider("", "test", client=SimpleNamespace(models=models))
    with pytest.raises(AIRequestError):
        provider.plan(PlanningRequest("edit", EditorState(), None, []))
    assert models.calls == 1


@pytest.mark.parametrize("status,category", [(401, "API Key 无效（HTTP 401）"), (403, "API Key 权限不足（HTTP 403）"), (429, "Gemini API 配额或 Rate Limit（HTTP 429）"), (500, "Gemini 服务器错误（5xx）")])
def test_http_error_categories(status, category):
    class HttpError(Exception):
        status_code = status
    error = error_from_exception(HttpError("provider response"), model="test", request_sent=True)
    assert error.category == category
    assert error.request_sent


def test_budget_limit_and_date_rollover(tmp_path):
    store = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    usage = AIUsageManager(store)
    status = usage.status()
    assert status.today_count == 0 and status.daily_limit == 20 and status.can_request
    for _ in range(20):
        usage.record_started_request("Gemini", "test")
        usage.record_result("Gemini", "test", "成功")
    assert usage.status().today_count == 20
    assert not usage.status().can_request
    store.setValue("ai/usage_date", "2000-01-01")
    assert usage.status().today_count == 0


def test_ai_panel_multiline_ctrl_enter(qtbot):
    panel = AIPanel()
    qtbot.addWidget(panel)
    panel.set_ready(True)
    panel.input.setPlainText("第一行\n第二行")
    assert panel.input.document().blockCount() == 2
    with qtbot.waitSignal(panel.prompt_submitted) as signal:
        qtbot.keyClick(panel.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert signal.args == ["第一行\n第二行"]
    panel.set_busy(True)
    assert not panel.input.isEnabled() and panel.cancel_button.isEnabled()
