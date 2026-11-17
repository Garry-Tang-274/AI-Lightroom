from __future__ import annotations

import base64

from openai import OpenAI
from pydantic import ValidationError

from app.ai.errors import AIRequestError, error_from_exception, safe_validation_errors
from app.ai.prompt_builder import build_prompt
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import EditingPlan, openai_response_schema
from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT


class OpenAIProvider(AIProvider):
    """Vision-only planner: the Responses API is asked for an EditingPlan, never pixels."""

    name = "OpenAI"

    def __init__(self, api_key: str, model: str, client=None, *, system_prompt: str = DEFAULT_SYSTEM_PROMPT, on_request_started=None, on_result=None) -> None:
        if not api_key and client is None:
            raise ValueError("OpenAI API Key 为空")
        self.model = model
        self.client = client or OpenAI(api_key=api_key, max_retries=0, timeout=120.0)
        self._api_key = api_key
        self.system_prompt = system_prompt
        self.on_request_started = on_request_started
        self.on_result = on_result

    def plan(self, request: PlanningRequest) -> EditingPlan:
        content: list[dict[str, object]] = [{"type": "input_text", "text": build_prompt(request, "")}]
        if request.preview_jpeg:
            image_url = "data:image/jpeg;base64," + base64.b64encode(request.preview_jpeg).decode("ascii")
            content.append({"type": "input_image", "image_url": image_url, "detail": "high"})
        if self.on_request_started:
            self.on_request_started()
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=self.system_prompt,
                input=[{"role": "user", "content": content}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "editing_plan",
                        "strict": True,
                        "schema": openai_response_schema(),
                    }
                },
            )
        except Exception as exc:
            raise error_from_exception(exc, model=self.model, request_sent=True, provider=self.name, secrets=(self._api_key,)) from exc
        text = getattr(response, "output_text", "")
        if not text:
            raise AIRequestError(
                "OpenAI 返回空内容", "OpenAI 未返回可执行的 EditingPlan。",
                provider=self.name, model=self.model, request_sent=True,
            )
        try:
            plan = EditingPlan.model_validate_json(text)
        except ValidationError as exc:
            raise AIRequestError(
                category="Pydantic schema 校验错误",
                message="OpenAI 返回 JSON 不符合严格 EditingPlan schema。",
                provider=self.name,
                model=self.model,
                local_exception=type(exc).__name__,
                validation_errors=safe_validation_errors(exc),
                request_sent=True,
            ) from exc
        if self.on_result:
            usage = getattr(response, "usage", None)
            self.on_result(
                "成功",
                getattr(usage, "input_tokens", None),
                getattr(usage, "output_tokens", None),
                getattr(usage, "total_tokens", None),
            )
        return plan

    def test_connection(self) -> str:
        if self.on_request_started:
            self.on_request_started()
        try:
            response = self.client.responses.create(
                model=self.model, input="Reply with OK only.", max_output_tokens=128,
            )
        except Exception as exc:
            raise error_from_exception(exc, model=self.model, request_sent=True, provider=self.name, secrets=(self._api_key,)) from exc
        if not getattr(response, "output_text", ""):
            raise AIRequestError("OpenAI 返回空内容", "连接测试没有返回文本。", provider=self.name, model=self.model, request_sent=True)
        if self.on_result:
            usage = getattr(response, "usage", None)
            self.on_result("连接测试成功", getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None), getattr(usage, "total_tokens", None))
        return "文字连接测试通过；图片分析与结构化调色需在编辑器中验证。"
