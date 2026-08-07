from __future__ import annotations

import json

from app.ai.provider import PlanningRequest
from app.ai.schemas import AVAILABLE_TOOLS
from app.ai.style_strategies import STYLE_STRATEGIES


SYSTEM_PROMPT = """你是专业摄影后期规划器。你只能规划确定性的像素处理，不能生成或重绘照片。
先看当前画面与完整编辑状态，再输出结构化 EditingPlan。所有数值是目标绝对值，不是增量。
优先做最小、可逆的调整。区域性要求必须使用蒙版；例如“天空压暗但地面不变”必须创建或复用天空蒙版，不能降低全局曝光。
后续命令基于当前状态继续编辑，不要擅自重置已满意的区域。避免 HDR 感、死黑、过饱和、光晕和过度青橙。
reasoning_summary 只写一两句可解释依据，不输出隐藏推理过程。只能使用给定工具。"""


def build_prompt(request: PlanningRequest) -> str:
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
    payload = {
        "user_instruction": request.instruction,
        "is_reinspection": request.is_reinspection,
        "current_editor_state": request.state.model_dump(mode="json"),
        "current_masks": masks,
        "recent_history": request.history_summary[-8:],
        "available_tools": AVAILABLE_TOOLS,
        "style_strategies": STYLE_STRATEGIES,
        "preview_attached": request.preview_jpeg is not None,
    }
    return SYSTEM_PROMPT + "\n\n当前任务上下文：\n" + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

