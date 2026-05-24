from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List

JsonLoader = Callable[[Path, Dict[str, Any]], Dict[str, Any]]
NowProvider = Callable[[], str]
PortAllocator = Callable[[str], int]


class SandboxService:
    def __init__(
        self,
        *,
        host: str,
        port_start: int,
        port_end: int,
        ready_timeout_seconds: float,
        ready_poll_seconds: float,
        state_name: str,
        log_name: str,
        load_json_file: JsonLoader,
        now_provider: NowProvider,
    ) -> None:
        self.host = host
        self.port_start = port_start
        self.port_end = port_end
        self.ready_timeout_seconds = ready_timeout_seconds
        self.ready_poll_seconds = ready_poll_seconds
        self.state_name = state_name
        self.log_name = log_name
        self.load_json_file = load_json_file
        self.now_provider = now_provider
        self.processes: Dict[str, subprocess.Popen[Any]] = {}
        self.lock = threading.Lock()

    def state_path(self, project_dir: Path) -> Path:
        return project_dir / "runtime" / self.state_name

    def log_path(self, project_dir: Path) -> Path:
        return project_dir / "runtime" / "logs" / self.log_name

    def read_state(self, project_dir: Path) -> Dict[str, Any]:
        state = self.load_json_file(self.state_path(project_dir), {})
        return state if isinstance(state, dict) else {}

    def write_state(self, project_dir: Path, state: Dict[str, Any]) -> None:
        path = self.state_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def pid_is_running(pid: Any) -> bool:
        try:
            normalized_pid = int(pid)
        except (TypeError, ValueError):
            return False
        if normalized_pid <= 0:
            return False
        try:
            os.kill(normalized_pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False

    @staticmethod
    def port_is_available(port: int, host: str) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                return False
        return True

    def allocate_port(self, project_slug: str) -> int:
        span = max(1, self.port_end - self.port_start + 1)
        offset = sum(ord(char) for char in project_slug) % span
        for index in range(span):
            port = self.port_start + ((offset + index) % span)
            if self.port_is_available(port, self.host):
                return port
        raise RuntimeError("sandbox_port_unavailable")

    def detect_plan(self, project_dir: Path, port: int) -> Dict[str, Any] | None:
        for package_path in (project_dir / "package.json", project_dir / "frontend" / "package.json"):
            if not package_path.exists():
                continue
            package = self.load_json_file(package_path, {})
            scripts = package.get("scripts") if isinstance(package, dict) else {}
            scripts = scripts if isinstance(scripts, dict) else {}
            package_dir = package_path.parent
            if "dev" in scripts:
                script = str(scripts.get("dev") or "")
                command = ["npm", "run", "dev"]
                if "vite" in script:
                    command.extend(["--", "--host", self.host, "--port", str(port)])
                return {
                    "technology": "node",
                    "command": command,
                    "cwd": str(package_dir),
                    "entrypoint": f"{package_path.relative_to(project_dir).as_posix()}:scripts.dev",
                    "dependencyStatus": "uses_existing_project_dependencies",
                }
            if "start" in scripts:
                return {
                    "technology": "node",
                    "command": ["npm", "run", "start"],
                    "cwd": str(package_dir),
                    "entrypoint": f"{package_path.relative_to(project_dir).as_posix()}:scripts.start",
                    "dependencyStatus": "uses_existing_project_dependencies",
                }

        for relative in ("app.py", "server.py", "main.py", "backend/app.py", "backend/server.py", "src/app.py", "src/main.py"):
            candidate = project_dir / relative
            if not candidate.exists() or not candidate.is_file():
                continue
            try:
                content = candidate.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                content = ""
            if "Flask" in content or "SocketIO" in content or "FastAPI" in content or "uvicorn" in content:
                return {
                    "technology": "python",
                    "command": [sys.executable or "python3", str(candidate)],
                    "cwd": str(candidate.parent),
                    "entrypoint": relative,
                    "dependencyStatus": "uses_current_python_environment",
                }

        static_root = None
        for relative in ("frontend/index.html", "index.html", "public/index.html", "src/index.html"):
            candidate = project_dir / relative
            if candidate.exists() and candidate.is_file():
                static_root = candidate.parent
                break
        if static_root is not None:
            return {
                "technology": "static",
                "command": [sys.executable or "python3", "-m", "http.server", str(port), "--bind", self.host],
                "cwd": str(static_root),
                "entrypoint": str(static_root.relative_to(project_dir)),
                "dependencyStatus": "standard_library",
            }
        return None

    def env(self, port: int) -> Dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "HOST": self.host,
                "PORT": str(port),
                "FLASK_RUN_HOST": self.host,
                "FLASK_RUN_PORT": str(port),
                "PYTHONUNBUFFERED": "1",
            }
        )
        return env

    def preview_url(self, port: int) -> str:
        return f"http://{self.host}:{port}/"

    def wait_for_http_ready(
        self,
        url: str,
        process: subprocess.Popen[Any],
        *,
        timeout_seconds: float | None = None,
    ) -> Dict[str, Any]:
        deadline = time.time() + max(0.1, self.ready_timeout_seconds if timeout_seconds is None else timeout_seconds)
        last_error = ""
        while time.time() < deadline:
            returncode = process.poll()
            if returncode is not None:
                return {
                    "ready": False,
                    "reason": "process_exited_before_http_ready",
                    "returncode": returncode,
                    "lastError": last_error,
                }
            try:
                request_obj = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(request_obj, timeout=0.8) as response:
                    status_code = int(getattr(response, "status", 200) or 200)
                    return {
                        "ready": 200 <= status_code < 500,
                        "reason": "http_ready",
                        "statusCode": status_code,
                        "lastError": "",
                    }
            except urllib.error.HTTPError as error:
                status_code = int(getattr(error, "code", 0) or 0)
                if 200 <= status_code < 500:
                    return {
                        "ready": True,
                        "reason": "http_ready",
                        "statusCode": status_code,
                        "lastError": "",
                    }
                last_error = str(error)
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last_error = str(error)
            time.sleep(max(0.05, self.ready_poll_seconds))

        return {
            "ready": False,
            "reason": "http_ready_timeout",
            "returncode": process.poll(),
            "lastError": last_error,
        }

    @staticmethod
    def terminate_process_group(process: subprocess.Popen[Any], *, timeout_seconds: float = 2.0) -> None:
        try:
            os.killpg(int(process.pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                os.kill(int(process.pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass

        deadline = time.time() + timeout_seconds
        while time.time() < deadline and process.poll() is None:
            time.sleep(0.1)

        if process.poll() is None:
            try:
                os.killpg(int(process.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                try:
                    os.kill(int(process.pid), signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    pass
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass

    def refresh_state(self, project_slug: str, project_dir: Path) -> Dict[str, Any]:
        state = self.read_state(project_dir)
        pid = state.get("pid")
        running = self.pid_is_running(pid)
        if state and state.get("status") == "running" and not running:
            state["status"] = "stopped"
            state["ready"] = False
            state["stoppedAt"] = self.now_provider()
            state["updatedAt"] = state["stoppedAt"]
            self.write_state(project_dir, state)
        if not state:
            state = {
                "schema_version": 1,
                "projectId": project_slug,
                "status": "idle",
                "ready": False,
                "host": self.host,
                "port": None,
                "url": None,
                "embedUrl": None,
                "previewKind": None,
                "pid": None,
                "command": [],
                "technology": None,
                "logPath": str(self.log_path(project_dir)),
            }
        state["running"] = bool(state.get("status") == "running" and running)
        if state["running"]:
            state.setdefault("ready", True)
            state.setdefault("embedUrl", state.get("url"))
            state.setdefault("previewKind", "browser")
        else:
            state["ready"] = False
        return state

    def terminate_process(self, project_slug: str, project_dir: Path, reason: str = "human_stop") -> Dict[str, Any]:
        with self.lock:
            state = self.refresh_state(project_slug, project_dir)
            pid = state.get("pid")
            process = self.processes.pop(project_slug, None)
            if not self.pid_is_running(pid):
                state.update({"status": "stopped", "running": False, "ready": False, "stopReason": reason, "updatedAt": self.now_provider()})
                self.write_state(project_dir, state)
                return state

            try:
                os.killpg(int(pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    pass

            deadline = time.time() + 2.0
            while time.time() < deadline and self.pid_is_running(pid):
                time.sleep(0.1)
            if process is not None:
                try:
                    process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    pass

            if self.pid_is_running(pid):
                try:
                    os.killpg(int(pid), signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except (OSError, ProcessLookupError):
                        pass
                if process is not None:
                    try:
                        process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        pass

            stopped_at = self.now_provider()
            state.update(
                {
                    "status": "stopped",
                    "running": False,
                    "ready": False,
                    "stopReason": reason,
                    "stoppedAt": stopped_at,
                    "updatedAt": stopped_at,
                }
            )
            self.write_state(project_dir, state)
            return state

    def start(
        self,
        project_slug: str,
        project_dir: Path,
        *,
        allocate_port: PortAllocator | None = None,
    ) -> Dict[str, Any]:
        with self.lock:
            existing = self.refresh_state(project_slug, project_dir)
            if existing.get("running"):
                return existing

            port = allocate_port(project_slug) if allocate_port is not None else self.allocate_port(project_slug)
            plan = self.detect_plan(project_dir, port)
            if plan is None:
                raise RuntimeError("sandbox_entrypoint_not_found")

            log_path = self.log_path(project_dir)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = log_path.open("a", encoding="utf-8")
            log_handle.write(f"\n[{self.now_provider()}] Starting sandbox: {' '.join(plan['command'])}\n")
            log_handle.flush()
            process = subprocess.Popen(
                plan["command"],
                cwd=plan["cwd"],
                env=self.env(port),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            log_handle.close()
            self.processes[project_slug] = process
            preview_url = self.preview_url(port)
            healthcheck = self.wait_for_http_ready(preview_url, process)
            if not healthcheck.get("ready"):
                self.processes.pop(project_slug, None)
                self.terminate_process_group(process)
                failed_state = {
                    "schema_version": 1,
                    "projectId": project_slug,
                    "status": "failed",
                    "running": False,
                    "ready": False,
                    "host": self.host,
                    "port": port,
                    "url": preview_url,
                    "embedUrl": None,
                    "previewKind": "browser",
                    "pid": process.pid,
                    "command": plan["command"],
                    "cwd": plan["cwd"],
                    "technology": plan["technology"],
                    "entrypoint": plan["entrypoint"],
                    "dependencyStatus": plan["dependencyStatus"],
                    "logPath": str(log_path),
                    "startedAt": self.now_provider(),
                    "stoppedAt": self.now_provider(),
                    "updatedAt": self.now_provider(),
                    "healthcheck": healthcheck,
                    "network": {"bind": self.host, "internetExposed": False, "previewUrl": preview_url},
                }
                self.write_state(project_dir, failed_state)
                raise RuntimeError(f"sandbox_not_ready:{healthcheck.get('reason') or 'unknown'}")
            state = {
                "schema_version": 1,
                "projectId": project_slug,
                "status": "running",
                "running": True,
                "ready": True,
                "host": self.host,
                "port": port,
                "url": preview_url,
                "embedUrl": preview_url,
                "previewKind": "browser",
                "pid": process.pid,
                "command": plan["command"],
                "cwd": plan["cwd"],
                "technology": plan["technology"],
                "entrypoint": plan["entrypoint"],
                "dependencyStatus": plan["dependencyStatus"],
                "logPath": str(log_path),
                "startedAt": self.now_provider(),
                "updatedAt": self.now_provider(),
                "healthcheck": healthcheck,
                "network": {"bind": self.host, "internetExposed": False, "previewUrl": preview_url},
            }
            self.write_state(project_dir, state)
            return state

    def log_tail(self, project_dir: Path, limit: int = 80) -> List[str]:
        path = self.log_path(project_dir)
        if not path.exists():
            return []
        try:
            return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        except OSError:
            return []
