from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image, ImageCms
from PySide6.QtCore import QSettings

from app.core.editor_state import EditorState, HSLAdjustment, HSLColor, LocalAdjustments, MaskLayer, MaskType, WatermarkLayer
from app.core.exporter import export_image
from app.core.image_processor import _exposure, _linear_to_srgb, _local_contrast, _srgb_to_linear, prepare_mask_source, render_image
from app.core.masks import generate_mask
from app.core.watermarks import WatermarkLibrary, composite_watermarks
from app.utils.io_utils import load_image, make_preview


def textured_image(width=192, height=128):
    return np.random.default_rng(17).integers(30, 225, (height, width, 3), dtype=np.uint8)


def test_neutral_render_returns_independent_pixel_identical_image():
    source = textured_image()
    result = render_image(source, EditorState())
    assert np.array_equal(source, result)
    assert not np.shares_memory(source, result)


@pytest.mark.parametrize("control", ["saturation", "vibrance", "hsl_red", "calibration_red"])
def test_color_strength_controls_preserve_neutral_gray(control):
    source = np.repeat(np.arange(256, dtype=np.uint8)[None, :, None], 3, axis=2)
    state = EditorState()
    if control in {"saturation", "vibrance"}:
        setattr(state.basic, control, 100)
    elif control == "hsl_red":
        state.hsl[HSLColor.RED] = HSLAdjustment(hue=100, saturation=100, luminance=100)
    else:
        state.calibration.red_primary_saturation = 100
        state.calibration.red_primary_hue = 100
    assert np.array_equal(render_image(source, state), source)


def test_local_clarity_does_not_mutate_its_input():
    source = textured_image().astype(np.float32) / 255.0
    original = source.copy()
    result = _local_contrast(source, 80, 0, 0)
    assert np.array_equal(source, original)
    assert not np.array_equal(result, original)


@pytest.mark.parametrize("exposure", [-5, -1, -0.25, 0.25, 1, 5])
def test_optimized_exposure_matches_linear_light_reference(exposure):
    values = np.linspace(0, 1, 16001, dtype=np.float32)[None, :, None]
    expected = _linear_to_srgb(_srgb_to_linear(values) * 2.0**exposure)
    assert np.allclose(_exposure(values, exposure), expected, atol=3e-7, rtol=1e-6)


def test_clarity_only_mask_keeps_unselected_pixels_unchanged():
    source = textured_image()
    state = EditorState(masks=[MaskLayer(
        name="Top clarity", type=MaskType.LINEAR_GRADIENT,
        parameters={"start_y": 0, "end_y": 0.4},
        adjustments=LocalAdjustments(clarity=80),
    )])
    result = render_image(source, state)
    assert np.array_equal(result[90:], source[90:])
    assert not np.array_equal(result[:30], source[:30])


@pytest.mark.parametrize("style", [0, 1, 2, 3])
def test_vignette_can_be_followed_by_local_color_and_detail(style):
    source = textured_image()
    state = EditorState(masks=[MaskLayer(
        name="Local", type=MaskType.RADIAL_GRADIENT,
        adjustments=LocalAdjustments(saturation=20, clarity=10, sharpen=20),
    )])
    state.basic.vignette = -30
    state.effects.vignette_style = style
    result = render_image(source, state)
    assert result.dtype == np.uint8 and result.shape == source.shape
    assert np.array_equal(result, render_image(source, state))


def test_color_grading_blending_is_effective():
    source = np.repeat(np.arange(256, dtype=np.uint8)[None, :, None], 3, axis=2)
    state = EditorState()
    state.color_grading.shadows.hue = 205
    state.color_grading.shadows.saturation = 60
    state.color_grading.blending = 0
    narrow = render_image(source, state)
    state.color_grading.blending = 100
    assert not np.array_equal(narrow, render_image(source, state))


def test_color_noise_detail_control_preserves_more_chroma_detail():
    source = textured_image()
    state = EditorState()
    state.detail.color_noise_reduction = 80
    state.detail.color_noise_reduction_detail = 0
    smoothed = render_image(source, state)
    state.detail.color_noise_reduction_detail = 100
    detailed = render_image(source, state)
    assert np.abs(detailed.astype(float) - source).mean() < np.abs(smoothed.astype(float) - source).mean()


def test_automatic_fringe_reduction_has_effect_without_manual_amount():
    source = np.full((100, 160, 3), 150, dtype=np.uint8)
    source[:, 60:63] = (220, 40, 220)
    state = EditorState()
    state.optics.remove_chromatic_aberration = True
    result = render_image(source, state)
    assert not np.array_equal(result[:, 60:63], source[:, 60:63])
    assert np.array_equal(result[:, :30], source[:, :30])


def test_semantic_mask_cache_does_not_change_precision():
    source = textured_image()
    source[:70] = (80, 140, 205)
    layer = MaskLayer(name="Sky", type=MaskType.SKY)
    first = generate_mask(source, layer)
    second = generate_mask(source, layer)
    assert np.array_equal(first, second)


def test_semantic_parameter_labels_do_not_share_cache_entries():
    source = textured_image()
    source[:70] = (80, 140, 205)
    sky = generate_mask(source, MaskLayer(name="Sky", type=MaskType.SEMANTIC, parameters={"label": "sky"}))
    vegetation = generate_mask(source, MaskLayer(name="Plants", type=MaskType.SEMANTIC, parameters={"label": "vegetation"}))
    assert not np.array_equal(sky, vegetation)


def test_full_luminance_range_includes_pure_black_and_white():
    source = np.repeat(np.arange(256, dtype=np.uint8)[None, :, None], 3, axis=2)
    layer = MaskLayer(name="All tones", type=MaskType.LUMINANCE_RANGE, parameters={"min": 0, "max": 1})
    assert np.all(generate_mask(source, layer) == 1)


def test_person_detection_rejects_images_smaller_than_detection_window():
    source = np.zeros((20, 30, 3), dtype=np.uint8)
    result = generate_mask(source, MaskLayer(name="People", type=MaskType.SEMANTIC, semantic_label="person"))
    assert result.shape == (20, 30) and not np.any(result)


def test_failed_export_preserves_existing_destination_and_removes_temporary_file(tmp_path, monkeypatch):
    destination = tmp_path / "已有照片.png"
    destination.write_bytes(b"previous export")

    def fail_save(self, stream, **kwargs):
        stream.write(b"partial invalid image")
        raise OSError("disk full")

    monkeypatch.setattr(Image.Image, "save", fail_save)
    with pytest.raises(OSError, match="disk full"):
        export_image(textured_image(), EditorState(), destination)
    assert destination.read_bytes() == b"previous export"
    assert list(tmp_path.iterdir()) == [destination]


def test_export_refuses_original_path_and_hardlink(tmp_path):
    original = tmp_path / "原图.png"
    original.write_bytes(b"original bytes")
    linked = tmp_path / "linked.png"
    linked.hardlink_to(original)
    for path in (original, linked):
        with pytest.raises(ValueError, match="原始照片"):
            export_image(textured_image(), EditorState(), path, source_path=original)
    assert original.read_bytes() == b"original bytes"


def test_transparent_palette_and_grayscale_load_like_rgba(tmp_path):
    for mode in ("P", "LA", "RGBA"):
        path = tmp_path / f"transparent-{mode}.png"
        if mode == "P":
            image = Image.new("P", (4, 4), 0)
            image.putpalette([255, 0, 0] + [0, 0, 0] * 255)
            image.save(path, transparency=0)
        else:
            Image.new(mode, (4, 4), (200, 0) if mode == "LA" else (200, 0, 0, 0)).save(path)
        assert np.all(load_image(path).pixels == 24)


def test_tagged_rgb_is_color_managed_and_export_profile_matches_pixels(tmp_path, monkeypatch):
    path = tmp_path / "tagged.png"
    Image.new("RGB", (10, 12), (80, 90, 100)).save(path, icc_profile=b"source-profile")
    actual_profile = ImageCms.ImageCmsProfile
    input_profile = SimpleNamespace(profile=SimpleNamespace(xcolor_space="RGB "))
    converted = []

    def profile(value):
        if isinstance(value, BytesIO):
            assert value.getvalue() == b"source-profile"
            return input_profile
        return actual_profile(value)

    def transform(image, source, target, outputMode):
        converted.append((image.mode, source, outputMode))
        return Image.new("RGB", image.size, (40, 50, 60))

    monkeypatch.setattr(ImageCms, "ImageCmsProfile", profile)
    monkeypatch.setattr(ImageCms, "profileToProfile", transform)
    loaded = load_image(path)
    assert converted == [("RGB", input_profile, "RGB")]
    assert tuple(loaded.pixels[0, 0]) == (40, 50, 60)
    assert loaded.icc_profile != b"source-profile"
    assert "sRGB" in actual_profile(BytesIO(loaded.icc_profile)).profile.profile_description


def test_srgb_tagged_grayscale_image_can_be_opened(tmp_path):
    path = tmp_path / "tagged-gray.png"
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    Image.new("L", (10, 12), 80).save(path, icc_profile=profile)
    assert np.all(load_image(path).pixels == 80)


def test_oriented_image_export_preserves_correct_dimensions_and_no_double_rotation(tmp_path):
    path = tmp_path / "portrait.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (40, 20), (80, 100, 120)).save(path, exif=exif)
    loaded = load_image(path)
    assert loaded.pixels.shape == (40, 20, 3)
    destination = tmp_path / "export.jpg"
    export_image(loaded.pixels, EditorState(), destination, exif=loaded.exif, icc_profile=loaded.icc_profile, source_path=path)
    with Image.open(destination) as exported:
        assert exported.size == (20, 40)
        assert exported.getexif().get(274, 1) == 1


def test_empty_image_and_invalid_preview_size_raise_clear_errors():
    with pytest.raises(ValueError, match="empty"):
        render_image(np.zeros((0, 5, 3), dtype=np.uint8), EditorState())
    with pytest.raises(ValueError, match="positive"):
        make_preview(textured_image(), 0)


def test_transformed_color_mask_matches_the_visible_ungraded_canvas():
    source = np.full((160, 240, 3), 120, dtype=np.uint8)
    source[20:110, 20:80] = (40, 80, 210)
    state = EditorState()
    state.transform.offset_x = 100
    canvas = prepare_mask_source(source, state)
    assert not np.array_equal(canvas, source)
    state.masks.append(MaskLayer(
        name="Blue", type=MaskType.COLOR_RANGE,
        parameters={"hue": 226, "tolerance": 25},
        adjustments=LocalAdjustments(exposure=-1),
    ))
    mask = generate_mask(canvas, state.masks[0])
    result = render_image(source, state)
    assert np.array_equal(result[mask == 0], canvas[mask == 0])
    assert np.any(result[mask > 0.9] < canvas[mask > 0.9])


def test_aspect_transform_keeps_the_image_center_fixed():
    source = np.zeros((101, 151, 3), dtype=np.uint8)
    source[50, 75] = 255
    state = EditorState()
    state.transform.aspect = 100
    canvas = prepare_mask_source(source, state)
    assert np.array_equal(canvas[50, 75], source[50, 75])


def watermark_library(tmp_path):
    library = WatermarkLibrary(QSettings(str(tmp_path / "library.ini"), QSettings.Format.IniFormat))
    library.directory = tmp_path / "marks"
    library.directory.mkdir()
    mark = tmp_path / "logo.png"
    Image.new("RGBA", (20, 10), (255, 50, 20, 192)).save(mark)
    entry = library.add(mark)
    return library, entry


def test_watermark_opacity_does_not_accumulate_in_cached_preview(tmp_path):
    library, entry = watermark_library(tmp_path)
    source = np.full((100, 200, 3), 40, dtype=np.uint8)
    layer = WatermarkLayer(asset_id=entry["id"], name="Logo", opacity=0.4, scale=0.3)
    first = composite_watermarks(source, [layer], library)
    for _ in range(4):
        assert np.array_equal(first, composite_watermarks(source, [layer], library))
    layer.opacity = 1
    opaque = composite_watermarks(source, [layer], library)
    assert opaque[..., 0].sum() > first[..., 0].sum()


@pytest.mark.parametrize("size", [(200, 100), (100, 200), (1200, 800)])
def test_small_watermark_uses_requested_fraction_at_preview_and_export_sizes(tmp_path, size):
    library, entry = watermark_library(tmp_path)
    source = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    layer = WatermarkLayer(asset_id=entry["id"], name="Logo", scale=0.3, position="center")
    result = composite_watermarks(source, [layer], library)
    yy, xx = np.where(result[..., 0] > 0)
    assert xx.max() - xx.min() + 1 == round(max(size) * 0.3)
    assert yy.max() - yy.min() + 1 == round(max(size) * 0.15)


def test_corrupt_watermark_is_not_added_to_library(tmp_path):
    library, _ = watermark_library(tmp_path)
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not an image")
    with pytest.raises(OSError):
        library.add(broken)
    assert len(library.entries()) == 1
    assert len(list(library.directory.iterdir())) == 1
