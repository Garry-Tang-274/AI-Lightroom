from __future__ import annotations

import cv2
import numpy as np

from app.core.editor_state import EditorState, HSLColor, LocalAdjustments, ToneCurve
from app.core.masks import generate_mask
from app.core.watermarks import composite_watermarks


_HSL_CENTERS = {
    HSLColor.RED: 0.0,
    HSLColor.ORANGE: 28.0,
    HSLColor.YELLOW: 58.0,
    HSLColor.GREEN: 120.0,
    HSLColor.AQUA: 180.0,
    HSLColor.BLUE: 225.0,
    HSLColor.PURPLE: 275.0,
    HSLColor.MAGENTA: 325.0,
}


def render_image(source: np.ndarray, state: EditorState) -> np.ndarray:
    """Render an RGB uint8 source deterministically from a complete edit state."""
    if source.dtype != np.uint8 or source.ndim != 3 or source.shape[2] != 3:
        raise ValueError("source must be an RGB uint8 image")

    image = source.astype(np.float32) / 255.0
    basic = state.basic
    image = _white_balance(image, basic.temperature, basic.tint)
    image = _exposure(image, basic.exposure)
    image = _tone(
        image,
        basic.contrast,
        basic.highlights,
        basic.shadows,
        basic.whites,
        basic.blacks,
    )
    image = _saturation(image, basic.saturation, basic.vibrance)
    image = _hsl(image, state)
    image = _color_grading(image, state)
    image = _curve(image, state.curves.rgb)
    for channel, curve in enumerate((state.curves.red, state.curves.green, state.curves.blue)):
        image[..., channel] = _curve_values(image[..., channel], curve)
    image = _local_contrast(image, basic.clarity, basic.texture, basic.dehaze)
    image = _sharpen(image, basic.sharpen)
    image = _vignette(image, basic.vignette)
    for layer in state.masks:
        if not layer.enabled or layer.opacity <= 0:
            continue
        mask = generate_mask(source, layer)[..., None]
        if not np.any(mask):
            continue
        adjusted = _apply_local_adjustments(image, layer.adjustments)
        image = image * (1.0 - mask) + adjusted * mask
    rendered = np.clip(np.rint(image * 255.0), 0, 255).astype(np.uint8)
    return composite_watermarks(rendered, state.watermarks)


def _apply_local_adjustments(image: np.ndarray, local: LocalAdjustments) -> np.ndarray:
    adjusted = _white_balance(image, local.temperature, local.tint)
    adjusted = _exposure(adjusted, local.exposure)
    adjusted = _tone(
        adjusted,
        local.contrast,
        local.highlights,
        local.shadows,
        local.whites,
        local.blacks,
    )
    adjusted = _saturation(adjusted, local.saturation, local.vibrance)
    adjusted = _local_contrast(adjusted, local.clarity, local.texture, local.dehaze)
    adjusted = _sharpen(adjusted, local.sharpen)
    return adjusted


def _srgb_to_linear(image: np.ndarray) -> np.ndarray:
    return np.where(image <= 0.04045, image / 12.92, ((image + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(image: np.ndarray) -> np.ndarray:
    image = np.clip(image, 0.0, 1.0)
    return np.where(image <= 0.0031308, image * 12.92, 1.055 * image ** (1 / 2.4) - 0.055)


def _luminance(image: np.ndarray) -> np.ndarray:
    return image[..., 0] * 0.2126 + image[..., 1] * 0.7152 + image[..., 2] * 0.0722


def _white_balance(image: np.ndarray, temperature: float, tint: float) -> np.ndarray:
    if temperature == 0 and tint == 0:
        return image
    temp = temperature / 100.0
    tint_value = tint / 100.0
    gains = np.array(
        [1.0 + 0.16 * temp + 0.05 * tint_value, 1.0 - 0.09 * tint_value, 1.0 - 0.16 * temp + 0.05 * tint_value],
        dtype=np.float32,
    )
    balanced = image * gains
    old_luma = _luminance(image)[..., None]
    new_luma = np.maximum(_luminance(balanced)[..., None], 1e-5)
    return np.clip(balanced * (old_luma / new_luma), 0.0, 1.0)


def _exposure(image: np.ndarray, exposure: float) -> np.ndarray:
    if exposure == 0:
        return image
    linear = _srgb_to_linear(image)
    return _linear_to_srgb(linear * (2.0**exposure))


def _tone(
    image: np.ndarray,
    contrast: float,
    highlights: float,
    shadows: float,
    whites: float,
    blacks: float,
) -> np.ndarray:
    if contrast:
        strength = contrast / 100.0
        slope = 2.0 ** (strength * 1.35)
        image = 0.5 + (image - 0.5) * slope

    luma = _luminance(np.clip(image, 0, 1))
    delta = np.zeros_like(luma)
    if highlights:
        weight = _smoothstep(0.42, 1.0, luma)
        direction_room = (1.0 - luma) if highlights > 0 else luma
        delta += (highlights / 100.0) * 0.42 * weight * direction_room
    if shadows:
        weight = 1.0 - _smoothstep(0.0, 0.58, luma)
        direction_room = (1.0 - luma) if shadows > 0 else luma
        delta += (shadows / 100.0) * 0.52 * weight * direction_room
    if whites:
        weight = _smoothstep(0.68, 1.0, luma)
        direction_room = (1.0 - luma) if whites > 0 else luma
        delta += (whites / 100.0) * 0.35 * weight * direction_room
    if blacks:
        weight = 1.0 - _smoothstep(0.0, 0.32, luma)
        direction_room = (1.0 - luma) if blacks > 0 else luma
        delta += (blacks / 100.0) * 0.35 * weight * direction_room

    if np.any(delta):
        ratio = (luma + delta) / np.maximum(luma, 1e-4)
        image = image * ratio[..., None]
        near_black = luma < 1e-4
        if np.any(near_black):
            image[near_black] = np.maximum(delta[near_black, None], 0)
    return np.clip(image, 0.0, 1.0)


def _smoothstep(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    x = np.clip((values - edge0) / max(edge1 - edge0, 1e-6), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _saturation(image: np.ndarray, saturation: float, vibrance: float) -> np.ndarray:
    if saturation == 0 and vibrance == 0:
        return image
    hsv = cv2.cvtColor(np.clip(image, 0, 1), cv2.COLOR_RGB2HSV)
    current = hsv[..., 1]
    if saturation:
        if saturation >= 0:
            current += (1.0 - current) * (saturation / 100.0)
        else:
            current *= 1.0 + saturation / 100.0
    if vibrance:
        selective = (1.0 - current) ** 1.5
        if vibrance >= 0:
            current += (1.0 - current) * selective * (vibrance / 100.0) * 0.85
        else:
            current *= 1.0 + (vibrance / 100.0) * selective * 0.75
    hsv[..., 1] = np.clip(current, 0.0, 1.0)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def _hsl(image: np.ndarray, state: EditorState) -> np.ndarray:
    if all(values.hue == values.saturation == values.luminance == 0 for values in state.hsl.values()):
        return image
    hsv = cv2.cvtColor(np.clip(image, 0, 1), cv2.COLOR_RGB2HSV)
    hue_original = hsv[..., 0].copy()
    sat_original = hsv[..., 1].copy()
    for color, adjustment in state.hsl.items():
        center = _HSL_CENTERS[color]
        distance = np.abs((hue_original - center + 180.0) % 360.0 - 180.0)
        weight = np.clip(1.0 - distance / 48.0, 0.0, 1.0)
        weight = weight * weight * (3.0 - 2.0 * weight)
        if adjustment.hue:
            hsv[..., 0] = (hsv[..., 0] + weight * adjustment.hue * 0.35) % 360.0
        if adjustment.saturation:
            amount = adjustment.saturation / 100.0
            target_delta = (1.0 - hsv[..., 1]) * amount if amount > 0 else hsv[..., 1] * amount
            hsv[..., 1] += weight * target_delta
        if adjustment.luminance:
            amount = adjustment.luminance / 100.0
            room = (1.0 - hsv[..., 2]) if amount > 0 else hsv[..., 2]
            hsv[..., 2] += weight * room * amount * 0.65
    hsv[..., 1] = np.clip(hsv[..., 1], 0.0, 1.0)
    hsv[..., 2] = np.clip(hsv[..., 2], 0.0, 1.0)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def _color_grading(image: np.ndarray, state: EditorState) -> np.ndarray:
    grading = state.color_grading
    if all(wheel.saturation == 0 and wheel.luminance == 0 for wheel in (grading.shadows, grading.midtones, grading.highlights)):
        return image
    luma = _luminance(image)
    balance = grading.balance / 500.0
    shadow_weight = 1.0 - _smoothstep(0.12 + balance, 0.55 + balance, luma)
    highlight_weight = _smoothstep(0.45 + balance, 0.88 + balance, luma)
    mid_weight = np.clip(1.0 - shadow_weight - highlight_weight, 0.0, 1.0)
    output = image.copy()
    for wheel, weight in (
        (grading.shadows, shadow_weight),
        (grading.midtones, mid_weight),
        (grading.highlights, highlight_weight),
    ):
        if wheel.saturation:
            hsv_color = np.array([[[wheel.hue, wheel.saturation / 100.0, 1.0]]], dtype=np.float32)
            color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2RGB)[0, 0]
            output = output * (1.0 - weight[..., None] * wheel.saturation / 500.0) + color * weight[..., None] * wheel.saturation / 500.0
        if wheel.luminance:
            output += weight[..., None] * (wheel.luminance / 100.0) * 0.12
    return np.clip(output, 0.0, 1.0)


def _curve(image: np.ndarray, curve: ToneCurve) -> np.ndarray:
    if _curve_is_identity(curve):
        return image
    return _curve_values(image, curve)


def _curve_values(values: np.ndarray, curve: ToneCurve) -> np.ndarray:
    if _curve_is_identity(curve):
        return values
    xs = np.asarray([point.x for point in curve.points], dtype=np.float32)
    ys = np.asarray([point.y for point in curve.points], dtype=np.float32)
    return np.interp(np.clip(values, 0, 1), xs, ys).astype(np.float32)


def _curve_is_identity(curve: ToneCurve) -> bool:
    return len(curve.points) == 2 and curve.points[0].x == curve.points[0].y == 0 and curve.points[1].x == curve.points[1].y == 1


def _local_contrast(image: np.ndarray, clarity: float, texture: float, dehaze: float) -> np.ndarray:
    output = image
    if texture:
        fine = cv2.GaussianBlur(output, (0, 0), 1.0)
        output = output + (output - fine) * (texture / 100.0) * 0.55
    if clarity:
        luma = _luminance(np.clip(output, 0, 1))
        radius = max(3.0, min(output.shape[:2]) / 90.0)
        base = cv2.GaussianBlur(luma, (0, 0), radius)
        detail = (luma - base) * (clarity / 100.0) * 0.9
        weight = 1.0 - np.abs(luma - 0.5) * 1.4
        output += (detail * np.clip(weight, 0.0, 1.0))[..., None]
    if dehaze:
        amount = dehaze / 100.0
        luma = _luminance(np.clip(output, 0, 1))
        low_frequency = cv2.GaussianBlur(luma, (0, 0), max(5.0, min(output.shape[:2]) / 45.0))
        output = (output - low_frequency[..., None] * amount * 0.16) * (1.0 + amount * 0.22)
    return np.clip(output, 0.0, 1.0)


def _sharpen(image: np.ndarray, sharpen: float) -> np.ndarray:
    if sharpen <= 0:
        return image
    blurred = cv2.GaussianBlur(image, (0, 0), 0.8)
    detail = image - blurred
    luma_detail = np.abs(_luminance(detail))
    threshold = 0.004
    mask = _smoothstep(threshold, threshold * 4.0, luma_detail)[..., None]
    return np.clip(image + detail * mask * (sharpen / 100.0) * 1.4, 0.0, 1.0)


def _vignette(image: np.ndarray, vignette: float) -> np.ndarray:
    if vignette == 0:
        return image
    height, width = image.shape[:2]
    y, x = np.ogrid[-1.0:1.0:complex(height), -1.0:1.0:complex(width)]
    radius = np.sqrt(x * x + y * y)
    edge = _smoothstep(0.35, 1.25, radius)
    amount = vignette / 100.0
    if amount < 0:
        factor = 1.0 + amount * 0.65 * edge
        return np.clip(image * factor[..., None], 0.0, 1.0)
    return np.clip(image + (1.0 - image) * (amount * 0.45 * edge[..., None]), 0.0, 1.0)
