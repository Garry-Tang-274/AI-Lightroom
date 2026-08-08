from __future__ import annotations

import cv2
import numpy as np

from app.core.editor_state import (
    DetailAdjustments,
    EditorState,
    EffectsAdjustments,
    HSLColor,
    LocalAdjustments,
    OpticsAdjustments,
    ToneCurve,
    TransformSettings,
)
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
    image = _transform_geometry(image, state.transform)
    image = _calibrate_primaries(image, state)
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
    image = _saturation(image, state.effects.curve_refine_saturation, 0.0)
    image = _local_contrast(image, basic.clarity, basic.texture, basic.dehaze)
    image = _reduce_noise(image, state.detail)
    image = _sharpen(image, basic.sharpen, state.detail)
    image = _defringe(image, state.optics)
    image = _vignette(image, basic.vignette, state.effects)
    image = _grain(image, state.effects)
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


def _sharpen(image: np.ndarray, sharpen: float, detail_settings: DetailAdjustments | None = None) -> np.ndarray:
    if sharpen <= 0:
        return image
    settings = detail_settings or DetailAdjustments()
    blurred = cv2.GaussianBlur(image, (0, 0), settings.sharpen_radius)
    detail = image - blurred
    luma_detail = np.abs(_luminance(detail))
    threshold = 0.010 - settings.sharpen_detail / 100.0 * 0.008
    mask = _smoothstep(threshold, threshold * 4.0, luma_detail)[..., None]
    if settings.sharpen_masking:
        luma = _luminance(image)
        edge = np.abs(luma - cv2.GaussianBlur(luma, (0, 0), 1.2))
        edge_mask = _smoothstep(0.004 + settings.sharpen_masking / 100.0 * 0.030, 0.10, edge)[..., None]
        mask *= edge_mask
    amount = 0.65 + settings.sharpen_detail / 100.0 * 0.95
    return np.clip(image + detail * mask * (sharpen / 100.0) * amount, 0.0, 1.0)


def _vignette(image: np.ndarray, vignette: float, effects: EffectsAdjustments | None = None) -> np.ndarray:
    if vignette == 0:
        return image
    settings = effects or EffectsAdjustments()
    height, width = image.shape[:2]
    y, x = np.ogrid[-1.0:1.0:complex(height), -1.0:1.0:complex(width)]
    aspect = width / max(height, 1)
    roundness = settings.vignette_roundness / 100.0
    x_scale = 1.0 + roundness * 0.35
    y_scale = 1.0 - roundness * 0.35
    radius = np.sqrt((x / max(x_scale, 0.2)) ** 2 + (y * aspect / max(y_scale, 0.2)) ** 2)
    start = 0.12 + settings.vignette_midpoint / 100.0 * 0.65
    end = start + 0.06 + settings.vignette_feather / 100.0 * 0.75
    edge = _smoothstep(start, end, radius)
    amount = vignette / 100.0
    if amount < 0:
        factor = 1.0 + amount * 0.65 * edge
        style_highlight_protection = 30.0 if settings.vignette_style == 1 else 0.0
        if settings.vignette_highlights or style_highlight_protection:
            highlight_protection = _smoothstep(0.55, 1.0, _luminance(image))
            protection = max(settings.vignette_highlights, style_highlight_protection)
            factor = factor + (1.0 - factor) * highlight_protection * protection / 100.0
        if settings.vignette_style == 2:
            # Color Priority keeps edge saturation from collapsing under a
            # dark vignette, approximating Lightroom's color-priority style.
            hsv = cv2.cvtColor(np.clip(image, 0, 1), cv2.COLOR_RGB2HSV)
            hsv[..., 1] *= 1.0 + edge * 0.08
            image = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        return np.clip(image * factor[..., None], 0.0, 1.0)
    return np.clip(image + (1.0 - image) * (amount * 0.45 * edge[..., None]), 0.0, 1.0)


def _reduce_noise(image: np.ndarray, settings: DetailAdjustments) -> np.ndarray:
    if settings.luminance_noise_reduction <= 0 and settings.color_noise_reduction <= 0:
        return image
    output = image.copy()
    if settings.color_noise_reduction > 0:
        lab = cv2.cvtColor(np.clip(output, 0, 1), cv2.COLOR_RGB2LAB)
        sigma = 0.5 + settings.color_noise_reduction / 100.0 * 2.0
        blurred_a = cv2.GaussianBlur(lab[..., 1], (0, 0), sigma)
        blurred_b = cv2.GaussianBlur(lab[..., 2], (0, 0), sigma)
        strength = settings.color_noise_reduction / 100.0 * (0.45 + settings.color_noise_reduction_smoothness / 200.0)
        lab[..., 1] = lab[..., 1] * (1.0 - strength) + blurred_a * strength
        lab[..., 2] = lab[..., 2] * (1.0 - strength) + blurred_b * strength
        output = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    if settings.luminance_noise_reduction > 0:
        lab = cv2.cvtColor(np.clip(output, 0, 1), cv2.COLOR_RGB2LAB)
        sigma = 0.5 + settings.luminance_noise_reduction / 100.0 * 2.8
        base = cv2.GaussianBlur(lab[..., 0], (0, 0), sigma)
        strength = settings.luminance_noise_reduction / 100.0 * (0.35 + (100.0 - settings.luminance_noise_reduction_detail) / 220.0)
        detail_keep = settings.luminance_noise_reduction_contrast / 100.0 * 0.30
        luma = lab[..., 0]
        smoothed = luma * (1.0 - strength) + base * strength
        lab[..., 0] = smoothed + (luma - base) * detail_keep
        output = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    return np.clip(output, 0.0, 1.0)


def _grain(image: np.ndarray, effects: EffectsAdjustments) -> np.ndarray:
    if effects.grain_amount <= 0:
        return image
    height, width = image.shape[:2]
    seed = int(width * 1000003 + height * 9176 + effects.grain_amount * 31 + effects.grain_size * 7 + effects.grain_roughness)
    noise = np.random.default_rng(seed).normal(0.0, 1.0, (height, width)).astype(np.float32)
    sigma = max(0.15, effects.grain_size / 100.0 * 1.5)
    noise = cv2.GaussianBlur(noise, (0, 0), sigma)
    noise /= max(float(np.std(noise)), 1e-5)
    rough = 0.35 + effects.grain_roughness / 100.0 * 0.65
    luma = _luminance(image)
    tonal_weight = 0.55 + (1.0 - luma) * 0.45
    amount = effects.grain_amount / 100.0 * 0.075 * rough
    return np.clip(image + noise[..., None] * tonal_weight[..., None] * amount, 0.0, 1.0)


def _defringe(image: np.ndarray, optics: OpticsAdjustments) -> np.ndarray:
    if (
        not optics.remove_chromatic_aberration
        and optics.defringe_purple_amount <= 0
        and optics.defringe_green_amount <= 0
    ):
        return image
    hsv = cv2.cvtColor(np.clip(image, 0, 1), cv2.COLOR_RGB2HSV)

    def desaturate_range(amount: float, low: float, high: float) -> None:
        if amount <= 0:
            return
        low_hue = low * 3.6
        high_hue = high * 3.6
        hue = hsv[..., 0]
        if low_hue <= high_hue:
            hue_mask = (hue >= low_hue) & (hue <= high_hue)
        else:
            hue_mask = (hue >= low_hue) | (hue <= high_hue)
        brightness = hsv[..., 2]
        edge = np.abs(brightness - cv2.GaussianBlur(brightness, (0, 0), 1.0))
        edge_weight = _smoothstep(0.008, 0.080, edge)
        factor = 1.0 - amount / 100.0 * (0.65 if optics.remove_chromatic_aberration else 0.45)
        hsv[..., 1][hue_mask] *= 1.0 - (1.0 - factor) * edge_weight[hue_mask]

    desaturate_range(optics.defringe_purple_amount, optics.defringe_purple_hue_low, optics.defringe_purple_hue_high)
    desaturate_range(optics.defringe_green_amount, optics.defringe_green_hue_low, optics.defringe_green_hue_high)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def _transform_geometry(image: np.ndarray, transform: TransformSettings) -> np.ndarray:
    if transform == TransformSettings():
        return image
    height, width = image.shape[:2]
    horizontal = transform.horizontal / 100.0 * width * 0.18
    vertical = transform.vertical / 100.0 * height * 0.18
    src = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    dst = np.float32([
        [horizontal, vertical], [width - 1 - horizontal, -vertical],
        [width - 1 + horizontal, height - 1 + vertical], [-horizontal, height - 1 - vertical],
    ])
    matrix = cv2.getPerspectiveTransform(src, dst)
    output = cv2.warpPerspective(image, matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    center = (width / 2.0, height / 2.0)
    rotation = cv2.getRotationMatrix2D(center, transform.rotate, transform.scale / 100.0)
    rotation[0, 0] *= 1.0 + transform.aspect / 100.0 * 0.18
    rotation[0, 1] *= 1.0 + transform.aspect / 100.0 * 0.18
    rotation[0, 2] += transform.offset_x / 100.0 * width * 0.20
    rotation[1, 2] += transform.offset_y / 100.0 * height * 0.20
    return cv2.warpAffine(output, rotation, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def _calibrate_primaries(image: np.ndarray, state: EditorState) -> np.ndarray:
    calibration = state.calibration
    if calibration == type(calibration)():
        return image
    hsv = cv2.cvtColor(np.clip(image, 0, 1), cv2.COLOR_RGB2HSV)
    for center, hue_adjustment, saturation_adjustment in (
        (0.0, calibration.red_primary_hue, calibration.red_primary_saturation),
        (120.0, calibration.green_primary_hue, calibration.green_primary_saturation),
        (240.0, calibration.blue_primary_hue, calibration.blue_primary_saturation),
    ):
        distance = np.abs((hsv[..., 0] - center + 180.0) % 360.0 - 180.0)
        weight = np.clip(1.0 - distance / 70.0, 0.0, 1.0)
        weight = weight * weight * (3.0 - 2.0 * weight)
        hsv[..., 0] = (hsv[..., 0] + weight * hue_adjustment * 0.22) % 360.0
        if saturation_adjustment:
            current = hsv[..., 1]
            delta = (1.0 - current) * (saturation_adjustment / 100.0) if saturation_adjustment > 0 else current * (saturation_adjustment / 100.0)
            hsv[..., 1] += weight * delta
    hsv[..., 1] = np.clip(hsv[..., 1], 0.0, 1.0)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
