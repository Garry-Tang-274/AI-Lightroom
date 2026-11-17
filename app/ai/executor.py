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
    "set_exposure": ("basic", "exposure"),
    "set_contrast": ("basic", "contrast"),
    "set_highlights": ("basic", "highlights"),
    "set_shadows": ("basic", "shadows"),
    "set_whites": ("basic", "whites"),
    "set_blacks": ("basic", "blacks"),
    "set_temperature": ("basic", "temperature"),
    "set_tint": ("basic", "tint"),
    "set_saturation": ("basic", "saturation"),
    "set_vibrance": ("basic", "vibrance"),
    "set_clarity": ("basic", "clarity"),
    "set_texture": ("basic", "texture"),
    "set_dehaze": ("basic", "dehaze"),
    "set_sharpen": ("basic", "sharpen"),
    "set_vignette": ("basic", "vignette"),
    "set_sharpen_radius": ("detail", "sharpen_radius"),
    "set_sharpen_detail": ("detail", "sharpen_detail"),
    "set_sharpen_masking": ("detail", "sharpen_masking"),
    "set_luminance_noise_reduction": ("detail", "luminance_noise_reduction"),
    "set_luminance_noise_reduction_detail": ("detail", "luminance_noise_reduction_detail"),
    "set_luminance_noise_reduction_contrast": ("detail", "luminance_noise_reduction_contrast"),
    "set_color_noise_reduction": ("detail", "color_noise_reduction"),
    "set_color_noise_reduction_detail": ("detail", "color_noise_reduction_detail"),
    "set_color_noise_reduction_smoothness": ("detail", "color_noise_reduction_smoothness"),
    "set_vignette_midpoint": ("effects", "vignette_midpoint"),
    "set_vignette_roundness": ("effects", "vignette_roundness"),
    "set_vignette_feather": ("effects", "vignette_feather"),
    "set_vignette_highlights": ("effects", "vignette_highlights"),
    "set_vignette_style": ("effects", "vignette_style"),
    "set_curve_refine_saturation": ("effects", "curve_refine_saturation"),
    "set_grain_amount": ("effects", "grain_amount"),
    "set_grain_size": ("effects", "grain_size"),
    "set_grain_roughness": ("effects", "grain_roughness"),
    "set_remove_chromatic_aberration": ("optics", "remove_chromatic_aberration"),
    "set_defringe_purple_amount": ("optics", "defringe_purple_amount"),
    "set_defringe_purple_hue_low": ("optics", "defringe_purple_hue_low"),
    "set_defringe_purple_hue_high": ("optics", "defringe_purple_hue_high"),
    "set_defringe_green_amount": ("optics", "defringe_green_amount"),
    "set_defringe_green_hue_low": ("optics", "defringe_green_hue_low"),
    "set_defringe_green_hue_high": ("optics", "defringe_green_hue_high"),
    "set_transform_vertical": ("transform", "vertical"),
    "set_transform_horizontal": ("transform", "horizontal"),
    "set_transform_rotate": ("transform", "rotate"),
    "set_transform_scale": ("transform", "scale"),
    "set_transform_offset_x": ("transform", "offset_x"),
    "set_transform_offset_y": ("transform", "offset_y"),
    "set_transform_aspect": ("transform", "aspect"),
    "set_calibration_red_primary_hue": ("calibration", "red_primary_hue"),
    "set_calibration_red_primary_saturation": ("calibration", "red_primary_saturation"),
    "set_calibration_green_primary_hue": ("calibration", "green_primary_hue"),
    "set_calibration_green_primary_saturation": ("calibration", "green_primary_saturation"),
    "set_calibration_blue_primary_hue": ("calibration", "blue_primary_hue"),
    "set_calibration_blue_primary_saturation": ("calibration", "blue_primary_saturation"),
    "set_color_grade_shadow_hue": ("color_grading", "shadows", "hue"),
    "set_color_grade_shadow_saturation": ("color_grading", "shadows", "saturation"),
    "set_color_grade_shadow_luminance": ("color_grading", "shadows", "luminance"),
    "set_color_grade_midtone_hue": ("color_grading", "midtones", "hue"),
    "set_color_grade_midtone_saturation": ("color_grading", "midtones", "saturation"),
    "set_color_grade_midtone_luminance": ("color_grading", "midtones", "luminance"),
    "set_color_grade_highlight_hue": ("color_grading", "highlights", "hue"),
    "set_color_grade_highlight_saturation": ("color_grading", "highlights", "saturation"),
    "set_color_grade_highlight_luminance": ("color_grading", "highlights", "luminance"),
    "set_color_grade_blending": ("color_grading", "blending"),
    "set_color_grade_balance": ("color_grading", "balance"),
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
        target = GLOBAL_FIELD_MAP[adjustment.tool]
        section, field, *nested = target
        if nested:
            wheel = getattr(updated.color_grading, field)
            if getattr(wheel, nested[0]) == adjustment.value:
                continue
            values = wheel.model_dump()
            values[nested[0]] = adjustment.value
            setattr(updated.color_grading, field, type(wheel).model_validate(values))
        elif section == "color_grading":
            if getattr(updated.color_grading, field) == adjustment.value:
                continue
            values = updated.color_grading.model_dump()
            values[field] = adjustment.value
            updated.color_grading = type(updated.color_grading).model_validate(values)
        else:
            values = getattr(updated, section)
            if field == "remove_chromatic_aberration":
                value = bool(round(adjustment.value))
            elif field == "vignette_style":
                value = int(round(adjustment.value))
            else:
                value = adjustment.value
            if getattr(values, field) == value:
                continue
            setattr(updated, section, values.with_value(field, value))
        changed.append(f"{section} {'.'.join((field, *nested))} = {adjustment.value:+g}")

    for adjustment in plan.hsl_adjustments:
        value = HSLAdjustment(
            hue=adjustment.hue,
            saturation=adjustment.saturation,
            luminance=adjustment.luminance,
        )
        if updated.hsl[adjustment.color] == value:
            continue
        updated.hsl[adjustment.color] = value
        changed.append(f"HSL {adjustment.color.value}")

    for adjustment in plan.curve_adjustments:
        channel = CURVE_FIELD_MAP[adjustment.tool]
        curve = ToneCurve(points=adjustment.points)
        if getattr(updated.curves, channel) == curve:
            continue
        setattr(updated.curves, channel, curve)
        changed.append(f"{channel.upper()} 曲线")

    for request in plan.requested_masks:
        if request.ref in refs:
            raise ValueError(f"AI plan contains a duplicate mask reference: {request.ref}")
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
            if getattr(layer.adjustments, key) == value:
                continue
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
