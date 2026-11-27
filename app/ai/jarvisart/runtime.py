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
from app.ai.jarvisart.support_matrix import operation_support
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

    def __init__(self, root: str = "", endpoint: str = "http://127.0.0.1:8765", *, auto_start: bool = True, manager: JarvisArtServiceManager | None = None,
                 on_request_started=None, on_stage=None, check_cancelled=None) -> None:
        self.manager = manager or JarvisArtServiceManager(root, endpoint)
        self.auto_start = auto_start
        self.on_request_started = on_request_started or (lambda: None)
        self.on_stage = on_stage or (lambda _stage, _message: None)
        self.check_cancelled = check_cancelled or (lambda: None)

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
        self.check_cancelled()
        if not preview_jpeg:
            raise AIRequestError("JarvisArt 缺少预览图", "JarvisArt 本地视觉分析需要当前 JPEG 预览图。", provider="JarvisArt Local GGUF", model="qwen2_vl")
        status = self.manager.status()
        if status.state != "Ready":
            if not self.auto_start:
                raise AIRequestError("JarvisArt 服务离线", status.message, provider="JarvisArt Local GGUF", model=status.model or "qwen2_vl")
            self.check_cancelled()
            self.on_stage("starting_local_model", "正在启动本地 JarvisArt 模型，尚未发送推理请求…")
            status = self.manager.start()
            self.check_cancelled()
            if status.state != "Ready":
                raise AIRequestError("JarvisArt 启动失败", status.message, provider="JarvisArt Local GGUF", model=status.model or "qwen2_vl")
        self.check_cancelled()
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
            self.check_cancelled()
            self.on_request_started()
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
        self.check_cancelled()
        return parse_jarvisart_lua(lua)


def parse_jarvisart_lua(lua: str) -> JarvisArtNativePlan:
    """Read the full top-level Lightroom table without evaluating Lua."""
    try:
        assignments = _top_level_lua_assignments(lua.strip())
    except ValueError as exc:
        raise _invalid_native_output(str(exc)) from exc
    if not assignments:
        raise AIRequestError(
            "JarvisArt 原生输出无效",
            "本地 JarvisArt GGUF 服务没有返回可解析的 Lightroom 参数。",
            provider="JarvisArt Local GGUF",
            model="qwen2_vl",
        )
    hsl: dict[str, dict[str, float]] = {}
    global_adjustments: list[dict[str, object]] = []
    unsupported: list[dict[str, str]] = []
    curves: list[dict[str, object]] = []
    curve_channels = {
        "ToneCurvePV2012": "rgb",
        "ToneCurvePV2012Red": "red",
        "ToneCurvePV2012Green": "green",
        "ToneCurvePV2012Blue": "blue",
    }
    for parameter, raw_value in assignments.items():
        if parameter in curve_channels:
            try:
                points = _tone_curve_points(raw_value)
            except ValueError as exc:
                raise _invalid_native_output(f"{parameter}: {exc}") from exc
            curves.append({"channel": curve_channels[parameter], "points": points})
            continue
        value = _lua_number(raw_value)
        if value is None:
            support = operation_support(parameter)
            if support.supported and support.target is None:
                continue
            if support.supported:
                raise _invalid_native_output(f"{parameter} 需要数值，返回的类型不正确。")
            reason = "需要 Lightroom 专有镜头或相机配置文件" if parameter in {"LensProfileSetup", "LensProfileName", "CameraProfile"} else support.reason
            unsupported.append({"operation": parameter, "reason": reason})
            continue
        match = re.fullmatch(r"(Hue|Saturation|Luminance)Adjustment(Red|Orange|Yellow|Green|Aqua|Blue|Purple|Magenta)", parameter)
        if match:
            field = {"Hue": "hue", "Saturation": "saturation", "Luminance": "luminance"}[match.group(1)]
            hsl.setdefault(match.group(2).lower(), {})[field] = value
        else:
            global_adjustments.append({"parameter": parameter, "value": value})
    return JarvisArtNativePlan.model_validate({
        "summary": "JarvisArt 已生成本地 Lightroom 调整方案。",
        "reasoning_summary": "已解析 Lightroom Develop 参数；可执行项交由本地渲染，未支持项单独报告。",
        "global_adjustments": global_adjustments,
        "hsl_adjustments": [{"color": color, **values} for color, values in hsl.items()],
        "curves": curves,
        "local_regions": [],
        "unsupported_operations": unsupported,
        "confidence": 0.78,
    })


def _invalid_native_output(message: str) -> AIRequestError:
    return AIRequestError("JarvisArt 原生输出无效", message,
                          provider="JarvisArt Local GGUF", model="qwen2_vl")


def _top_level_lua_assignments(source: str) -> dict[str, str]:
    """Read a complete data table, rejecting truncated or executable content."""
    source = re.sub(r"^return\s+", "", source).strip()
    if not source.startswith("{"):
        raise ValueError("返回内容不是 Lightroom 参数表。")
    values: dict[str, str] = {}
    index = 1
    size = len(source)
    while index < size:
        while index < size and source[index].isspace():
            index += 1
        if index < size and source[index] == "}":
            if source[index + 1:].strip() not in {"", ";"}:
                raise ValueError("参数表结束后包含额外内容。")
            return values
        match = re.match(r"""(?:\[\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\]|([A-Za-z_][A-Za-z0-9_]*))\s*=""",
                         source[index:])
        if match is None:
            raise ValueError("参数表不完整或键名格式错误。")
        key = match.group(1) or match.group(2)
        if key in values:
            raise ValueError(f"参数 {key} 重复，未执行有歧义的方案。")
        index += len(match.group(0))
        while index < size and source[index].isspace():
            index += 1
        start = index
        if index < size and source[index] == "{":
            depth = 0
            quote: str | None = None
            escaped = False
            while index < size:
                character = source[index]
                if quote:
                    if escaped:
                        escaped = False
                    elif character == "\\":
                        escaped = True
                    elif character == quote:
                        quote = None
                elif character in "'\"":
                    quote = character
                elif character == "{":
                    depth += 1
                elif character == "}":
                    depth -= 1
                    if depth == 0:
                        index += 1
                        break
                index += 1
            if depth != 0 or quote:
                raise ValueError(f"{key} 的嵌套参数表被截断。")
        elif index < size and source[index] in "'\"":
            quote = source[index]
            index += 1
            escaped = False
            closed = False
            while index < size:
                if escaped:
                    escaped = False
                elif source[index] == "\\":
                    escaped = True
                elif source[index] == quote:
                    index += 1
                    closed = True
                    break
                index += 1
            if not closed:
                raise ValueError(f"{key} 的字符串被截断。")
        else:
            while index < size and source[index] not in ",}":
                index += 1
        values[key] = source[start:index].strip()
        if not values[key]:
            raise ValueError(f"{key} 缺少值。")
        while index < size and source[index].isspace():
            index += 1
        if index < size and source[index] == ",":
            index += 1
        elif index >= size or source[index] != "}":
            raise ValueError("参数表被截断或缺少分隔符。")
    raise ValueError("参数表被截断，未执行任何调整。")


def _lua_number(raw_value: str) -> float | None:
    value = raw_value.strip()
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
        return float(value)
    if value == "true":
        return 1.0
    if value == "false":
        return 0.0
    return None


def _tone_curve_points(raw_value: str) -> list[dict[str, float]]:
    number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    if not raw_value.startswith("{") or not raw_value.endswith("}"):
        raise ValueError("曲线必须是控制点参数表。")
    indexed_pattern = rf"\[\s*({number})\s*\]\s*=\s*({number})"
    indexed = re.findall(indexed_pattern, raw_value)
    if indexed:
        if re.sub(indexed_pattern, "", raw_value).strip(" \n\r\t{},"):
            raise ValueError("曲线包含无法解析的控制点。")
        items = [(float(x), float(y)) for x, y in indexed]
        indices = [item[0] for item in items]
        if len(set(indices)) != len(indices):
            raise ValueError("曲线索引重复。")
        if len(items) >= 4 and set(indices) in (set(range(len(items))), set(range(1, len(items) + 1))):
            numbers = [y for _, y in sorted(items)]
            if len(numbers) % 2:
                raise ValueError("曲线坐标必须成对。")
            pairs = list(zip(numbers[::2], numbers[1::2]))
        else:
            pairs = items
    else:
        if re.sub(number, "", raw_value).strip(" \n\r\t{},"):
            raise ValueError("曲线包含无法解析的数值。")
        numbers = [float(value) for value in re.findall(number, raw_value)]
        if len(numbers) % 2:
            raise ValueError("曲线坐标必须成对。")
        pairs = list(zip(numbers[::2], numbers[1::2]))
    if not 2 <= len(pairs) <= 16 or any(not (0 <= x <= 255 and 0 <= y <= 255) for x, y in pairs):
        raise ValueError("曲线需要 2–16 个 0–255 范围内的控制点。")
    if len({x for x, _ in pairs}) != len(pairs):
        raise ValueError("曲线控制点的横坐标必须互不相同。")
    return [{"x": x, "y": y} for x, y in pairs]


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
