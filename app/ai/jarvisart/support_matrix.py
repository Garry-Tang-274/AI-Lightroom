from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SupportMatrixEntry:
    native_operation: str
    target: str | None
    supported: bool
    reason: str = ""


# This is intentionally data, not scattered provider conditionals. It records
# every native Lightroom operation that the adapter is prepared to encounter.
SUPPORT_MATRIX: dict[str, SupportMatrixEntry] = {
    "Exposure2012": SupportMatrixEntry("Exposure2012", "set_exposure", True),
    "Contrast2012": SupportMatrixEntry("Contrast2012", "set_contrast", True),
    "Highlights2012": SupportMatrixEntry("Highlights2012", "set_highlights", True),
    "Shadows2012": SupportMatrixEntry("Shadows2012", "set_shadows", True),
    "Whites2012": SupportMatrixEntry("Whites2012", "set_whites", True),
    "Blacks2012": SupportMatrixEntry("Blacks2012", "set_blacks", True),
    "IncrementalTemperature": SupportMatrixEntry("IncrementalTemperature", "set_temperature", True),
    "IncrementalTint": SupportMatrixEntry("IncrementalTint", "set_tint", True),
    "Saturation": SupportMatrixEntry("Saturation", "set_saturation", True),
    "Vibrance": SupportMatrixEntry("Vibrance", "set_vibrance", True),
    "Clarity2012": SupportMatrixEntry("Clarity2012", "set_clarity", True),
    "Texture": SupportMatrixEntry("Texture", "set_texture", True),
    "Dehaze": SupportMatrixEntry("Dehaze", "set_dehaze", True),
    "Sharpness": SupportMatrixEntry("Sharpness", "set_sharpen", True),
    "PostCropVignetteAmount": SupportMatrixEntry("PostCropVignetteAmount", "set_vignette", True),
    "Temperature": SupportMatrixEntry("Temperature", "set_temperature", True),
    "Tint": SupportMatrixEntry("Tint", "set_tint", True),
    "SharpenRadius": SupportMatrixEntry("SharpenRadius", "set_sharpen_radius", True),
    "SharpenDetail": SupportMatrixEntry("SharpenDetail", "set_sharpen_detail", True),
    "SharpenEdgeMasking": SupportMatrixEntry("SharpenEdgeMasking", "set_sharpen_masking", True),
    "LuminanceSmoothing": SupportMatrixEntry("LuminanceSmoothing", "set_luminance_noise_reduction", True),
    "LuminanceNoiseReductionDetail": SupportMatrixEntry("LuminanceNoiseReductionDetail", "set_luminance_noise_reduction_detail", True),
    "LuminanceNoiseReductionContrast": SupportMatrixEntry("LuminanceNoiseReductionContrast", "set_luminance_noise_reduction_contrast", True),
    "ColorNoiseReduction": SupportMatrixEntry("ColorNoiseReduction", "set_color_noise_reduction", True),
    "ColorNoiseReductionDetail": SupportMatrixEntry("ColorNoiseReductionDetail", "set_color_noise_reduction_detail", True),
    "ColorNoiseReductionSmoothness": SupportMatrixEntry("ColorNoiseReductionSmoothness", "set_color_noise_reduction_smoothness", True),
    "PostCropVignetteMidpoint": SupportMatrixEntry("PostCropVignetteMidpoint", "set_vignette_midpoint", True),
    "PostCropVignetteRoundness": SupportMatrixEntry("PostCropVignetteRoundness", "set_vignette_roundness", True),
    "PostCropVignetteFeather": SupportMatrixEntry("PostCropVignetteFeather", "set_vignette_feather", True),
    "PostCropVignetteHighlightContrast": SupportMatrixEntry("PostCropVignetteHighlightContrast", "set_vignette_highlights", True),
    "PostCropVignetteStyle": SupportMatrixEntry("PostCropVignetteStyle", "set_vignette_style", True),
    "CurveRefineSaturation": SupportMatrixEntry("CurveRefineSaturation", "set_curve_refine_saturation", True),
    "GrainAmount": SupportMatrixEntry("GrainAmount", "set_grain_amount", True),
    "GrainSize": SupportMatrixEntry("GrainSize", "set_grain_size", True),
    "GrainFrequency": SupportMatrixEntry("GrainFrequency", "set_grain_roughness", True),
    "RemoveChromaticAberration": SupportMatrixEntry("RemoveChromaticAberration", "set_remove_chromatic_aberration", True),
    "DefringePurpleAmount": SupportMatrixEntry("DefringePurpleAmount", "set_defringe_purple_amount", True),
    "DefringePurpleHueLo": SupportMatrixEntry("DefringePurpleHueLo", "set_defringe_purple_hue_low", True),
    "DefringePurpleHueHi": SupportMatrixEntry("DefringePurpleHueHi", "set_defringe_purple_hue_high", True),
    "DefringeGreenAmount": SupportMatrixEntry("DefringeGreenAmount", "set_defringe_green_amount", True),
    "DefringeGreenHueLo": SupportMatrixEntry("DefringeGreenHueLo", "set_defringe_green_hue_low", True),
    "DefringeGreenHueHi": SupportMatrixEntry("DefringeGreenHueHi", "set_defringe_green_hue_high", True),
    "PerspectiveVertical": SupportMatrixEntry("PerspectiveVertical", "set_transform_vertical", True),
    "PerspectiveHorizontal": SupportMatrixEntry("PerspectiveHorizontal", "set_transform_horizontal", True),
    "PerspectiveRotate": SupportMatrixEntry("PerspectiveRotate", "set_transform_rotate", True),
    "PerspectiveScale": SupportMatrixEntry("PerspectiveScale", "set_transform_scale", True),
    "PerspectiveX": SupportMatrixEntry("PerspectiveX", "set_transform_offset_x", True),
    "PerspectiveY": SupportMatrixEntry("PerspectiveY", "set_transform_offset_y", True),
    "PerspectiveAspect": SupportMatrixEntry("PerspectiveAspect", "set_transform_aspect", True),
    "RedHue": SupportMatrixEntry("RedHue", "set_calibration_red_primary_hue", True),
    "RedSaturation": SupportMatrixEntry("RedSaturation", "set_calibration_red_primary_saturation", True),
    "GreenHue": SupportMatrixEntry("GreenHue", "set_calibration_green_primary_hue", True),
    "GreenSaturation": SupportMatrixEntry("GreenSaturation", "set_calibration_green_primary_saturation", True),
    "BlueHue": SupportMatrixEntry("BlueHue", "set_calibration_blue_primary_hue", True),
    "BlueSaturation": SupportMatrixEntry("BlueSaturation", "set_calibration_blue_primary_saturation", True),
    "ColorGradeShadowHue": SupportMatrixEntry("ColorGradeShadowHue", "set_color_grade_shadow_hue", True),
    "ColorGradeShadowSat": SupportMatrixEntry("ColorGradeShadowSat", "set_color_grade_shadow_saturation", True),
    "ColorGradeShadowLum": SupportMatrixEntry("ColorGradeShadowLum", "set_color_grade_shadow_luminance", True),
    "ColorGradeMidtoneHue": SupportMatrixEntry("ColorGradeMidtoneHue", "set_color_grade_midtone_hue", True),
    "ColorGradeMidtoneSat": SupportMatrixEntry("ColorGradeMidtoneSat", "set_color_grade_midtone_saturation", True),
    "ColorGradeMidtoneLum": SupportMatrixEntry("ColorGradeMidtoneLum", "set_color_grade_midtone_luminance", True),
    "ColorGradeHighlightHue": SupportMatrixEntry("ColorGradeHighlightHue", "set_color_grade_highlight_hue", True),
    "ColorGradeHighlightSat": SupportMatrixEntry("ColorGradeHighlightSat", "set_color_grade_highlight_saturation", True),
    "ColorGradeHighlightLum": SupportMatrixEntry("ColorGradeHighlightLum", "set_color_grade_highlight_luminance", True),
    "ColorGradeBlending": SupportMatrixEntry("ColorGradeBlending", "set_color_grade_blending", True),
    "ColorGradeBalance": SupportMatrixEntry("ColorGradeBalance", "set_color_grade_balance", True),
    "SplitToningShadowHue": SupportMatrixEntry("SplitToningShadowHue", "set_color_grade_shadow_hue", True),
    "SplitToningShadowSaturation": SupportMatrixEntry("SplitToningShadowSaturation", "set_color_grade_shadow_saturation", True),
    "SplitToningHighlightHue": SupportMatrixEntry("SplitToningHighlightHue", "set_color_grade_highlight_hue", True),
    "SplitToningHighlightSaturation": SupportMatrixEntry("SplitToningHighlightSaturation", "set_color_grade_highlight_saturation", True),
    "SplitToningBalance": SupportMatrixEntry("SplitToningBalance", "set_color_grade_balance", True),
    # These values label or support a Develop preset but do not alter pixels on
    # their own. Treat them as preserved metadata, never as an error.
    "ProcessVersion": SupportMatrixEntry("ProcessVersion", None, True),
    "WhiteBalance": SupportMatrixEntry("WhiteBalance", None, True),
    "ToneCurveName2012": SupportMatrixEntry("ToneCurveName2012", None, True),
    "AutoToneDigest": SupportMatrixEntry("AutoToneDigest", None, True),
    "AutoToneDigestNoSat": SupportMatrixEntry("AutoToneDigestNoSat", None, True),
    "HasSettings": SupportMatrixEntry("HasSettings", None, True),
    "ParametricShadowSplit": SupportMatrixEntry("ParametricShadowSplit", None, True),
    "ParametricMidtoneSplit": SupportMatrixEntry("ParametricMidtoneSplit", None, True),
    "ParametricHighlightSplit": SupportMatrixEntry("ParametricHighlightSplit", None, True),
    "LensBlur": SupportMatrixEntry("LensBlur", None, False, "AI Lightroom has no Lens Blur renderer"),
    "CameraCalibration": SupportMatrixEntry("CameraCalibration", None, False, "nested camera calibration profile is not supported; use the explicit primary controls"),
    "PointColors": SupportMatrixEntry("PointColors", None, False, "point color editing is not implemented"),
    "GenerativeRemove": SupportMatrixEntry("GenerativeRemove", None, False, "generative editing is intentionally disabled"),
}


def operation_support(native_operation: str) -> SupportMatrixEntry:
    return SUPPORT_MATRIX.get(
        native_operation,
        SupportMatrixEntry(native_operation, None, False, "unknown JarvisArt Lightroom operation"),
    )
