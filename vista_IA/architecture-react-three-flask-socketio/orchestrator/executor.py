"""Task executor for Sprint 3.

The executor launches one worker process for one task and returns a structured
TaskResult. It deliberately leaves full validation to Sprint 4.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

try:
    from .contracts import ContractError, validate_task, validate_task_result
    from .control_plane_artifact_executor import (
        execute_control_plane_artifact_task,
        should_use_control_plane_artifact_executor,
        task_result_payload as control_plane_artifact_task_result_payload,
    )
    from .host_write_executor import (
        execute_host_write_task,
        should_use_host_write_executor,
        task_result_payload,
    )
    from .runtime_failure_classifier import classify_runtime_failure
    from .worker_adapter import CodexSubprocessWorkerAdapter, Command, TaskWorkerAdapter
except ImportError:  # pragma: no cover - supports direct script execution during bootstraps.
    from contracts import ContractError, validate_task, validate_task_result  # type: ignore
    from control_plane_artifact_executor import (  # type: ignore
        execute_control_plane_artifact_task,
        should_use_control_plane_artifact_executor,
        task_result_payload as control_plane_artifact_task_result_payload,
    )
    from host_write_executor import (  # type: ignore
        execute_host_write_task,
        should_use_host_write_executor,
        task_result_payload,
    )
    from runtime_failure_classifier import classify_runtime_failure  # type: ignore
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

    if should_use_control_plane_artifact_executor(validated_task):
        started = time.monotonic()
        artifact = execute_control_plane_artifact_task(validated_task, workspace_path)
        task_result = control_plane_artifact_task_result_payload(artifact)
        duration = round(time.monotonic() - started, 6)
        return {
            "task_result": task_result,
            "execution": {
                "task_id": validated_task["id"],
                "execution_strategy": "control_plane_artifact",
                "selector_reason": artifact.get("selector_reason"),
                "task_kind": validated_task.get("kind"),
                "expected_files": list(validated_task.get("expected_files") or []),
                "returncode": 0 if task_result["completed"] else 1,
                "duration_seconds": duration,
                "stdout": "",
                "stderr": "\n".join(task_result["blockers"]),
                "timed_out": False,
                "control_plane_artifact": artifact,
                "worker_returncode": None,
                "worker_duration_seconds": 0.0,
                "worker_process_stdout": "",
                "worker_process_stderr": "",
                "worker_adapter": "control_plane_artifact_executor",
                "worker_adapter_command": [],
            },
        }

    if should_use_host_write_executor(validated_task) and _command_allows_host_write(command):
        host_write = execute_host_write_task(validated_task, workspace_path)
        task_result = task_result_payload(host_write)
        return {
            "task_result": task_result,
            "execution": {
                "task_id": validated_task["id"],
                "execution_strategy": "host_write",
                "selector_reason": host_write.get("selector_reason"),
                "task_kind": validated_task.get("kind"),
                "expected_files": list(validated_task.get("expected_files") or []),
                "returncode": 0 if task_result["completed"] else 1,
                "duration_seconds": 0.0,
                "stdout": "",
                "stderr": "\n".join(task_result["blockers"]),
                "timed_out": False,
                "host_write": host_write,
                "worker_returncode": None,
                "worker_duration_seconds": 0.0,
                "worker_process_stdout": "",
                "worker_process_stderr": "",
                "worker_adapter": "host_write_executor",
                "worker_adapter_command": [],
            },
        }

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
            "execution_strategy": "codex_worker",
            "selector_reason": "host_write_not_applicable",
            "task_kind": validated_task.get("kind"),
            "expected_files": list(validated_task.get("expected_files") or []),
            "worker_returncode": worker.returncode,
            "worker_duration_seconds": worker.duration_seconds,
            "worker_process_stdout": worker.stdout,
            "worker_process_stderr": worker.stderr,
            "worker_adapter": worker.adapter_name,
            "worker_adapter_command": worker.command,
        },
    }


def _command_allows_host_write(command: Command | None) -> bool:
    if command is None:
        return True
    if isinstance(command, list):
        parts = [str(part) for part in command]
    else:
        try:
            parts = shlex.split(str(command))
        except ValueError:
            parts = str(command).split()
    if not parts:
        return True
    first = Path(parts[0]).name.lower()
    if first == "codex":
        return True
    return len(parts) >= 3 and Path(parts[0]).name.lower().startswith("python") and parts[1] == "-m" and parts[2] == "codex"


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
    infrastructure = classify_runtime_failure(stdout, stderr)
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
            "execution_strategy": "codex_worker",
            "selector_reason": "host_write_not_applicable",
            "task_kind": task.get("kind"),
            "expected_files": list(task.get("expected_files") or []),
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
            "infrastructure_failure": bool(infrastructure.get("infrastructureFailure")),
            "fatal_infrastructure_failure": bool(infrastructure.get("fatalInfrastructureFailure")),
            "infrastructure_markers": list(infrastructure.get("markers") or []),
            "fatal_infrastructure_markers": list(infrastructure.get("fatalMarkers") or []),
        },
    }
