"""Formal worker adapters for isolated task execution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

try:
    from .contracts import validate_task
    from .safe_process_env import safe_child_process_env
except ImportError:  # pragma: no cover - supports direct script execution during bootstraps.
    from contracts import validate_task  # type: ignore
    from safe_process_env import safe_child_process_env  # type: ignore


Command = str | list[str]


@dataclass(frozen=True)
class WorkerProcessExecution:
    """Raw process-level result returned by a worker adapter."""

    adapter_name: str
    command: list[str]
    stdout: str
    stderr: str
    returncode: int | None
    duration_seconds: float
    timed_out: bool
    stopped_by_request: bool


class TaskWorkerAdapter(Protocol):
    """Adapter contract for one isolated task worker."""

    name: str

    def execute(
        self,
        task: dict[str, Any],
        *,
        workspace: str | Path,
        command: Command | None = None,
        shell: bool = False,
        python_executable: str | None = None,
        worker_timeout_grace_seconds: int = 5,
        extra_env: dict[str, str] | None = None,
        on_process_start: Callable[[subprocess.Popen[str]], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> WorkerProcessExecution:
        """Execute one validated task and return raw process evidence."""


class CodexSubprocessWorkerAdapter:
    """Launch `workers.codex_worker` as one subprocess per task."""

    name = "codex_subprocess_worker"

    def execute(
        self,
        task: dict[str, Any],
        *,
        workspace: str | Path,
        command: Command | None = None,
        shell: bool = False,
        python_executable: str | None = None,
        worker_timeout_grace_seconds: int = 5,
        extra_env: dict[str, str] | None = None,
        on_process_start: Callable[[subprocess.Popen[str]], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> WorkerProcessExecution:
        validated_task = validate_task(task)
        workspace_path = Path(workspace).resolve()
        python = python_executable or sys.executable
        started = time.monotonic()
        stdout = ""
        stderr = ""
        timed_out = False
        stopped_by_request = False
        process: subprocess.Popen[str] | None = None
        adapter_command: list[str] = []

        with tempfile.TemporaryDirectory(prefix="task-executor-") as temp_dir:
            task_file = Path(temp_dir) / "task.json"
            task_file.write_text(json.dumps(validated_task, ensure_ascii=True), encoding="utf-8")

            adapter_command = [
                python,
                "-m",
                "workers.codex_worker",
                "--task-file",
                str(task_file),
                "--workspace",
                str(workspace_path),
                "--timeout-seconds",
                str(validated_task["timeout_seconds"]),
            ]
            if command is not None:
                adapter_command.extend(["--command-json", json.dumps(command, ensure_ascii=True)])
            if shell:
                adapter_command.append("--shell")

            repo_root = str(Path(__file__).resolve().parents[1])
            env = safe_child_process_env(os.environ, extra=extra_env, allowlist={"PYTHONPATH"})
            env["PYTHONPATH"] = repo_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

            process = subprocess.Popen(
                adapter_command,
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            if on_process_start is not None:
                on_process_start(process)

            try:
                deadline = time.monotonic() + validated_task["timeout_seconds"] + worker_timeout_grace_seconds
                while True:
                    if should_stop is not None and should_stop():
                        stopped_by_request = True
                        process.terminate()
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        process.terminate()
                        break
                    try:
                        stdout, stderr = process.communicate(timeout=min(0.25, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        continue
                if process.poll() is None:
                    stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()

        return WorkerProcessExecution(
            adapter_name=self.name,
            command=adapter_command,
            stdout=stdout,
            stderr=stderr,
            returncode=process.returncode if process is not None else None,
            duration_seconds=round(time.monotonic() - started, 6),
            timed_out=timed_out,
            stopped_by_request=stopped_by_request,
        )
