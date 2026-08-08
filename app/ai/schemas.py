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
    clarity: float | None = Field(None, ge=-100, le=100)
    dehaze: float | None = Field(None, ge=-100, le=100)


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
