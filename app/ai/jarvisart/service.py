from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

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

    _owned_pids: set[int] = set()

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
        before = self._listener_pids()
        current = self.status()
        if current.state == "Ready":
            return current
        if not self.root:
            return JarvisArtServiceStatus("Error", "未检测到 JarvisArt；请在设置中选择 JarvisArt 根目录。", endpoint=self.endpoint)
        launcher = self.root / "scripts" / "launch_services.ps1"
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-File", str(launcher), "-WaitForReady"],
                cwd=str(self.root), capture_output=True, text=True, timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return JarvisArtServiceStatus("Error", "JarvisArt 启动超时。", root=str(self.root), endpoint=self.endpoint)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "JarvisArt 启动失败。").strip()[-500:]
            return JarvisArtServiceStatus("Error", detail, root=str(self.root), endpoint=self.endpoint)
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            status = self.status()
            if status.state == "Ready":
                self._owned_pids.update(self._listener_pids() - before)
                return status
            time.sleep(0.5)
        return self.status()

    def stop_owned(self) -> JarvisArtServiceStatus:
        for pid in tuple(self._owned_pids):
            try:
                process = psutil.Process(pid)
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
                self._owned_pids.discard(pid)
        return self.status()

    def _listener_pids(self) -> set[int]:
        return {connection.pid for connection in psutil.net_connections(kind="tcp") if connection.status == psutil.CONN_LISTEN and connection.laddr.port in {8002, 8765} and connection.pid}

    def _request_json(self, path: str, timeout: float) -> dict:
        request = Request(self.endpoint + path, headers={"Accept": "application/json"})
        with self._opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JarvisArt health response must be an object")
        return payload
