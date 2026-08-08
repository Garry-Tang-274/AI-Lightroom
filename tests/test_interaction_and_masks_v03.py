from __future__ import annotations

import cv2
import numpy as np
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from app.ai.executor import apply_editing_plan
from app.ai.orchestrator import _reject_unreliable_masks
from app.ai.schemas import EditingPlan
from app.core.editor_state import EditorState, MaskLayer, MaskType
from app.core.masks import generate_mask, mask_confidence
from app.core.image_processor import render_image
from app.ui.main_window import MainWindow


def _sky_ground_image() -> np.ndarray:
    pixels = np.zeros((180, 300, 3), dtype=np.uint8)
    pixels[:82] = (80, 145, 220)
    pixels[82:] = (95, 80, 55)
    return pixels


def _road_image() -> np.ndarray:
    pixels = _sky_ground_image()
    pixels[70:] = (50, 95, 50)
    road = np.array([[115, 179], [185, 179], [165, 72], [135, 72]], dtype=np.int32)
    cv2.fillConvexPoly(pixels, road, (110, 110, 110))
    cv2.line(pixels, (120, 179), (145, 72), (230, 230, 210), 3)
    cv2.line(pixels, (180, 179), (155, 72), (230, 230, 210), 3)
    return pixels


def test_slider_drag_updates_preview_and_creates_one_history_entry(qtbot, tmp_path):
    path = tmp_path / "slider.jpg"
    Image.fromarray(np.full((140, 220, 3), 80, dtype=np.uint8)).save(path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_image(str(path))
    slider = window.adjustments.controls["exposure"].slider
    slider.sliderPressed.emit()
    slider.setValue(30)
    slider.setValue(65)
    assert window.state.basic.exposure == 0.65
    qtbot.waitUntil(lambda: window.current_preview is not None and window.current_preview.mean() > 80, timeout=3000)
    slider.sliderReleased.emit()
    assert len(window.history.entries) == 2
    window.undo()
    assert window.state.basic.exposure == 0


def test_wheel_over_slider_does_not_change_value(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    slider = window.adjustments.controls["contrast"].slider
    slider.setValue(19)
    event = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, 120), Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(slider, event)
    assert slider.value() == 19


def test_sky_and_road_masks_are_image_driven_and_local():
    sky_ground = _sky_ground_image()
    sky = generate_mask(sky_ground, MaskLayer(name="sky", type=MaskType.SKY))
    assert sky[:45].mean() > 0.6 and sky[120:].mean() < 0.15
    state = EditorState(masks=[MaskLayer(name="sky", type=MaskType.SKY)])
    state.masks[0].adjustments.exposure = -1.0
    rendered = render_image(sky_ground, state)
    assert rendered[:45].mean() < sky_ground[:45].mean() - 18
    assert abs(float(rendered[140:].mean()) - float(sky_ground[140:].mean())) < 2
    road = generate_mask(_road_image(), MaskLayer(name="road", type=MaskType.SEMANTIC, semantic_label="road"))
    assert road[150, 150] > 0.5 and road[:50].mean() < 0.02 and mask_confidence(road, "road") > 0


def test_mask_overlay_and_ai_requested_mask_use_real_generator(qtbot, tmp_path):
    pixels = _sky_ground_image()
    path = tmp_path / "mask.png"
    Image.fromarray(pixels).save(path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_image(str(path))
    window._create_mask("sky")
    window.mask_panel.preview_button.setChecked(True)
    assert not window.image_view._mask_overlay_item.pixmap().isNull()
    plan = EditingPlan.model_validate({
        "summary": "sky", "reasoning_summary": "local", "confidence": 0.8,
        "requested_masks": [{"tool": "create_sky_mask", "ref": "sky_1", "name": "AI Sky"}],
        "local_adjustments": [{"mask_ref": "sky_1", "adjustments": {"exposure": -0.4}}],
    })
    execution = apply_editing_plan(EditorState(), plan)
    _reject_unreliable_masks(pixels, EditorState(), execution)
    assert len(execution.state.masks) == 1
    assert execution.state.masks[0].adjustments.exposure == -0.4


def test_mask_panel_exposes_local_texture(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert "texture" in window.mask_panel.controls
