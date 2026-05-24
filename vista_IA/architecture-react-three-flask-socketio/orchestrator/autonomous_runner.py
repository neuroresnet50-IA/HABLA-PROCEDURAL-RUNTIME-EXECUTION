"""Hands-free command runner guarded by an explicit allowlist.

This is not a keyboard automation tool. It runs declared console work without
interactive approvals only when each command matches a persisted policy.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from shlex import split as shlex_split
from typing import Any

try:
    from .security_policy import (
        DEFAULT_SECURITY_POLICY_PATH,
        DEFAULT_OPERATOR_APPROVAL_PATH,
        decide_command,
        load_security_policy,
        load_operator_approval,
        record_security_event,
        sha256_file,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from security_policy import (  # type: ignore
        DEFAULT_SECURITY_POLICY_PATH,
        DEFAULT_OPERATOR_APPROVAL_PATH,
        decide_command,
        load_security_policy,
        load_operator_approval,
        record_security_event,
        sha256_file,
    )


DEFAULT_POLICY_PATH = Path("runtime/auto_approval_policy.json")
DEFAULT_PLAN_PATH = Path("runtime/autonomous_commands.json")
DEFAULT_LOG_PATH = Path("runtime/logs/autonomous_runner.jsonl")
DEFAULT_REPORT_PATH = Path("runtime/artifacts/autonomous_runner_latest.json")
DEFAULT_TIMEOUT_SECONDS = 300
MAX_CAPTURE_CHARS = 12000
DANGEROUS_EXECUTABLES = frozenset(
    {
        "bash",
        "chmod",
        "chown",
        "curl",
        "dd",
        "docker",
        "git-reset",
        "kill",
        "mkfs",
        "mv",
        "rm",
        "rsync",
        "scp",
        "sh",
        "ssh",
        "sudo",
        "tee",
        "wget",
    }
)


class AutonomousRunnerError(ValueError):
    """Raised when the autonomous runner receives invalid input."""


def load_policy(path: str | Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as handle:
        policy = json.load(handle)
    return validate_policy(policy)


def load_plan(path: str | Path = DEFAULT_PLAN_PATH) -> list[dict[str, Any]]:
    plan_path = Path(path)
    with plan_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise AutonomousRunnerError("Autonomous command plan must be a list")
    return [validate_plan_item(item, index) for index, item in enumerate(payload)]


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise AutonomousRunnerError("Policy must be an object")
    if policy.get("schema_version") != 1:
        raise AutonomousRunnerError("Policy.schema_version must be 1")
    allowed_prefixes = policy.get("allowed_prefixes")
    if not isinstance(allowed_prefixes, list) or not allowed_prefixes:
        raise AutonomousRunnerError("Policy.allowed_prefixes must be a non-empty list")
    normalized_prefixes = [_normalize_command(prefix) for prefix in allowed_prefixes]

    blocked = policy.get("blocked_executables", [])
    if not isinstance(blocked, list):
        raise AutonomousRunnerError("Policy.blocked_executables must be a list")
    blocked_executables = sorted({*_normalize_executables(blocked), *DANGEROUS_EXECUTABLES})

    return {
        **policy,
        "allowed_prefixes": normalized_prefixes,
        "blocked_executables": blocked_executables,
    }


def validate_plan_item(item: dict[str, Any], index: int = 0) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AutonomousRunnerError(f"Plan item {index} must be an object")
    command_id = item.get("id", f"command-{index + 1:03d}")
    if not isinstance(command_id, str) or not command_id.strip():
        raise AutonomousRunnerError(f"Plan item {index}.id must be a non-empty string")
    command = _normalize_command(item.get("command"))
    timeout_seconds = item.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds < 1:
        raise AutonomousRunnerError(f"Plan item {command_id}.timeout_seconds must be a positive integer")
    cwd = item.get("cwd", ".")
    if not isinstance(cwd, str) or not cwd.strip():
        raise AutonomousRunnerError(f"Plan item {command_id}.cwd must be a non-empty string")
    return {
        "id": command_id,
        "title": str(item.get("title", command_id)),
        "command": command,
        "cwd": cwd,
        "timeout_seconds": timeout_seconds,
    }


def is_command_allowed(command: list[str], policy: dict[str, Any]) -> tuple[bool, str]:
    if not command:
        return False, "Command is empty"

    executable = _executable_name(command[0])
    blocked = set(policy["blocked_executables"])
    if executable in blocked:
        return False, f"Executable is blocked by policy: {executable}"

    for prefix in policy["allowed_prefixes"]:
        if len(command) >= len(prefix) and command[: len(prefix)] == prefix:
            return True, f"Matched allowed prefix: {_format_command(prefix)}"
    return False, "Command did not match any allowed prefix"


def run_autonomous_plan(
    *,
    plan: list[dict[str, Any]],
    policy: dict[str, Any],
    workspace: str | Path,
    log_path: str | Path = DEFAULT_LOG_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    dry_run: bool = True,
    continue_on_failure: bool = False,
    security_policy: dict[str, Any] | None = None,
    operator_approval: dict[str, Any] | None = None,
    approval_password: str | None = None,
    plan_sha256: str | None = None,
) -> dict[str, Any]:
    workspace_path = Path(workspace).resolve()
    if not workspace_path.exists() or not workspace_path.is_dir():
        raise AutonomousRunnerError(f"Workspace does not exist: {workspace_path}")

    started_at = _utc_now()
    events: list[dict[str, Any]] = []

    for item in plan:
        event = _run_plan_item(
            item,
            policy=policy,
            workspace=workspace_path,
            dry_run=dry_run,
            security_policy=security_policy,
            operator_approval=operator_approval,
            approval_password=approval_password,
            plan_sha256=plan_sha256,
        )
        _append_jsonl(Path(log_path), event)
        events.append(event)
        if event["status"] not in {"passed", "dry-run"} and not continue_on_failure:
            break

    report = {
        "schema_version": 1,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "dry_run": dry_run,
        "completed": bool(events) and all(event["status"] in {"passed", "dry-run"} for event in events),
        "total": len(events),
        "passed": sum(1 for event in events if event["status"] == "passed"),
        "failed": sum(1 for event in events if event["status"] == "failed"),
        "blocked": sum(1 for event in events if event["status"] == "blocked"),
        "events": events,
    }
    _atomic_write_json(Path(report_path), report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run preapproved console work without interactive prompts.")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN_PATH))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--log", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--security-policy", default=str(DEFAULT_SECURITY_POLICY_PATH))
    parser.add_argument("--no-security-policy", action="store_true")
    parser.add_argument("--operator-approval", default=str(DEFAULT_OPERATOR_APPROVAL_PATH))
    parser.add_argument("--no-operator-approval", action="store_true")
    parser.add_argument("--approval-password-env", default="SECURITY_APPROVAL_PASSWORD")
    parser.add_argument("--run", action="store_true", help="Execute commands. Without this, only dry-run validation runs.")
    parser.add_argument("--continue-on-failure", action="store_true")
    args = parser.parse_args(argv)

    try:
        policy = load_policy(args.policy)
        plan = load_plan(args.plan)
        security_policy = None
        if not args.no_security_policy and Path(args.security_policy).exists():
            security_policy = load_security_policy(args.security_policy)
        operator_approval = None
        approval_password = None
        plan_digest = sha256_file(args.plan)
        approval_path = Path(args.operator_approval)
        if not args.no_operator_approval and approval_path.exists():
            operator_approval = load_operator_approval(approval_path)
            approval_password = os.environ.get(args.approval_password_env)
            if approval_password is None and args.run:
                approval_password = getpass.getpass("Operator approval password: ")
        report = run_autonomous_plan(
            plan=plan,
            policy=policy,
            workspace=args.workspace,
            log_path=args.log,
            report_path=args.report,
            dry_run=not args.run,
            continue_on_failure=args.continue_on_failure,
            security_policy=security_policy,
            operator_approval=operator_approval,
            approval_password=approval_password,
            plan_sha256=plan_digest,
        )
    except Exception as exc:
        error = {"status": "error", "error_type": type(exc).__name__, "message": str(exc)}
        print(json.dumps(error, ensure_ascii=True, sort_keys=True), file=sys.stderr)
        return 2

    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["completed"] else 1


def _run_plan_item(
    item: dict[str, Any],
    *,
    policy: dict[str, Any],
    workspace: Path,
    dry_run: bool,
    security_policy: dict[str, Any] | None,
    operator_approval: dict[str, Any] | None,
    approval_password: str | None,
    plan_sha256: str | None,
) -> dict[str, Any]:
    started = time.monotonic()
    command = item["command"]
    allowed, reason = is_command_allowed(command, policy)
    cwd_result = _resolve_cwd(workspace, item["cwd"])
    base_event = {
        "recorded_at": _utc_now(),
        "id": item["id"],
        "title": item["title"],
        "command": command,
        "cwd": str(cwd_result[0]) if cwd_result[0] is not None else item["cwd"],
        "timeout_seconds": item["timeout_seconds"],
        "policy_reason": reason,
        "duration_seconds": 0.0,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "security_decision": None,
    }

    if security_policy is not None:
        security_decision = decide_command(
            command,
            policy=security_policy,
            cwd=item["cwd"],
            workspace=workspace,
            operator_approval=operator_approval,
            approval_password=approval_password,
            plan_sha256=plan_sha256,
        )
        record_security_event(security_decision, policy=security_policy)
        base_event["security_decision"] = security_decision
        if security_decision["decision"] != "allow":
            return {
                **base_event,
                "status": "blocked",
                "policy_reason": (
                    f"Security decision {security_decision['decision']}: "
                    f"{security_decision['reason']}"
                ),
            }
        allowed = True
        reason = security_decision["reason"]

    if cwd_result[1]:
        return {**base_event, "status": "blocked", "policy_reason": cwd_result[1]}
    if not allowed:
        return {**base_event, "status": "blocked"}
    if dry_run:
        return {**base_event, "status": "dry-run"}

    process = subprocess.Popen(
        command,
        cwd=str(cwd_result[0]),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=item["timeout_seconds"])
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

    duration = round(time.monotonic() - started, 6)
    status = "passed" if process.returncode == 0 and not timed_out else "failed"
    policy_reason = reason
    if timed_out:
        policy_reason = f"Command timed out after {item['timeout_seconds']} seconds"

    return {
        **base_event,
        "status": status,
        "policy_reason": policy_reason,
        "duration_seconds": duration,
        "returncode": process.returncode,
        "stdout": _tail(stdout),
        "stderr": _tail(stderr),
    }


def _resolve_cwd(workspace: Path, cwd: str) -> tuple[Path | None, str | None]:
    candidate = (workspace / cwd).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError:
        return None, f"cwd escapes workspace: {cwd}"
    if not candidate.exists() or not candidate.is_dir():
        return None, f"cwd does not exist or is not a directory: {cwd}"
    return candidate, None


def _normalize_command(value: Any) -> list[str]:
    if isinstance(value, str):
        value = shlex_split(value)
    if not isinstance(value, list) or not value:
        raise AutonomousRunnerError("Command must be a non-empty string or list")
    command: list[str] = []
    for index, part in enumerate(value):
        if not isinstance(part, str) or not part:
            raise AutonomousRunnerError(f"Command part {index} must be a non-empty string")
        if "\x00" in part:
            raise AutonomousRunnerError("Command parts must not contain NUL bytes")
        command.append(part)
    return command


def _normalize_executables(values: list[Any]) -> set[str]:
    executables: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise AutonomousRunnerError("blocked_executables entries must be non-empty strings")
        executables.add(_executable_name(value))
    return executables


def _executable_name(value: str) -> str:
    name = Path(value).name
    if name == "git" and value.endswith("git-reset"):
        return "git-reset"
    return name


def _format_command(command: list[str]) -> str:
    return " ".join(command)


def _tail(value: str) -> str:
    if len(value) <= MAX_CAPTURE_CHARS:
        return value
    return value[-MAX_CAPTURE_CHARS:]


def _append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
