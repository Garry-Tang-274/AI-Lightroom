from __future__ import annotations

from app.ai.capabilities import ProviderConfig
from app.ai.errors import AIRequestError
from app.ai.jarvisart.adapter import JarvisArtAdapter
from app.ai.jarvisart.runtime import JarvisArtRuntime, MockJarvisArtRuntime, RealJarvisArtRuntimeStub
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import EditingPlan
from pydantic import ValidationError


class JarvisArtProvider(AIProvider):
    id = "jarvisart_local"

    def __init__(self, config: ProviderConfig, *, runtime: JarvisArtRuntime | None = None, **_kwargs) -> None:
        self.config = config
        self.runtime = runtime or (RealJarvisArtRuntimeStub() if config.local_mode == "real" else MockJarvisArtRuntime())
        self.name = f"JarvisArt Local · {self.runtime.status.state}"
        self.capabilities = config.capabilities
        self.last_unsupported_operations: list[str] = []

    @property
    def runtime_status(self):
        return self.runtime.status

    def plan(self, request: PlanningRequest) -> EditingPlan:
        try:
            native = self.runtime.infer(request.preview_jpeg, request.instruction, request.state)
        except AIRequestError:
            raise
        except ValidationError as exc:
            raise AIRequestError(
                "JarvisArt fixture parse failed",
                "本地 JarvisArt NativePlan 不符合预期的原生输出结构。",
                provider="JarvisArt Local", model=self.config.model,
                validation_errors=exc.errors(include_url=False), request_sent=False,
            ) from exc
        try:
            result = JarvisArtAdapter().adapt(native)
        except (ValidationError, ValueError) as exc:
            raise AIRequestError(
                "JarvisArt adapter unsupported output",
                "JarvisArt NativePlan 无法安全映射到当前 AI Lightroom EditingPlan。",
                provider="JarvisArt Local", model=self.config.model,
                local_exception=type(exc).__name__, request_sent=False,
            ) from exc
        self.last_unsupported_operations = list(result.unsupported_operations)
        return result.plan

    def test_connection(self) -> str:
        return f"JarvisArt Local: {self.runtime.status.state}"
