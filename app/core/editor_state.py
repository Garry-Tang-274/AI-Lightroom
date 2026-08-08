from __future__ import annotations

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HSLColor(StrEnum):
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    AQUA = "aqua"
    BLUE = "blue"
    PURPLE = "purple"
    MAGENTA = "magenta"


class BasicAdjustments(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    exposure: float = Field(0.0, ge=-5.0, le=5.0)
    contrast: float = Field(0.0, ge=-100.0, le=100.0)
    highlights: float = Field(0.0, ge=-100.0, le=100.0)
    shadows: float = Field(0.0, ge=-100.0, le=100.0)
    whites: float = Field(0.0, ge=-100.0, le=100.0)
    blacks: float = Field(0.0, ge=-100.0, le=100.0)
    temperature: float = Field(0.0, ge=-100.0, le=100.0)
    tint: float = Field(0.0, ge=-100.0, le=100.0)
    saturation: float = Field(0.0, ge=-100.0, le=100.0)
    vibrance: float = Field(0.0, ge=-100.0, le=100.0)
    clarity: float = Field(0.0, ge=-100.0, le=100.0)
    texture: float = Field(0.0, ge=-100.0, le=100.0)
    dehaze: float = Field(0.0, ge=-100.0, le=100.0)
    sharpen: float = Field(0.0, ge=0.0, le=100.0)
    vignette: float = Field(0.0, ge=-100.0, le=100.0)

    def with_value(self, key: str, value: float) -> "BasicAdjustments":
        if key not in type(self).model_fields:
            raise KeyError(key)
        values = self.model_dump()
        values[key] = value
        return type(self).model_validate(values)


class HSLAdjustment(BaseModel):
    hue: float = Field(0.0, ge=-100.0, le=100.0)
    saturation: float = Field(0.0, ge=-100.0, le=100.0)
    luminance: float = Field(0.0, ge=-100.0, le=100.0)


class CurvePoint(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class ToneCurve(BaseModel):
    points: list[CurvePoint] = Field(
        default_factory=lambda: [CurvePoint(x=0.0, y=0.0), CurvePoint(x=1.0, y=1.0)]
    )

    @field_validator("points")
    @classmethod
    def validate_points(cls, points: list[CurvePoint]) -> list[CurvePoint]:
        if len(points) < 2:
            raise ValueError("A curve needs at least two control points")
        ordered = sorted(points, key=lambda point: point.x)
        if any(right.x - left.x < 0.001 for left, right in zip(ordered, ordered[1:])):
            raise ValueError("Curve control point x values must be distinct")
        return ordered


class CurveSettings(BaseModel):
    rgb: ToneCurve = Field(default_factory=ToneCurve)
    red: ToneCurve = Field(default_factory=ToneCurve)
    green: ToneCurve = Field(default_factory=ToneCurve)
    blue: ToneCurve = Field(default_factory=ToneCurve)


class ColorWheel(BaseModel):
    hue: float = Field(0.0, ge=0.0, le=360.0)
    saturation: float = Field(0.0, ge=0.0, le=100.0)
    luminance: float = Field(0.0, ge=-100.0, le=100.0)


class ColorGrading(BaseModel):
    shadows: ColorWheel = Field(default_factory=ColorWheel)
    midtones: ColorWheel = Field(default_factory=ColorWheel)
    highlights: ColorWheel = Field(default_factory=ColorWheel)
    blending: float = Field(50.0, ge=0.0, le=100.0)
    balance: float = Field(0.0, ge=-100.0, le=100.0)


class MaskType(StrEnum):
    LINEAR_GRADIENT = "linear_gradient"
    RADIAL_GRADIENT = "radial_gradient"
    LUMINANCE_RANGE = "luminance_range"
    COLOR_RANGE = "color_range"
    SKY = "sky"
    SUBJECT = "subject"
    SEMANTIC = "semantic"
    BRUSH = "brush"


class LocalAdjustments(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    exposure: float = Field(0.0, ge=-5.0, le=5.0)
    contrast: float = Field(0.0, ge=-100.0, le=100.0)
    highlights: float = Field(0.0, ge=-100.0, le=100.0)
    shadows: float = Field(0.0, ge=-100.0, le=100.0)
    whites: float = Field(0.0, ge=-100.0, le=100.0)
    blacks: float = Field(0.0, ge=-100.0, le=100.0)
    temperature: float = Field(0.0, ge=-100.0, le=100.0)
    tint: float = Field(0.0, ge=-100.0, le=100.0)
    saturation: float = Field(0.0, ge=-100.0, le=100.0)
    clarity: float = Field(0.0, ge=-100.0, le=100.0)
    texture: float = Field(0.0, ge=-100.0, le=100.0)
    dehaze: float = Field(0.0, ge=-100.0, le=100.0)

    def with_value(self, key: str, value: float) -> "LocalAdjustments":
        if key not in type(self).model_fields:
            raise KeyError(key)
        values = self.model_dump()
        values[key] = value
        return type(self).model_validate(values)


class BrushPoint(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class BrushStroke(BaseModel):
    points: list[BrushPoint] = Field(min_length=1)
    size: float = Field(0.08, ge=0.002, le=1.0)
    hardness: float = Field(0.65, ge=0.0, le=1.0)
    opacity: float = Field(1.0, ge=0.0, le=1.0)
    erase: bool = False


class MaskLayer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    type: MaskType
    enabled: bool = True
    opacity: float = Field(1.0, ge=0.0, le=1.0)
    feather: float = Field(0.5, ge=0.0, le=1.0)
    inverted: bool = False
    semantic_label: str | None = None
    parameters: dict[str, float | str | bool] = Field(default_factory=dict)
    adjustments: LocalAdjustments = Field(default_factory=LocalAdjustments)
    strokes: list[BrushStroke] = Field(default_factory=list)


class WatermarkLayer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    asset_id: str
    name: str
    enabled: bool = True
    position: str = Field("bottom_right", pattern="^(top_left|top_right|bottom_left|bottom_right|center|custom)$")
    x: float = Field(1.0, ge=0.0, le=1.0)
    y: float = Field(1.0, ge=0.0, le=1.0)
    scale: float = Field(0.18, ge=0.01, le=1.0)
    opacity: float = Field(1.0, ge=0.0, le=1.0)
    margin: float = Field(0.03, ge=0.0, le=0.25)


def default_hsl() -> dict[HSLColor, HSLAdjustment]:
    return {color: HSLAdjustment() for color in HSLColor}


class EditorState(BaseModel):
    """The single source of truth shared by manual controls and AI plans."""

    model_config = ConfigDict(validate_assignment=True)

    basic: BasicAdjustments = Field(default_factory=BasicAdjustments)
    hsl: dict[HSLColor, HSLAdjustment] = Field(default_factory=default_hsl)
    curves: CurveSettings = Field(default_factory=CurveSettings)
    color_grading: ColorGrading = Field(default_factory=ColorGrading)
    masks: list[MaskLayer] = Field(default_factory=list)
    watermarks: list[WatermarkLayer] = Field(default_factory=list)

    def is_pristine(self) -> bool:
        return self == type(self)()

    def snapshot(self) -> "EditorState":
        return type(self).model_validate_json(self.model_dump_json())
