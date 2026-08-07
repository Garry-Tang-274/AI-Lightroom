from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.editor_state import BasicAdjustments, CurvePoint, EditorState, ToneCurve


def test_editor_state_round_trip_and_snapshot_are_independent():
    state = EditorState()
    state.basic = state.basic.with_value("exposure", 0.35)
    snapshot = state.snapshot()
    state.basic.exposure = 0.1
    assert snapshot.basic.exposure == 0.35
    assert EditorState.model_validate_json(snapshot.model_dump_json()) == snapshot


def test_adjustment_ranges_are_validated():
    with pytest.raises(ValidationError):
        BasicAdjustments(exposure=7)
    with pytest.raises(ValidationError):
        BasicAdjustments(contrast=-101)


def test_curve_points_are_sorted_and_distinct():
    curve = ToneCurve(points=[CurvePoint(x=1, y=1), CurvePoint(x=0, y=0)])
    assert [point.x for point in curve.points] == [0, 1]
    with pytest.raises(ValidationError):
        ToneCurve(points=[CurvePoint(x=0.5, y=0.2), CurvePoint(x=0.5, y=0.8)])

