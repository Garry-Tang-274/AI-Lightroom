from __future__ import annotations

import json
import os
import subprocess
import time
import ipaddress
from tempfile import TemporaryFile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

import psutil


@dataclass(frozen=True, slots=True)
class JarvisArtServiceStatus:
    state: str
    message: str
    model: str = ""
    root: str = ""
    endpoint: str = ""


class JarvisArtServiceManager:
    """Own only JarvisArt services launched by this application process.

    The launcher under a user-selected JarvisArt installation remains the
    authority for model files and GPU flags. This manager only health-checks it
    and invokes that existing launcher when the user asks to start local AI.
    """

    _owned_pids: dict[int, float] = {}

    def __init__(self, root: str = "", endpoint: str = "http://127.0.0.1:8765", *, opener: Callable = urlopen) -> None:
        self.root = self.discover_root(root)
        self.endpoint = endpoint.rstrip("/")
        self._opener = opener

    @staticmethod
    def discover_root(configured_root: str = "") -> Path | None:
        # A configured path is authoritative.  For a source checkout, also
        # discover a sibling JarvisArt directory without encoding a machine
        # specific drive or user path into the application.
        try:
            sibling_install = Path(__file__).resolve().parents[4] / "JarvisArt"
        except IndexError:  # Defensive for unusual/frozen layouts.
            sibling_install = Path.cwd().parent / "JarvisArt"
        candidates = [configured_root, os.getenv("AI_LIGHTROOM_JARVISART_ROOT", ""), sibling_install]
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate).expanduser()
            if (path / "scripts" / "launch_services.ps1").is_file():
                return path.resolve()
        return None

    def status(self) -> JarvisArtServiceStatus:
        try:
            self._validate_endpoint()
        except ValueError as exc:
            return JarvisArtServiceStatus("Error", str(exc), endpoint=self.endpoint)
        try:
            health = self._request_json("/health", timeout=2.5)
        except (OSError, URLError, ValueError):
            root = str(self.root) if self.root else ""
            message = "未检测到 JarvisArt 安装。" if not self.root else "JarvisArt 本地服务未启动。"
            return JarvisArtServiceStatus("Offline", message, root=root, endpoint=self.endpoint)
        model_status = str(health.get("model_status", ""))
        model = str(health.get("model", ""))
        detail = str(health.get("model_detail", ""))
        if health.get("status") == "ok" and model_status == "online":
            return JarvisArtServiceStatus("Ready", "JarvisArt 本地 GGUF GPU 服务已就绪。", model, str(self.root or ""), self.endpoint)
        return JarvisArtServiceStatus("Loading", detail or "JarvisArt 模型正在启动。", model, str(self.root or ""), self.endpoint)

    def start(self, timeout_seconds: float = 180.0) -> JarvisArtServiceStatus:
        current = self.status()
        if current.state == "Error":
            return current
        if current.state == "Ready":
            return current
        before = self._listener_pids()
        if not self.root:
            return JarvisArtServiceStatus("Error", "未检测到 JarvisArt；请在设置中选择 JarvisArt 根目录。", endpoint=self.endpoint)
        launcher = self.root / "scripts" / "launch_services.ps1"
        try:
            # The PowerShell launcher starts long-lived model/backend children.
            # On Windows those children can inherit pipe handles, so
            # capture_output/communicate waits for EOF even after the launcher
            # exits. A file-backed capture has no inherited-EOF dependency.
            with TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as output:
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-File", str(launcher), "-WaitForReady"],
                    cwd=str(self.root), stdout=output, stderr=subprocess.STDOUT, timeout=timeout_seconds,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                output.seek(0)
                launcher_output = output.read()
        except subprocess.TimeoutExpired:
            return JarvisArtServiceStatus("Error", "JarvisArt 启动超时。", root=str(self.root), endpoint=self.endpoint)
        except OSError as exc:
            return JarvisArtServiceStatus("Error", f"无法运行 JarvisArt 启动器：{type(exc).__name__}", root=str(self.root), endpoint=self.endpoint)
        if result.returncode != 0:
            detail = (launcher_output or "JarvisArt 启动失败。").strip()[-500:]
            return JarvisArtServiceStatus("Error", detail, root=str(self.root), endpoint=self.endpoint)
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            status = self.status()
            if status.state == "Ready":
                for pid in self._listener_pids() - before:
                    try:
                        self._owned_pids[pid] = psutil.Process(pid).create_time()
                    except psutil.Error:
                        pass
                return status
            time.sleep(0.5)
        return self.status()

    def stop_owned(self) -> JarvisArtServiceStatus:
        for pid in tuple(self._owned_pids):
            try:
                process = psutil.Process(pid)
                if process.create_time() != self._owned_pids[pid]:
                    continue  # A terminated child's PID may now belong to another app.
                command = " ".join(process.cmdline()).lower()
                if "jarvisart" in command or "llama-server" in command or "server.py" in command:
                    process.terminate()
                    try:
                        process.wait(timeout=8)
                    except psutil.TimeoutExpired:
                        process.kill()
            except (psutil.Error, OSError):
                pass
            finally:
                self._owned_pids.pop(pid, None)
        return self.status()

    def _listener_pids(self) -> set[int]:
        try:
            port = urlsplit(self.endpoint).port or 80
            return {connection.pid for connection in psutil.net_connections(kind="tcp") if connection.status == psutil.CONN_LISTEN and connection.laddr.port in {8002, port} and connection.pid}
        except (psutil.Error, OSError):
            return set()

    def _validate_endpoint(self) -> None:
        endpoint = urlsplit(self.endpoint)
        if endpoint.scheme not in {"http", "https"} or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            raise ValueError("JarvisArt endpoint 必须是本机 HTTP 地址，不包含凭据、查询参数或片段。")
        host = (endpoint.hostname or "").lower()
        try:
            local = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = False
        if not local:
            raise ValueError("JarvisArt Local 只允许 127.0.0.1、::1 或 localhost；不会向远程地址发送预览。")
        endpoint.port  # Validate malformed port syntax without connecting.

    def _request_json(self, path: str, timeout: float) -> dict:
        self._validate_endpoint()
        request = Request(self.endpoint + path, headers={"Accept": "application/json"})
        with self._opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JarvisArt health response must be an object")
        return payload
