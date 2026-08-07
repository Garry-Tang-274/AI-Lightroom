from __future__ import annotations

import numpy as np

from app.core.editor_state import CurvePoint, EditorState, ToneCurve
from app.core.image_processor import render_image


def gradient_image(width: int = 160, height: int = 100) -> np.ndarray:
    x = np.linspace(0, 255, width, dtype=np.uint8)
    gray = np.repeat(x[None, :], height, axis=0)
    return np.stack([gray, np.flip(gray, axis=1), np.full_like(gray, 96)], axis=2)


def test_pristine_render_is_pixel_stable():
    source = gradient_image()
    rendered = render_image(source, EditorState())
    assert np.array_equal(rendered, source)


def test_render_is_non_destructive_and_deterministic():
    source = gradient_image()
    original = source.copy()
    state = EditorState()
    state.basic.exposure = 0.5
    state.basic.highlights = -25
    state.basic.clarity = 12
    first = render_image(source, state)
    second = render_image(source, state)
    assert np.array_equal(source, original)
    assert np.array_equal(first, second)
    assert not np.array_equal(first, source)


def test_exposure_and_curve_have_expected_direction():
    source = np.full((32, 32, 3), 96, dtype=np.uint8)
    state = EditorState()
    state.basic.exposure = 1.0
    brighter = render_image(source, state)
    assert brighter.mean() > source.mean()

    state = EditorState()
    state.curves.rgb = ToneCurve(
        points=[CurvePoint(x=0, y=0), CurvePoint(x=0.5, y=0.35), CurvePoint(x=1, y=1)]
    )
    darker = render_image(source, state)
    assert darker.mean() < source.mean()

