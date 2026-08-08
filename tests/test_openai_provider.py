from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from app.ai.errors import AIRequestError
from app.ai.openai_provider import OpenAIProvider
from app.ai.orchestrator import AIOrchestrator
from app.ai.provider import PlanningRequest
from app.ai.schemas import EditingPlan, openai_response_schema
from app.core.editor_state import EditorState, MaskType
from app.core.image_processor import render_image


def _response_plan() -> EditingPlan:
    return EditingPlan.model_validate(
        {
            "summary": "Balanced cinematic adjustment",
            "reasoning_summary": "Preserve the foreground and adjust the sky locally.",
            "global_adjustments": [{"tool": "set_contrast", "value": 6}],
            "hsl_adjustments": [{"color": "blue", "hue": 0, "saturation": -5, "luminance": -3}],
            "curve_adjustments": [{"tool": "set_rgb_curve", "points": [{"x": 0, "y": 0}, {"x": 1, "y": 1}]}],
            "requested_masks": [{"tool": "create_sky_mask", "ref": "sky_1", "name": "Sky"}],
            "local_adjustments": [{"mask_ref": "sky_1", "adjustments": {"exposure": -0.35, "highlights": -12}}],
            "confidence": 0.88,
            "needs_reinspection": False,
        }
    )


def test_openai_response_drives_editing_plan_and_renderer_without_network():
    plan = _response_plan()

    class FakeResponses:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(output_text=plan.model_dump_json(), usage=SimpleNamespace(input_tokens=123, output_tokens=45, total_tokens=168))

    responses = FakeResponses()
    provider = OpenAIProvider("", "gpt-5.6-terra", client=SimpleNamespace(responses=responses))
    pixels = np.zeros((160, 240, 3), dtype=np.uint8)
    pixels[:82] = (90, 150, 225)
    pixels[82:] = (95, 85, 60)
    result = AIOrchestrator(provider, reinspection_enabled=False).process("Create a subtle cinematic look and darken the sky.", pixels, EditorState(), [])

    assert result.provider_name == "OpenAI"
    assert result.state.basic.contrast == 6
    assert any(layer.type == MaskType.SKY for layer in result.state.masks)
    assert not np.array_equal(render_image(pixels, result.state), pixels)
    assert responses.kwargs["model"] == "gpt-5.6-terra"
    assert responses.kwargs["text"]["format"]["type"] == "json_schema"
    assert "tools" not in responses.kwargs
    content = responses.kwargs["input"][0]["content"]
    assert any(part["type"] == "input_image" and part["image_url"].startswith("data:image/jpeg;base64,") for part in content)


def test_openai_provider_reports_invalid_output_and_never_retries():
    class FakeResponses:
        calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(output_text='{"summary":"incomplete"}')

    responses = FakeResponses()
    provider = OpenAIProvider("", "test-model", client=SimpleNamespace(responses=responses))
    with pytest.raises(AIRequestError, match="严格 EditingPlan") as raised:
        provider.plan(PlanningRequest("edit", EditorState(), b"jpeg", []))
    assert raised.value.provider == "OpenAI"
    assert raised.value.request_sent
    assert responses.calls == 1


def test_openai_strict_schema_forbids_extras_and_requires_object_properties():
    schema = openai_response_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    for definition in schema.get("$defs", {}).values():
        if "properties" in definition:
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])
