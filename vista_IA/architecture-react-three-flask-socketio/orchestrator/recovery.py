"""Recovery decisions and persistence for Sprint 5.

This module records failures, creates checkpoints, proposes retry/block/split
decisions, and provides guaranteed process shutdown helpers. It does not run
benchmarks or modify the legacy runtime.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

try:
    from .contracts import ContractError, validate_task, validate_task_result
    from .state_store import StateStore
except ImportError:  # pragma: no cover - supports direct script execution during bootstraps.
    from contracts import ContractError, validate_task, validate_task_result  # type: ignore
    from state_store import StateStore  # type: ignore


RECOVERY_ACTIONS = frozenset({"retry", "block", "split", "noop"})


def recover_task(
    task: dict[str, Any],
    failure: dict[str, Any] | None = None,
    *,
    retry_count: int = 0,
    store: StateStore | None = None,
    checkpoint_key: str | None = None,
    allow_split: bool = True,
) -> dict[str, Any]:
    """Record failure, decide recovery, and persist a checkpoint."""

    target_store = _require_store(store)
    validated_task = validate_task(task)
    normalized_failure = normalize_failure(failure)
    decision = decide_recovery(
        validated_task,
        normalized_failure,
        retry_count=retry_count,
        allow_split=allow_split,
    )
    failure_event = register_failure(
        validated_task,
        normalized_failure,
        retry_count=retry_count,
        decision=decision,
        store=target_store,
    )
    checkpoint = create_recovery_checkpoint(
        validated_task,
        normalized_failure,
        decision,
        retry_count=retry_count,
        store=target_store,
        checkpoint_key=checkpoint_key,
    )
    return {
        "task_id": validated_task["id"],
        "decision": decision,
        "failure_event": failure_event,
        "checkpoint": checkpoint,
    }


def register_failure(
    task: dict[str, Any],
    failure: dict[str, Any] | None = None,
    *,
    retry_count: int = 0,
    decision: dict[str, Any] | None = None,
    store: StateStore | None = None,
) -> dict[str, Any]:
    """Append a failure entry to runtime/failures.jsonl."""

    if retry_count < 0:
        raise ContractError("retry_count must be greater than or equal to 0")
    validated_task = validate_task(task)
    normalized_failure = normalize_failure(failure)
    payload = {
        "task_id": validated_task["id"],
        "retry_count": retry_count,
        "max_retries": validated_task["max_retries"],
        "failure": normalized_failure,
        "decision": decision,
    }
    return _require_store(store).append_failure(payload)


def create_recovery_checkpoint(
    task: dict[str, Any],
    failure: dict[str, Any] | None,
    decision: dict[str, Any],
    *,
    retry_count: int = 0,
    store: StateStore | None = None,
    checkpoint_key: str | None = None,
) -> dict[str, Any]:
    """Persist a checkpoint under runtime/checkpoints/."""

    validated_task = validate_task(task)
    normalized_failure = normalize_failure(failure)
    _validate_decision(decision)
    key = checkpoint_key or _default_checkpoint_key(validated_task, retry_count)
    path = _require_store(store).save_checkpoint(
        key,
        {
            "task": validated_task,
            "failure": normalized_failure,
            "decision": decision,
            "retry_count": retry_count,
        },
    )
    return {"checkpoint_key": key, "path": str(path)}


def decide_recovery(
    task: dict[str, Any],
    failure: dict[str, Any] | None = None,
    *,
    retry_count: int = 0,
    allow_split: bool = True,
) -> dict[str, Any]:
    """Return a structured recovery decision for one task failure."""

    if retry_count < 0:
        raise ContractError("retry_count must be greater than or equal to 0")
    validated_task = validate_task(task)
    normalized_failure = normalize_failure(failure)

    if _is_success(normalized_failure):
        return _decision("noop", "Task result already completed without blockers.", retry_count)

    if allow_split and _suggests_split(normalized_failure) and _can_split_task(validated_task):
        split_tasks = split_task(validated_task, reason="Failure suggests timeout or oversized task.")
        return _decision(
            "split",
            "Failure suggests timeout or oversized task; split into smaller tasks.",
            retry_count,
            split_tasks=split_tasks,
        )

    if retry_count < validated_task["max_retries"]:
        return _decision(
            "retry",
            "Retries remain for this task.",
            retry_count,
            next_retry_count=retry_count + 1,
        )

    return _decision(
        "block",
        "Task reached max_retries and must be blocked for manual or recovery handling.",
        retry_count,
    )


def split_task(task: dict[str, Any], *, reason: str = "Split requested") -> list[dict[str, Any]]:
    """Split a task into small contract-valid subtasks using explicit heuristics."""

    validated_task = validate_task(task)
    expected_files = validated_task["expected_files"]
    if len(expected_files) > 1:
        units = [(f"Produce expected file {path}", [path]) for path in expected_files]
    else:
        parts = _split_goal(validated_task["goal"])
        units = [(part, expected_files) for part in parts]

    split_tasks: list[dict[str, Any]] = []
    for index, (goal, files) in enumerate(units, start=1):
        task_id = f"{validated_task['id']}-SPLIT-{index:03d}"
        split_tasks.append(
            validate_task(
                {
                    "id": task_id,
                    "title": f"{validated_task['title']} split {index}",
                    "goal": f"{goal}. Reason: {reason}",
                    "status": "pending",
                    "priority": max(validated_task["priority"] - index, 0),
                    "dependencies": list(validated_task["dependencies"]),
                    "expected_files": list(files),
                    "validation_commands": [_expected_files_command(files)],
                    "timeout_seconds": validated_task["timeout_seconds"],
                    "max_retries": validated_task["max_retries"],
                    "mode": validated_task["mode"],
                    "checkpoint_key": f"{task_id.lower()}-checkpoint",
                }
            )
        )
    return split_tasks


def terminate_wait_kill(process: Any, *, wait_seconds: float = 5.0) -> dict[str, Any]:
    """Close a process with terminate(), wait, then kill() if still running."""

    if wait_seconds < 0:
        raise ContractError("wait_seconds must be greater than or equal to 0")
    started = time.monotonic()
    result: dict[str, Any] = {
        "pid": getattr(process, "pid", None),
        "was_running": False,
        "terminate_called": False,
        "kill_called": False,
        "wait_after_terminate_timed_out": False,
        "wait_after_kill_timed_out": False,
        "still_running": False,
        "returncode": None,
        "duration_seconds": 0.0,
        "errors": [],
    }

    try:
        initial_returncode = process.poll()
    except AttributeError as exc:
        raise ContractError("process must provide poll, terminate, wait, and kill methods") from exc
    except Exception as exc:
        result["errors"].append(f"initial poll failed: {type(exc).__name__}: {exc}")
        initial_returncode = None

    if initial_returncode is not None:
        result["returncode"] = initial_returncode
        result["duration_seconds"] = _elapsed(started)
        return result

    result["was_running"] = True
    try:
        process.terminate()
        result["terminate_called"] = True
    except Exception as exc:  # Process objects can fail if already gone.
        result["errors"].append(f"terminate failed: {type(exc).__name__}: {exc}")

    _wait_with_timeout(
        process,
        wait_seconds=wait_seconds,
        timeout_flag="wait_after_terminate_timed_out",
        result=result,
        label="wait after terminate",
    )

    if _safe_poll(process, result, "poll after terminate") is None:
        try:
            result["kill_called"] = True
            process.kill()
        except Exception as exc:
            result["errors"].append(f"kill failed: {type(exc).__name__}: {exc}")
        _wait_with_timeout(
            process,
            wait_seconds=wait_seconds,
            timeout_flag="wait_after_kill_timed_out",
            result=result,
            label="wait after kill",
        )

    result["returncode"] = _safe_poll(process, result, "final poll")
    result["still_running"] = result["returncode"] is None
    result["duration_seconds"] = _elapsed(started)
    return result


def normalize_failure(failure: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize executor/validator output or ad hoc failure metadata."""

    if failure is None:
        return {}
    if not isinstance(failure, dict):
        raise ContractError("failure must be an object")

    if "task_result" in failure and isinstance(failure["task_result"], dict):
        normalized = dict(failure)
        normalized["task_result"] = validate_task_result(failure["task_result"])
        return normalized

    task_result_keys = {
        "task_id",
        "completed",
        "files_created",
        "files_modified",
        "validation_ran",
        "validation_passed",
        "blockers",
        "next_recommendation",
    }
    if task_result_keys.issubset(failure):
        return {"task_result": validate_task_result(failure)}

    return dict(failure)


def _decision(action: str, reason: str, retry_count: int, **extra: Any) -> dict[str, Any]:
    decision = {
        "action": action,
        "reason": reason,
        "retry_count": retry_count,
    }
    decision.update(extra)
    return _validate_decision(decision)


def _validate_decision(decision: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise ContractError("decision must be an object")
    action = decision.get("action")
    if action not in RECOVERY_ACTIONS:
        raise ContractError(f"decision.action must be one of: {', '.join(sorted(RECOVERY_ACTIONS))}")
    return decision


def _is_success(failure: dict[str, Any]) -> bool:
    task_result = failure.get("task_result")
    if isinstance(task_result, dict):
        return bool(task_result["completed"] and task_result["validation_passed"] and not task_result["blockers"])
    return bool(failure.get("completed") is True and failure.get("validation_passed") is True)


def _suggests_split(failure: dict[str, Any]) -> bool:
    text = _failure_text(failure)
    markers = (
        "timeout",
        "timed out",
        "too large",
        "demasiado grande",
        "oversized",
        "split",
        "dividir",
    )
    return any(marker in text for marker in markers)


def _failure_text(failure: dict[str, Any]) -> str:
    parts: list[str] = []
    task_result = failure.get("task_result")
    if isinstance(task_result, dict):
        parts.extend(task_result.get("blockers", []))
        parts.append(task_result.get("next_recommendation", ""))
    for key in ("cause", "reason", "message", "stderr", "stdout"):
        value = failure.get(key)
        if isinstance(value, str):
            parts.append(value)
    execution = failure.get("execution")
    if isinstance(execution, dict):
        if execution.get("timed_out"):
            parts.append("timeout")
        for key in ("stderr", "stdout"):
            value = execution.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts).lower()


def _split_goal(goal: str) -> list[str]:
    parts = [part.strip(" .;:") for part in goal.replace("\n", ";").split(";") if part.strip()]
    if len(parts) > 1:
        return parts
    return [f"Prepare smaller scope for {goal}", f"Complete smaller scope for {goal}"]


def _can_split_task(task: dict[str, Any]) -> bool:
    task_id = str(task.get("id") or "")
    if "-SPLIT-" in task_id:
        return False
    expected_files = list(task.get("expected_files") or [])
    return len(expected_files) > 1 or len(_split_goal(str(task.get("goal") or ""))) > 1


def _expected_files_command(expected_files: list[str]) -> str:
    return (
        "python3 -B -c "
        + repr(
            "from pathlib import Path; "
            f"missing=[p for p in {expected_files!r} if not Path(p).is_file()]; "
            "assert not missing, missing"
        )
    )


def _default_checkpoint_key(task: dict[str, Any], retry_count: int) -> str:
    return f"{task['id'].lower()}-retry-{retry_count}-recovery"


def _require_store(store: StateStore | None) -> StateStore:
    if store is None:
        raise ContractError("Recovery persistence requires an explicit StateStore bound to a project runtime.")
    return store


def _wait_with_timeout(
    process: Any,
    *,
    wait_seconds: float,
    timeout_flag: str,
    result: dict[str, Any],
    label: str,
) -> None:
    try:
        process.wait(timeout=wait_seconds)
    except subprocess.TimeoutExpired as exc:
        result[timeout_flag] = True
        result["errors"].append(f"{label} timed out: {exc}")
    except Exception as exc:
        result["errors"].append(f"{label} failed: {type(exc).__name__}: {exc}")


def _safe_poll(process: Any, result: dict[str, Any], label: str) -> int | None:
    try:
        return process.poll()
    except Exception as exc:
        result["errors"].append(f"{label} failed: {type(exc).__name__}: {exc}")
        return None


def _elapsed(started: float) -> float:
    return round(time.monotonic() - started, 6)
