from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.ai.errors import AIRequestError
from app.ai.jarvisart.schemas import JarvisArtNativePlan
from app.ai.jarvisart.service import JarvisArtServiceManager
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
    """Local GGUF/native hook; never falls back to a cloud provider."""

    @property
    def status(self) -> JarvisArtRuntimeStatus:
        return JarvisArtRuntimeStatus("real", "Local GGUF Model Not Installed", "本地 JarvisArt GGUF / 原生运行环境尚未安装。")

    def infer(self, preview_jpeg: bytes | None, instruction: str, state: EditorState) -> JarvisArtNativePlan:
        raise AIRequestError(
            "JarvisArt 本地模型未安装",
            "Local GGUF 模式需要先安装用户自己的 JarvisArt 兼容 GGUF 和本地运行环境；本次没有发送云端请求。",
            provider="JarvisArt Local GGUF",
            model="qwen2_vl",
            request_sent=False,
        )


class LocalJarvisArtRuntime(JarvisArtRuntime):
    """Localhost client for the separately installed JarvisArt service.

    It sends a temporary, configured JPEG preview through loopback only. The
    original image, model weights, and the GGUF/native runtime remain outside
    this app.
    """

    def __init__(self, root: str = "", endpoint: str = "http://127.0.0.1:8765", *, auto_start: bool = True, manager: JarvisArtServiceManager | None = None) -> None:
        self.manager = manager or JarvisArtServiceManager(root, endpoint)
        self.auto_start = auto_start

    @property
    def status(self) -> JarvisArtRuntimeStatus:
        status = self.manager.status()
        return JarvisArtRuntimeStatus("real", status.state, status.message)

    def start(self) -> JarvisArtRuntimeStatus:
        status = self.manager.start()
        return JarvisArtRuntimeStatus("real", status.state, status.message)

    def stop(self) -> JarvisArtRuntimeStatus:
        status = self.manager.stop_owned()
        return JarvisArtRuntimeStatus("real", status.state, status.message)

    def infer(self, preview_jpeg: bytes | None, instruction: str, state: EditorState) -> JarvisArtNativePlan:
        if not preview_jpeg:
            raise AIRequestError("JarvisArt 缺少预览图", "JarvisArt 本地视觉分析需要当前 JPEG 预览图。", provider="JarvisArt Local GGUF", model="qwen2_vl")
        status = self.manager.status()
        if status.state != "Ready":
            if not self.auto_start:
                raise AIRequestError("JarvisArt 服务离线", status.message, provider="JarvisArt Local GGUF", model=status.model or "qwen2_vl")
            status = self.manager.start()
            if status.state != "Ready":
                raise AIRequestError("JarvisArt 启动失败", status.message, provider="JarvisArt Local GGUF", model=status.model or "qwen2_vl")
        temp_path: Path | None = None
        try:
            with NamedTemporaryFile(prefix="ai-lightroom-jarvisart-", suffix=".jpg", delete=False) as handle:
                handle.write(preview_jpeg)
                temp_path = Path(handle.name)
            request = Request(
                self.manager.endpoint + "/develop_settings",
                data=json.dumps({"photo_path": str(temp_path), "prompt": instruction}).encode("utf-8"),
                headers={"Content-Type": "application/json", "Accept": "text/plain"}, method="POST",
            )
            # Local quantized models can take several minutes on consumer
            # hardware.  This runs in the dedicated AI worker, so favour a
            # reliable local result over a cloud-style short request deadline.
            with urlopen(request, timeout=300.0) as response:
                lua = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            raise AIRequestError("JarvisArt 本地服务错误", detail or f"HTTP {exc.code}", provider="JarvisArt Local GGUF", model=status.model or "qwen2_vl", http_status=exc.code) from exc
        except (URLError, OSError, TimeoutError) as exc:
            raise AIRequestError("JarvisArt 服务离线或超时", "无法完成本地 JarvisArt GGUF 推理；照片未发生任何修改。", provider="JarvisArt Local GGUF", model=status.model or "qwen2_vl", local_exception=type(exc).__name__) from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
        return parse_jarvisart_lua(lua)


def parse_jarvisart_lua(lua: str) -> JarvisArtNativePlan:
    """Parse the scalar Lightroom Lua returned by the existing local bridge.

    This deliberately accepts only a compact safe subset. Unknown Lightroom
    settings remain visible as unsupported operations instead of being guessed.
    """
    source = lua.removeprefix("return").strip()
    scalar_pairs = re.findall(r'(?:\["([^"\\]+)"\]|([A-Za-z_][A-Za-z0-9_]*))\s*=\s*(-?\d+(?:\.\d+)?)', source)
    hsl: dict[str, dict[str, float]] = {}
    global_adjustments: list[dict[str, object]] = []
    unsupported: list[dict[str, str]] = []
    known = {
        "Exposure2012", "Contrast2012", "Highlights2012", "Shadows2012", "Whites2012", "Blacks2012",
        "IncrementalTemperature", "IncrementalTint", "Saturation", "Vibrance", "Clarity2012", "Texture", "Dehaze", "Sharpness", "PostCropVignetteAmount",
    }
    for quoted, bare, raw_value in scalar_pairs:
        parameter = quoted or bare
        value = float(raw_value)
        match = re.fullmatch(r"(Hue|Saturation|Luminance)Adjustment(Red|Orange|Yellow|Green|Aqua|Blue|Purple|Magenta)", parameter)
        if match:
            field = {"Hue": "hue", "Saturation": "saturation", "Luminance": "luminance"}[match.group(1)]
            hsl.setdefault(match.group(2).lower(), {})[field] = value
        elif parameter in known:
            global_adjustments.append({"parameter": parameter, "value": value})
        elif parameter not in {"ProcessVersion", "Temperature", "Tint", "WhiteBalance"}:
            unsupported.append({"operation": parameter, "reason": "当前 AI Lightroom 本地渲染器不支持该 JarvisArt Lightroom 参数"})
    if not scalar_pairs:
        raise AIRequestError("JarvisArt 原生输出无效", "本地 JarvisArt GGUF 服务未返回可解析的 Lightroom 参数。", provider="JarvisArt Local GGUF", model="qwen2_vl")
    return JarvisArtNativePlan.model_validate({
        "summary": "JarvisArt 已生成本地 Lightroom 调整方案。",
        "reasoning_summary": "已将 JarvisArt 返回的 Lightroom 全局参数安全映射到当前编辑器。",
        "global_adjustments": global_adjustments,
        "hsl_adjustments": [{"color": color, **values} for color, values in hsl.items()],
        "curves": [], "local_regions": [], "unsupported_operations": unsupported, "confidence": 0.78,
    })


class MockJarvisArtRuntime(JarvisArtRuntime):
    @property
    def status(self) -> JarvisArtRuntimeStatus:
        return JarvisArtRuntimeStatus("mock", "Offline Mock Test", "本地 fixture 只用于开发测试；不会读取、理解或分析当前照片。")

    def infer(self, preview_jpeg: bytes | None, instruction: str, state: EditorState) -> JarvisArtNativePlan:
        lowered = instruction.lower()
        road = any(term in lowered for term in ("road", "公路", "道路", "荒漠"))
        plan = {
            "summary": "离线 JarvisArt Mock 测试参数（不代表真实图片分析）。",
            "reasoning_summary": "这是固定 fixture，仅用于开发链路验证；它没有查看当前照片或理解摄影意图。",
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
