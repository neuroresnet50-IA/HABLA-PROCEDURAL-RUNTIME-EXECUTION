"""Single-task worker process for Sprint 3.

This worker executes one bounded command for one valid Task. It does not keep
session state and it does not perform Sprint 4 validation.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from orchestrator.contracts import ContractError, validate_task, validate_task_result
    from orchestrator.safe_process_env import safe_child_process_env
    from backend.cyberlace_document_guard import inspect_runtime_document_inputs
except ImportError:  # pragma: no cover - direct path execution fallback.
    sys.path.insert(0, str(REPO_ROOT))
    from orchestrator.contracts import ContractError, validate_task, validate_task_result
    from orchestrator.safe_process_env import safe_child_process_env
    from backend.cyberlace_document_guard import inspect_runtime_document_inputs
    from orchestrator.safe_process_env import safe_child_process_env
    from backend.cyberlace_document_guard import inspect_runtime_document_inputs


Command = str | list[str]
MAX_OUTPUT_CHARS = 24_000
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run_task(
    task: dict[str, Any],
    *,
    workspace: str | Path,
    command: Command | None = None,
    shell: bool = False,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Execute one task command and return task_result plus execution details."""

    started = time.monotonic()
    validated_task = validate_task(task)
    workspace_path = Path(workspace).resolve()
    timeout = timeout_seconds if timeout_seconds is not None else validated_task["timeout_seconds"]

    blockers: list[str] = []
    if timeout < 1:
        blockers.append("timeout_seconds must be greater than 0")
    if not workspace_path.exists() or not workspace_path.is_dir():
        blockers.append(f"Workspace does not exist or is not a directory: {workspace_path}")

    before_snapshot, snapshot_blockers = _snapshot_expected_files(workspace_path, validated_task)
    blockers.extend(snapshot_blockers)

    execution: dict[str, Any] = {
        "task_id": validated_task["id"],
        "worker_pid": os.getpid(),
        "child_pid": None,
        "workspace": str(workspace_path),
        "command": command,
        "shell": shell,
        "timeout_seconds": timeout,
        "timed_out": False,
        "returncode": None,
        "duration_seconds": 0.0,
        "stdout": "",
        "stderr": "",
    }

    if command is None:
        blockers.append("No execution command provided for this task")

    if not blockers and command is not None:
        document_decision = _worker_document_decision(validated_task, workspace_path, command)
        if _decision_blocks(document_decision):
            blocker = "CyberLACE document hard gate blocked worker before child process launch."
            execution.update(
                {
                    "returncode": 126,
                    "duration_seconds": _elapsed(started),
                    "stderr": blocker,
                    "cyberlace_document_decision": document_decision,
                }
            )
            task_result = _task_result(
                validated_task,
                completed=False,
                files_created=[],
                files_modified=[],
                blockers=[blocker],
                next_recommendation="Remove secrets from the workspace or use a secure credential workflow before retrying.",
            )
            return {"task_result": task_result, "execution": execution}

    if blockers:
        task_result = _task_result(
            validated_task,
            completed=False,
            files_created=[],
            files_modified=[],
            blockers=blockers,
            next_recommendation="Provide an isolated command for this task before execution.",
        )
        execution["duration_seconds"] = _elapsed(started)
        return {"task_result": task_result, "execution": execution}

    command_args = _normalize_command(command, shell=shell)
    process = subprocess.Popen(
        command_args,
        cwd=str(workspace_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=shell,
        env=safe_child_process_env(
            os.environ,
            extra={"VISTA_AGENT_PROJECT_DIR": str(workspace_path)},
        ),
    )
    execution["child_pid"] = process.pid

    try:
        stdout, stderr = process.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

    duration = _elapsed(started)
    after_snapshot, after_blockers = _snapshot_expected_files(workspace_path, validated_task)
    files_created, files_modified = _diff_expected_files(before_snapshot, after_snapshot)
    missing_expected_files = _missing_expected_files(after_snapshot)

    execution.update(
        {
            "timed_out": timed_out,
            "returncode": process.returncode,
            "duration_seconds": duration,
            "stdout": _tail_text(stdout),
            "stderr": _tail_text(stderr),
        }
    )

    blockers.extend(after_blockers)
    if missing_expected_files:
        blockers.append(
            "Missing expected evidence files: " + ", ".join(sorted(missing_expected_files))
        )

    completed = bool(process.returncode == 0 and not timed_out and not blockers)
    if timed_out:
        blockers.append(f"Task timed out after {timeout} seconds")
        next_recommendation = "Retry with a smaller task or let recovery split the scope."
    elif process.returncode != 0:
        blockers.append(f"Process exited with return code {process.returncode}")
        next_recommendation = "Inspect stdout/stderr and retry this isolated task after fixing the cause."
    elif missing_expected_files:
        next_recommendation = "Create the expected evidence files before considering this task complete."
    else:
        next_recommendation = "Run Sprint 4 validation before marking project progress as verified."

    task_result = _task_result(
        validated_task,
        completed=completed,
        files_created=files_created,
        files_modified=files_modified,
        blockers=blockers,
        next_recommendation=next_recommendation,
    )
    return {"task_result": task_result, "execution": execution}


def _command_to_text(command: Command) -> str:
    if isinstance(command, list):
        return " ".join(command)
    return str(command or "")


def _command_instruction_text(command: Command) -> str:
    if isinstance(command, list) and command:
        return str(command[-1] or "")
    return str(command or "")


def _worker_document_decision(task: dict[str, Any], workspace_path: Path, command: Command) -> dict[str, Any]:
    task_requirement = str(task.get("goal") or task.get("title") or task.get("id") or "")
    instruction_text = _command_instruction_text(command)
    return inspect_runtime_document_inputs(
        requirement=task_requirement,
        project_dir=workspace_path,
        repo_root=REPO_ROOT,
        task=task,
        directive={"rendered_instruction": instruction_text},
        session_id=os.environ.get("VISTA_AGENT_SESSION_ID"),
        project_slug=os.environ.get("VISTA_AGENT_PROJECT_SLUG") or workspace_path.name,
        scan_workspace=True,
    )


def _decision_blocks(decision: dict[str, Any] | None) -> bool:
    if not isinstance(decision, dict):
        return True
    action = str(decision.get("runtimeAction") or decision.get("action") or "").upper()
    return bool(decision.get("blocked") is True or decision.get("blocksRuntime") is True or action in {"BLOCK", "QUARANTINE", "HUMAN_REVIEW"})


def load_task(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_task(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute one orchestration task in isolation.")
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--command-json")
    parser.add_argument("--shell", action="store_true")
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args(argv)

    try:
        task = load_task(args.task_file)
        command = _decode_command_json(args.command_json)
        result = run_task(
            task,
            workspace=args.workspace,
            command=command,
            shell=args.shell,
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except Exception as exc:  # The executor treats this as worker infrastructure failure.
        error = {"worker_error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(error, ensure_ascii=True, sort_keys=True), file=sys.stderr)
        return 2


def _decode_command_json(value: str | None) -> Command | None:
    if value is None:
        return None
    command = json.loads(value)
    if isinstance(command, str):
        return command
    if isinstance(command, list) and all(isinstance(part, str) for part in command):
        return command
    raise ContractError("command-json must decode to a string or a list of strings")


def _normalize_command(command: Command, *, shell: bool) -> Command:
    if shell:
        return command if isinstance(command, str) else " ".join(shlex.quote(part) for part in command)
    return shlex.split(command) if isinstance(command, str) else command


def _snapshot_expected_files(
    workspace: Path,
    task: dict[str, Any],
) -> tuple[dict[str, tuple[bool, int | None, int | None]], list[str]]:
    snapshot: dict[str, tuple[bool, int | None, int | None]] = {}
    blockers: list[str] = []
    for relative_path in task["expected_files"]:
        try:
            path = _resolve_under_workspace(workspace, relative_path)
        except ContractError as exc:
            blockers.append(str(exc))
            continue
        if not path.exists():
            snapshot[relative_path] = (False, None, None)
            continue
        if not path.is_file():
            blockers.append(f"Expected evidence path is not a file: {relative_path}")
            snapshot[relative_path] = (True, None, None)
            continue
        stat = path.stat()
        snapshot[relative_path] = (True, stat.st_mtime_ns, stat.st_size)
    return snapshot, blockers


def _diff_expected_files(
    before: dict[str, tuple[bool, int | None, int | None]],
    after: dict[str, tuple[bool, int | None, int | None]],
) -> tuple[list[str], list[str]]:
    files_created: list[str] = []
    files_modified: list[str] = []
    for path, after_state in after.items():
        before_state = before.get(path, (False, None, None))
        if not before_state[0] and after_state[0]:
            files_created.append(path)
        elif before_state[0] and after_state[0] and before_state != after_state:
            files_modified.append(path)
    return files_created, files_modified


def _missing_expected_files(
    after: dict[str, tuple[bool, int | None, int | None]]
) -> list[str]:
    return [path for path, after_state in after.items() if not after_state[0]]


def _resolve_under_workspace(workspace: Path, relative_path: str) -> Path:
    path = (workspace / relative_path).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise ContractError(f"Expected file escapes workspace: {relative_path}") from exc
    return path


def _task_result(
    task: dict[str, Any],
    *,
    completed: bool,
    files_created: list[str],
    files_modified: list[str],
    blockers: list[str],
    next_recommendation: str,
) -> dict[str, Any]:
    return validate_task_result(
        {
            "task_id": task["id"],
            "completed": completed,
            "files_created": files_created,
            "files_modified": files_modified,
            "validation_ran": [],
            "validation_passed": False,
            "blockers": blockers,
            "next_recommendation": next_recommendation,
        }
    )


def _tail_text(value: str | None, *, limit: int = MAX_OUTPUT_CHARS) -> str:
    text = value or ""
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"[output truncated; omitted {omitted} chars]\n{text[-limit:]}"


def _elapsed(started: float) -> float:
    return round(time.monotonic() - started, 6)


if __name__ == "__main__":
    raise SystemExit(main())
