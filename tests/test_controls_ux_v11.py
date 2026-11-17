from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from app.core.editor_state import CurvePoint, EditorState, HSLColor, MaskLayer, MaskType, ToneCurve, WatermarkLayer
from app.ui.adjustment_panel import AdjustmentPanel, ParameterSlider, SliderSpec
from app.ui.curve_editor import CurveEditor, CurvePanel
from app.ui.mask_panel import MaskPanel
from app.ui.watermark_panel import WatermarkPanel


def _wheel(widget):
    event = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(), QPoint(0, 120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)


def test_numeric_fields_and_selectors_ignore_wheel(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    control = panel.controls["exposure"]
    control.set_value(0.42)
    _wheel(control.value_label)
    _wheel(control.slider)
    _wheel(panel.hsl_selector)
    assert control.value_label.value() == 0.42
    assert control.slider.value() == 42
    assert panel.hsl_selector.currentIndex() == 0


def test_double_click_restores_nonzero_default_and_one_transaction(qtbot):
    control = ParameterSlider(SliderSpec("scale", "缩放", 50, 150, default=100))
    qtbot.addWidget(control)
    control.set_value(125)
    events = []
    control.interaction_started.connect(lambda _: events.append("begin"))
    control.interaction_finished.connect(lambda _: events.append("end"))
    qtbot.mouseDClick(control.slider, Qt.MouseButton.LeftButton)
    assert control.slider.value() == 100
    assert control.value_label.value() == 100
    assert events == ["begin", "end"]


def test_percentage_value_field_preserves_normalized_model_units(qtbot):
    control = ParameterSlider(SliderSpec("opacity", "不透明度", 0, 100, 100, 1, 100, "%"))
    qtbot.addWidget(control)
    changes = []
    control.value_changed.connect(lambda key, value: changes.append((key, value)))
    control.value_label.setValue(35)
    assert changes[-1] == ("opacity", .35)
    assert control.slider.value() == 35
    control.set_value(.63)
    assert control.value_label.value() == 63


def test_hsl_and_grading_switches_keep_current_user_values(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    panel.set_state(EditorState())
    panel.hsl_controls["saturation"].slider.setValue(28)
    panel.hsl_selector.setCurrentIndex(1)
    panel.hsl_selector.setCurrentIndex(0)
    assert panel.hsl_controls["saturation"].slider.value() == 28
    panel.grading_controls["saturation"].slider.setValue(12)
    panel.grading_selector.setCurrentIndex(2)
    panel.grading_selector.setCurrentIndex(0)
    assert panel.grading_controls["saturation"].slider.value() == 12


def test_parameter_search_expands_matches_then_restores_disclosures(qtbot):
    panel = AdjustmentPanel()
    qtbot.addWidget(panel)
    initial = [section.header.isChecked() for section in panel._sections]
    panel.search.setText("grain_amount")
    visible = [section for section in panel._sections if not section.isHidden()]
    assert len(visible) == 1
    assert visible[0].header.isChecked()
    assert not panel.advanced_controls["effects"]["grain_amount"].isHidden()
    assert panel.advanced_controls["effects"]["vignette_midpoint"].isHidden()
    panel.search.clear()
    assert [section.header.isChecked() for section in panel._sections] == initial
    panel.search.setText("no such adjustment")
    assert not panel.no_results.isHidden()


def test_curve_same_x_click_moves_existing_point_without_invalid_curve(qtbot):
    editor = CurveEditor()
    qtbot.addWidget(editor)
    editor.resize(300, 200)
    editor.set_curve(ToneCurve(points=[CurvePoint(x=0, y=0), CurvePoint(x=.5, y=.5), CurvePoint(x=1, y=1)]))
    events = []
    editor.interaction_started.connect(lambda: events.append("begin"))
    editor.interaction_finished.connect(lambda: events.append("end"))
    point = editor._to_widget(CurvePoint(x=.5, y=.8)).toPoint()
    qtbot.mouseClick(editor, Qt.MouseButton.LeftButton, pos=point)
    assert len(editor.curve().points) == 3
    assert editor.curve().points[1].y > .75
    assert events == ["begin", "end"]


def test_curve_remove_and_reset_have_atomic_transactions(qtbot):
    panel = CurvePanel()
    qtbot.addWidget(panel)
    panel.editor.resize(300, 200)
    panel.editor.set_curve(ToneCurve(points=[CurvePoint(x=0, y=0), CurvePoint(x=.5, y=.5), CurvePoint(x=1, y=1)]))
    events = []
    panel.interaction_started.connect(lambda: events.append("begin"))
    panel.interaction_finished.connect(lambda: events.append("end"))
    qtbot.mouseClick(panel.editor, Qt.MouseButton.RightButton, pos=panel.editor._to_widget(CurvePoint(x=.5, y=.5)).toPoint())
    assert len(panel.editor.curve().points) == 2
    assert events == ["begin", "end"]
    panel.reset_button.click()
    assert events == ["begin", "end", "begin", "end"]


def test_mask_range_edit_is_visible_and_retains_other_parameters(qtbot):
    panel = MaskPanel()
    qtbot.addWidget(panel)
    layer = MaskLayer(name="Range", type=MaskType.LUMINANCE_RANGE, parameters={"min": .2, "max": .7})
    panel.set_state(EditorState(masks=[layer]))
    changes = []
    panel.mask_property_changed.connect(lambda *args: changes.append(args))
    controls = panel.parameter_controls[MaskType.LUMINANCE_RANGE]
    controls["min"].slider.setValue(80)
    assert changes[-1] == (layer.id, "parameters", {"min": .8, "max": .8})
    assert controls["max"].value_label.value() == .8
    assert not panel.range_section.isHidden()


def test_mask_selection_keeps_local_edits_and_brush_mode_on_refresh(qtbot):
    panel = MaskPanel()
    qtbot.addWidget(panel)
    first = MaskLayer(name="Brush", type=MaskType.BRUSH)
    second = MaskLayer(name="Sky", type=MaskType.SKY)
    state = EditorState(masks=[first, second])
    panel.set_state(state, first.id)
    panel.controls["exposure"].slider.setValue(-40)
    panel.list_widget.setCurrentRow(1)
    panel.list_widget.setCurrentRow(0)
    assert panel.controls["exposure"].slider.value() == -40
    panel.paint_button.setChecked(True)
    panel.set_state(state, first.id)
    assert panel.paint_button.isChecked()


def test_watermark_custom_position_wheel_and_transaction(qtbot):
    panel = WatermarkPanel()
    qtbot.addWidget(panel)
    layer = WatermarkLayer(name="Logo", asset_id="example")
    panel.set_state(EditorState(watermarks=[layer]))
    panel.position.setCurrentIndex(panel.position.findData("custom"))
    assert not panel.x_control.isHidden()
    changes = []
    transactions = []
    panel.property_changed.connect(lambda *args: changes.append(args))
    panel.interaction_started.connect(lambda _: transactions.append("begin"))
    panel.interaction_finished.connect(lambda _: transactions.append("end"))
    panel.x_control.slider.sliderPressed.emit()
    panel.x_control.slider.setValue(30)
    panel.x_control.slider.setValue(40)
    panel.x_control.slider.sliderReleased.emit()
    assert changes[-1] == (layer.id, "x", .4)
    assert transactions == ["begin", "end"]
    _wheel(panel.scale)
    _wheel(panel.opacity_control.value_label)
    assert panel.scale.value() == 18
    assert panel.opacity_control.value_label.value() == 100
    panel.set_state(EditorState())
    assert not panel.properties.isEnabled()
    assert not panel.rename_button.isEnabled()


def test_edit_panels_fit_narrow_sidebars(qtbot):
    for panel in (AdjustmentPanel(), MaskPanel(), WatermarkPanel()):
        qtbot.addWidget(panel)
        panel.resize(320, 680)
        panel.show()
        qtbot.wait(10)
        assert panel.minimumSizeHint().width() <= 320
        assert panel.width() == 320
