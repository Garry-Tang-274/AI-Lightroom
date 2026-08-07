from __future__ import annotations

from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import (
    CurveAdjustmentPlan,
    EditingPlan,
    GlobalAdjustment,
    HSLAdjustmentPlan,
    LocalAdjustmentPlan,
    LocalAdjustmentValues,
    MaskRequest,
)
from app.core.editor_state import HSLColor, MaskType


class MockProvider(AIProvider):
    """Offline planner that exercises the complete structured editing pipeline."""

    name = "Mock（离线）"

    def plan(self, request: PlanningRequest) -> EditingPlan:
        text = request.instruction.lower()
        if any(phrase in text for phrase in ("太重", "淡一点", "退一点", "减弱", "less intense", "tone it down")):
            return self._reduce_intensity(request, 0.65)

        global_ops: list[GlobalAdjustment] = []
        hsl_ops: list[HSLAdjustmentPlan] = []
        curve_ops: list[CurveAdjustmentPlan] = []
        mask_requests: list[MaskRequest] = []
        local_ops: list[LocalAdjustmentPlan] = []
        notes: list[str] = []

        def set_global(field: str, value: float) -> None:
            global_ops.append(GlobalAdjustment(tool=f"set_{field}", value=_clamp_field(field, value)))

        basic = request.state.basic
        cinematic = any(word in text for word in ("电影", "cinematic", "青橙", "moody", "氛围"))
        rainy = any(word in text for word in ("雨天", "rainy", "阴雨"))
        documentary = any(word in text for word in ("纪实", "documentary", "低饱和城市"))
        landscape = any(word in text for word in ("风光", "自然", "宏伟", "landscape"))
        flat = any(word in text for word in ("有点平", "太平", "灰", "层次", "flat"))

        if cinematic:
            set_global("contrast", basic.contrast + 9)
            set_global("highlights", min(basic.highlights, -18))
            set_global("shadows", max(basic.shadows, 9))
            set_global("saturation", basic.saturation - (8 if rainy else 5))
            set_global("vibrance", basic.vibrance + 7)
            set_global("clarity", basic.clarity + 5)
            set_global("dehaze", basic.dehaze + 4)
            set_global("vignette", min(basic.vignette, -8))
            hsl_ops.extend(
                [
                    HSLAdjustmentPlan(color=HSLColor.BLUE, hue=-5 if rainy else -2, saturation=-7, luminance=-5),
                    HSLAdjustmentPlan(color=HSLColor.ORANGE, hue=0, saturation=4, luminance=3),
                ]
            )
            curve_ops.append(
                CurveAdjustmentPlan(
                    tool="set_rgb_curve",
                    points=[
                        {"x": 0.0, "y": 0.025},
                        {"x": 0.25, "y": 0.22},
                        {"x": 0.72, "y": 0.76},
                        {"x": 1.0, "y": 0.985},
                    ],
                )
            )
            notes.append("建立克制的电影感明暗与冷暖层次")

        if documentary:
            set_global("contrast", basic.contrast + 7)
            set_global("highlights", min(basic.highlights, -18))
            set_global("shadows", max(basic.shadows, 8))
            set_global("saturation", basic.saturation - 14)
            set_global("clarity", basic.clarity + 4)
            hsl_ops.append(HSLAdjustmentPlan(color=HSLColor.YELLOW, saturation=-10))
            notes.append("降低干扰色彩并保留纪实层次")

        if landscape:
            set_global("contrast", basic.contrast + 8)
            set_global("highlights", min(basic.highlights, -22))
            set_global("shadows", max(basic.shadows, 16))
            set_global("vibrance", basic.vibrance + 11)
            set_global("clarity", basic.clarity + 7)
            set_global("dehaze", basic.dehaze + 7)
            notes.append("加强风光尺度感，同时保护高光和阴影")

        if flat and not (cinematic or documentary or landscape):
            set_global("contrast", basic.contrast + 8)
            set_global("highlights", basic.highlights - 12)
            set_global("shadows", basic.shadows + 10)
            set_global("clarity", basic.clarity + 6)
            set_global("dehaze", basic.dehaze + 3)
            notes.append("恢复画面层次，避免 HDR 感")

        if any(word in text for word in ("天空", "sky")) and any(word in text for word in ("压暗", "压一点", "暗一点", "dark", "dramatic", "宏伟")):
            reference, mask_request = _find_or_request_mask(request, "sky", "AI — 天空", "create_sky_mask", "sky_1")
            if mask_request:
                mask_requests.append(mask_request)
            current_exposure, current_highlights = _local_values(request, reference)
            local_ops.append(
                LocalAdjustmentPlan(
                    mask_ref=reference,
                    adjustments=LocalAdjustmentValues(
                        exposure=max(-5, current_exposure - 0.3),
                        highlights=max(-100, current_highlights - 15),
                        dehaze=5 if landscape else None,
                    ),
                )
            )
            notes.append("仅在天空蒙版内压暗并控制高光")

        if any(word in text for word in ("地面提亮", "提亮地面", "ground brighter")):
            reference, mask_request = _find_or_request_mask(request, "ground", "AI — 地面", "create_semantic_mask", "ground_1")
            if mask_request:
                mask_requests.append(mask_request)
            current_exposure, _ = _local_values(request, reference)
            local_ops.append(LocalAdjustmentPlan(mask_ref=reference, adjustments=LocalAdjustmentValues(exposure=current_exposure + 0.3, shadows=15)))
            notes.append("只提亮地面")

        if any(word in text for word in ("建筑") ) and any(word in text for word in ("太黄", "偏黄", "冷一点")):
            reference, mask_request = _find_or_request_mask(request, "building", "AI — 建筑", "create_semantic_mask", "building_1")
            if mask_request:
                mask_requests.append(mask_request)
            local_ops.append(LocalAdjustmentPlan(mask_ref=reference, adjustments=LocalAdjustmentValues(temperature=-8, tint=-2, saturation=-4)))
            notes.append("仅降低建筑的偏黄")

        if any(word in text for word in ("刷", "选中蒙版", "这块")) and any(word in text for word in ("冷", "偏蓝")):
            local_ops.append(LocalAdjustmentPlan(mask_ref="selected", adjustments=LocalAdjustmentValues(temperature=-12)))
            notes.append("只调整当前选中的画笔蒙版")

        if not any((global_ops, hsl_ops, curve_ops, mask_requests, local_ops)):
            set_global("contrast", basic.contrast + 5)
            set_global("highlights", basic.highlights - 8)
            set_global("shadows", basic.shadows + 6)
            notes.append("做轻量、自然的层次优化")

        summary = "；".join(notes) or "已应用结构化调整"
        return EditingPlan(
            summary=summary,
            reasoning_summary="根据当前编辑状态选择可逆参数；区域要求通过独立蒙版执行。",
            global_adjustments=global_ops,
            hsl_adjustments=hsl_ops,
            curve_adjustments=curve_ops,
            requested_masks=mask_requests,
            local_adjustments=local_ops,
            confidence=0.78,
            needs_reinspection=False,
        )

    def _reduce_intensity(self, request: PlanningRequest, factor: float) -> EditingPlan:
        global_ops: list[GlobalAdjustment] = []
        for field, value in request.state.basic.model_dump().items():
            if value:
                global_ops.append(GlobalAdjustment(tool=f"set_{field}", value=value * factor))
        hsl_ops = []
        for color, values in request.state.hsl.items():
            if values.hue or values.saturation or values.luminance:
                hsl_ops.append(
                    HSLAdjustmentPlan(
                        color=color,
                        hue=values.hue * factor,
                        saturation=values.saturation * factor,
                        luminance=values.luminance * factor,
                    )
                )
        local_ops = []
        for layer in request.state.masks:
            values = {key: value * factor for key, value in layer.adjustments.model_dump().items() if value}
            if values:
                local_ops.append(LocalAdjustmentPlan(mask_ref=layer.id, adjustments=LocalAdjustmentValues(**values)))
        return EditingPlan(
            summary="已将当前效果整体减弱约三分之一，并保留现有蒙版结构。",
            reasoning_summary="这是基于当前状态的增量回退，不会重做或覆盖已建立的区域关系。",
            global_adjustments=global_ops,
            hsl_adjustments=hsl_ops,
            local_adjustments=local_ops,
            confidence=0.93,
            needs_reinspection=False,
        )


def _find_or_request_mask(
    request: PlanningRequest,
    semantic: str,
    name: str,
    tool: str,
    ref: str,
) -> tuple[str, MaskRequest | None]:
    for layer in request.state.masks:
        if layer.semantic_label == semantic or layer.type.value == semantic or semantic in layer.name.lower():
            return layer.id, None
    return ref, MaskRequest(tool=tool, ref=ref, name=name, semantic_label=semantic if tool == "create_semantic_mask" else None)


def _local_values(request: PlanningRequest, reference: str) -> tuple[float, float]:
    for layer in request.state.masks:
        if layer.id == reference:
            return layer.adjustments.exposure, layer.adjustments.highlights
    return 0.0, 0.0


def _clamp_field(field: str, value: float) -> float:
    if field == "exposure":
        return max(-5.0, min(5.0, value))
    if field == "sharpen":
        return max(0.0, min(100.0, value))
    return max(-100.0, min(100.0, value))
