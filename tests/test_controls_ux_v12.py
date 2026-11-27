"""Manual-edit review and empty-canvas UX; no network or user data."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from app.core.editor_state import CurvePoint, EditorState, HSLColor, ToneCurve
from app.ui.adjustment_panel import AdjustmentPanel, ParameterSlider, SliderSpec
from app.ui.histogram_widget import HistogramWidget
from app.ui.image_view import ImageView


def test_single_parameter_reset_is_atomic_and_uses_nonzero_default(qtbot):
    control = ParameterSlider(SliderSpec("sharpen_radius", "锐化半径", 30, 300, 100, .8))
    qtbot.addWidget(control)
    events = []
    control.interaction_started.connect(lambda key: events.append(("begin", key)))
    control.value_changed.connect(lambda key, value: events.append(("value", value)))
    control.interaction_finished.connect(lambda key: events.append(("end", key)))
    control.set_value(1.5)
    assert events == []
    assert control.label.property("modified") is True
    control.reset_button.click()
    assert events == [("begin", "sharpen_radius"), ("value", .8), ("end", "sharpen_radius")]
    assert not control.is_modified()
    assert not control.reset_button.isEnabled()
    assert control.label.property("modified") is False


def test_changed_counts_include_other_hsl_grading_and_curve_channels(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    state = EditorState()
    state.basic.exposure = .4
    state.hsl[HSLColor.BLUE].saturation = -20
    state.hsl[HSLColor.BLUE].luminance = -8
    state.color_grading.highlights.saturation = 10
    state.curves.red = ToneCurve(points=[CurvePoint(x=0, y=.1), CurvePoint(x=1, y=1)])
    state.optics.remove_chromatic_aberration = True
    state.effects.vignette_style = 2
    panel.set_state(state)
    assert panel.changed_count.text() == "7 项"
    assert panel._hsl_group.header.text().endswith("2")
    assert panel._curve_group.header.text().endswith("1")
    assert panel.hsl_selector.itemText(panel.hsl_selector.findData("blue")).endswith(" •")
    panel.modified_only.setChecked(True)
    assert panel.hsl_selector.currentData() == "blue"
    assert panel.grading_selector.currentData() == "highlights"
    assert panel.curve_panel.channel.currentData() == "red"
    assert panel.hsl_controls["hue"].isHidden()
    assert not panel.hsl_controls["saturation"].isHidden()
    assert not panel.remove_chromatic_aberration.isHidden()
    assert not panel.vignette_style.isHidden()


def test_modified_filter_does_not_remove_dragged_control_until_release(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    panel.controls["exposure"].slider.setValue(100)
    panel.modified_only.setChecked(True)
    control = panel.controls["exposure"]
    control.slider.sliderPressed.emit()
    control.slider.setValue(0)
    assert not control.isHidden()
    assert panel.changed_count.text() == "0 项"
    control.slider.sliderReleased.emit()
    assert control.isHidden()
    assert not panel.no_results.isHidden()


def test_search_and_modified_filter_restore_original_expansion(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    initial = [section.header.isChecked() for section in panel._sections]
    panel.controls["contrast"].slider.setValue(20)
    panel.advanced_controls["effects"]["grain_amount"].slider.setValue(12)
    panel.modified_only.setChecked(True)
    panel.search.setText("grain_amount")
    assert len([section for section in panel._sections if not section.isHidden()]) == 1
    assert not panel.advanced_controls["effects"]["grain_amount"].isHidden()
    panel.search.clear()
    assert len([section for section in panel._sections if not section.isHidden()]) == 2
    panel.modified_only.setChecked(False)
    assert [section.header.isChecked() for section in panel._sections] == initial


def test_external_state_refresh_updates_count_and_selects_modified_channel(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    panel.modified_only.setChecked(True)
    state = EditorState()
    state.hsl[HSLColor.ORANGE].hue = -9
    panel.set_state(state)
    assert panel.hsl_selector.currentData() == "orange"
    assert panel.changed_count.text() == "1 项"
    assert not panel._hsl_group.isHidden()
    panel.set_state(EditorState())
    assert panel.changed_count.text() == "0 项"
    assert not panel.no_results.isHidden()


def test_filter_browsing_does_not_emit_edits(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    events = []
    for signal in (panel.adjustment_changed, panel.hsl_changed, panel.curve_changed,
                   panel.color_grading_changed, panel.advanced_adjustment_changed):
        signal.connect(lambda *args: events.append(args))
    state = EditorState()
    state.hsl[HSLColor.BLUE].hue = 8
    panel.set_state(state)
    panel.modified_only.setChecked(True)
    panel.hsl_selector.setCurrentIndex(0)
    assert not panel.hsl_empty.isHidden()
    panel.search.setText("color")
    panel.search.clear()
    panel.modified_only.setChecked(False)
    assert events == []


def test_advanced_and_curve_changes_immediately_update_summary(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    panel.advanced_controls["detail"]["sharpen_radius"].slider.setValue(160)
    panel.curve_panel.editor._set_points([CurvePoint(x=0, y=.2), CurvePoint(x=1, y=1)])
    assert panel.changed_count.text() == "2 项"
    panel.advanced_controls["detail"]["sharpen_radius"].reset_button.click()
    panel.curve_panel.reset_button.click()
    assert panel.changed_count.text() == "0 项"


def test_grading_blending_balance_are_visible_counted_and_resettable(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    changes = []
    panel.advanced_adjustment_changed.connect(lambda *args: changes.append(args))
    state = EditorState()
    state.color_grading.blending = 72
    state.color_grading.balance = -25
    panel.set_state(state)
    panel.modified_only.setChecked(True)
    blending = panel.advanced_controls["color_grading"]["blending"]
    balance = panel.advanced_controls["color_grading"]["balance"]
    assert panel.changed_count.text() == "2 项"
    assert not blending.isHidden() and not balance.isHidden()
    assert panel.grading_selector.isHidden()
    assert panel.grading_empty.isHidden()
    blending.reset_button.click()
    assert changes == [("color_grading", "blending", 50)]
    balance.slider.setValue(12)
    assert changes[-1] == ("color_grading", "balance", 12)
    assert panel.changed_count.text() == "1 项"


def test_empty_canvas_open_button_and_image_lifecycle(qtbot):
    view = ImageView()
    qtbot.addWidget(view)
    view.resize(640, 480)
    view.show()
    opened = []
    view.open_requested.connect(lambda: opened.append(True))
    qtbot.mouseClick(view.open_button, Qt.MouseButton.LeftButton)
    assert opened == [True]
    view.set_image(np.zeros((100, 200, 3), dtype=np.uint8))
    assert view.open_button.isHidden()
    view.set_comparison(np.zeros((100, 200, 3), dtype=np.uint8), True)
    view.clear_image()
    assert not view.open_button.isHidden()
    assert not view._comparison_enabled
    assert view.viewport().rect().contains(view.open_button.geometry())


def test_horizontal_wheel_does_not_change_image_zoom(qtbot):
    view = ImageView()
    qtbot.addWidget(view)
    view.set_image(np.zeros((100, 200, 3), dtype=np.uint8))
    zoom = view.transform().m11()
    event = QWheelEvent(QPointF(50, 50), QPointF(50, 50), QPoint(), QPoint(120, 0),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(view.viewport(), event)
    assert view.transform().m11() == zoom


def test_histogram_sample_bounded_and_empty_clears_clipping(qtbot):
    histogram = HistogramWidget()
    qtbot.addWidget(histogram)
    histogram.set_image(np.full((479, 719, 3), 255, dtype=np.uint8))
    assert histogram._histograms[0].sum() <= 240 * 360
    assert histogram._clip_high == 100
    histogram.set_image(None)
    assert histogram._clip_high == histogram._clip_low == 0
    assert histogram._histograms == []
    histogram.caption.setChecked(False)
    assert histogram.height() == 36


def test_modified_editor_fits_narrow_panel(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    panel.resize(320, 700)
    panel.show()
    panel.controls["exposure"].slider.setValue(20)
    panel.modified_only.setChecked(True)
    qtbot.wait(10)
    assert panel.minimumSizeHint().width() <= 320
    assert panel.widget().width() <= panel.viewport().width()
