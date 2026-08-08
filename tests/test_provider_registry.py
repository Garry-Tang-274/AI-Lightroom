from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PIL import Image
from io import BytesIO

from app.ai.errors import AIRequestError
from app.ai.orchestrator import AIOrchestrator, encode_preview
from app.ai.provider import PlanningRequest
from app.ai.provider_registry import provider_registry
from app.ai.qwen_provider import QWEN_DEFAULT_BASE_URL, QWEN_VISION_TIMEOUT_SECONDS, QwenProvider
from app.ai.schemas import EditingPlan
from app.core.editor_state import EditorState, MaskType
from app.ui.settings_dialog import SettingsDialog
from app.utils.config import SettingsManager


def _plan() -> EditingPlan:
    return EditingPlan.model_validate({
        "summary": "Qwen plan", "reasoning_summary": "Use local sky adjustment.",
        "global_adjustments": [{"tool": "set_contrast", "value": 7}],
        "requested_masks": [{"tool": "create_sky_mask", "ref": "sky", "name": "Sky"}],
        "local_adjustments": [{"mask_ref": "sky", "adjustments": {"exposure": -0.3}}],
        "confidence": 0.9, "needs_reinspection": False,
    })


def test_registry_exposes_decoupled_provider_metadata_and_capabilities():
    qwen = provider_registry.descriptor("qwen")
    assert qwen.default_model == "qwen3.7-plus"
    assert qwen.default_base_url == QWEN_DEFAULT_BASE_URL
    assert qwen.capabilities.supports_vision
    assert qwen.capabilities.supports_structured_output
    assert provider_registry.descriptor("custom").capabilities.supports_custom_base_url
    assert {item.id for item in provider_registry.descriptors()} >= {"gemini", "openai", "qwen", "custom", "mock", "jarvisart_local"}


def test_qwen_vision_json_plan_drives_existing_renderer_without_network():
    plan = _plan()

    class FakeCompletions:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content=None,
                    tool_calls=[SimpleNamespace(function=SimpleNamespace(
                        name="submit_editing_plan", arguments=plan.model_dump_json(),
                    ))],
                ))],
                usage=SimpleNamespace(prompt_tokens=120, completion_tokens=50, total_tokens=170),
            )

    completions = FakeCompletions()
    provider = QwenProvider("", client=SimpleNamespace(chat=SimpleNamespace(completions=completions)))
    pixels = np.zeros((160, 240, 3), dtype=np.uint8)
    pixels[:82] = (90, 150, 225)
    pixels[82:] = (95, 85, 60)
    original = pixels.copy()
    result = AIOrchestrator(provider, preview_size=1536, reinspection_enabled=False).process("Make the sky slightly darker.", pixels, EditorState(), [])

    assert result.state.basic.contrast == 7
    assert any(layer.type == MaskType.SKY for layer in result.state.masks)
    assert np.array_equal(pixels, original)  # analysis never overwrites source pixels
    assert completions.kwargs["model"] == "qwen3.7-plus"
    assert "response_format" not in completions.kwargs
    assert completions.kwargs["extra_body"] == {"enable_thinking": False}
    assert completions.kwargs["tool_choice"] == "required"
    assert completions.kwargs["tools"][0]["function"]["name"] == "submit_editing_plan"
    user_content = completions.kwargs["messages"][1]["content"]
    assert any(item["type"] == "image_url" and item["image_url"]["url"].startswith("data:image/jpeg;base64,") for item in user_content)
    prompt = next(item["text"] for item in user_content if item["type"] == "text")
    assert '"global_adjustments"' in prompt
    assert "Never output keys named analysis" in prompt


def test_qwen_error_json_and_invalid_key_are_reported_without_retry():
    class BadCompletions:
        calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=None,
                tool_calls=[SimpleNamespace(function=SimpleNamespace(
                    name="submit_editing_plan", arguments="{not json",
                ))],
            ))])

    bad = BadCompletions()
    provider = QwenProvider("", client=SimpleNamespace(chat=SimpleNamespace(completions=bad)))
    with pytest.raises(AIRequestError, match="严格 EditingPlan"):
        provider.plan(PlanningRequest("edit", EditorState(), b"jpeg", []))
    assert bad.calls == 1

    class HttpError(Exception):
        status_code = 401

    class UnauthorizedCompletions:
        def create(self, **kwargs):
            raise HttpError("bad key")

    provider = QwenProvider("", client=SimpleNamespace(chat=SimpleNamespace(completions=UnauthorizedCompletions())))
    with pytest.raises(AIRequestError) as raised:
        provider.test_connection()
    assert raised.value.category == "API Key 无效（HTTP 401）"
    assert raised.value.provider == "阿里云百炼 / Qwen"


def test_custom_requires_base_url_and_registry_preserves_capability_choice():
    qwen = provider_registry.make_config("qwen")
    with pytest.raises(ValueError, match="API Key"):
        provider_registry.create(qwen, "")
    config = provider_registry.make_config("custom", "vision-model", "", "My Gateway", custom_vision=True, custom_structured_output=False)
    with pytest.raises(ValueError, match="Base URL"):
        provider_registry.create(config, "key")
    config = provider_registry.make_config("custom", "vision-model", "http://127.0.0.1:11434/v1", "My Gateway", custom_vision=False, custom_structured_output=False)
    assert config.display_name == "My Gateway"
    assert not config.capabilities.supports_vision
    assert not config.capabilities.supports_structured_output


def test_settings_exposes_qwen_and_custom_provider_choices(qtbot, tmp_path):
    manager = SettingsManager()
    manager.store = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    manager.store.setValue("ai/active_provider", "qwen")
    dialog = SettingsDialog(manager)
    qtbot.addWidget(dialog)
    assert dialog.provider.findData("qwen") >= 0
    assert dialog.provider.findData("custom") >= 0
    assert dialog.provider.findData("jarvisart_local") >= 0
    assert dialog.model.text() == "qwen3.7-plus"
    assert dialog.base_url.text() == QWEN_DEFAULT_BASE_URL


def test_settings_migrates_legacy_gemini_selection(tmp_path):
    manager = SettingsManager()
    manager.store = QSettings(str(tmp_path / "legacy.ini"), QSettings.Format.IniFormat)
    manager.store.setValue("ai/provider", "auto")
    manager.store.setValue("ai/gemini_model", "legacy-gemini")
    runtime = manager.runtime()
    assert runtime.provider == "gemini"
    assert runtime.active_model == "legacy-gemini"


def test_qwen_analysis_preview_uses_configured_small_copy_not_original():
    pixels = np.zeros((2000, 3000, 3), dtype=np.uint8)
    preview = encode_preview(pixels, max_edge=1536)
    with Image.open(BytesIO(preview)) as image:
        assert max(image.size) == 1536


def test_qwen_uses_a_longer_visual_deadline_without_enabling_retries(monkeypatch):
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("app.ai.openai_compatible_provider.OpenAI", FakeClient)
    QwenProvider("test-key")

    assert captured["timeout"] == QWEN_VISION_TIMEOUT_SECONDS
    assert captured["max_retries"] == 0


def test_qwen_normalises_only_known_noop_semantic_mask_hints():
    payload = _plan().model_dump(mode="json")
    payload["requested_masks"][0]["parameters"] = {
        "sample_point_x": 0.5,
        "sample_point_y": 0.3,
        "range": 0.2,
    }
    arguments = QwenProvider._normalise_semantic_mask_hints(json.dumps(payload))
    parsed = EditingPlan.model_validate_json(arguments)
    assert parsed.requested_masks[0].parameters.model_dump(exclude_none=True) == {}


def test_qwen_keeps_unknown_or_mathematical_mask_parameters_strict():
    payload = _plan().model_dump(mode="json")
    payload["requested_masks"][0]["parameters"] = {"sample_point_x": 0.5, "unexpected": 1}
    assert QwenProvider._normalise_semantic_mask_hints(json.dumps(payload)) == json.dumps(payload)

    payload["requested_masks"][0]["tool"] = "create_linear_gradient"
    payload["requested_masks"][0]["parameters"] = {"sample_point_x": 0.5}
    assert QwenProvider._normalise_semantic_mask_hints(json.dumps(payload)) == json.dumps(payload)
