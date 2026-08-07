from __future__ import annotations

from google import genai
from google.genai import types

from app.ai.prompt_builder import build_prompt
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import EditingPlan


class GeminiProvider(AIProvider):
    name = "Gemini"

    def __init__(self, api_key: str, model: str, client=None) -> None:
        if not api_key and client is None:
            raise ValueError("Gemini API Key 为空")
        self.model = model
        self.client = client or genai.Client(api_key=api_key)

    def plan(self, request: PlanningRequest) -> EditingPlan:
        contents: list[object] = [build_prompt(request)]
        if request.preview_jpeg:
            contents.append(types.Part.from_bytes(data=request.preview_jpeg, mime_type="image/jpeg"))
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EditingPlan,
            ),
        )
        if not response.text:
            raise ValueError("Gemini 没有返回编辑计划")
        return EditingPlan.model_validate_json(response.text)

