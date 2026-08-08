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
    "Temperature": SupportMatrixEntry("Temperature", None, False, "absolute Kelvin temperature has no safe relative mapping"),
    "LensBlur": SupportMatrixEntry("LensBlur", None, False, "AI Lightroom has no Lens Blur renderer"),
    "CameraCalibration": SupportMatrixEntry("CameraCalibration", None, False, "camera calibration is not implemented"),
    "PointColors": SupportMatrixEntry("PointColors", None, False, "point color editing is not implemented"),
    "GenerativeRemove": SupportMatrixEntry("GenerativeRemove", None, False, "generative editing is intentionally disabled"),
}


def operation_support(native_operation: str) -> SupportMatrixEntry:
    return SUPPORT_MATRIX.get(
        native_operation,
        SupportMatrixEntry(native_operation, None, False, "unknown JarvisArt Lightroom operation"),
    )
