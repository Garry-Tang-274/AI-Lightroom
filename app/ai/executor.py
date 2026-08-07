from __future__ import annotations

from dataclasses import dataclass

from app.ai.schemas import EditingPlan
from app.core.editor_state import (
    CurveSettings,
    EditorState,
    HSLAdjustment,
    MaskLayer,
    MaskType,
    ToneCurve,
)


GLOBAL_FIELD_MAP = {
    "set_exposure": "exposure",
    "set_contrast": "contrast",
    "set_highlights": "highlights",
    "set_shadows": "shadows",
    "set_whites": "whites",
    "set_blacks": "blacks",
    "set_temperature": "temperature",
    "set_tint": "tint",
    "set_saturation": "saturation",
    "set_vibrance": "vibrance",
    "set_clarity": "clarity",
    "set_texture": "texture",
    "set_dehaze": "dehaze",
    "set_sharpen": "sharpen",
    "set_vignette": "vignette",
}

CURVE_FIELD_MAP = {
    "set_rgb_curve": "rgb",
    "set_red_curve": "red",
    "set_green_curve": "green",
    "set_blue_curve": "blue",
}

MASK_TYPE_MAP = {
    "create_linear_gradient": MaskType.LINEAR_GRADIENT,
    "create_radial_gradient": MaskType.RADIAL_GRADIENT,
    "create_luminance_mask": MaskType.LUMINANCE_RANGE,
    "create_color_range_mask": MaskType.COLOR_RANGE,
    "create_sky_mask": MaskType.SKY,
    "create_subject_mask": MaskType.SUBJECT,
    "create_semantic_mask": MaskType.SEMANTIC,
}


@dataclass(slots=True)
class ExecutionResult:
    state: EditorState
    changed_fields: list[str]
    created_masks: list[str]


def apply_editing_plan(state: EditorState, plan: EditingPlan, selected_mask_id: str | None = None) -> ExecutionResult:
    updated = state.snapshot()
    changed: list[str] = []
    created: list[str] = []
    refs: dict[str, str] = {}

    for adjustment in plan.global_adjustments:
        field = GLOBAL_FIELD_MAP[adjustment.tool]
        updated.basic = updated.basic.with_value(field, adjustment.value)
        changed.append(f"全局 {field} = {adjustment.value:+g}")

    for adjustment in plan.hsl_adjustments:
        updated.hsl[adjustment.color] = HSLAdjustment(
            hue=adjustment.hue,
            saturation=adjustment.saturation,
            luminance=adjustment.luminance,
        )
        changed.append(f"HSL {adjustment.color.value}")

    for adjustment in plan.curve_adjustments:
        channel = CURVE_FIELD_MAP[adjustment.tool]
        setattr(updated.curves, channel, ToneCurve(points=adjustment.points))
        changed.append(f"{channel.upper()} 曲线")

    for request in plan.requested_masks:
        layer = MaskLayer(
            name=request.name,
            type=MASK_TYPE_MAP[request.tool],
            semantic_label=request.semantic_label,
            parameters=request.parameters.model_dump(exclude_none=True),
            feather=request.feather,
            inverted=request.inverted,
        )
        updated.masks.append(layer)
        refs[request.ref] = layer.id
        created.append(layer.name)

    for local in plan.local_adjustments:
        layer = _resolve_mask(updated, local.mask_ref, refs, selected_mask_id)
        if layer is None:
            raise ValueError(f"AI plan referenced an unknown mask: {local.mask_ref}")
        values = local.adjustments.model_dump(exclude_none=True)
        for key, value in values.items():
            layer.adjustments = layer.adjustments.with_value(key, value)
            changed.append(f"{layer.name} {key} = {value:+g}")

    return ExecutionResult(updated, changed, created)


def _resolve_mask(
    state: EditorState,
    reference: str,
    refs: dict[str, str],
    selected_mask_id: str | None,
) -> MaskLayer | None:
    target = refs.get(reference, reference)
    if reference == "selected" and selected_mask_id:
        target = selected_mask_id
    for layer in state.masks:
        if layer.id == target or layer.name == target:
            return layer
    return None

