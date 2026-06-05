"""Task-scoped runtime residue cleaner.

The broom is intentionally conservative: it does not delete canonical history,
failures, checkpoints, directives or product files. It reconciles transient
state lists and writes an auditable sweep report so the runtime can ignore old
failure residue without losing forensic evidence.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BROOM_COMMAND_NAME = "to-sweep-with-a-broom"
TRANSIENT_STATUSES = {"preparing", "running"}
BLOCKED_STATUSES = {"blocked"}
FAILED_STATUSES = {"failed"}
LACE_SPLIT_TASK_PATTERN = re.compile(r"^(LACE-\d{8}-(\d{3}))-SPLIT-\d{3}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sweep_with_broom(
    project_root: str | Path,
    *,
    task_id: str | None = None,
    phase: str = "manual",
    dry_run: bool = False,
    reason: str = "task_residue_cleanup",
) -> dict[str, Any]:
    project_path = Path(project_root).expanduser().resolve()
    runtime_dir = project_path / "runtime"
    artifacts_dir = runtime_dir / "artifacts" / "broom"
    report: dict[str, Any] = {
        "ok": True,
        "tool": BROOM_COMMAND_NAME,
        "phase": phase,
        "reason": reason,
        "dryRun": bool(dry_run),
        "projectRoot": str(project_path),
        "runtimeDir": str(runtime_dir),
        "taskId": str(task_id or ""),
        "createdAt": utc_now(),
        "actions": [],
        "ignoredResidue": [],
        "warnings": [],
    }
    if not runtime_dir.is_dir():
        report["ok"] = False
        report["error"] = "runtime_dir_missing"
        return report

    state_path = runtime_dir / "project_state.json"
    queue_path = runtime_dir / "task_queue.json"
    history_path = runtime_dir / "task_history.jsonl"
    failures_path = runtime_dir / "failures.jsonl"

    state = _read_json_object(state_path)
    queue = _read_json_list(queue_path)
    history_tail = _latest_jsonl(history_path)
    history_events = _read_jsonl_objects(history_path)
    failure_tail = _latest_jsonl(failures_path)
    current_task_id = _choose_current_task_id(task_id, state, queue, history_tail)
    report["taskId"] = current_task_id or str(task_id or "")

    defer_actions = _defer_invalid_lace_split_tasks(queue, project_path, history_events, current_task_id)
    if defer_actions:
        report["actions"].extend(defer_actions)
        if not dry_run:
            _atomic_write_json(queue_path, queue)

    queue_status = {str(item.get("id")): str(item.get("status") or "") for item in queue if isinstance(item, dict)}
    queue_ids = set(queue_status)
    report["queueStatus"] = queue_status

    if state:
        changes = _reconcile_project_state(state, queue_status, current_task_id)
        report["actions"].extend(changes)
        if changes and not dry_run:
            _atomic_write_json(state_path, state)

    stale_failure_reason = _stale_runtime_record_reason(failure_tail, current_task_id)
    if stale_failure_reason:
        report["ignoredResidue"].append({
            "kind": "failure_record",
            "reason": stale_failure_reason,
            "taskId": _task_id_from_record(failure_tail),
        })

    stale_history_reason = _stale_runtime_record_reason(history_tail, current_task_id)
    if stale_history_reason:
        report["ignoredResidue"].append({
            "kind": "history_record",
            "reason": stale_history_reason,
            "taskId": _task_id_from_record(history_tail),
        })

    if current_task_id and current_task_id not in queue_ids:
        report["warnings"].append(f"task_id_not_in_queue:{current_task_id}")

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    safe_task = _safe_slug(report.get("taskId") or "no-task")
    safe_phase = _safe_slug(phase or "manual")
    report_path = artifacts_dir / f"{utc_now().replace(':', '').replace('-', '')}-{safe_task}-{safe_phase}.json"
    latest_path = artifacts_dir / "latest.json"
    report["reportPath"] = _relative_to_project(project_path, report_path)
    report["latestPath"] = _relative_to_project(project_path, latest_path)
    if not dry_run:
        _atomic_write_json(report_path, report)
        _atomic_write_json(latest_path, report)
    return report



def _defer_invalid_lace_split_tasks(
    queue: list[Any],
    project_path: Path,
    history_events: list[dict[str, Any]],
    current_task_id: str | None,
) -> list[dict[str, Any]]:
    completed_ids = {
        str(item.get("id") or "")
        for item in queue
        if isinstance(item, dict) and item.get("status") == "completed" and str(item.get("id") or "")
    }
    for event in history_events:
        result = event.get("result") if isinstance(event, dict) else None
        if not isinstance(result, dict):
            continue
        task_id = str(result.get("task_id") or "")
        if task_id and result.get("completed") is True and result.get("validation_passed") is True:
            completed_ids.add(task_id)

    actions: list[dict[str, Any]] = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("id") or "")
        match = LACE_SPLIT_TASK_PATTERN.match(task_id)
        if not match:
            continue
        if task_id == current_task_id and item.get("status") in TRANSIENT_STATUSES:
            continue
        if item.get("status") not in BLOCKED_STATUSES | FAILED_STATUSES:
            continue

        parent_task_id = match.group(1)
        cycle_number = int(match.group(2))
        if parent_task_id not in completed_ids:
            continue
        cycle_doc = project_path / "docs" / "lace_cycles" / f"ciclo-{cycle_number:02d}.md"
        checkpoint_dir = project_path / "runtime" / "checkpoints"
        checkpoint_paths = list(checkpoint_dir.glob(f"lace-cycle-{cycle_number:03d}-*.json"))
        if not cycle_doc.is_file() or not checkpoint_paths:
            continue

        before = str(item.get("status") or "")
        item["status"] = "deferred"
        actions.append({
            "action": "defer_invalid_lace_split_task",
            "taskId": task_id,
            "parentTaskId": parent_task_id,
            "before": before,
            "after": "deferred",
            "reason": "parent_lace_cycle_validated_and_split_task_is_invalid_recovery_residue",
            "cycleDoc": _relative_to_project(project_path, cycle_doc),
            "checkpointCount": len(checkpoint_paths),
        })
    return actions

def _reconcile_project_state(state: dict[str, Any], queue_status: dict[str, str], current_task_id: str | None) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    blocked_before = [str(item) for item in state.get("blocked_tasks") or [] if str(item).strip()]
    failed_before = [str(item) for item in state.get("failed_tasks") or [] if str(item).strip()]

    blocked_after = [task for task in blocked_before if queue_status.get(task) in BLOCKED_STATUSES]
    failed_after = [task for task in failed_before if queue_status.get(task) in FAILED_STATUSES]
    if blocked_after != blocked_before:
        state["blocked_tasks"] = blocked_after
        actions.append({"action": "drop_stale_blocked_tasks", "before": blocked_before, "after": blocked_after})
    if failed_after != failed_before:
        state["failed_tasks"] = failed_after
        actions.append({"action": "drop_stale_failed_tasks", "before": failed_before, "after": failed_after})

    current = str(state.get("current_task_id") or "")
    if current and queue_status.get(current) not in TRANSIENT_STATUSES:
        state["current_task_id"] = current_task_id if current_task_id and queue_status.get(current_task_id) in TRANSIENT_STATUSES else None
        actions.append({"action": "clear_stale_current_task_id", "before": current, "after": state.get("current_task_id")})

    if actions:
        state["updated_at"] = utc_now()
    return actions


def _choose_current_task_id(task_id: str | None, state: dict[str, Any], queue: list[Any], history_tail: dict[str, Any] | None) -> str | None:
    for candidate in (task_id, state.get("current_task_id") if isinstance(state, dict) else None):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    for status in ("running", "preparing"):
        for item in queue:
            if isinstance(item, dict) and item.get("status") == status and str(item.get("id") or "").strip():
                return str(item["id"]).strip()
    history_task = _task_id_from_record(history_tail)
    return history_task or None


def _stale_runtime_record_reason(record: dict[str, Any] | None, current_task_id: str | None) -> str:
    if not isinstance(record, dict) or not current_task_id:
        return ""
    record_task_id = _task_id_from_record(record)
    if record_task_id and record_task_id != current_task_id:
        return f"different_task:{record_task_id}"
    return ""


def _task_id_from_record(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("task_id", "taskId", "currentTaskId"):
            raw = value.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        for item in value.values():
            found = _task_id_from_record(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _task_id_from_record(item)
            if found:
                return found
    return ""


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_json_list(path: Path) -> list[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("tasks"), list):
        return value["tasks"]
    return []



def _read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events

def _latest_jsonl(path: Path) -> dict[str, Any] | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return {"raw": line[-1200:]}
        return payload if isinstance(payload, dict) else {"value": payload}
    return None


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _relative_to_project(project_path: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_path).as_posix()
    except ValueError:
        return str(path)


def _safe_slug(value: Any) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip()).strip("-._")
    return slug[:80] or "item"
