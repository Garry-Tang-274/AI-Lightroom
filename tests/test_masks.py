from __future__ import annotations

import numpy as np

from app.core.editor_state import (
    BrushPoint,
    BrushStroke,
    EditorState,
    LocalAdjustments,
    MaskLayer,
    MaskType,
)
from app.core.image_processor import render_image
from app.core.masks import generate_mask


def test_linear_and_radial_masks_have_expected_geometry():
    source = np.zeros((100, 160, 3), dtype=np.uint8)
    linear = MaskLayer(
        name="top",
        type=MaskType.LINEAR_GRADIENT,
        parameters={"start_x": 0.5, "start_y": 0.0, "end_x": 0.5, "end_y": 0.7},
    )
    linear_mask = generate_mask(source, linear)
    assert linear_mask[5].mean() > linear_mask[90].mean() + 0.7

    radial = MaskLayer(name="center", type=MaskType.RADIAL_GRADIENT)
    radial_mask = generate_mask(source, radial)
    assert radial_mask[50, 80] > 0.95
    assert radial_mask[0, 0] < 0.05


def test_brush_mask_rasterizes_normalized_stroke():
    source = np.zeros((100, 100, 3), dtype=np.uint8)
    layer = MaskLayer(
        name="brush",
        type=MaskType.BRUSH,
        strokes=[BrushStroke(points=[BrushPoint(x=0.2, y=0.5), BrushPoint(x=0.8, y=0.5)], size=0.1)],
    )
    mask = generate_mask(source, layer)
    assert mask[50, 50] > 0.9
    assert mask[5, 50] < 0.01


def test_local_adjustment_changes_only_masked_region():
    source = np.full((100, 100, 3), 80, dtype=np.uint8)
    state = EditorState(
        masks=[
            MaskLayer(
                name="top",
                type=MaskType.LINEAR_GRADIENT,
                parameters={"start_x": 0.5, "start_y": 0.0, "end_x": 0.5, "end_y": 0.45},
                adjustments=LocalAdjustments(exposure=1.0),
            )
        ]
    )
    rendered = render_image(source, state)
    assert rendered[2].mean() > source[2].mean() + 25
    assert abs(float(rendered[-1].mean()) - float(source[-1].mean())) < 2


def test_sky_mask_prefers_blue_upper_region():
    source = np.zeros((120, 180, 3), dtype=np.uint8)
    source[:65] = (80, 145, 220)
    source[65:] = (95, 80, 55)
    mask = generate_mask(source, MaskLayer(name="sky", type=MaskType.SKY))
    assert mask[:40].mean() > 0.65
    assert mask[90:].mean() < 0.15
