from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.editor_state import CurvePoint, HSLColor


GlobalTool = Literal[
    "set_exposure",
    "set_contrast",
    "set_highlights",
    "set_shadows",
    "set_whites",
    "set_blacks",
    "set_temperature",
    "set_tint",
    "set_saturation",
    "set_vibrance",
    "set_clarity",
    "set_texture",
    "set_dehaze",
    "set_sharpen",
    "set_vignette",
]

CurveTool = Literal["set_rgb_curve", "set_red_curve", "set_green_curve", "set_blue_curve"]

MaskTool = Literal[
    "create_linear_gradient",
    "create_radial_gradient",
    "create_luminance_mask",
    "create_color_range_mask",
    "create_sky_mask",
    "create_subject_mask",
    "create_semantic_mask",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GlobalAdjustment(StrictModel):
    tool: GlobalTool
    value: float

    @model_validator(mode="after")
    def validate_value(self) -> "GlobalAdjustment":
        if self.tool == "set_exposure" and not -5 <= self.value <= 5:
            raise ValueError("exposure must be between -5 and 5")
        if self.tool == "set_sharpen" and not 0 <= self.value <= 100:
            raise ValueError("sharpen must be between 0 and 100")
        if self.tool not in {"set_exposure", "set_sharpen"} and not -100 <= self.value <= 100:
            raise ValueError(f"{self.tool} must be between -100 and 100")
        return self


class HSLAdjustmentPlan(StrictModel):
    tool: Literal["adjust_hsl"] = "adjust_hsl"
    color: HSLColor
    hue: float = Field(0.0, ge=-100, le=100)
    saturation: float = Field(0.0, ge=-100, le=100)
    luminance: float = Field(0.0, ge=-100, le=100)


class CurveAdjustmentPlan(StrictModel):
    tool: CurveTool
    points: list[CurvePoint] = Field(min_length=2, max_length=16)


class MaskParameters(StrictModel):
    start_x: float | None = Field(None, ge=0, le=1)
    start_y: float | None = Field(None, ge=0, le=1)
    end_x: float | None = Field(None, ge=0, le=1)
    end_y: float | None = Field(None, ge=0, le=1)
    center_x: float | None = Field(None, ge=0, le=1)
    center_y: float | None = Field(None, ge=0, le=1)
    # Google GenAI's Schema model rejects JSON Schema ``exclusiveMinimum``.
    radius_x: float | None = Field(None, ge=0.001, le=1)
    radius_y: float | None = Field(None, ge=0.001, le=1)
    rotation: float | None = Field(None, ge=-180, le=180)
    min: float | None = Field(None, ge=0, le=1)
    max: float | None = Field(None, ge=0, le=1)
    hue: float | None = Field(None, ge=0, le=360)
    tolerance: float | None = Field(None, ge=1, le=180)
    min_saturation: float | None = Field(None, ge=0, le=1)


class MaskRequest(StrictModel):
    tool: MaskTool
    ref: str = Field(description="Unique reference used by local adjustments, such as mask_1")
    name: str
    semantic_label: str | None = None
    parameters: MaskParameters = Field(default_factory=MaskParameters)
    feather: float = Field(0.5, ge=0, le=1)
    inverted: bool = False


class LocalAdjustmentValues(StrictModel):
    exposure: float | None = Field(None, ge=-5, le=5)
    contrast: float | None = Field(None, ge=-100, le=100)
    highlights: float | None = Field(None, ge=-100, le=100)
    shadows: float | None = Field(None, ge=-100, le=100)
    whites: float | None = Field(None, ge=-100, le=100)
    blacks: float | None = Field(None, ge=-100, le=100)
    temperature: float | None = Field(None, ge=-100, le=100)
    tint: float | None = Field(None, ge=-100, le=100)
    saturation: float | None = Field(None, ge=-100, le=100)
    vibrance: float | None = Field(None, ge=-100, le=100)
    clarity: float | None = Field(None, ge=-100, le=100)
    texture: float | None = Field(None, ge=-100, le=100)
    dehaze: float | None = Field(None, ge=-100, le=100)
    sharpen: float | None = Field(None, ge=0, le=100)


class LocalAdjustmentPlan(StrictModel):
    mask_ref: str = Field(description="A requested-mask ref, existing mask id/name, or selected")
    adjustments: LocalAdjustmentValues


class EditingPlan(StrictModel):
    summary: str
    reasoning_summary: str
    global_adjustments: list[GlobalAdjustment] = Field(default_factory=list)
    hsl_adjustments: list[HSLAdjustmentPlan] = Field(default_factory=list)
    curve_adjustments: list[CurveAdjustmentPlan] = Field(default_factory=list)
    local_adjustments: list[LocalAdjustmentPlan] = Field(default_factory=list)
    requested_masks: list[MaskRequest] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    needs_reinspection: bool = False


AVAILABLE_TOOLS = {
    "global": list(GlobalTool.__args__),
    "hsl": ["adjust_hsl"],
    "curves": list(CurveTool.__args__),
    "masks": list(MaskTool.__args__),
    "local_adjustments": list(LocalAdjustmentValues.model_fields),
}


def editing_plan_json_contract() -> str:
    """Compact, provider-neutral JSON contract for JSON-mode providers.

    Gemini and OpenAI receive a wire-level schema.  OpenAI-compatible JSON
    mode only guarantees syntactically valid JSON, so it must also receive the
    exact field contract in the prompt.  Keep this concise: it is sent with
    every visual request and must be easy for a model to follow.
    """
    return """\
OUTPUT CONTRACT (mandatory): Return exactly one JSON object and no Markdown.
Use exactly these nine snake_case top-level keys, including empty lists:
{
  \"summary\": \"short user-facing result\",
  \"reasoning_summary\": \"one or two short visible reasons\",
  \"global_adjustments\": [],
  \"hsl_adjustments\": [],
  \"curve_adjustments\": [],
  \"local_adjustments\": [],
  \"requested_masks\": [],
  \"confidence\": 0.0,
  \"needs_reinspection\": false
}
Never output keys named analysis, global, hsl, toneCurve, localAdjustments,
requestedMasks, tools, plan, or any other extra key.

global_adjustments item: {\"tool\": \"set_exposure\", \"value\": 0.0}.
Only use a global tool listed in available_tools.global. Values are target
absolute values; exposure is -5..5, sharpen is 0..100, all other global
values are -100..100.
hsl_adjustments item: {\"tool\": \"adjust_hsl\", \"color\": \"blue\",
\"hue\": 0.0, \"saturation\": 0.0, \"luminance\": 0.0}. Color is one of
red, orange, yellow, green, aqua, blue, purple, magenta; HSL values are -100..100.
curve_adjustments item: {\"tool\": \"set_rgb_curve\", \"points\":
[{\"x\": 0.0, \"y\": 0.0}, {\"x\": 1.0, \"y\": 1.0}]}. Use only listed
curve tools; x/y are 0..1 and at least two points are required.
requested_masks item: {\"tool\": \"create_sky_mask\", \"ref\": \"sky_1\",
\"name\": \"Sky\", \"semantic_label\": \"sky\", \"parameters\": {},
\"feather\": 0.5, \"inverted\": false}. Use only listed mask tools.
For create_sky_mask, create_subject_mask, and create_semantic_mask, parameters
MUST be exactly {}: their regions are generated from the image and semantic_label.
Never emit sample_point_x, sample_point_y, range, sample points, polygons, or
any other parameters for these semantic mask tools. Only mathematical mask tools
may use their documented parameters.
local_adjustments item: {\"mask_ref\": \"sky_1\", \"adjustments\":
{\"exposure\": -0.3}}. mask_ref must match a requested mask ref or an existing
mask id/name. Local keys may only be exposure, contrast, highlights, shadows,
whites, blacks, temperature, tint, saturation, vibrance, clarity, texture, dehaze,
sharpen. Do not output
null, omitted required fields, comments, or unsupported adjustment names.
"""


def gemini_response_schema() -> dict:
    """Return a Gemini-compatible copy while keeping local Pydantic validation strict.

    Gemini's response-schema endpoint rejects JSON Schema's
    ``additionalProperties`` field.  It is removed only from the wire schema;
    ``StrictModel(extra='forbid')`` still rejects extra fields locally.
    """
    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items() if key != "additionalProperties"}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value
    return clean(EditingPlan.model_json_schema())


def openai_response_schema() -> dict:
    """Return a strict Responses API schema for the same local EditingPlan.

    OpenAI Structured Outputs requires every object to explicitly forbid extra
    properties and to list each property as required. Optional Pydantic fields
    remain nullable in their existing ``anyOf`` definitions.
    """
    def clean(value):
        if isinstance(value, dict):
            result = {key: clean(item) for key, item in value.items() if key != "default"}
            properties = result.get("properties")
            if isinstance(properties, dict):
                result["additionalProperties"] = False
                result["required"] = list(properties)
            return result
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value
    return clean(EditingPlan.model_json_schema())
