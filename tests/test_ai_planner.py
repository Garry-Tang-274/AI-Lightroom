from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from app.ai.executor import apply_editing_plan
from app.ai.gemini_provider import GeminiProvider
from app.ai.mock_provider import MockProvider
from app.ai.orchestrator import AIOrchestrator, encode_preview
from app.ai.provider import PlanningRequest
from app.ai.schemas import EditingPlan, GlobalAdjustment
from app.core.editor_state import EditorState, MaskType


def test_editing_plan_rejects_unknown_tools_and_out_of_range_values():
    with pytest.raises(ValidationError):
        GlobalAdjustment(tool="invent_magic_filter", value=1)
    with pytest.raises(ValidationError):
        GlobalAdjustment(tool="set_exposure", value=5.5)


def test_plan_json_round_trip_and_executor_create_real_sky_mask():
    plan = EditingPlan.model_validate(
        {
            "summary": "压暗天空",
            "reasoning_summary": "局部需求使用天空蒙版。",
            "global_adjustments": [{"tool": "set_contrast", "value": 8}],
            "requested_masks": [{"tool": "create_sky_mask", "ref": "sky_1", "name": "天空"}],
            "local_adjustments": [
                {"mask_ref": "sky_1", "adjustments": {"exposure": -0.3, "highlights": -15}}
            ],
            "confidence": 0.9,
            "needs_reinspection": False,
        }
    )
    parsed = EditingPlan.model_validate_json(plan.model_dump_json())
    result = apply_editing_plan(EditorState(), parsed)
    assert result.state.basic.contrast == 8
    assert result.state.masks[0].type == MaskType.SKY
    assert result.state.masks[0].adjustments.exposure == -0.3


def test_mock_provider_runs_core_success_scenario_and_followup():
    source = np.zeros((160, 240, 3), dtype=np.uint8)
    source[:80] = (80, 145, 220)
    source[80:] = (95, 85, 60)
    orchestrator = AIOrchestrator(MockProvider())
    first = orchestrator.process(
        "这张画面有点平，帮我做出轻微电影感，天空稍微压一点，但不要把地面搞暗。",
        source,
        EditorState(),
        [],
    )
    assert first.state.basic.contrast > 0
    assert any(layer.type == MaskType.SKY for layer in first.state.masks)
    sky = next(layer for layer in first.state.masks if layer.type == MaskType.SKY)
    assert sky.adjustments.exposure < 0
    assert first.vision_calls == 1

    second = orchestrator.process("有点重了，退一点。", source, first.state, [first.final_plan.summary])
    assert abs(second.state.basic.contrast) < abs(first.state.basic.contrast)
    assert second.vision_calls == 0
    assert len(second.state.masks) == len(first.state.masks)


def test_preview_encoding_caps_long_edge():
    source = np.full((900, 1800, 3), 120, dtype=np.uint8)
    encoded = encode_preview(source, max_edge=600, quality=82)
    with Image.open(BytesIO(encoded)) as image:
        assert image.size == (600, 300)


def test_gemini_provider_uses_structured_schema_and_parses_response():
    response_plan = EditingPlan(
        summary="轻调",
        reasoning_summary="保留自然效果。",
        global_adjustments=[GlobalAdjustment(tool="set_contrast", value=5)],
        confidence=0.8,
    )

    class FakeModels:
        def __init__(self):
            self.kwargs = None

        def generate_content(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(text=response_plan.model_dump_json())

    fake = SimpleNamespace(models=FakeModels())
    provider = GeminiProvider("", "gemini-test", client=fake)
    request = PlanningRequest("调整", EditorState(), b"jpeg", [])
    parsed = provider.plan(request)
    assert parsed.global_adjustments[0].value == 5
    assert fake.models.kwargs["model"] == "gemini-test"
    assert len(fake.models.kwargs["contents"]) == 2
    assert fake.models.kwargs["config"].http_options.retry_options.attempts == 1
