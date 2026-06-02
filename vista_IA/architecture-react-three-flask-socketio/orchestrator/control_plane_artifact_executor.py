"""Deterministic control-plane artifact materialization.

This executor is intentionally narrower than host_write: it only writes
control-plane artifacts that the runtime itself owns and can produce without a
Codex worker. Final closure still belongs to orchestrator.validator.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .complexity_estimator import estimate_complexity
    from .contracts import ContractError, validate_task_result
except ImportError:  # pragma: no cover - supports direct script execution.
    from complexity_estimator import estimate_complexity  # type: ignore
    from contracts import ContractError, validate_task_result  # type: ignore


CONTROL_PLANE_ARTIFACT_STRATEGY = "control_plane_artifact"
COMPLEXITY_ESTIMATE_PATH = "runtime/complexity_estimate.json"
TASK_RESULT_KEYS = frozenset(
    {
        "task_id",
        "completed",
        "files_created",
        "files_modified",
        "validation_ran",
        "validation_passed",
        "blockers",
        "next_recommendation",
    }
)


def should_use_control_plane_artifact_executor(task: dict[str, Any]) -> bool:
    """Return True only for deterministic runtime-owned artifacts."""

    if not isinstance(task, dict):
        return False
    expected_files = _expected_files(task)
    return expected_files == [COMPLEXITY_ESTIMATE_PATH]


def execute_control_plane_artifact_task(task: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """Materialize a supported control-plane artifact in the project workspace."""

    task_id = str(task.get("id") or "UNKNOWN-TASK")
    result: dict[str, Any] = {
        "task_id": task_id,
        "completed": False,
        "files_created": [],
        "files_modified": [],
        "validation_ran": [],
        "validation_passed": False,
        "blockers": [],
        "next_recommendation": "",
        "execution_strategy": CONTROL_PLANE_ARTIFACT_STRATEGY,
        "selector_reason": "runtime complexity_estimate deterministic fast path",
        "evidence": [],
    }

    workspace_path = Path(workspace).resolve()
    blockers = validate_control_plane_artifact_task(task, workspace_path)
    if blockers:
        result["blockers"] = blockers
        result["next_recommendation"] = "Route unsupported artifacts to codex_worker or fix expected_files."
        return result

    expected_file = COMPLEXITY_ESTIMATE_PATH
    target = _resolve_complexity_estimate_path(workspace_path, expected_file)
    existed = target.exists()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = build_complexity_estimate_artifact(task, workspace_path, existing_path=target if existed else None)
        tmp_path = target.with_name(f".{target.name}.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(target)
        if existed:
            result["files_modified"].append(expected_file)
        else:
            result["files_created"].append(expected_file)
        result["evidence"].append(
            {
                "expected_file": expected_file,
                "path": str(target),
                "size": target.stat().st_size,
                "created": not existed,
            }
        )
    except Exception as exc:
        result["blockers"].append(
            f"ControlPlaneArtifactExecutor failed for {expected_file}: {type(exc).__name__}: {exc}"
        )

    result["completed"] = not result["blockers"] and bool(result["files_created"] or result["files_modified"])
    result["next_recommendation"] = (
        "Run validator before marking this task completed."
        if result["completed"]
        else "Fix control-plane artifact blockers and rerun the isolated task."
    )
    return result


def validate_control_plane_artifact_task(task: dict[str, Any], workspace: Path) -> list[str]:
    blockers: list[str] = []
    if not isinstance(task, dict):
        return ["Task must be an object."]
    expected_files = _expected_files(task)
    if expected_files != [COMPLEXITY_ESTIMATE_PATH]:
        blockers.append("ControlPlaneArtifactExecutor only supports runtime/complexity_estimate.json.")
    if not Path(workspace).exists() or not Path(workspace).is_dir():
        blockers.append(f"Workspace does not exist or is not a directory: {Path(workspace).resolve()}")
    try:
        _resolve_complexity_estimate_path(Path(workspace).resolve(), COMPLEXITY_ESTIMATE_PATH)
    except ContractError as exc:
        blockers.append(str(exc))
    return blockers


def build_complexity_estimate_artifact(
    task: dict[str, Any],
    workspace: Path,
    *,
    existing_path: Path | None = None,
) -> dict[str, Any]:
    goal = str(task.get("goal") or task.get("title") or "")
    runtime_mode = str(task.get("mode") or "build")
    existing = _read_existing_object(existing_path)
    estimate = estimate_complexity(
        goal,
        runtime_mode=runtime_mode,
        project_file_count=_count_material_files(workspace),
        launch_mode="existing",
        project_slug=workspace.name,
    )
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        **estimate,
        **{key: value for key, value in existing.items() if key not in {"task_id", "task_title", "task_goal"}},
        "analysis_updated_at": now,
        "task_id": str(task.get("id") or ""),
        "task_title": str(task.get("title") or ""),
        "task_goal": goal,
        "task_scope": "complexity_estimate_only",
        "expected_files": [COMPLEXITY_ESTIMATE_PATH],
        "fast_path": {
            "executor": "control_plane_artifact_executor",
            "reason": "runtime_complexity_estimate",
            "codex_skipped": True,
            "validator_remains_authority": True,
        },
        "control_plane_contract": _control_plane_contract(goal),
    }
    payload["reasons"] = _merge_reasons(
        estimate.get("reasons"),
        [
            "control_plane_artifact_fast_path",
            "codex worker skipped for deterministic runtime artifact",
        ],
    )
    return payload


def task_result_payload(result: dict[str, Any]) -> dict[str, Any]:
    return validate_task_result({key: result[key] for key in TASK_RESULT_KEYS})


def _expected_files(task: dict[str, Any]) -> list[str]:
    files = task.get("expected_files")
    if not isinstance(files, list):
        return []
    return [str(item).strip().lstrip("./") for item in files if str(item).strip()]


def _resolve_complexity_estimate_path(workspace: Path, expected_file: str) -> Path:
    raw = str(expected_file or "")
    relative = Path(raw)
    if raw != COMPLEXITY_ESTIMATE_PATH:
        raise ContractError(f"Unsupported control-plane artifact path: {expected_file}")
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        raise ContractError(f"Unsafe control-plane artifact path: {expected_file}")
    workspace_real = Path(workspace).resolve()
    candidate = (workspace_real / relative).resolve(strict=False)
    try:
        candidate.relative_to(workspace_real)
    except ValueError as exc:
        raise ContractError(f"Control-plane artifact escapes workspace: {expected_file}") from exc
    return candidate


def _read_existing_object(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _count_material_files(workspace: Path) -> int:
    ignored_parts = {".git", "__pycache__", "node_modules", ".venv", "venv"}
    count = 0
    for path in Path(workspace).rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(workspace).parts)
        if parts & ignored_parts:
            continue
        if path.as_posix().endswith("/runtime/complexity_estimate.json"):
            continue
        count += 1
    return count


def _control_plane_contract(goal: str) -> dict[str, Any]:
    normalized = re.sub(r"\s+", " ", goal).strip()
    return {
        "owner": "control_plane",
        "closure": "validator confirms runtime/complexity_estimate.json exists in the workspace",
        "worker_may_edit_control_plane_state": False,
        "task_summary": normalized[:500],
        "out_of_scope": [
            "runtime/project_state.json",
            "runtime/task_queue.json",
            "runtime/task_history.jsonl",
            "runtime/failures.jsonl",
        ],
    }


def _merge_reasons(base: Any, extra: list[str]) -> list[str]:
    merged: list[str] = []
    if isinstance(base, list):
        merged.extend(str(item) for item in base if str(item).strip())
    for item in extra:
        if item not in merged:
            merged.append(item)
    return merged
