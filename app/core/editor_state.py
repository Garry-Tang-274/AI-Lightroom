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


class DetailAdjustments(BaseModel):
    """Fine-detail controls shared by manual editing and Lightroom adapters."""

    sharpen_radius: float = Field(0.8, ge=0.3, le=3.0)
    sharpen_detail: float = Field(25.0, ge=0.0, le=100.0)
    sharpen_masking: float = Field(0.0, ge=0.0, le=100.0)
    luminance_noise_reduction: float = Field(0.0, ge=0.0, le=100.0)
    luminance_noise_reduction_detail: float = Field(50.0, ge=0.0, le=100.0)
    luminance_noise_reduction_contrast: float = Field(0.0, ge=0.0, le=100.0)
    color_noise_reduction: float = Field(0.0, ge=0.0, le=100.0)
    color_noise_reduction_detail: float = Field(50.0, ge=0.0, le=100.0)
    color_noise_reduction_smoothness: float = Field(50.0, ge=0.0, le=100.0)

    def with_value(self, key: str, value: float) -> "DetailAdjustments":
        if key not in type(self).model_fields:
            raise KeyError(key)
        values = self.model_dump()
        values[key] = value
        return type(self).model_validate(values)


class EffectsAdjustments(BaseModel):
    """Film-grain and post-crop vignette controls."""

    vignette_midpoint: float = Field(50.0, ge=0.0, le=100.0)
    vignette_roundness: float = Field(0.0, ge=-100.0, le=100.0)
    vignette_feather: float = Field(50.0, ge=0.0, le=100.0)
    vignette_highlights: float = Field(0.0, ge=0.0, le=100.0)
    vignette_style: int = Field(0, ge=0, le=3)
    curve_refine_saturation: float = Field(0.0, ge=-100.0, le=100.0)
    grain_amount: float = Field(0.0, ge=0.0, le=100.0)
    grain_size: float = Field(25.0, ge=0.0, le=100.0)
    grain_roughness: float = Field(50.0, ge=0.0, le=100.0)

    def with_value(self, key: str, value: float) -> "EffectsAdjustments":
        if key not in type(self).model_fields:
            raise KeyError(key)
        values = self.model_dump()
        values[key] = value
        return type(self).model_validate(values)


class OpticsAdjustments(BaseModel):
    """Conservative local equivalents for Lightroom optics controls."""

    remove_chromatic_aberration: bool = False
    defringe_purple_amount: float = Field(0.0, ge=0.0, le=100.0)
    defringe_purple_hue_low: float = Field(30.0, ge=0.0, le=100.0)
    defringe_purple_hue_high: float = Field(70.0, ge=0.0, le=100.0)
    defringe_green_amount: float = Field(0.0, ge=0.0, le=100.0)
    defringe_green_hue_low: float = Field(40.0, ge=0.0, le=100.0)
    defringe_green_hue_high: float = Field(60.0, ge=0.0, le=100.0)

    def with_value(self, key: str, value: float | bool) -> "OpticsAdjustments":
        if key not in type(self).model_fields:
            raise KeyError(key)
        values = self.model_dump()
        values[key] = value
        return type(self).model_validate(values)


class TransformSettings(BaseModel):
    """Non-destructive geometry controls, expressed in Lightroom-like units."""

    vertical: float = Field(0.0, ge=-100.0, le=100.0)
    horizontal: float = Field(0.0, ge=-100.0, le=100.0)
    rotate: float = Field(0.0, ge=-45.0, le=45.0)
    scale: float = Field(100.0, ge=50.0, le=150.0)
    offset_x: float = Field(0.0, ge=-100.0, le=100.0)
    offset_y: float = Field(0.0, ge=-100.0, le=100.0)
    aspect: float = Field(0.0, ge=-100.0, le=100.0)

    def with_value(self, key: str, value: float) -> "TransformSettings":
        if key not in type(self).model_fields:
            raise KeyError(key)
        values = self.model_dump()
        values[key] = value
        return type(self).model_validate(values)


class CalibrationSettings(BaseModel):
    """Camera-calibration style primary controls for deterministic RGB input."""

    red_primary_hue: float = Field(0.0, ge=-100.0, le=100.0)
    red_primary_saturation: float = Field(0.0, ge=-100.0, le=100.0)
    green_primary_hue: float = Field(0.0, ge=-100.0, le=100.0)
    green_primary_saturation: float = Field(0.0, ge=-100.0, le=100.0)
    blue_primary_hue: float = Field(0.0, ge=-100.0, le=100.0)
    blue_primary_saturation: float = Field(0.0, ge=-100.0, le=100.0)

    def with_value(self, key: str, value: float) -> "CalibrationSettings":
        if key not in type(self).model_fields:
            raise KeyError(key)
        values = self.model_dump()
        values[key] = value
        return type(self).model_validate(values)


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
    vibrance: float = Field(0.0, ge=-100.0, le=100.0)
    clarity: float = Field(0.0, ge=-100.0, le=100.0)
    texture: float = Field(0.0, ge=-100.0, le=100.0)
    dehaze: float = Field(0.0, ge=-100.0, le=100.0)
    sharpen: float = Field(0.0, ge=0.0, le=100.0)

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
    detail: DetailAdjustments = Field(default_factory=DetailAdjustments)
    effects: EffectsAdjustments = Field(default_factory=EffectsAdjustments)
    optics: OpticsAdjustments = Field(default_factory=OpticsAdjustments)
    transform: TransformSettings = Field(default_factory=TransformSettings)
    calibration: CalibrationSettings = Field(default_factory=CalibrationSettings)
    masks: list[MaskLayer] = Field(default_factory=list)
    watermarks: list[WatermarkLayer] = Field(default_factory=list)

    def is_pristine(self) -> bool:
        return self == type(self)()

    def snapshot(self) -> "EditorState":
        return type(self).model_validate_json(self.model_dump_json())
