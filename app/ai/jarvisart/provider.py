from __future__ import annotations

from app.ai.capabilities import ProviderConfig
from app.ai.jarvisart.adapter import JarvisArtAdapter
from app.ai.jarvisart.runtime import JarvisArtRuntime, MockJarvisArtRuntime, RealJarvisArtRuntimeStub
from app.ai.provider import AIProvider, PlanningRequest
from app.ai.schemas import EditingPlan


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
        native = self.runtime.infer(request.preview_jpeg, request.instruction, request.state)
        result = JarvisArtAdapter().adapt(native)
        self.last_unsupported_operations = list(result.unsupported_operations)
        return result.plan

    def test_connection(self) -> str:
        return f"JarvisArt Local: {self.runtime.status.state}"
