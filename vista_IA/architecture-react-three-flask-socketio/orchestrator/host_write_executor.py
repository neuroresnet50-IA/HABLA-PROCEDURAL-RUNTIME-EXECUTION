"""Host-side materialization for simple file-write tasks.

This executor is intentionally narrow: it writes only declared expected files
for simple tasks, then leaves final closure to the validator.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .contracts import ContractError, validate_task_result
except ImportError:  # pragma: no cover - supports direct script execution.
    from contracts import ContractError, validate_task_result  # type: ignore


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

SIMPLE_MAX_EXPECTED_FILES = 3
HOST_WRITE_STRATEGY = "host_write"
SIMPLE_KIND = "simple_file_write"

SIMPLE_INTENT_MARKERS = (
    "crear archivo",
    "crea el archivo",
    "create the file",
    "write ",
    "write file",
    "write the file",
    "escribe ",
    "complete contents must be exactly",
    "contenido exactamente",
    "debe contener exactamente",
    "archivo esperado",
)

DOCUMENT_PLAN_MARKERS = (
    "escribe la solucion o plan en docs/",
    "escribe la solución o plan en docs/",
    "write the solution or plan in docs/",
    "write the solution or plan to docs/",
)

COMPLEX_TASK_MARKERS = (
    "refactor",
    "debug",
    "debugging",
    "install",
    "dependency",
    "dependencies",
    "dependencias",
    "run app",
    "start server",
    "backend",
    "frontend",
    "flask",
    "react",
    "api",
    "database",
    "base de datos",
    "many files",
    "muchos archivos",
    "multi-file",
    "multiarchivo",
    "test suite",
    "pytest",
    "unittest",
)

PROTECTED_RUNTIME_EXACT = frozenset(
    {
        "runtime/project_state.json",
        "runtime/task_queue.json",
        "runtime/task_history.jsonl",
        "runtime/failures.jsonl",
        "runtime/tool_invocation_policy.jsonl",
    }
)

PROTECTED_RUNTIME_PREFIXES = (
    "runtime/checkpoints/",
    "runtime/directives/",
    "runtime/logs/",
)

EXACT_CONTENT_PATTERNS = (
    re.compile(r"its complete contents must be exactly\s+(?P<content>.+)", re.IGNORECASE | re.DOTALL),
    re.compile(r"el archivo debe contener exactamente\s+(?P<content>.+)", re.IGNORECASE | re.DOTALL),
)


def should_use_host_write_executor(task: dict[str, Any]) -> bool:
    """Return True only for narrow, simple file materialization tasks."""

    if not isinstance(task, dict):
        return False
    expected_files = _expected_files(task)
    if not expected_files or len(expected_files) > SIMPLE_MAX_EXPECTED_FILES:
        return False
    if any(_raw_path_is_unsafe(path) or is_protected_runtime_path(Path(path)) for path in expected_files):
        return False
    if _is_docs_plan_materialization(task, expected_files):
        return True
    if _looks_complex(task):
        return False
    return _has_host_write_intent(task)


def execute_host_write_task(task: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """Materialize simple expected files in the host workspace.

    The returned `completed` flag means materialization succeeded. The runtime
    must still call `orchestrator.validator.validate_task_execution` before
    closing progress.
    """

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
        "execution_strategy": HOST_WRITE_STRATEGY,
        "selector_reason": "simple_file_write host materialization",
        "materialized": False,
        "evidence": [],
    }

    workspace_path = Path(workspace).resolve()
    blockers = validate_host_write_task(task, workspace_path)
    if blockers:
        result["blockers"] = blockers
        result["next_recommendation"] = "Route complex or unsafe tasks to codex_worker, or fix expected_files."
        return result

    exact_content = extract_exact_content(str(task.get("goal") or ""))
    expected_files = _expected_files(task)

    for expected_file in expected_files:
        try:
            target = resolve_safe_expected_file(workspace_path, expected_file)
            existed = target.exists()
            content = exact_content if exact_content is not None else build_minimal_markdown(task, expected_file)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
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
            result["blockers"].append(f"HostWriteExecutor failed for {expected_file}: {type(exc).__name__}: {exc}")

    result["materialized"] = not result["blockers"] and bool(result["files_created"] or result["files_modified"])
    result["completed"] = False
    result["next_recommendation"] = (
        "Run validator before marking this task completed."
        if result["materialized"]
        else "Fix host_write blockers and rerun the isolated task."
    )
    return result


def validate_host_write_task(task: dict[str, Any], workspace: Path) -> list[str]:
    blockers: list[str] = []
    if not isinstance(task, dict):
        return ["Task must be an object."]

    expected_files = _expected_files(task)
    if not expected_files:
        blockers.append("HostWriteExecutor requires non-empty expected_files.")
    if len(expected_files) > SIMPLE_MAX_EXPECTED_FILES:
        blockers.append("HostWriteExecutor refuses tasks that touch many expected files.")
    docs_plan = _is_docs_plan_materialization(task, expected_files)
    if not _has_host_write_intent(task) and not docs_plan:
        blockers.append("Task is not a simple_file_write materialization task.")
    if _looks_complex(task) and not docs_plan:
        blockers.append("HostWriteExecutor refuses complex tasks; use codex_worker.")

    workspace_path = Path(workspace).resolve()
    if not workspace_path.exists() or not workspace_path.is_dir():
        blockers.append(f"Workspace does not exist or is not a directory: {workspace_path}")

    for expected_file in expected_files:
        try:
            resolve_safe_expected_file(workspace_path, expected_file)
        except ContractError as exc:
            blockers.append(str(exc))

    return blockers


def extract_exact_content(goal: str) -> str | None:
    text = str(goal or "").strip()
    if not text:
        return None
    for pattern in EXACT_CONTENT_PATTERNS:
        match = pattern.search(text)
        if match:
            return _clean_exact_content(match.group("content"))
    return None


def build_minimal_markdown(task: dict[str, Any], expected_file: str) -> str:
    title = str(task.get("title") or task.get("id") or "Host write artifact").strip()
    goal = str(task.get("goal") or "").strip()
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        f"# {title}\n\n"
        f"- task_id: {task.get('id')}\n"
        f"- goal: {goal}\n"
        f"- expected_file: {expected_file}\n"
        f"- materialized_at: {created_at}\n"
        "- note: Materialized by orchestrator.host_write_executor; validator remains final authority.\n"
    )


def resolve_safe_expected_file(workspace: Path, expected_file: str) -> Path:
    if not isinstance(expected_file, str) or not expected_file.strip():
        raise ContractError("Expected file must be a non-empty relative path.")
    if _raw_path_is_unsafe(expected_file):
        raise ContractError(f"Unsafe expected file path for host_write: {expected_file}")

    relative = Path(expected_file)
    if is_protected_runtime_path(relative):
        raise ContractError(f"HostWriteExecutor refuses protected runtime path: {expected_file}")

    workspace_real = Path(workspace).resolve()
    candidate = workspace_real / relative
    parent_real = candidate.parent.resolve(strict=False)
    _assert_inside_workspace(workspace_real, parent_real, expected_file)
    candidate_real = candidate.resolve(strict=False)
    _assert_inside_workspace(workspace_real, candidate_real, expected_file)
    if candidate.exists() and candidate.is_symlink():
        _assert_inside_workspace(workspace_real, candidate.resolve(strict=True), expected_file)
    return candidate_real


def is_protected_runtime_path(path: Path) -> bool:
    normalized = path.as_posix().lstrip("./")
    if normalized in PROTECTED_RUNTIME_EXACT:
        return True
    return normalized.startswith(PROTECTED_RUNTIME_PREFIXES)


def task_result_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Return only the canonical TaskResult fields from a host_write result."""

    return validate_task_result({key: result[key] for key in TASK_RESULT_KEYS})


def _expected_files(task: dict[str, Any]) -> list[str]:
    files = task.get("expected_files")
    if not isinstance(files, list):
        return []
    return [str(item) for item in files if str(item).strip()]


def _has_host_write_intent(task: dict[str, Any]) -> bool:
    kind = str(task.get("kind") or "").strip().lower()
    strategy = str(task.get("execution_strategy") or "").strip().lower()
    if kind == SIMPLE_KIND or strategy == HOST_WRITE_STRATEGY:
        return True
    text = f"{task.get('title') or ''} {task.get('goal') or ''}".lower()
    return any(marker in text for marker in SIMPLE_INTENT_MARKERS)


def _looks_complex(task: dict[str, Any]) -> bool:
    text = f"{task.get('title') or ''} {task.get('goal') or ''}".lower()
    return any(marker in text for marker in COMPLEX_TASK_MARKERS)


def _is_docs_plan_materialization(task: dict[str, Any], expected_files: list[str]) -> bool:
    if not expected_files:
        return False
    if not all(str(path).startswith("docs/") and str(path).endswith(".md") for path in expected_files):
        return False
    text = f"{task.get('title') or ''} {task.get('goal') or ''}".lower()
    return any(marker in text for marker in DOCUMENT_PLAN_MARKERS)


def _raw_path_is_unsafe(value: str) -> bool:
    raw = str(value or "")
    if "\x00" in raw:
        return True
    if "\\" in raw:
        return True
    path = Path(raw)
    if path.is_absolute():
        return True
    return any(part == ".." for part in path.parts)


def _assert_inside_workspace(workspace: Path, path: Path, expected_file: str) -> None:
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise ContractError(f"Expected file escapes workspace: {expected_file}") from exc


def _clean_exact_content(value: str) -> str:
    content = str(value or "").strip()
    if "\n" in content:
        content = content.splitlines()[0].strip()
    if (
        len(content) >= 2
        and content[0] == content[-1]
        and content[0] in {"'", '"', "`"}
    ):
        return content[1:-1]
    if content.endswith("."):
        content = content[:-1]
    return content
