from dataclasses import replace
from types import SimpleNamespace

import pytest
from PIL import Image
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.core.editor_state import EditorState, MaskLayer, WatermarkLayer, MaskType
from app.core.recipes import RecipeLibrary
from app.ui.main_window import MainWindow
from app.utils.config import SettingsManager


def make_photo(tmp_path, name, color):
    path = tmp_path / name
    Image.new("RGB", (48, 32), color).save(path)
    return path


def await_photo(qtbot, window, path):
    qtbot.waitUntil(lambda: not window._loading and window.loaded_image is not None
                    and window.loaded_image.path == path, timeout=5000)


def test_group_return_restores_each_state_and_redo_without_extra_prompt(qtbot, tmp_path, monkeypatch):
    a = make_photo(tmp_path, "第一张.jpg", "gray")
    b = make_photo(tmp_path, "第二张.png", "blue")
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(QMessageBox, "question", lambda *a: pytest.fail("Group revisits must resume silently"))
    window.open_photo_set([a, a, b])
    await_photo(qtbot, window, a)
    assert window.photo_set == (a, b) and window.set_picker.text() == "1 / 2"
    assert window.session_store.load(a) is None
    window._set_basic_adjustment("exposure", .4)
    window._flush_history()
    window._set_basic_adjustment("contrast", 12)
    window.undo()
    window.next_photo.trigger()
    await_photo(qtbot, window, b)
    assert window.state.is_pristine() and not window.next_photo.isEnabled()
    window._set_basic_adjustment("temperature", 7)
    window.previous_photo.trigger()
    await_photo(qtbot, window, a)
    assert window.state.basic.exposure == .4 and window.state.basic.contrast == 0
    window.redo()
    assert window.state.basic.contrast == 12
    window._navigate_set(1)
    await_photo(qtbot, window, b)
    assert window.state.basic.temperature == 7 and not window.history.can_redo


def test_failed_member_does_not_replace_current_or_block_jump(qtbot, tmp_path, monkeypatch):
    a = make_photo(tmp_path, "a.jpg", "gray")
    b = make_photo(tmp_path, "b.png", "red")
    bad = tmp_path / "corrupt.jpg"
    bad.write_bytes(b"invalid JPEG")
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_photo_set([bad, a, b])
    await_photo(qtbot, w, a)
    assert w._photo_index == 1
    w._set_basic_adjustment("exposure", .25)
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[2]))
    w._navigate_set(0)
    qtbot.waitUntil(lambda: bool(errors))
    assert w.loaded_image.path == a and w._photo_index == 1 and w.state.basic.exposure == .25
    w.next_photo.trigger()
    await_photo(qtbot, w, b)


def test_recipe_is_persistent_not_a_photo_or_clipboard_dump():
    manager = SettingsManager()
    lib = RecipeLibrary(manager.store)
    source = EditorState()
    source.basic.exposure = .25
    source.hsl["blue"].hue = 8
    source.transform.rotate = 8
    source.masks.append(MaskLayer(name="source sky", type=MaskType.SKY))
    source.watermarks.append(WatermarkLayer(name="source mark", asset_id="private"))
    lib.save("街拍", source)
    target = EditorState()
    target.transform.rotate = -5
    target.optics.remove_chromatic_aberration = True
    target.masks.append(MaskLayer(name="target sky", type=MaskType.SKY))
    second = RecipeLibrary(SettingsManager().store)
    assert second.names() == ["街拍"]
    after = second.apply("街拍", target)
    assert after.basic == source.basic and after.hsl == source.hsl
    assert after.transform == target.transform and after.optics == target.optics
    assert after.masks == target.masks and not after.watermarks
    assert "private" not in manager.store.value(lib.key) and target.basic.exposure == 0
    with pytest.raises(ValueError):
        lib.save("街拍", target)
    second.remove("街拍")
    assert not lib.names()


def test_recipe_application_one_undo_no_empty_repeats(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)
    p = make_photo(tmp_path, "target.png", "brown")
    w.open_image(str(p))
    look = EditorState()
    look.basic.contrast = 20
    look.basic.shadows = 12
    w.recipes.save("暖调", look)
    w._apply_recipe("暖调")
    w._apply_recipe("暖调")
    assert len(w.history.entries) == 2 and w.state.basic == look.basic
    w.undo()
    assert w.state.is_pristine()


def test_history_click_preserves_pending_numeric_edit(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_image(str(make_photo(tmp_path, "numeric.jpg", "black")))
    w._set_basic_adjustment("exposure", 1)
    w._flush_history()
    w._set_basic_adjustment("contrast", 20)
    w._history_row_selected(0)
    assert w.state.is_pristine()
    w.redo()
    w.redo()
    assert w.state.basic.contrast == 20 and w.state.basic.exposure == 1


def test_cancel_after_worker_result_was_queued_discards_it(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_image(str(make_photo(tmp_path, "cancel.jpg", "gray")))
    w._ai_before_state = w.state.snapshot()
    w._ai_document = w._document_generation
    w._ai_worker = SimpleNamespace(is_cancelled=True)
    w.ai_panel.set_busy(True)
    proposed = EditorState()
    proposed.basic.exposure = 2
    w._ai_finished(SimpleNamespace(state=proposed))
    assert w.state.is_pristine() and len(w.history.entries) == 1
    assert w._ai_worker is None and not w.ai_panel.retry_button.isVisible()


def test_replaced_file_does_not_inherit_old_images_pending_edits(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)
    a = make_photo(tmp_path, "replaced.jpg", "gray")
    b = make_photo(tmp_path, "next.png", "teal")
    w.open_photo_set([a, b])
    await_photo(qtbot, w, a)
    w._set_basic_adjustment("exposure", 1)
    Image.new("RGB", (192, 128), "red").save(a)
    w.next_photo.trigger()
    await_photo(qtbot, w, b)
    w.previous_photo.trigger()
    await_photo(qtbot, w, a)
    assert w.state.is_pristine() and w.loaded_image.width == 192


def test_shared_grading_controls_update_state_and_undo(qtbot, tmp_path):
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_image(str(make_photo(tmp_path, "grading.jpg", "gray")))
    control = w.adjustments.advanced_controls["color_grading"]["blending"]
    control.slider.setValue(round(73 * control.spec.scale))
    assert w.state.color_grading.blending == 73
    w.undo()
    assert w.state.color_grading.blending == 50


def test_export_protects_other_originals_and_can_omit_exif(qtbot, tmp_path, monkeypatch):
    a = tmp_path / "a.jpg"
    exif = Image.Exif()
    exif[315] = "Photographer"
    Image.new("RGB", (80, 60), "gold").save(a, exif=exif)
    b = make_photo(tmp_path, "b.png", "teal")
    w = MainWindow()
    qtbot.addWidget(w)
    w.open_photo_set([a, b])
    await_photo(qtbot, w, a)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(b), "PNG"))
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warned.append(args[2]))
    w.export_image_dialog()
    assert warned and w._export_worker is None
    with Image.open(b) as other:
        assert other.getpixel((0, 0)) == (0, 128, 128)
    dest = tmp_path / "share.png"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(dest), "PNG"))
    w.runtime_settings = replace(w.runtime_settings, export_keep_exif=False)
    w.export_image_dialog()
    qtbot.waitUntil(lambda: w._export_worker is None, timeout=5000)
    with Image.open(dest) as output:
        assert not output.getexif() and output.size == (80, 60) and output.info["icc_profile"]
    with Image.open(a) as original:
        assert original.getexif()[315] == "Photographer"
