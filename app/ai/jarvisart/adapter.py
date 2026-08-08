from __future__ import annotations

from dataclasses import dataclass

from app.ai.jarvisart.schemas import JarvisArtNativePlan
from app.ai.jarvisart.support_matrix import operation_support
from app.ai.schemas import (
    CurveAdjustmentPlan, EditingPlan, GlobalAdjustment, HSLAdjustmentPlan,
    LocalAdjustmentPlan, LocalAdjustmentValues, MaskParameters, MaskRequest,
)
from app.core.editor_state import CurvePoint


_MASK_TOOL = {
    "sky": "create_sky_mask", "subject": "create_subject_mask", "semantic": "create_semantic_mask",
    "linear_gradient": "create_linear_gradient", "radial_gradient": "create_radial_gradient",
    "luminance_range": "create_luminance_mask", "color_range": "create_color_range_mask",
}
_CURVE_TOOL = {"rgb": "set_rgb_curve", "red": "set_red_curve", "green": "set_green_curve", "blue": "set_blue_curve"}
_LOCAL_MAP = {
    "LocalExposure2012": "exposure", "LocalContrast2012": "contrast", "LocalHighlights2012": "highlights",
    "LocalShadows2012": "shadows", "LocalWhites2012": "whites", "LocalBlacks2012": "blacks",
    "LocalTemperature": "temperature", "LocalTint": "tint", "LocalSaturation": "saturation",
    "LocalClarity2012": "clarity", "LocalTexture": "texture", "LocalDehaze": "dehaze",
}


@dataclass(frozen=True, slots=True)
class JarvisArtAdaptResult:
    plan: EditingPlan
    unsupported_operations: tuple[str, ...]


class JarvisArtAdapter:
    def adapt(self, native: JarvisArtNativePlan) -> JarvisArtAdaptResult:
        unsupported = [f"{item.operation}: {item.reason}" for item in native.unsupported_operations]
        globals_: list[GlobalAdjustment] = []
        for item in native.global_adjustments:
            support = operation_support(item.parameter)
            if not support.supported:
                unsupported.append(f"{item.parameter}: {support.reason}")
                continue
            if support.target is None:
                continue
            value = _adapt_native_value(item.parameter, item.value)
            globals_.append(GlobalAdjustment(tool=support.target, value=value))
        hsl = [HSLAdjustmentPlan(color=item.color, hue=item.hue, saturation=item.saturation, luminance=item.luminance) for item in native.hsl_adjustments]
        curves = [CurveAdjustmentPlan(tool=_CURVE_TOOL[item.channel], points=[CurvePoint(x=point.x / 255, y=point.y / 255) for point in item.points]) for item in native.curves]
        masks: list[MaskRequest] = []
        locals_: list[LocalAdjustment] = []
        for region in native.local_regions:
            mask = region.mask
            masks.append(MaskRequest(
                tool=_MASK_TOOL[mask.type], ref=mask.ref, name=mask.name,
                semantic_label=mask.semantic_label,
                parameters=MaskParameters.model_validate(mask.parameters), feather=mask.feather, inverted=mask.inverted,
            ))
            values: dict[str, float] = {}
            for item in region.adjustments:
                target = _LOCAL_MAP.get(item.parameter)
                if target is None:
                    unsupported.append(f"{item.parameter}: local Lightroom operation is not supported")
                    continue
                values[target] = item.value
            if values:
                locals_.append(LocalAdjustmentPlan(mask_ref=mask.ref, adjustments=LocalAdjustmentValues.model_validate(values)))
        return JarvisArtAdaptResult(
            EditingPlan(
                summary=native.summary, reasoning_summary=native.reasoning_summary,
                global_adjustments=globals_, hsl_adjustments=hsl, curve_adjustments=curves,
                requested_masks=masks, local_adjustments=locals_, confidence=native.confidence,
                needs_reinspection=False,
            ),
            tuple(dict.fromkeys(unsupported)),
        )


def _adapt_native_value(parameter: str, value: float) -> float:
    """Convert native Lightroom units only where the application uses another unit."""
    if parameter == "Temperature":
        # Lightroom supplies Kelvin while the editor's established manual
        # control is a relative -100..100 temperature shift around daylight.
        return max(-100.0, min(100.0, (value - 5500.0) / 25.0))
    if parameter == "Tint":
        return max(-100.0, min(100.0, value))
    return value
