from __future__ import annotations

from google import genai
from google.genai import types
from google.genai._transformers import t_schema
from pydantic import ValidationError

from app.ai.errors import AIRequestError, error_from_exception, safe_validation_errors
from app.ai.prompt_builder import build_prompt
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import EditingPlan, gemini_response_schema
from app.ai.system_prompt import DEFAULT_SYSTEM_PROMPT


class GeminiProvider(AIProvider):
    name = "Gemini"

    def __init__(self, api_key: str, model: str, client=None, *, system_prompt: str = DEFAULT_SYSTEM_PROMPT, on_request_started=None, on_result=None) -> None:
        if not api_key and client is None:
            raise ValueError("Gemini API Key 为空")
        self.model = model
        self.client = client or genai.Client(api_key=api_key)
        self._api_key = api_key
        self.system_prompt = system_prompt
        self.on_request_started = on_request_started
        self.on_result = on_result

    @staticmethod
    def validate_response_schema() -> None:
        """Fail locally before billing if Pydantic emits an unsupported Gemini schema."""
        try:
            # Run the same Pydantic-to-Gemini conversion the SDK performs,
            # including reference flattening, without issuing a network request.
            t_schema(None, gemini_response_schema())
        except ValidationError as exc:
            raise AIRequestError(
                category="Gemini structured output 配置错误",
                message="本地 EditingPlan JSON Schema 不兼容 Gemini SDK，云端请求未发出。",
                local_exception=type(exc).__name__,
                validation_errors=safe_validation_errors(exc),
                request_sent=False,
            ) from exc

    def plan(self, request: PlanningRequest) -> EditingPlan:
        self.validate_response_schema()
        contents: list[object] = [build_prompt(request, self.system_prompt)]
        if request.preview_jpeg:
            contents.append(types.Part.from_bytes(data=request.preview_jpeg, mime_type="image/jpeg"))
        if self.on_request_started:
            self.on_request_started()
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=gemini_response_schema(),
                    http_options=types.HttpOptions(timeout=120_000, retry_options=types.HttpRetryOptions(attempts=1)),
                ),
            )
        except Exception as exc:
            raise error_from_exception(exc, model=self.model, request_sent=True, secrets=(self._api_key,)) from exc
        if not response.text:
            raise AIRequestError("Gemini 返回空内容", "Gemini 未返回可执行的 EditingPlan。", model=self.model, request_sent=True)
        try:
            plan = EditingPlan.model_validate_json(response.text)
        except ValidationError as exc:
            raise AIRequestError(
                category="Pydantic schema 校验错误",
                message="Gemini 返回 JSON 不符合严格 EditingPlan schema。",
                model=self.model,
                local_exception=type(exc).__name__,
                validation_errors=safe_validation_errors(exc),
                request_sent=True,
            ) from exc
        if self.on_result:
            usage = getattr(response, "usage_metadata", None)
            self.on_result(
                "成功",
                getattr(usage, "prompt_token_count", None),
                getattr(usage, "candidates_token_count", None),
                getattr(usage, "total_token_count", None),
            )
        return plan

    def test_connection(self) -> str:
        if self.on_request_started:
            self.on_request_started()
        try:
            response = self.client.models.generate_content(
                model=self.model, contents="Reply with OK only.",
                config=types.GenerateContentConfig(
                    max_output_tokens=128,
                    http_options=types.HttpOptions(timeout=120_000, retry_options=types.HttpRetryOptions(attempts=1)),
                ),
            )
        except Exception as exc:
            raise error_from_exception(exc, model=self.model, request_sent=True, secrets=(self._api_key,)) from exc
        if not response.text:
            raise AIRequestError("Gemini 返回空内容", "连接测试没有返回文本。", model=self.model, request_sent=True)
        if self.on_result:
            usage = getattr(response, "usage_metadata", None)
            self.on_result("连接测试成功", getattr(usage, "prompt_token_count", None), getattr(usage, "candidates_token_count", None), getattr(usage, "total_token_count", None))
        return "文字连接测试通过；图片分析与结构化调色需在编辑器中验证。"
