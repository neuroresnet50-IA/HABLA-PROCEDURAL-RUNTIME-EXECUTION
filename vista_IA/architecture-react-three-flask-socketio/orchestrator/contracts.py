"""Validation contracts for the persistent orchestration runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any


ALLOWED_MODES = frozenset({"smoke", "build", "medium", "long-run"})
ALLOWED_TASK_STATUSES = frozenset({"pending", "running", "completed", "failed", "blocked"})
ALLOWED_PROJECT_STATUSES = frozenset(
    {
        "initialized",
        "preparing",
        "running",
        "paused",
        "completed",
        "failed",
        "blocked",
        "stopped",
        "human_alignment_pending",
    }
)
OPTIONAL_PROJECT_STATE_FIELDS = frozenset(
    {
        "live_app",
        "pending_control_plane_work",
        "pending_human_alignment_tasks",
        "last_queue_clear_at",
        "last_queue_clear_force",
        "last_queue_clear_removed_task_ids",
        "last_preparing_at",
        "preparing_session_id",
        "last_released_zombie_task_ids",
        "last_released_zombie_at",
        "last_released_zombie_reason",
        "last_runtime_repair_at",
        "last_runtime_repair_reason",
        "last_cyberlace_block_at",
        "last_cyberlace_block_reason",
        "last_cyberlace_block_paths",
        "last_cyberlace_denied_action",
        "last_cyberlace_safe_alternative",
    }
)


class ContractError(ValueError):
    """Raised when runtime data violates a persisted contract."""


def validate_task(task: dict[str, Any]) -> dict[str, Any]:
    """Validate the minimum Task contract and return a shallow copy."""

    _expect_mapping(task, "Task")
    required = {
        "id",
        "title",
        "goal",
        "status",
        "priority",
        "dependencies",
        "expected_files",
        "validation_commands",
        "timeout_seconds",
        "max_retries",
        "mode",
        "checkpoint_key",
    }
    _require_exact_fields(task, required, "Task")

    normalized = dict(task)
    _expect_non_empty_string(normalized["id"], "Task.id")
    _expect_non_empty_string(normalized["title"], "Task.title")
    _expect_non_empty_string(normalized["goal"], "Task.goal")
    _expect_choice(normalized["status"], ALLOWED_TASK_STATUSES, "Task.status")
    _expect_non_negative_int(normalized["priority"], "Task.priority")
    _expect_string_list(normalized["dependencies"], "Task.dependencies", unique=True)
    _expect_string_list(normalized["expected_files"], "Task.expected_files")
    _expect_string_list(normalized["validation_commands"], "Task.validation_commands")
    _expect_positive_int(normalized["timeout_seconds"], "Task.timeout_seconds")
    _expect_non_negative_int(normalized["max_retries"], "Task.max_retries")
    _expect_choice(normalized["mode"], ALLOWED_MODES, "Task.mode")
    _expect_optional_non_empty_string(normalized["checkpoint_key"], "Task.checkpoint_key")
    return normalized


def validate_task_result(result: dict[str, Any]) -> dict[str, Any]:
    """Validate the minimum TaskResult contract and return a shallow copy."""

    _expect_mapping(result, "TaskResult")
    required = {
        "task_id",
        "completed",
        "files_created",
        "files_modified",
        "validation_ran",
        "validation_passed",
        "blockers",
        "next_recommendation",
    }
    _require_exact_fields(result, required, "TaskResult")

    normalized = dict(result)
    _expect_non_empty_string(normalized["task_id"], "TaskResult.task_id")
    _expect_bool(normalized["completed"], "TaskResult.completed")
    _expect_string_list(normalized["files_created"], "TaskResult.files_created")
    _expect_string_list(normalized["files_modified"], "TaskResult.files_modified")
    _expect_string_list(normalized["validation_ran"], "TaskResult.validation_ran")
    _expect_bool(normalized["validation_passed"], "TaskResult.validation_passed")
    _expect_string_list(normalized["blockers"], "TaskResult.blockers")
    _expect_string(normalized["next_recommendation"], "TaskResult.next_recommendation")
    return normalized


def validate_project_state(state: dict[str, Any]) -> dict[str, Any]:
    """Validate the minimum ProjectState contract and return a shallow copy."""

    _expect_mapping(state, "ProjectState")
    required = {
        "schema_version",
        "project_id",
        "status",
        "mode",
        "current_task_id",
        "completed_tasks",
        "failed_tasks",
        "blocked_tasks",
        "checkpoints",
        "created_at",
        "updated_at",
    }
    _require_fields(state, required, OPTIONAL_PROJECT_STATE_FIELDS, "ProjectState")

    normalized = dict(state)
    if normalized["schema_version"] != 1:
        raise ContractError("ProjectState.schema_version must be 1")
    _expect_non_empty_string(normalized["project_id"], "ProjectState.project_id")
    _expect_choice(normalized["status"], ALLOWED_PROJECT_STATUSES, "ProjectState.status")
    _expect_choice(normalized["mode"], ALLOWED_MODES, "ProjectState.mode")
    _expect_optional_non_empty_string(normalized["current_task_id"], "ProjectState.current_task_id")
    _expect_string_list(normalized["completed_tasks"], "ProjectState.completed_tasks", unique=True)
    _expect_string_list(normalized["failed_tasks"], "ProjectState.failed_tasks", unique=True)
    _expect_string_list(normalized["blocked_tasks"], "ProjectState.blocked_tasks", unique=True)
    _expect_string_list(normalized["checkpoints"], "ProjectState.checkpoints", unique=True)
    _expect_datetime_string(normalized["created_at"], "ProjectState.created_at")
    _expect_datetime_string(normalized["updated_at"], "ProjectState.updated_at")
    if "live_app" in normalized:
        _expect_optional_mapping(normalized["live_app"], "ProjectState.live_app")
    if "pending_control_plane_work" in normalized:
        _expect_optional_mapping(
            normalized["pending_control_plane_work"],
            "ProjectState.pending_control_plane_work",
        )
    if "pending_human_alignment_tasks" in normalized:
        _expect_string_list(
            normalized["pending_human_alignment_tasks"],
            "ProjectState.pending_human_alignment_tasks",
            unique=True,
        )
    if "last_queue_clear_at" in normalized:
        _expect_datetime_string(normalized["last_queue_clear_at"], "ProjectState.last_queue_clear_at")
    if "last_queue_clear_force" in normalized:
        _expect_bool(normalized["last_queue_clear_force"], "ProjectState.last_queue_clear_force")
    if "last_queue_clear_removed_task_ids" in normalized:
        _expect_string_list(
            normalized["last_queue_clear_removed_task_ids"],
            "ProjectState.last_queue_clear_removed_task_ids",
            unique=True,
        )
    if "preparing_session_id" in normalized:
        _expect_optional_non_empty_string(normalized["preparing_session_id"], "ProjectState.preparing_session_id")
    if "last_preparing_at" in normalized:
        _expect_datetime_string(normalized["last_preparing_at"], "ProjectState.last_preparing_at")
    if "last_released_zombie_task_ids" in normalized:
        _expect_string_list(
            normalized["last_released_zombie_task_ids"],
            "ProjectState.last_released_zombie_task_ids",
            unique=True,
        )
    if "last_released_zombie_at" in normalized:
        _expect_datetime_string(normalized["last_released_zombie_at"], "ProjectState.last_released_zombie_at")
    if "last_released_zombie_reason" in normalized:
        _expect_string(normalized["last_released_zombie_reason"], "ProjectState.last_released_zombie_reason")
    if "last_runtime_repair_at" in normalized:
        _expect_datetime_string(normalized["last_runtime_repair_at"], "ProjectState.last_runtime_repair_at")
    if "last_runtime_repair_reason" in normalized:
        _expect_string(normalized["last_runtime_repair_reason"], "ProjectState.last_runtime_repair_reason")
    if "last_cyberlace_block_at" in normalized:
        _expect_datetime_string(normalized["last_cyberlace_block_at"], "ProjectState.last_cyberlace_block_at")
    if "last_cyberlace_block_reason" in normalized:
        _expect_string(normalized["last_cyberlace_block_reason"], "ProjectState.last_cyberlace_block_reason")
    if "last_cyberlace_block_paths" in normalized:
        _expect_string_list(
            normalized["last_cyberlace_block_paths"],
            "ProjectState.last_cyberlace_block_paths",
            unique=True,
        )
    if "last_cyberlace_denied_action" in normalized:
        _expect_optional_non_empty_string(
            normalized["last_cyberlace_denied_action"],
            "ProjectState.last_cyberlace_denied_action",
        )
    if "last_cyberlace_safe_alternative" in normalized:
        _expect_optional_mapping(
            normalized["last_cyberlace_safe_alternative"],
            "ProjectState.last_cyberlace_safe_alternative",
        )
    return normalized


def validate_task_queue(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate a persistent task queue represented as a list of Tasks."""

    if not isinstance(queue, list):
        raise ContractError("TaskQueue must be a list")

    tasks = [validate_task(item) for item in queue]
    task_ids = [task["id"] for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ContractError("TaskQueue task ids must be unique")

    known_ids = set(task_ids)
    for task in tasks:
        missing = sorted(set(task["dependencies"]) - known_ids)
        if missing:
            raise ContractError(f"Task {task['id']} has unknown dependencies: {missing}")
    return tasks


def _require_exact_fields(data: dict[str, Any], required: set[str], label: str) -> None:
    _require_fields(data, required, frozenset(), label)


def _require_fields(data: dict[str, Any], required: set[str], optional: set[str] | frozenset[str], label: str) -> None:
    present = set(data)
    missing = sorted(required - present)
    extra = sorted(present - required - set(optional))
    if missing:
        raise ContractError(f"{label} missing required fields: {missing}")
    if extra:
        raise ContractError(f"{label} has unsupported fields: {extra}")


def _expect_mapping(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")


def _expect_optional_mapping(value: Any, label: str) -> None:
    if value is None:
        return
    _expect_mapping(value, label)


def _expect_string(value: Any, label: str) -> None:
    if not isinstance(value, str):
        raise ContractError(f"{label} must be a string")


def _expect_non_empty_string(value: Any, label: str) -> None:
    _expect_string(value, label)
    if not value.strip():
        raise ContractError(f"{label} must not be empty")
    if "\x00" in value:
        raise ContractError(f"{label} must not contain NUL bytes")


def _expect_optional_non_empty_string(value: Any, label: str) -> None:
    if value is None:
        return
    _expect_non_empty_string(value, label)


def _expect_string_list(value: Any, label: str, *, unique: bool = False) -> None:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be a list")
    for index, item in enumerate(value):
        _expect_non_empty_string(item, f"{label}[{index}]")
    if unique and len(value) != len(set(value)):
        raise ContractError(f"{label} must not contain duplicates")


def _expect_choice(value: Any, allowed: frozenset[str], label: str) -> None:
    _expect_non_empty_string(value, label)
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ContractError(f"{label} must be one of: {allowed_values}")


def _expect_bool(value: Any, label: str) -> None:
    if not isinstance(value, bool):
        raise ContractError(f"{label} must be a boolean")


def _expect_positive_int(value: Any, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{label} must be an integer")
    if value < 1:
        raise ContractError(f"{label} must be greater than 0")


def _expect_non_negative_int(value: Any, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{label} must be an integer")
    if value < 0:
        raise ContractError(f"{label} must be greater than or equal to 0")


def _expect_datetime_string(value: Any, label: str) -> None:
    _expect_non_empty_string(value, label)
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ContractError(f"{label} must be an ISO 8601 date-time") from exc
