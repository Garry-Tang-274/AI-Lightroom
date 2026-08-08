from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image

from app.ai.executor import ExecutionResult, apply_editing_plan
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import EditingPlan
from app.core.editor_state import EditorState
from app.core.image_processor import render_image
from app.core.masks import generate_mask, mask_confidence
from app.core.editor_state import MaskType


_VISIONLESS_PATTERNS = re.compile(
    r"(太重|淡一点|退一点|减弱|减半|恢复一点|对比弱一点|饱和度少一点|less intense|tone it down)",
    re.IGNORECASE,
)
_FORCE_VISION_PATTERNS = re.compile(r"(重新看看|再看|是不是|脸|天空.*太暗|look again|reinspect)", re.IGNORECASE)


@dataclass(slots=True)
class AIProcessResult:
    state: EditorState
    plans: list[EditingPlan]
    changed_fields: list[str]
    created_masks: list[str]
    provider_name: str
    vision_calls: int
    unsupported_operations: list[str]
    analysis_preview_max_edge: int

    @property
    def final_plan(self) -> EditingPlan:
        return self.plans[-1]


class AIOrchestrator:
    def __init__(
        self,
        provider: AIProvider,
        *,
        preview_size: int = 1280,
        jpeg_quality: int = 85,
        reinspection_enabled: bool = True,
        max_vision_calls: int = 2,
    ) -> None:
        self.provider = provider
        self.preview_size = max(512, min(4096, preview_size))
        self.jpeg_quality = max(70, min(95, jpeg_quality))
        self.reinspection_enabled = reinspection_enabled
        self.max_vision_calls = max(1, min(2, max_vision_calls))

    def process(
        self,
        instruction: str,
        source_preview: np.ndarray,
        state: EditorState,
        history_summary: list[str],
        selected_mask_id: str | None = None,
    ) -> AIProcessResult:
        use_vision = self.should_use_vision(instruction) or bool(getattr(self.provider, "requires_visual_input", False))
        rendered = render_image(source_preview, state)
        preview_jpeg = encode_preview(rendered, self.preview_size, self.jpeg_quality) if use_vision else None
        request = PlanningRequest(instruction, state.snapshot(), preview_jpeg, history_summary)
        plan = self.provider.plan(request)
        execution = apply_editing_plan(state, plan, selected_mask_id)
        _reject_unreliable_masks(source_preview, state, execution)
        plans = [plan]
        changed = execution.changed_fields.copy()
        created = execution.created_masks.copy()
        vision_calls = 1 if use_vision else 0
        unsupported = list(getattr(self.provider, "last_unsupported_operations", ()))

        if (
            plan.needs_reinspection
            and self.reinspection_enabled
            and vision_calls < self.max_vision_calls
        ):
            rerendered = render_image(source_preview, execution.state)
            followup = PlanningRequest(
                instruction="重新检查刚才的结果，只输出必要的微调，不重复已经正确的操作。",
                state=execution.state.snapshot(),
                preview_jpeg=encode_preview(rerendered, self.preview_size, self.jpeg_quality),
                history_summary=history_summary + [plan.summary],
                is_reinspection=True,
            )
            second_plan = self.provider.plan(followup)
            second = apply_editing_plan(execution.state, second_plan, selected_mask_id)
            _reject_unreliable_masks(source_preview, execution.state, second)
            execution = second
            plans.append(second_plan)
            changed.extend(second.changed_fields)
            created.extend(second.created_masks)
            vision_calls += 1
            unsupported.extend(getattr(self.provider, "last_unsupported_operations", ()))

        return AIProcessResult(
            state=execution.state,
            plans=plans,
            changed_fields=changed,
            created_masks=created,
            provider_name=self.provider.name,
            vision_calls=vision_calls,
            unsupported_operations=list(dict.fromkeys(unsupported)),
            analysis_preview_max_edge=self.preview_size,
        )

    @staticmethod
    def should_use_vision(instruction: str) -> bool:
        if _FORCE_VISION_PATTERNS.search(instruction):
            return True
        return not bool(_VISIONLESS_PATTERNS.search(instruction))


def encode_preview(pixels: np.ndarray, max_edge: int = 1280, quality: int = 85) -> bytes:
    image = Image.fromarray(pixels, "RGB")
    scale = min(1.0, max_edge / max(image.size))
    if scale < 1.0:
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True, subsampling=2)
    return output.getvalue()


def _reject_unreliable_masks(source: np.ndarray, prior_state: EditorState, execution: ExecutionResult) -> None:
    """AI mask requests use the same local image analysis as the manual UI."""
    existing_ids = {layer.id for layer in prior_state.masks}
    rejected: list[str] = []
    retained = []
    for layer in execution.state.masks:
        if layer.id in existing_ids or layer.type not in {MaskType.SKY, MaskType.SUBJECT, MaskType.SEMANTIC}:
            retained.append(layer)
            continue
        confidence = mask_confidence(generate_mask(source, layer), layer.semantic_label or layer.type.value)
        if confidence <= 0:
            rejected.append(layer.name)
            continue
        layer.parameters["mask_confidence"] = confidence
        retained.append(layer)
    if rejected:
        execution.state.masks = retained
        execution.created_masks[:] = [name for name in execution.created_masks if name not in rejected]
        execution.changed_fields.extend([f"未能可靠识别 {name}，未创建蒙版" for name in rejected])
