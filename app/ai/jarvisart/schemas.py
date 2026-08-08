from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NativeStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class NativeAdjustment(NativeStrictModel):
    parameter: str
    value: float


class NativeHSLAdjustment(NativeStrictModel):
    color: Literal["red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"]
    hue: float = 0
    saturation: float = 0
    luminance: float = 0


class NativeCurvePoint(NativeStrictModel):
    x: float = Field(ge=0, le=255)
    y: float = Field(ge=0, le=255)


class NativeCurve(NativeStrictModel):
    channel: Literal["rgb", "red", "green", "blue"]
    points: list[NativeCurvePoint] = Field(min_length=2)


class NativeMask(NativeStrictModel):
    ref: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: Literal["sky", "subject", "semantic", "linear_gradient", "radial_gradient", "luminance_range", "color_range"]
    semantic_label: str | None = None
    parameters: dict[str, float] = Field(default_factory=dict)
    feather: float = Field(default=0.25, ge=0, le=1)
    inverted: bool = False


class NativeLocalRegion(NativeStrictModel):
    mask: NativeMask
    adjustments: list[NativeAdjustment] = Field(default_factory=list)


class UnsupportedNativeOperation(NativeStrictModel):
    operation: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class JarvisArtNativePlan(NativeStrictModel):
    """Lossless boundary for official JarvisArt Lightroom-style output."""

    summary: str = Field(min_length=1)
    reasoning_summary: str = Field(min_length=1)
    global_adjustments: list[NativeAdjustment] = Field(default_factory=list)
    hsl_adjustments: list[NativeHSLAdjustment] = Field(default_factory=list)
    curves: list[NativeCurve] = Field(default_factory=list)
    local_regions: list[NativeLocalRegion] = Field(default_factory=list)
    unsupported_operations: list[UnsupportedNativeOperation] = Field(default_factory=list)
    confidence: float = Field(default=0.75, ge=0, le=1)
