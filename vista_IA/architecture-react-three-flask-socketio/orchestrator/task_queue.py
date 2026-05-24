"""Persistent task queue operations for Sprint 2."""

from __future__ import annotations

from typing import Any

try:
    from .contracts import (
        ALLOWED_TASK_STATUSES,
        ContractError,
        validate_task,
        validate_task_queue,
    )
    from .state_store import StateStore
except ImportError:  # pragma: no cover - supports direct script execution during bootstraps.
    from contracts import (  # type: ignore
        ALLOWED_TASK_STATUSES,
        ContractError,
        validate_task,
        validate_task_queue,
    )
    from state_store import StateStore  # type: ignore


class TaskQueue:
    """Load, validate, order, and persist the runtime task queue."""

    def __init__(self, store: StateStore | None = None, *, bootstrap_empty: bool = False) -> None:
        self.store = _require_store(store)
        if bootstrap_empty and not self.store.task_queue_path.exists():
            self._tasks = []
        else:
            self._tasks = self.store.load_task_queue()
        self.validate_queue()

    def reload(self) -> list[dict[str, Any]]:
        self._tasks = self.store.load_task_queue()
        return self.list()

    def save(self) -> None:
        self.store.save_task_queue(self._tasks)

    def enqueue(self, task: dict[str, Any], *, persist: bool = True) -> dict[str, Any]:
        validated_task = validate_task(task)
        candidate = [*self._tasks, validated_task]
        _validate_unique_task_ids(candidate)
        validate_task_queue(candidate)
        _assert_acyclic(candidate)
        self._tasks = candidate
        if persist:
            self.save()
        return dict(validated_task)

    def enqueue_many(self, tasks: list[dict[str, Any]], *, persist: bool = True) -> list[dict[str, Any]]:
        validated_tasks = [validate_task(task) for task in tasks]
        candidate = [*self._tasks, *validated_tasks]
        _validate_unique_task_ids(candidate)
        validate_task_queue(candidate)
        _assert_acyclic(candidate)
        self._tasks = candidate
        if persist:
            self.save()
        return [dict(task) for task in validated_tasks]

    def list(self) -> list[dict[str, Any]]:
        return [dict(task) for task in self._tasks]

    def ordered_tasks(self) -> list[dict[str, Any]]:
        return sort_by_dependencies_and_priority(self._tasks)

    def validate_queue(self) -> list[dict[str, Any]]:
        self._tasks = validate_task_queue(self._tasks)
        _assert_acyclic(self._tasks)
        return self.list()

    def completed_task_ids(self) -> set[str]:
        completed = {task["id"] for task in self._tasks if task["status"] == "completed"}
        try:
            completed.update(self.store.load_project_state().get("completed_tasks", []))
        except ContractError:
            pass
        return completed

    def blocked_tasks(self) -> list[dict[str, Any]]:
        completed = self.completed_task_ids()
        blocked: list[dict[str, Any]] = []
        for task in self._tasks:
            if task["status"] != "pending":
                continue
            missing = [dependency for dependency in task["dependencies"] if dependency not in completed]
            if missing:
                blocked.append({"task_id": task["id"], "missing_dependencies": missing})
        return blocked

    def ready_tasks(self) -> list[dict[str, Any]]:
        completed = self.completed_task_ids()
        index_by_id = _index_by_task_id(self._tasks)
        ready = [
            task
            for task in self._tasks
            if task["status"] == "pending"
            and all(dependency in completed for dependency in task["dependencies"])
        ]
        return sorted(
            (dict(task) for task in ready),
            key=lambda task: (-task["priority"], index_by_id[task["id"]], task["id"]),
        )

    def next_ready_task(self) -> dict[str, Any] | None:
        ready = self.ready_tasks()
        return ready[0] if ready else None

    def mark_task_status(
        self,
        task_id: str,
        status: str,
        *,
        persist: bool = True,
    ) -> dict[str, Any]:
        if status not in ALLOWED_TASK_STATUSES:
            raise ContractError(f"status must be one of: {', '.join(sorted(ALLOWED_TASK_STATUSES))}")

        for index, task in enumerate(self._tasks):
            if task["id"] != task_id:
                continue
            updated = dict(task)
            updated["status"] = status
            validated = validate_task(updated)
            candidate = [*self._tasks]
            candidate[index] = validated
            validate_task_queue(candidate)
            _assert_acyclic(candidate)
            self._tasks = candidate
            if persist:
                self.save()
            return dict(validated)

        raise ContractError(f"Task not found: {task_id}")


def sort_by_dependencies_and_priority(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a DAG order, choosing higher priority first when dependencies allow."""

    validated = validate_task_queue(tasks)
    index_by_id = _index_by_task_id(validated)
    remaining = {task["id"]: dict(task) for task in validated}
    ordered: list[dict[str, Any]] = []

    while remaining:
        available = [
            task
            for task in remaining.values()
            if all(dependency not in remaining for dependency in task["dependencies"])
        ]
        if not available:
            cycle_ids = ", ".join(sorted(remaining))
            raise ContractError(f"TaskQueue dependencies contain a cycle: {cycle_ids}")

        selected = sorted(
            available,
            key=lambda task: (-task["priority"], index_by_id[task["id"]], task["id"]),
        )[0]
        ordered.append(dict(selected))
        del remaining[selected["id"]]

    return ordered


def load_queue(store: StateStore | None = None) -> list[dict[str, Any]]:
    return TaskQueue(_require_store(store)).list()


def save_queue(tasks: list[dict[str, Any]], store: StateStore | None = None) -> None:
    target_store = _require_store(store)
    validated = validate_task_queue(tasks)
    _assert_acyclic(validated)
    target_store.save_task_queue(validated)


def enqueue(task: dict[str, Any], store: StateStore | None = None) -> dict[str, Any]:
    return TaskQueue(_require_store(store)).enqueue(task)


def enqueue_many(tasks: list[dict[str, Any]], store: StateStore | None = None) -> list[dict[str, Any]]:
    return TaskQueue(_require_store(store)).enqueue_many(tasks)


def list_tasks(store: StateStore | None = None) -> list[dict[str, Any]]:
    return TaskQueue(_require_store(store)).list()


def next_ready_task(store: StateStore | None = None) -> dict[str, Any] | None:
    return TaskQueue(_require_store(store)).next_ready_task()


def mark_task_status(
    task_id: str,
    status: str,
    store: StateStore | None = None,
) -> dict[str, Any]:
    return TaskQueue(_require_store(store)).mark_task_status(task_id, status)


def validate_queue(
    tasks: list[dict[str, Any]] | None = None,
    store: StateStore | None = None,
) -> list[dict[str, Any]]:
    if tasks is not None:
        validated = validate_task_queue(tasks)
        _assert_acyclic(validated)
        return [dict(task) for task in validated]
    return TaskQueue(_require_store(store)).validate_queue()


def _require_store(store: StateStore | None) -> StateStore:
    if store is None:
        raise ContractError("TaskQueue requires an explicit StateStore bound to a project runtime.")
    return store


def _assert_acyclic(tasks: list[dict[str, Any]]) -> None:
    sort_by_dependencies_and_priority(tasks)


def _validate_unique_task_ids(tasks: list[dict[str, Any]]) -> None:
    task_ids = [task["id"] for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ContractError("TaskQueue task ids must be unique")


def _index_by_task_id(tasks: list[dict[str, Any]]) -> dict[str, int]:
    return {task["id"]: index for index, task in enumerate(tasks)}
