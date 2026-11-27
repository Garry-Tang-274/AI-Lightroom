"""Pixel-contract checks for the float-buffer/native-pass optimizations."""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.core.editor_state import EditorState, HSLAdjustment, HSLColor
from app.core.image_processor import _HSL_CENTERS, _hsl, _luminance, _smoothstep, _tone


def test_native_luminance_matches_float_reference_on_strided_image():
    source = np.random.default_rng(21).random((91, 137, 3), dtype=np.float32)[::2, ::2]
    original = source.copy()
    expected = source[..., 0] * 0.2126 + source[..., 1] * 0.7152 + source[..., 2] * 0.0722
    actual = _luminance(source)
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1.2e-7)
    assert actual.dtype == np.float32
    assert np.array_equal(source, original)


def test_smoothstep_reuses_only_its_own_buffer():
    source = np.linspace(-0.3, 1.3, 4097, dtype=np.float32)
    source.flags.writeable = False
    normalized = np.clip((source - 0.12) / 0.65, 0, 1)
    expected = normalized * normalized * (3 - 2 * normalized)
    assert np.array_equal(_smoothstep(0.12, 0.77, source), expected)


def test_contrast_fast_path_matches_existing_formula_without_mutation():
    source = np.random.default_rng(22).random((73, 113, 3), dtype=np.float32)
    source.flags.writeable = False
    for contrast in (-100, -25, 25, 100):
        expected = np.clip(0.5 + (source - 0.5) * 2 ** (contrast / 100 * 1.35), 0, 1)
        assert np.array_equal(_tone(source, contrast, 0, 0, 0, 0), expected)


def reference_hsl(image, state):
    """Pre-optimization equations, retaining modulo-based circular distance."""
    hsv = cv2.cvtColor(np.clip(image, 0, 1), cv2.COLOR_RGB2HSV)
    original_hue = hsv[..., 0].copy()
    chroma = np.clip((hsv[..., 1] - 0.01) / 0.11, 0, 1)
    chroma = chroma * chroma * (3 - 2 * chroma)
    for color, adjustment in state.hsl.items():
        distance = np.abs((original_hue - _HSL_CENTERS[color] + 180) % 360 - 180)
        weight = np.clip(1 - distance / 48, 0, 1)
        weight = weight * weight * (3 - 2 * weight) * chroma
        hsv[..., 0] = (hsv[..., 0] + weight * adjustment.hue * 0.35) % 360
        amount = adjustment.saturation / 100
        delta = (1 - hsv[..., 1]) * amount if amount > 0 else hsv[..., 1] * amount
        hsv[..., 1] += weight * delta
        amount = adjustment.luminance / 100
        room = 1 - hsv[..., 2] if amount > 0 else hsv[..., 2]
        hsv[..., 2] += weight * room * amount * 0.65
    hsv[..., 1:] = np.clip(hsv[..., 1:], 0, 1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


@pytest.mark.parametrize("strength", [-100, 35, 100])
def test_planar_hsl_preserves_overlapping_ranges_and_hue_wrap(strength):
    # Cover the hue seam, all eight overlapping ranges, and nearly gray pixels.
    hsv = np.empty((7, 3601, 3), dtype=np.float32)
    hsv[..., 0] = np.linspace(0, 359.999, 3601, dtype=np.float32)
    hsv[..., 1] = np.array([0, 0.01, 0.05, 0.12, 0.3, 0.7, 1], dtype=np.float32)[:, None]
    hsv[..., 2] = 0.6
    source = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    source.flags.writeable = False
    state = EditorState()
    for index, color in enumerate(HSLColor):
        sign = 1 if index % 2 else -1
        state.hsl[color] = HSLAdjustment(
            hue=strength * sign, saturation=strength, luminance=strength * sign,
        )
    actual = _hsl(source, state)
    expected = reference_hsl(source, state)
    # Equivalent circular-distance arithmetic can round differently in float32;
    # it must remain far below a single 8-bit output level.
    np.testing.assert_allclose(actual, expected, rtol=0, atol=2e-6)
    assert np.max(np.abs(np.rint(actual * 255) - np.rint(expected * 255))) <= 1
