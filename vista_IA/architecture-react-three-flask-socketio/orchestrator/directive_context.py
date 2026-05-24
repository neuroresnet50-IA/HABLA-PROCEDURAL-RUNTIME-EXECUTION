"""Build structured task context for future directive generation.

Sprint 7 stops at context assembly. It reads persisted runtime evidence and
does not generate or persist worker directives yet.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

try:
    from .contracts import ContractError
    from .plan_loader import PlanLoadError, load_plan, sprint_scope
    from .policy_loader import PolicyLoadError, load_policy
    from .state_store import StateStore
    from .task_queue import TaskQueue
except ImportError:  # pragma: no cover - supports direct script execution.
    from contracts import ContractError  # type: ignore
    from plan_loader import PlanLoadError, load_plan, sprint_scope  # type: ignore
    from policy_loader import PolicyLoadError, load_policy  # type: ignore
    from state_store import StateStore  # type: ignore
    from task_queue import TaskQueue  # type: ignore


class DirectiveContextError(RuntimeError):
    """Raised when a directive context cannot be built in strict mode."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        component: str | None = None,
        path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.component = component
        self.path = path

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "component": self.component,
            "path": self.path,
        }


def build_directive_context(
    *,
    repo_root: str | Path | None = None,
    runtime_dir: str | Path | None = None,
    task_workspace_root: str | Path | None = None,
    task_id: str | None = None,
    sprint_number: int | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Return policy, plan, runtime state, active task, evidence, and checkpoint.

    When strict is false, missing runtime pieces are represented in
    runtime_errors so callers can degrade explicitly instead of relying on
    implicit memory.
    """

    root = _repo_root(repo_root)
    workspace_root = _repo_root(task_workspace_root) if task_workspace_root is not None else root
    if runtime_dir is None:
        raise DirectiveContextError(
            "runtime_dir_required",
            "build_directive_context requires an explicit project runtime_dir.",
            component="runtime",
        )
    store = StateStore(runtime_dir=runtime_dir)
    errors: list[dict[str, Any]] = []

    policy = _load_component("policy", lambda: load_policy(root), errors, strict) or {}
    plan = _load_component("plan", lambda: load_plan(root), errors, strict) or {}
    project_state = _load_component("project_state", store.load_project_state, errors, strict) or {}
    task_queue = _load_component("task_queue", store.load_task_queue, errors, strict) or []
    history = _load_component("task_history", store.load_task_history, errors, strict) or []
    failures = _load_component("failures", store.load_failures, errors, strict) or []

    queue_runtime = _build_queue_runtime(store, task_queue, errors, strict)
    active_task, task_selection = _select_active_task(
        task_queue,
        project_state,
        queue_runtime.get("manager"),
        requested_task_id=task_id,
        errors=errors,
        strict=strict,
    )
    selected_task_id = active_task.get("id") if active_task else None
    inferred_sprint_number = sprint_number or _infer_sprint_number(plan, active_task)
    sprint = _build_sprint_context(plan, inferred_sprint_number, errors, strict)
    evidence = _inspect_task_evidence(workspace_root, active_task, errors, strict)
    checkpoint = _load_checkpoint_context(store, project_state, active_task, errors, strict)
    complexity_estimate = _load_complexity_estimate(store.runtime_dir, errors, strict)

    active_history = _filter_events_by_task_id(history, selected_task_id)
    active_failures = _filter_events_by_task_id(failures, selected_task_id)

    return {
        "schema_version": 1,
        "context_type": "directive_context",
        "repo_root": str(root),
        "system_root": str(root),
        "task_workspace_root": str(workspace_root),
        "runtime_dir": str(store.runtime_dir),
        "degraded": bool(errors),
        "runtime_errors": errors,
        "policy": policy,
        "plan": plan,
        "project_state": project_state,
        "task_queue": {
            "tasks": [dict(task) for task in task_queue],
            "overview": queue_runtime["overview"],
            "blocked_tasks": queue_runtime["blocked_tasks"],
            "ready_task_ids": queue_runtime["ready_task_ids"],
        },
        "history": {
            "total_events": len(history),
            "recent_events": history[-20:],
            "active_task_events": active_history,
        },
        "failures": {
            "total_events": len(failures),
            "recent_events": failures[-20:],
            "active_task_events": active_failures,
        },
        "checkpoint": checkpoint,
        "complexity_estimate": complexity_estimate,
        "active_task": active_task,
        "task_selection": task_selection,
        "sprint": sprint,
        "rules": _policy_rules(policy, sprint),
        "evidence": evidence,
        "audit": {
            "inputs": {
                "policy_file": str(root / "AGENTS.md"),
                "plan_file": str(root / "PLANS.md"),
                "task_workspace_root": str(workspace_root),
                "project_state_file": str(store.project_state_path),
                "task_queue_file": str(store.task_queue_path),
                "task_history_file": str(store.task_history_path),
                "failures_file": str(store.failures_path),
                "checkpoints_dir": str(store.checkpoints_dir),
            },
            "requested_task_id": task_id,
            "requested_sprint_number": sprint_number,
            "selected_task_id": selected_task_id,
        },
    }


def _load_complexity_estimate(runtime_dir: Path, errors: list[dict[str, Any]], strict: bool) -> dict[str, Any]:
    path = Path(runtime_dir) / "complexity_estimate.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _record_error(errors, "complexity_estimate", exc, strict)
        return {}
    if not isinstance(payload, dict):
        _record_error(errors, "complexity_estimate", DirectiveContextError(
            "invalid_complexity_estimate",
            "runtime/complexity_estimate.json must contain an object.",
            component="complexity_estimate",
            path=str(path),
        ), strict)
        return {}
    return payload


def current_directive_context(**kwargs: Any) -> dict[str, Any]:
    """Alias for callers that want the current control-plane context."""

    return build_directive_context(**kwargs)


def get_active_task(context: dict[str, Any]) -> dict[str, Any] | None:
    """Return the selected task from an already built directive context."""

    task = context.get("active_task")
    return dict(task) if isinstance(task, dict) else None


def get_sprint_context(context: dict[str, Any]) -> dict[str, Any]:
    """Return sprint scope from an already built directive context."""

    sprint = context.get("sprint")
    return dict(sprint) if isinstance(sprint, dict) else {}


def _repo_root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]


def _load_component(
    component: str,
    loader: Callable[[], Any],
    errors: list[dict[str, Any]],
    strict: bool,
) -> Any:
    try:
        return loader()
    except (ContractError, PolicyLoadError, PlanLoadError, OSError) as exc:
        _record_error(errors, component, exc, strict)
        return None


def _record_error(
    errors: list[dict[str, Any]],
    component: str,
    exc: Exception,
    strict: bool,
    *,
    code: str | None = None,
) -> None:
    payload = {
        "component": component,
        "code": code or getattr(exc, "code", type(exc).__name__),
        "message": getattr(exc, "message", str(exc)),
        "path": getattr(exc, "path", None),
    }
    errors.append(payload)
    if strict:
        raise DirectiveContextError(
            str(payload["code"]),
            str(payload["message"]),
            component=component,
            path=payload["path"],
        ) from exc


def _build_queue_runtime(
    store: StateStore,
    task_queue: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    strict: bool,
) -> dict[str, Any]:
    manager: TaskQueue | None = None
    blocked_tasks: list[dict[str, Any]] = []
    ready_tasks: list[dict[str, Any]] = []

    if task_queue:
        try:
            manager = TaskQueue(store)
            blocked_tasks = manager.blocked_tasks()
            ready_tasks = manager.ready_tasks()
        except (ContractError, OSError) as exc:
            _record_error(errors, "task_queue_runtime", exc, strict)

    return {
        "manager": manager,
        "blocked_tasks": blocked_tasks,
        "ready_task_ids": [task["id"] for task in ready_tasks],
        "overview": {
            "total": len(task_queue),
            "by_status": _count_by_status(task_queue),
            "next_ready_task_id": ready_tasks[0]["id"] if ready_tasks else None,
        },
    }


def _select_active_task(
    task_queue: list[dict[str, Any]],
    project_state: dict[str, Any],
    manager: TaskQueue | None,
    *,
    requested_task_id: str | None,
    errors: list[dict[str, Any]],
    strict: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    selection = {
        "requested_task_id": requested_task_id,
        "project_state_current_task_id": project_state.get("current_task_id"),
        "selected_task_id": None,
        "source": None,
        "reason": "",
    }

    if requested_task_id:
        task = _find_task(task_queue, requested_task_id)
        if task:
            selection.update({"selected_task_id": task["id"], "source": "requested_task_id"})
            return task, selection
        exc = DirectiveContextError("task_not_found", f"Requested task not found: {requested_task_id}")
        _record_error(errors, "active_task", exc, strict)

    current_task_id = project_state.get("current_task_id")
    if isinstance(current_task_id, str) and current_task_id.strip():
        task = _find_task(task_queue, current_task_id)
        if task:
            selection.update({"selected_task_id": task["id"], "source": "project_state.current_task_id"})
            return task, selection
        exc = DirectiveContextError("current_task_not_found", f"Current task not found: {current_task_id}")
        _record_error(errors, "active_task", exc, strict)

    try:
        task = manager.next_ready_task() if manager is not None else None
    except ContractError as exc:
        _record_error(errors, "active_task", exc, strict)
        task = None

    if task:
        selection.update({"selected_task_id": task["id"], "source": "next_ready_task"})
        return task, selection

    selection["reason"] = "No active task and no ready task found in persisted queue."
    return None, selection


def _build_sprint_context(
    plan: dict[str, Any],
    sprint_number: int | None,
    errors: list[dict[str, Any]],
    strict: bool,
) -> dict[str, Any]:
    if not sprint_number:
        return {
            "number": None,
            "objective": "",
            "deliverables": [],
            "acceptance": [],
            "out_of_scope_deliverables": [],
            "source": "not_inferred",
        }
    try:
        scope = sprint_scope(plan, sprint_number)
        scope["source"] = "requested_or_inferred"
        return scope
    except (PlanLoadError, KeyError, TypeError) as exc:
        _record_error(errors, "sprint", exc, strict)
        return {
            "number": sprint_number,
            "objective": "",
            "deliverables": [],
            "acceptance": [],
            "out_of_scope_deliverables": [],
            "source": "error",
        }


def _infer_sprint_number(plan: dict[str, Any], task: dict[str, Any] | None) -> int | None:
    if not task:
        return None

    text = " ".join([task.get("id", ""), task.get("title", ""), task.get("goal", "")])
    match = re.search(r"\bSprint\s+(\d+)\b|\bS(\d+)\b", text, flags=re.I)
    if match:
        return int(match.group(1) or match.group(2))

    expected_files = {_clean_markdown_token(path) for path in task.get("expected_files", [])}
    best_number: int | None = None
    best_score = 0
    for key, sprint in plan.get("sprints", {}).items():
        score = 0
        for deliverable in sprint.get("deliverables", []):
            clean = _clean_markdown_token(deliverable)
            if clean in expected_files:
                score += 2
            elif any(clean and (clean in path or path in clean) for path in expected_files):
                score += 1
        if score > best_score:
            best_score = score
            best_number = int(key)
    return best_number


def _inspect_task_evidence(
    repo_root: Path,
    task: dict[str, Any] | None,
    errors: list[dict[str, Any]],
    strict: bool,
) -> dict[str, Any]:
    if not task:
        return {
            "expected_files": [],
            "found": [],
            "missing": [],
            "validation_commands": [],
            "blockers": ["No active task selected; no task evidence can be inspected."],
        }

    records: list[dict[str, Any]] = []
    blockers: list[str] = []
    for relative_path in task.get("expected_files", []):
        try:
            path = _resolve_under_root(repo_root, relative_path)
            exists = path.exists()
            is_file = path.is_file() if exists else False
            size = path.stat().st_size if exists and path.is_file() else None
            records.append(
                {
                    "path": relative_path,
                    "absolute_path": str(path),
                    "exists": exists,
                    "is_file": is_file,
                    "size": size,
                }
            )
            if not exists:
                blockers.append(f"Missing expected file: {relative_path}")
        except ContractError as exc:
            _record_error(errors, "evidence", exc, strict)
            blockers.append(str(exc))
            records.append(
                {
                    "path": relative_path,
                    "absolute_path": None,
                    "exists": False,
                    "is_file": False,
                    "size": None,
                }
            )

    return {
        "expected_files": records,
        "found": [record["path"] for record in records if record["exists"]],
        "missing": [record["path"] for record in records if not record["exists"]],
        "validation_commands": list(task.get("validation_commands", [])),
        "blockers": blockers,
    }


def _load_checkpoint_context(
    store: StateStore,
    project_state: dict[str, Any],
    task: dict[str, Any] | None,
    errors: list[dict[str, Any]],
    strict: bool,
) -> dict[str, Any]:
    available = _safe_list_checkpoints(store, errors, strict)
    candidates: list[tuple[str, str]] = []
    if task and task.get("checkpoint_key"):
        candidates.append((task["checkpoint_key"], "task.checkpoint_key"))
    for key in reversed(project_state.get("checkpoints", []) if isinstance(project_state, dict) else []):
        candidates.append((key, "project_state.checkpoints"))
    for key in reversed(available):
        candidates.append((key, "runtime/checkpoints"))

    tried: list[dict[str, str]] = []
    seen: set[str] = set()
    for key, source in candidates:
        if key in seen:
            continue
        seen.add(key)
        tried.append({"checkpoint_key": key, "source": source})
        try:
            data = store.load_checkpoint(key)
            return {
                "checkpoint_key": key,
                "source": source,
                "path": str(store.checkpoints_dir / f"{key}.json"),
                "available_checkpoint_keys": available,
                "tried": tried,
                "data": data,
            }
        except (ContractError, OSError) as exc:
            if source == "task.checkpoint_key" and key not in available:
                continue
            _record_error(errors, "checkpoint", exc, strict)

    return {
        "checkpoint_key": None,
        "source": "none",
        "path": None,
        "available_checkpoint_keys": available,
        "tried": tried,
        "data": None,
    }


def _safe_list_checkpoints(store: StateStore, errors: list[dict[str, Any]], strict: bool) -> list[str]:
    try:
        return store.list_checkpoints()
    except (ContractError, OSError) as exc:
        _record_error(errors, "checkpoint", exc, strict)
        return []


def _policy_rules(policy: dict[str, Any], sprint: dict[str, Any]) -> dict[str, Any]:
    hard_rules = list(policy.get("runtime_hard_rules", []))
    directive_policy = list(policy.get("directive_policy", []))
    sprint_delivery_policy = list(policy.get("sprint_delivery_policy", []))
    implementation_policy = list(policy.get("implementation_policy", []))
    out_of_scope = list(sprint.get("out_of_scope_deliverables", []))
    return {
        "runtime_hard_rules": hard_rules,
        "directive_policy": directive_policy,
        "sprint_delivery_policy": sprint_delivery_policy,
        "implementation_policy": implementation_policy,
        "active_constraints": _unique(
            [
                *hard_rules,
                *directive_policy,
                "Respect the selected sprint deliverables and do not advance future deliverables.",
                *[f"Out of scope for current sprint: {item}" for item in out_of_scope],
            ]
        ),
    }


def _filter_events_by_task_id(events: list[dict[str, Any]], task_id: str | None) -> list[dict[str, Any]]:
    if not task_id:
        return []
    return [event for event in events if _event_task_id(event) == task_id]


def _event_task_id(event: dict[str, Any]) -> str | None:
    result = event.get("result")
    if isinstance(result, dict) and isinstance(result.get("task_id"), str):
        return result["task_id"]
    failure = event.get("failure")
    if isinstance(failure, dict):
        if isinstance(failure.get("task_id"), str):
            return failure["task_id"]
        nested = failure.get("failure")
        if isinstance(nested, dict):
            task_result = nested.get("task_result")
            if isinstance(task_result, dict) and isinstance(task_result.get("task_id"), str):
                return task_result["task_id"]
    return None


def _find_task(task_queue: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    for task in task_queue:
        if task.get("id") == task_id:
            return dict(task)
    return None


def _count_by_status(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        status = str(task.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _resolve_under_root(repo_root: Path, relative_path: str) -> Path:
    path = (repo_root / relative_path).resolve()
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise ContractError(f"Expected file escapes repository root: {relative_path}") from exc
    return path


def _clean_markdown_token(value: str) -> str:
    return value.strip().strip("`").strip()


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
