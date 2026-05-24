"""Real task validation for Sprint 4.

This module validates disk evidence and declared validation commands for one
already executed task. It does not implement recovery, benchmarking, or runtime
migration.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

try:
    from .contracts import (
        ContractError,
        validate_task,
        validate_task_result as validate_task_result_contract,
    )
    from .security_policy import (
        SecurityPolicyError,
        decide_command,
        record_security_event,
        validate_security_policy,
    )
except ImportError:  # pragma: no cover - supports direct script execution during bootstraps.
    from contracts import (  # type: ignore
        ContractError,
        validate_task,
        validate_task_result as validate_task_result_contract,
    )
    from security_policy import (  # type: ignore
        SecurityPolicyError,
        decide_command,
        record_security_event,
        validate_security_policy,
    )


DEFAULT_VALIDATION_TIMEOUT_SECONDS = 60
VALIDATION_SECURITY_EVENTS_NAME = "validation_security_events.jsonl"


def default_validation_security_policy() -> dict[str, Any]:
    """Return the explicit policy used before running declared validation commands."""

    return validate_security_policy(
        {
            "schema_version": 1,
            "default_decision": "deny",
            "risk_categories": {
                "read": {"activated": True, "decision": "allow", "risk_level": "low"},
                "test_or_build": {"activated": True, "decision": "allow", "risk_level": "low"},
                "shell": {"activated": True, "decision": "deny", "risk_level": "forbidden"},
                "network": {"activated": True, "decision": "deny", "risk_level": "high"},
                "delete": {"activated": True, "decision": "deny", "risk_level": "forbidden"},
                "permissions": {"activated": True, "decision": "deny", "risk_level": "forbidden"},
                "processes": {"activated": True, "decision": "deny", "risk_level": "high"},
                "docker": {"activated": True, "decision": "deny", "risk_level": "high"},
                "unknown": {"activated": True, "decision": "deny", "risk_level": "medium"},
            },
            "allow_prefixes": [],
            "ask_prefixes": [],
            "deny_prefixes": [
                ["bash"],
                ["sh"],
                ["curl"],
                ["wget"],
                ["ssh"],
                ["scp"],
                ["rm"],
                ["rmdir"],
                ["chmod"],
                ["chown"],
                ["sudo"],
                ["kill"],
                ["pkill"],
                ["docker"],
                ["pip", "install"],
                ["pip3", "install"],
                ["python", "-m", "pip", "install"],
                ["python3", "-m", "pip", "install"],
                ["npm", "install"],
                ["npm", "add"],
                ["npm", "publish"],
            ],
        }
    )


def validate_task_execution(
    task: dict[str, Any],
    execution_result: dict[str, Any],
    *,
    workspace: str | Path,
    command_timeout_seconds: int = DEFAULT_VALIDATION_TIMEOUT_SECONDS,
    validation_security_policy: dict[str, Any] | None = None,
    validation_security_log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate one task result against disk evidence and validation commands."""

    if command_timeout_seconds < 1:
        raise ContractError("command_timeout_seconds must be greater than 0")

    validated_task = validate_task(task)
    incoming_result = _extract_task_result(execution_result)
    if incoming_result["task_id"] != validated_task["id"]:
        raise ContractError("TaskResult.task_id must match Task.id")

    workspace_path = Path(workspace).resolve()
    blockers = list(incoming_result["blockers"])
    workspace_ready = workspace_path.exists() and workspace_path.is_dir()
    if not workspace_ready:
        blockers.append(f"Workspace does not exist or is not a directory: {workspace_path}")

    evidence = _inspect_expected_files(validated_task, incoming_result, workspace_path)
    blockers.extend(evidence["blockers"])

    command_results = (
        _run_validation_commands(
            validated_task["validation_commands"],
            workspace_path=workspace_path,
            timeout_seconds=command_timeout_seconds,
            security_policy=validation_security_policy or default_validation_security_policy(),
            security_log_path=validation_security_log_path,
        )
        if workspace_ready
        else _skipped_validation_commands(validated_task["validation_commands"])
    )
    blockers.extend(_command_blockers(command_results))

    validation_ran = [result["command"] for result in command_results]
    validation_passed = not blockers
    completed = bool(incoming_result["completed"] and validation_passed)
    next_recommendation = (
        "Task evidence and validation commands passed."
        if validation_passed
        else "Fix blockers, rerun the isolated task if needed, then validate again."
    )

    task_result = validate_task_result_contract(
        {
            "task_id": validated_task["id"],
            "completed": completed,
            "files_created": incoming_result["files_created"],
            "files_modified": incoming_result["files_modified"],
            "validation_ran": validation_ran,
            "validation_passed": validation_passed,
            "blockers": blockers,
            "next_recommendation": next_recommendation,
        }
    )
    return {
        "task_result": task_result,
        "validation": {
            "task_id": validated_task["id"],
            "workspace": str(workspace_path),
            "evidence": evidence,
            "commands": command_results,
            "validation_passed": validation_passed,
        },
    }


def validate_task_result(
    task: dict[str, Any],
    task_result: dict[str, Any],
    *,
    workspace: str | Path,
    command_timeout_seconds: int = DEFAULT_VALIDATION_TIMEOUT_SECONDS,
    validation_security_policy: dict[str, Any] | None = None,
    validation_security_log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate a direct TaskResult dictionary and return a TaskResult dictionary."""

    return validate_task_execution(
        task,
        task_result,
        workspace=workspace,
        command_timeout_seconds=command_timeout_seconds,
        validation_security_policy=validation_security_policy,
        validation_security_log_path=validation_security_log_path,
    )["task_result"]


def _extract_task_result(execution_result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(execution_result, dict):
        raise ContractError("execution_result must be an object")
    candidate = execution_result.get("task_result", execution_result)
    if not isinstance(candidate, dict):
        raise ContractError("execution_result.task_result must be an object")
    return validate_task_result_contract(candidate)


def _inspect_expected_files(
    task: dict[str, Any],
    task_result: dict[str, Any],
    workspace: Path,
) -> dict[str, Any]:
    reported_created = set(task_result["files_created"])
    reported_modified = set(task_result["files_modified"])
    expected = set(task["expected_files"])
    blockers: list[str] = []
    records: list[dict[str, Any]] = []

    for relative_path in task["expected_files"]:
        try:
            path = _resolve_under_workspace(workspace, relative_path)
            exists = path.exists()
            size = path.stat().st_size if exists and path.is_file() else None
            is_file = path.is_file() if exists else False
        except ContractError as exc:
            exists = False
            size = None
            is_file = False
            blockers.append(str(exc))

        records.append(
            {
                "path": relative_path,
                "exists": exists,
                "is_file": is_file,
                "size": size,
                "reported_created": relative_path in reported_created,
                "reported_modified": relative_path in reported_modified,
            }
        )
        if not exists:
            blockers.append(f"Missing expected file: {relative_path}")
        elif not is_file:
            blockers.append(f"Expected evidence path is not a file: {relative_path}")
        if _is_forbidden_control_plane_path(relative_path):
            blockers.append(f"Expected file targets control-plane state: {relative_path}")

    reported_outside_expected = sorted((reported_created | reported_modified) - expected)
    for relative_path in sorted(reported_created | reported_modified):
        if _is_forbidden_control_plane_path(relative_path):
            blockers.append(f"Worker reported change to control-plane state: {relative_path}")
    for relative_path in reported_outside_expected:
        try:
            exists = _resolve_under_workspace(workspace, relative_path).exists()
        except ContractError as exc:
            exists = False
            blockers.append(str(exc))
        if not exists:
            blockers.append(f"Reported changed file does not exist on disk: {relative_path}")

    found = [record["path"] for record in records if record["exists"]]
    missing = [record["path"] for record in records if not record["exists"]]
    return {
        "expected_files": records,
        "found": found,
        "missing": missing,
        "reported_created": sorted(reported_created),
        "reported_modified": sorted(reported_modified),
        "reported_outside_expected": reported_outside_expected,
        "blockers": blockers,
    }


def _run_validation_commands(
    commands: list[str],
    *,
    workspace_path: Path,
    timeout_seconds: int,
    security_policy: dict[str, Any],
    security_log_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        started = time.monotonic()
        timed_out = False
        normalized_command: list[str] | None = None
        security_decision: dict[str, Any]
        try:
            security_decision = decide_command(
                command,
                policy=security_policy,
                cwd=".",
                workspace=workspace_path,
            )
            normalized_command = list(security_decision.get("command") or [])
        except (SecurityPolicyError, ValueError) as exc:
            security_decision = {
                "schema_version": 1,
                "decision": "deny",
                "risk_level": "forbidden",
                "category": "invalid",
                "reason": f"Invalid validation command: {exc}",
                "command": [],
                "cwd": str(workspace_path),
                "workspace": str(workspace_path),
            }
        _record_validation_security_decision(
            security_decision,
            workspace_path=workspace_path,
            security_policy=security_policy,
            security_log_path=security_log_path,
        )
        if security_decision.get("decision") != "allow" or not normalized_command:
            results.append(
                {
                    "command": command,
                    "normalized_command": normalized_command or [],
                    "returncode": None,
                    "stdout": "",
                    "stderr": f"Validation command blocked by security policy: {security_decision.get('reason')}",
                    "duration_seconds": round(time.monotonic() - started, 6),
                    "timed_out": False,
                    "security_blocked": True,
                    "security_decision": security_decision,
                }
            )
            continue
        try:
            completed = subprocess.run(
                normalized_command,
                cwd=str(workspace_path),
                shell=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = None
            stdout = _coerce_output(exc.stdout)
            stderr = _coerce_output(exc.stderr)
        results.append(
            {
                "command": command,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration_seconds": round(time.monotonic() - started, 6),
                "timed_out": timed_out,
                "security_blocked": False,
                "security_decision": security_decision,
                "normalized_command": normalized_command,
            }
        )
    return results


def _record_validation_security_decision(
    decision: dict[str, Any],
    *,
    workspace_path: Path,
    security_policy: dict[str, Any],
    security_log_path: str | Path | None,
) -> None:
    target_path = Path(security_log_path) if security_log_path is not None else workspace_path / "runtime" / VALIDATION_SECURITY_EVENTS_NAME
    record_security_event(decision, policy=security_policy, log_path=target_path)


def _skipped_validation_commands(commands: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": "Workspace is unavailable; command was not run.",
            "duration_seconds": 0.0,
            "timed_out": False,
        }
        for command in commands
    ]


def _command_blockers(command_results: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for result in command_results:
        if result.get("security_blocked"):
            reason = result.get("security_decision", {}).get("reason") or "blocked"
            blockers.append(f"Validation command blocked by security policy ({reason}): {result['command']}")
        elif result["timed_out"]:
            blockers.append(f"Validation command timed out: {result['command']}")
        elif result["returncode"] != 0:
            blockers.append(
                f"Validation command failed with return code {result['returncode']}: {result['command']}"
            )
    return blockers


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _resolve_under_workspace(workspace: Path, relative_path: str) -> Path:
    path = (workspace / relative_path).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise ContractError(f"Expected file escapes workspace: {relative_path}") from exc
    return path


def _is_forbidden_control_plane_path(relative_path: str) -> bool:
    normalized = str(Path(str(relative_path or ".")).as_posix())
    forbidden_exact = {
        ".agent-project.json",
        "agent-project.json",
        "runtime/project_state.json",
        "runtime/task_queue.json",
        "runtime/task_history.jsonl",
        "runtime/failures.jsonl",
        "runtime/tool_invocation_policy.jsonl",
        f"runtime/{VALIDATION_SECURITY_EVENTS_NAME}",
        "runtime/artifacts/tool_invocation_policy_latest.json",
    }
    if normalized in forbidden_exact:
        return True
    if normalized.startswith(".vista/"):
        return True
    return normalized.startswith(
        (
            "runtime/checkpoints/",
            "runtime/directives/",
            "runtime/logs/",
            "runtime/artifacts/tool_invocations/",
        )
    )
