from __future__ import annotations

import json

from app.ai.provider import PlanningRequest
from app.ai.schemas import AVAILABLE_TOOLS, editing_plan_json_contract
from app.ai.style_strategies import STYLE_STRATEGIES
from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT


def build_prompt(request: PlanningRequest, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    masks = [
        {
            "id": layer.id,
            "name": layer.name,
            "type": layer.type.value,
            "semantic_label": layer.semantic_label,
            "adjustments": layer.adjustments.model_dump(),
        }
        for layer in request.state.masks
    ]
    # Watermark asset identifiers and long brush strokes are local rendering inputs,
    # not model capabilities. Only transmit editable state and mask references.
    editor_state = request.state.model_dump(mode="json", exclude={"watermarks", "masks"})
    editor_state["masks"] = masks
    payload = {
        "user_instruction": request.instruction,
        "is_reinspection": request.is_reinspection,
        "current_editor_state": editor_state,
        "current_masks": masks,
        "recent_history": request.history_summary[-8:],
        "available_tools": AVAILABLE_TOOLS,
        "style_strategies": STYLE_STRATEGIES,
        "preview_attached": request.preview_jpeg is not None,
    }
    return (
        system_prompt.strip()
        + "\n\n"
        + editing_plan_json_contract()
        + "\n当前任务上下文：\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
