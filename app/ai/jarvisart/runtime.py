from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.ai.errors import AIRequestError
from app.ai.jarvisart.schemas import JarvisArtNativePlan
from app.core.editor_state import EditorState


@dataclass(frozen=True, slots=True)
class JarvisArtRuntimeStatus:
    mode: str
    state: str
    message: str


class JarvisArtRuntime(ABC):
    @property
    @abstractmethod
    def status(self) -> JarvisArtRuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def infer(self, preview_jpeg: bytes | None, instruction: str, state: EditorState) -> JarvisArtNativePlan:
        raise NotImplementedError


class RealJarvisArtRuntimeStub(JarvisArtRuntime):
    """Future official local-model hook; never falls back to a cloud provider."""

    @property
    def status(self) -> JarvisArtRuntimeStatus:
        return JarvisArtRuntimeStatus("real", "Real Model Not Installed", "官方 JarvisArt 本地模型尚未安装。")

    def infer(self, preview_jpeg: bytes | None, instruction: str, state: EditorState) -> JarvisArtNativePlan:
        raise AIRequestError(
            "JarvisArt 本地模型未安装",
            "Real Native 模式需要先安装官方 JarvisArt-1208 权重和本地运行环境；本次没有发送云端请求。",
            provider="JarvisArt Local",
            model="JarvisArt-1208",
            request_sent=False,
        )


class MockJarvisArtRuntime(JarvisArtRuntime):
    @property
    def status(self) -> JarvisArtRuntimeStatus:
        return JarvisArtRuntimeStatus("mock", "Mock Native Ready", "本地 fixture 模拟原生 JarvisArt 输出；不上传照片，也不产生云端费用。")

    def infer(self, preview_jpeg: bytes | None, instruction: str, state: EditorState) -> JarvisArtNativePlan:
        lowered = instruction.lower()
        road = any(term in lowered for term in ("road", "公路", "道路", "荒漠"))
        plan = {
            "summary": "本地 JarvisArt Mock 已生成可执行调色方案。",
            "reasoning_summary": "以克制的局部对比和低饱和为主，所有输出均通过本地适配器验证。",
            "global_adjustments": [
                {"parameter": "Exposure2012", "value": -0.22 if road else 0.12},
                {"parameter": "Contrast2012", "value": 10 if road else 6},
                {"parameter": "Vibrance", "value": -7 if road else 3},
            ],
            "hsl_adjustments": [{"color": "blue", "hue": -3, "saturation": -8, "luminance": -5}],
            "curves": [{"channel": "rgb", "points": [{"x": 0, "y": 0}, {"x": 64, "y": 55}, {"x": 192, "y": 204}, {"x": 255, "y": 255}]}],
            "local_regions": [],
            "unsupported_operations": [],
            "confidence": 0.76,
        }
        if road:
            plan["local_regions"] = [
                {"mask": {"ref": "road_1", "name": "Road", "type": "semantic", "semantic_label": "road"}, "adjustments": [{"parameter": "LocalExposure2012", "value": -0.22}, {"parameter": "LocalClarity2012", "value": 12}]},
                {"mask": {"ref": "sky_1", "name": "Sky", "type": "sky"}, "adjustments": [{"parameter": "LocalHighlights2012", "value": -16}]},
            ]
        return JarvisArtNativePlan.model_validate(plan)
