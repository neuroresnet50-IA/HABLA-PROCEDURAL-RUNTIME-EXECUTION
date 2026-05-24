"""Task executor for Sprint 3.

The executor launches one worker process for one task and returns a structured
TaskResult. It deliberately leaves full validation to Sprint 4.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

try:
    from .contracts import ContractError, validate_task, validate_task_result
    from .worker_adapter import CodexSubprocessWorkerAdapter, Command, TaskWorkerAdapter
except ImportError:  # pragma: no cover - supports direct script execution during bootstraps.
    from contracts import ContractError, validate_task, validate_task_result  # type: ignore
    from worker_adapter import CodexSubprocessWorkerAdapter, Command, TaskWorkerAdapter  # type: ignore


def execute_task(
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
    worker_adapter: TaskWorkerAdapter | None = None,
) -> dict[str, Any]:
    """Execute one task and return a TaskResult-compatible dictionary."""

    return execute_task_with_details(
        task,
        workspace=workspace,
        command=command,
        shell=shell,
        python_executable=python_executable,
        worker_timeout_grace_seconds=worker_timeout_grace_seconds,
        extra_env=extra_env,
        on_process_start=on_process_start,
        should_stop=should_stop,
        worker_adapter=worker_adapter,
    )["task_result"]


def execute_task_with_details(
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
    worker_adapter: TaskWorkerAdapter | None = None,
) -> dict[str, Any]:
    """Launch a fresh worker process for one task and return execution details."""

    validated_task = validate_task(task)
    workspace_path = Path(workspace).resolve()
    adapter = worker_adapter or CodexSubprocessWorkerAdapter()
    worker = adapter.execute(
        validated_task,
        workspace=workspace_path,
        command=command,
        shell=shell,
        python_executable=python_executable,
        worker_timeout_grace_seconds=worker_timeout_grace_seconds,
        extra_env=extra_env,
        on_process_start=on_process_start,
        should_stop=should_stop,
    )

    if worker.timed_out:
        return _worker_timeout_result(
            validated_task,
            stdout=worker.stdout,
            stderr=worker.stderr,
            worker_returncode=worker.returncode,
            worker_duration_seconds=worker.duration_seconds,
            worker_adapter=worker.adapter_name,
        )
    if worker.stopped_by_request:
        return _worker_failure_result(
            validated_task,
            stdout=worker.stdout,
            stderr=worker.stderr,
            worker_returncode=worker.returncode,
            worker_duration_seconds=worker.duration_seconds,
            reason="Worker process stopped because session stop was requested",
            worker_adapter=worker.adapter_name,
        )

    if worker.returncode != 0:
        return _worker_failure_result(
            validated_task,
            stdout=worker.stdout,
            stderr=worker.stderr,
            worker_returncode=worker.returncode,
            worker_duration_seconds=worker.duration_seconds,
            worker_adapter=worker.adapter_name,
        )

    try:
        payload = json.loads(worker.stdout)
        task_result = validate_task_result(payload["task_result"])
        execution = payload.get("execution", {})
    except (KeyError, TypeError, json.JSONDecodeError, ContractError) as exc:
        return _worker_failure_result(
            validated_task,
            stdout=worker.stdout,
            stderr=worker.stderr,
            worker_returncode=worker.returncode,
            worker_duration_seconds=worker.duration_seconds,
            reason=f"Worker returned invalid structured output: {exc}",
            worker_adapter=worker.adapter_name,
        )

    return {
        "task_result": task_result,
        "execution": {
            **execution,
            "worker_returncode": worker.returncode,
            "worker_duration_seconds": worker.duration_seconds,
            "worker_process_stdout": worker.stdout,
            "worker_process_stderr": worker.stderr,
            "worker_adapter": worker.adapter_name,
            "worker_adapter_command": worker.command,
        },
    }


def _worker_timeout_result(
    task: dict[str, Any],
    *,
    stdout: str,
    stderr: str,
    worker_returncode: int | None,
    worker_duration_seconds: float,
    worker_adapter: str,
) -> dict[str, Any]:
    return _structured_failure(
        task,
        reason=f"Worker process timed out after {task['timeout_seconds']} seconds",
        stdout=stdout,
        stderr=stderr,
        worker_returncode=worker_returncode,
        worker_duration_seconds=worker_duration_seconds,
        timed_out=True,
        worker_adapter=worker_adapter,
    )


def _worker_failure_result(
    task: dict[str, Any],
    *,
    stdout: str,
    stderr: str,
    worker_returncode: int | None,
    worker_duration_seconds: float,
    worker_adapter: str,
    reason: str | None = None,
) -> dict[str, Any]:
    return _structured_failure(
        task,
        reason=reason or f"Worker process exited with return code {worker_returncode}",
        stdout=stdout,
        stderr=stderr,
        worker_returncode=worker_returncode,
        worker_duration_seconds=worker_duration_seconds,
        timed_out=False,
        worker_adapter=worker_adapter,
    )


def _structured_failure(
    task: dict[str, Any],
    *,
    reason: str,
    stdout: str,
    stderr: str,
    worker_returncode: int | None,
    worker_duration_seconds: float,
    timed_out: bool,
    worker_adapter: str,
) -> dict[str, Any]:
    task_result = validate_task_result(
        {
            "task_id": task["id"],
            "completed": False,
            "files_created": [],
            "files_modified": [],
            "validation_ran": [],
            "validation_passed": False,
            "blockers": [reason],
            "next_recommendation": "Retry this isolated task after inspecting worker output.",
        }
    )
    return {
        "task_result": task_result,
        "execution": {
            "task_id": task["id"],
            "timed_out": timed_out,
            "returncode": None,
            "duration_seconds": worker_duration_seconds,
            "stdout": "",
            "stderr": "",
            "worker_returncode": worker_returncode,
            "worker_duration_seconds": worker_duration_seconds,
            "worker_adapter": worker_adapter,
            "worker_process_stdout": stdout,
            "worker_process_stderr": stderr,
        },
    }
