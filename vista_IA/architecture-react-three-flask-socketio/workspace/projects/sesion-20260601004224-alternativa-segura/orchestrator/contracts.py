from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping


ALLOWED_MODES = ("smoke", "build", "medium", "long-run")
TASK_STATUSES = ("pending", "running", "completed", "failed", "blocked")


class ContractError(ValueError):
    """Raised when persisted runtime data does not match the contract."""


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ContractError(f"{field_name} must be a list of strings")
    return list(value)


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    goal: str
    status: str
    priority: int
    dependencies: list[str] = field(default_factory=list)
    expected_files: list[str] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    timeout_seconds: int = 900
    max_retries: int = 3
    mode: str = "build"
    checkpoint_key: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "Task":
        task = cls(
            id=str(payload.get("id") or ""),
            title=str(payload.get("title") or ""),
            goal=str(payload.get("goal") or ""),
            status=str(payload.get("status") or ""),
            priority=int(payload.get("priority", 0)),
            dependencies=_string_list(payload.get("dependencies", []), "dependencies"),
            expected_files=_string_list(payload.get("expected_files", []), "expected_files"),
            validation_commands=_string_list(payload.get("validation_commands", []), "validation_commands"),
            timeout_seconds=int(payload.get("timeout_seconds", 0)),
            max_retries=int(payload.get("max_retries", 0)),
            mode=str(payload.get("mode") or ""),
            checkpoint_key=payload.get("checkpoint_key"),
        )
        task.validate()
        return task

    def validate(self) -> None:
        if not self.id or not self.title or not self.goal:
            raise ContractError("task id, title and goal are required")
        if self.status not in TASK_STATUSES:
            raise ContractError(f"invalid task status: {self.status}")
        if self.mode not in ALLOWED_MODES:
            raise ContractError(f"invalid task mode: {self.mode}")
        if self.timeout_seconds <= 0:
            raise ContractError("timeout_seconds must be greater than zero")
        if self.max_retries < 0:
            raise ContractError("max_retries cannot be negative")
        if self.checkpoint_key is not None and not isinstance(self.checkpoint_key, str):
            raise ContractError("checkpoint_key must be a string or null")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    completed: bool
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    validation_ran: list[str] = field(default_factory=list)
    validation_passed: bool = False
    blockers: list[str] = field(default_factory=list)
    next_recommendation: str = ""

    def validate(self) -> None:
        if not self.task_id:
            raise ContractError("task_result.task_id is required")
        if self.completed and (not self.validation_passed or self.blockers):
            raise ContractError("completed task results require passed validation and no blockers")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class ProjectState:
    project_slug: str
    status: str
    mode: str
    updated_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ProjectState":
        state = cls(
            project_slug=str(payload.get("project_slug") or payload.get("projectSlug") or ""),
            status=str(payload.get("status") or ""),
            mode=str(payload.get("mode") or ""),
            updated_at=str(payload.get("updated_at") or payload.get("updatedAt") or utc_now_iso()),
        )
        state.validate()
        return state

    def validate(self) -> None:
        if not self.project_slug:
            raise ContractError("project_slug is required")
        if self.mode not in ALLOWED_MODES:
            raise ContractError(f"invalid project mode: {self.mode}")
        if not self.status:
            raise ContractError("project status is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
