from __future__ import annotations

import cv2
import numpy as np
import threading
import weakref
from collections import OrderedDict

from app.core.editor_state import BrushStroke, MaskLayer, MaskType


_CACHE_LOCK = threading.Lock()
_SEMANTIC_CACHE: OrderedDict[tuple, tuple[weakref.ReferenceType, np.ndarray]] = OrderedDict()
_CACHE_MAX_BYTES = 96 * 1024 * 1024
_cache_bytes = 0


def generate_mask(source: np.ndarray, layer: MaskLayer) -> np.ndarray:
    """Generate a float32 mask at the exact source dimensions."""
    if source.dtype != np.uint8 or source.ndim != 3 or source.shape[2] != 3:
        raise ValueError("source must be RGB uint8")
    height, width = source.shape[:2]
    cache_key = None
    if layer.type in {MaskType.SKY, MaskType.SUBJECT, MaskType.SEMANTIC}:
        cache_key = (
            int(source.__array_interface__["data"][0]),
            source.shape,
            source.strides,
            layer.type.value,
            layer.semantic_label,
        )
        cached = _cache_get(cache_key, source)
        if cached is not None:
            mask = cached
            if layer.inverted:
                mask = 1.0 - mask
            return np.clip(mask * layer.opacity, 0.0, 1.0).astype(np.float32)
    if layer.type == MaskType.LINEAR_GRADIENT:
        mask = _linear(height, width, layer.parameters)
    elif layer.type == MaskType.RADIAL_GRADIENT:
        mask = _radial(height, width, layer.parameters, layer.feather)
    elif layer.type == MaskType.LUMINANCE_RANGE:
        mask = _luminance_range(source, layer.parameters, layer.feather)
    elif layer.type == MaskType.COLOR_RANGE:
        mask = _color_range(source, layer.parameters, layer.feather)
    elif layer.type == MaskType.SKY:
        mask = _sky(source)
    elif layer.type == MaskType.SUBJECT:
        mask = _subject(source)
    elif layer.type == MaskType.SEMANTIC:
        mask = _semantic(source, layer.semantic_label or str(layer.parameters.get("label", "subject")))
    elif layer.type == MaskType.BRUSH:
        mask = _brush(height, width, layer.strokes)
    else:  # pragma: no cover - enum protects this branch
        raise ValueError(f"Unsupported mask type: {layer.type}")
    if cache_key is not None:
        _cache_put(cache_key, source, mask)
    if layer.inverted:
        mask = 1.0 - mask
    return np.clip(mask * layer.opacity, 0.0, 1.0).astype(np.float32)


def _cache_get(key: tuple, source: np.ndarray) -> np.ndarray | None:
    global _cache_bytes
    with _CACHE_LOCK:
        entry = _SEMANTIC_CACHE.get(key)
        if entry is None:
            return None
        reference, packed = entry
        if reference() is not source:
            _cache_bytes -= packed.nbytes
            del _SEMANTIC_CACHE[key]
            return None
        _SEMANTIC_CACHE.move_to_end(key)
        return packed.astype(np.float32) / 255.0


def _cache_put(key: tuple, source: np.ndarray, mask: np.ndarray) -> None:
    global _cache_bytes
    packed = np.clip(np.rint(mask * 255.0), 0, 255).astype(np.uint8)
    with _CACHE_LOCK:
        previous = _SEMANTIC_CACHE.pop(key, None)
        if previous is not None:
            _cache_bytes -= previous[1].nbytes
        _SEMANTIC_CACHE[key] = (weakref.ref(source), packed)
        _cache_bytes += packed.nbytes
        while _cache_bytes > _CACHE_MAX_BYTES and _SEMANTIC_CACHE:
            _, (_, removed) = _SEMANTIC_CACHE.popitem(last=False)
            _cache_bytes -= removed.nbytes


def _coordinates(height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    return x / max(width - 1, 1), y / max(height - 1, 1)


def _linear(height: int, width: int, params: dict) -> np.ndarray:
    x, y = _coordinates(height, width)
    start = np.array([float(params.get("start_x", 0.5)), float(params.get("start_y", 0.0))], np.float32)
    end = np.array([float(params.get("end_x", 0.5)), float(params.get("end_y", 0.65))], np.float32)
    direction = end - start
    length_squared = max(float(np.dot(direction, direction)), 1e-6)
    projection = ((x - start[0]) * direction[0] + (y - start[1]) * direction[1]) / length_squared
    return np.clip(1.0 - projection, 0.0, 1.0)


def _radial(height: int, width: int, params: dict, feather: float) -> np.ndarray:
    x, y = _coordinates(height, width)
    center_x = float(params.get("center_x", 0.5))
    center_y = float(params.get("center_y", 0.5))
    radius_x = max(float(params.get("radius_x", 0.35)), 0.005)
    radius_y = max(float(params.get("radius_y", 0.35)), 0.005)
    angle = np.deg2rad(float(params.get("rotation", 0.0)))
    dx, dy = x - center_x, y - center_y
    rotated_x = np.cos(angle) * dx + np.sin(angle) * dy
    rotated_y = -np.sin(angle) * dx + np.cos(angle) * dy
    distance = np.sqrt((rotated_x / radius_x) ** 2 + (rotated_y / radius_y) ** 2)
    inner = max(0.0, 1.0 - max(feather, 0.01))
    return 1.0 - _smoothstep(inner, 1.0, distance)


def _luminance_range(source: np.ndarray, params: dict, feather: float) -> np.ndarray:
    rgb = source.astype(np.float32) / 255.0
    luma = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    low = float(params.get("min", 0.55))
    high = float(params.get("max", 1.0))
    softness = max(0.01, feather * 0.25)
    rising = _smoothstep(low - softness, low + softness, luma)
    falling = 1.0 - _smoothstep(high - softness, high + softness, luma)
    return rising * falling


def _color_range(source: np.ndarray, params: dict, feather: float) -> np.ndarray:
    hsv = cv2.cvtColor(source.astype(np.float32) / 255.0, cv2.COLOR_RGB2HSV)
    target_hue = float(params.get("hue", 210.0)) % 360.0
    tolerance = max(float(params.get("tolerance", 35.0)), 1.0)
    min_saturation = float(params.get("min_saturation", 0.08))
    hue_distance = np.abs((hsv[..., 0] - target_hue + 180.0) % 360.0 - 180.0)
    hue_weight = 1.0 - _smoothstep(tolerance * (0.35 + feather * 0.35), tolerance, hue_distance)
    sat_weight = _smoothstep(max(0.0, min_saturation - 0.08), min(1.0, min_saturation + 0.08), hsv[..., 1])
    return hue_weight * sat_weight


def _sky(source: np.ndarray) -> np.ndarray:
    height, width = source.shape[:2]
    rgb = source.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    luma = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    blur = cv2.GaussianBlur(luma, (0, 0), max(1.0, min(height, width) / 180.0))
    texture = cv2.GaussianBlur(np.abs(luma - blur), (0, 0), 2.0)
    _, y = _coordinates(height, width)
    upper = 1.0 - _smoothstep(0.35, 0.88, y)
    blue = 1.0 - _smoothstep(55.0, 105.0, np.abs((hsv[..., 0] - 210.0 + 180.0) % 360.0 - 180.0))
    blue *= _smoothstep(0.05, 0.22, hsv[..., 1])
    cloudy = (1.0 - _smoothstep(0.015, 0.07, texture)) * _smoothstep(0.34, 0.72, luma)
    probability = upper * np.maximum(blue, cloudy * 0.72)
    binary = (probability > 0.24).astype(np.uint8)
    binary = _top_connected(binary)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    soft = cv2.GaussianBlur(binary.astype(np.float32), (0, 0), max(1.2, min(height, width) / 220.0))
    return np.clip(np.maximum(probability * 0.65, soft), 0.0, 1.0)


def _top_connected(binary: np.ndarray) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if count <= 1:
        return binary
    output = np.zeros_like(binary)
    top_band = max(2, binary.shape[0] // 30)
    for label in range(1, count):
        component = labels == label
        if np.any(component[:top_band]) or stats[label, cv2.CC_STAT_AREA] > binary.size * 0.12:
            output[component] = 1
    return output


def _subject(source: np.ndarray) -> np.ndarray:
    """Image-driven foreground saliency; no fixed central ellipse fallback."""
    height, width = source.shape[:2]
    lab = cv2.cvtColor(source, cv2.COLOR_RGB2LAB).astype(np.float32)
    local = cv2.GaussianBlur(lab, (0, 0), max(5.0, min(height, width) / 22.0))
    contrast = np.linalg.norm(lab - local, axis=2)
    contrast = cv2.GaussianBlur(contrast, (0, 0), max(2.0, min(height, width) / 120.0))
    minimum, maximum = float(contrast.min()), float(contrast.max())
    if maximum - minimum < 2.0:
        return np.zeros((height, width), dtype=np.float32)
    return np.clip((contrast - np.percentile(contrast, 60)) / max(np.percentile(contrast, 96) - np.percentile(contrast, 60), 1e-4), 0, 1).astype(np.float32)


def _semantic(source: np.ndarray, label: str) -> np.ndarray:
    normalized = label.strip().lower()
    hsv = cv2.cvtColor(source.astype(np.float32) / 255.0, cv2.COLOR_RGB2HSV)
    height, width = source.shape[:2]
    if normalized == "sky":
        return _sky(source)
    if normalized in {"subject", "foreground"}:
        return _subject(source)
    if normalized == "person":
        return _people(source)
    if normalized == "vehicle":
        return _vehicle(source)
    if normalized in {"face", "skin"}:
        hue = hsv[..., 0]
        skin = ((hue < 52) | (hue > 345)).astype(np.float32)
        skin *= _smoothstep(0.08, 0.28, hsv[..., 1]) * (1.0 - _smoothstep(0.82, 1.0, hsv[..., 2]))
        return cv2.GaussianBlur(skin * _subject(source), (0, 0), 2.0)
    if normalized == "vegetation":
        hue_distance = np.abs((hsv[..., 0] - 115.0 + 180.0) % 360.0 - 180.0)
        return (1.0 - _smoothstep(28, 72, hue_distance)) * _smoothstep(0.12, 0.35, hsv[..., 1])
    if normalized == "water":
        hue_distance = np.abs((hsv[..., 0] - 205.0 + 180.0) % 360.0 - 180.0)
        blue = 1.0 - _smoothstep(35, 85, hue_distance)
        luma = source.astype(np.float32).mean(axis=2) / 255.0
        smooth = 1.0 - _local_texture(luma)
        return np.clip(blue * smooth * _largest_components(blue * smooth, 0.22), 0, 1)
    if normalized == "road":
        return _road(source)
    if normalized == "ground":
        return np.maximum(_road(source), _ground(source))
    if normalized in {"building", "architecture"}:
        return _building(source)
    if normalized == "background":
        return np.clip(1.0 - _subject(source), 0.0, 1.0)
    return np.zeros((height, width), dtype=np.float32)


def _local_texture(luma: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(luma, (0, 0), 3.0)
    texture = cv2.GaussianBlur(np.abs(luma - blur), (0, 0), 2.0)
    return np.clip(texture / max(float(np.percentile(texture, 90)), 1e-4), 0, 1)


def _largest_components(score: np.ndarray, threshold: float) -> np.ndarray:
    binary = (score > threshold).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    output = np.zeros_like(score, dtype=np.float32)
    if count <= 1:
        return output
    area_floor = score.size * 0.003
    for component in range(1, count):
        if stats[component, cv2.CC_STAT_AREA] >= area_floor:
            output[labels == component] = 1.0
    return output


def _road(source: np.ndarray) -> np.ndarray:
    """Conservative road candidate: connected smooth neutral surface + line geometry."""
    rgb = source.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    luma = rgb.mean(axis=2)
    smooth = 1.0 - _local_texture(luma)
    neutral = 1.0 - _smoothstep(0.16, 0.62, hsv[..., 1])
    edges = cv2.Canny(source, 55, 145)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=max(20, source.shape[1] // 12), minLineLength=max(18, source.shape[1] // 10), maxLineGap=18)
    line_map = np.zeros(source.shape[:2], dtype=np.float32)
    if lines is None:
        return line_map
    converging = 0
    left_boundaries: list[tuple[float, float]] = []
    right_boundaries: list[tuple[float, float]] = []
    for x1, y1, x2, y2 in lines[:, 0]:
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if 18 < angle < 162:
            cv2.line(line_map, (x1, y1), (x2, y2), 1.0, max(2, source.shape[1] // 160), cv2.LINE_AA)
            converging += 1
            if abs(y2 - y1) > 2:
                slope = (x2 - x1) / (y2 - y1)
                intercept = x1 - slope * y1
                if slope < -0.04:
                    left_boundaries.append((slope, intercept))
                elif slope > 0.04:
                    right_boundaries.append((slope, intercept))
    if converging < 2:
        return np.zeros_like(luma)
    if left_boundaries and right_boundaries:
        left = min(left_boundaries, key=lambda item: abs(item[0]))
        right = min(right_boundaries, key=lambda item: abs(item[0]))
        y_bottom = source.shape[0] - 1
        y_top = max(0, int(source.shape[0] * 0.18))
        left_top, right_top = left[0] * y_top + left[1], right[0] * y_top + right[1]
        left_bottom, right_bottom = left[0] * y_bottom + left[1], right[0] * y_bottom + right[1]
        if left_top < right_top and left_bottom < right_bottom:
            geometry = np.zeros_like(luma)
            polygon = np.array(
                [[left_bottom, y_bottom], [right_bottom, y_bottom], [right_top, y_top], [left_top, y_top]],
                dtype=np.int32,
            )
            cv2.fillConvexPoly(geometry, polygon, 1.0)
            return np.clip(geometry * neutral * (0.45 + 0.55 * smooth), 0, 1)
    candidate = cv2.GaussianBlur(line_map, (0, 0), max(5.0, min(source.shape[:2]) / 25.0)) * smooth * neutral
    components = _largest_components(candidate, 0.08)
    return np.clip(candidate * components * 2.2, 0, 1)


def _ground(source: np.ndarray) -> np.ndarray:
    rgb = source.astype(np.float32) / 255.0
    luma = rgb.mean(axis=2)
    texture = _local_texture(luma)
    edges = cv2.Canny(source, 60, 160).astype(np.float32) / 255.0
    horizontal = cv2.GaussianBlur(edges, (0, 0), max(3.0, min(source.shape[:2]) / 70.0))
    score = np.clip((texture * 0.65 + horizontal * 0.35), 0, 1)
    return score * _largest_components(score, 0.18)


def _building(source: np.ndarray) -> np.ndarray:
    rgb = source.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    neutral = 1.0 - _smoothstep(0.13, 0.72, hsv[..., 1])
    edges = cv2.Canny(source, 55, 155).astype(np.float32) / 255.0
    vertical = cv2.Sobel(edges, cv2.CV_32F, 1, 0, ksize=3)
    structural = cv2.GaussianBlur(np.abs(vertical), (0, 0), max(2.0, min(source.shape[:2]) / 110.0))
    structural /= max(float(np.percentile(structural, 92)), 1e-4)
    score = np.clip(neutral * structural, 0, 1)
    return score * _largest_components(score, 0.12)


def _people(source: np.ndarray) -> np.ndarray:
    detector = cv2.HOGDescriptor()
    detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    rectangles, weights = detector.detectMultiScale(source, winStride=(8, 8), padding=(8, 8), scale=1.05)
    mask = np.zeros(source.shape[:2], dtype=np.float32)
    for (x, y, width, height), weight in zip(rectangles, weights):
        if float(weight) >= 0.25:
            cv2.rectangle(mask, (x, y), (x + width, y + height), 1.0, -1)
    return cv2.GaussianBlur(mask, (0, 0), 2.0) if np.any(mask) else mask


def _vehicle(source: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(source, 70, 180)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros(source.shape[:2], dtype=np.float32)
    image_area = source.shape[0] * source.shape[1]
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = width * height
        if area < image_area * 0.004 or width < height * 1.25 or width > source.shape[1] * 0.75:
            continue
        perimeter = cv2.arcLength(contour, True)
        if perimeter and cv2.contourArea(contour) / perimeter < 1.5:
            continue
        cv2.rectangle(mask, (x, y), (x + width, y + height), 1.0, -1)
    return cv2.GaussianBlur(mask, (0, 0), 2.0) if np.any(mask) else mask


def mask_confidence(mask: np.ndarray, label: str | None = None) -> float:
    """Return a conservative confidence based on actual mask content, not a location prior."""
    coverage = float((mask >= 0.35).mean())
    if coverage < 0.008 or coverage > 0.88:
        return 0.0
    contrast = float(mask.std())
    if contrast < 0.035:
        return 0.0
    return min(1.0, (coverage / 0.06) * min(1.0, contrast / 0.18))


def _brush(height: int, width: int, strokes: list[BrushStroke]) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.float32)
    short_edge = min(height, width)
    for stroke in strokes:
        layer = np.zeros_like(mask)
        points = [(round(point.x * (width - 1)), round(point.y * (height - 1))) for point in stroke.points]
        radius = max(1, round(stroke.size * short_edge / 2.0))
        thickness = radius * 2
        if len(points) == 1:
            cv2.circle(layer, points[0], radius, stroke.opacity, -1, cv2.LINE_AA)
        else:
            for first, second in zip(points, points[1:]):
                cv2.line(layer, first, second, stroke.opacity, thickness, cv2.LINE_AA)
                cv2.circle(layer, second, radius, stroke.opacity, -1, cv2.LINE_AA)
        if stroke.hardness < 1:
            sigma = max(0.1, radius * (1.0 - stroke.hardness) * 0.65)
            layer = cv2.GaussianBlur(layer, (0, 0), sigma)
        if stroke.erase:
            mask *= 1.0 - layer
        else:
            mask = np.maximum(mask, layer)
    return np.clip(mask, 0.0, 1.0)


def _smoothstep(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    x = np.clip((values - edge0) / max(edge1 - edge0, 1e-6), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)
