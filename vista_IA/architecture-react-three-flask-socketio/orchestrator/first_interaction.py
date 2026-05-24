"""Bootstrap for the first Codex interaction in a workspace.

The bootstrap reads repository policy, security policy, the persisted command
plan, asks the operator password once, and then starts autonomous execution.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from .autonomous_runner import (
        DEFAULT_LOG_PATH,
        DEFAULT_PLAN_PATH,
        DEFAULT_POLICY_PATH,
        DEFAULT_REPORT_PATH,
        load_plan,
        load_policy,
        run_autonomous_plan,
    )
    from .security_policy import (
        DEFAULT_OPERATOR_APPROVAL_PATH,
        DEFAULT_SECURITY_POLICY_PATH,
        create_operator_approval,
        decide_command,
        load_operator_approval,
        load_security_policy,
        sha256_file,
    )
except ImportError:  # pragma: no cover - direct script execution fallback.
    from autonomous_runner import (  # type: ignore
        DEFAULT_LOG_PATH,
        DEFAULT_PLAN_PATH,
        DEFAULT_POLICY_PATH,
        DEFAULT_REPORT_PATH,
        load_plan,
        load_policy,
        run_autonomous_plan,
    )
    from security_policy import (  # type: ignore
        DEFAULT_OPERATOR_APPROVAL_PATH,
        DEFAULT_SECURITY_POLICY_PATH,
        create_operator_approval,
        decide_command,
        load_operator_approval,
        load_security_policy,
        sha256_file,
    )


DEFAULT_BOOTSTRAP_REPORT_PATH = Path("runtime/artifacts/first_interaction_latest.json")


class FirstInteractionError(RuntimeError):
    """Raised when first-interaction bootstrap cannot proceed."""


def run_first_interaction(
    *,
    workspace: str | Path = ".",
    plan_path: str | Path = DEFAULT_PLAN_PATH,
    auto_policy_path: str | Path = DEFAULT_POLICY_PATH,
    security_policy_path: str | Path = DEFAULT_SECURITY_POLICY_PATH,
    approval_file: str | Path = DEFAULT_OPERATOR_APPROVAL_PATH,
    runner_log_path: str | Path = DEFAULT_LOG_PATH,
    runner_report_path: str | Path = DEFAULT_REPORT_PATH,
    bootstrap_report_path: str | Path = DEFAULT_BOOTSTRAP_REPORT_PATH,
    password: str,
    expires_hours: int = 10,
    categories: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    workspace_path = Path(workspace).resolve()
    if not workspace_path.exists() or not workspace_path.is_dir():
        raise FirstInteractionError(f"Workspace does not exist: {workspace_path}")
    if not password:
        raise FirstInteractionError("Operator password must not be empty")

    _require_workspace_file(workspace_path, "AGENTS.md")
    _require_workspace_file(workspace_path, "PLANS.md")

    plan_file = _resolve_under_workspace(workspace_path, plan_path)
    auto_policy_file = _resolve_under_workspace(workspace_path, auto_policy_path)
    security_policy_file = _resolve_under_workspace(workspace_path, security_policy_path)
    approval_path = _resolve_under_workspace(workspace_path, approval_file)
    runner_log = _resolve_under_workspace(workspace_path, runner_log_path)
    runner_report = _resolve_under_workspace(workspace_path, runner_report_path)
    bootstrap_report = _resolve_under_workspace(workspace_path, bootstrap_report_path)

    plan = load_plan(plan_file)
    auto_policy = load_policy(auto_policy_file)
    security_policy = load_security_policy(security_policy_file)
    plan_digest = sha256_file(plan_file)

    preflight = _preflight_plan(
        plan,
        security_policy=security_policy,
        workspace=workspace_path,
        plan_sha256=plan_digest,
    )
    denied = [decision for decision in preflight if decision["decision"] == "deny"]
    if denied:
        report = {
            "schema_version": 1,
            "status": "blocked",
            "reason": "Plan contains denied commands",
            "plan_path": str(plan_file),
            "plan_sha256": plan_digest,
            "denied": denied,
            "preflight_decisions": preflight,
        }
        _atomic_write_json(bootstrap_report, report)
        return report

    categories_to_approve = categories or sorted(security_policy["risk_categories"])
    approval_action = "reused"
    approval = _load_existing_approval(approval_path)
    if not _approval_reusable(
        approval,
        plan_sha256=plan_digest,
        workspace=workspace_path,
        plan=plan,
        security_policy=security_policy,
        password=password,
    ):
        approval = create_operator_approval(
            plan_path=plan_file,
            workspace=workspace_path,
            categories=categories_to_approve,
            password=password,
            expires_hours=expires_hours,
            approval_file=approval_path,
        )
        approval_action = "created"

    runner_report_payload = run_autonomous_plan(
        plan=plan,
        policy=auto_policy,
        workspace=workspace_path,
        log_path=runner_log,
        report_path=runner_report,
        dry_run=dry_run,
        security_policy=security_policy,
        operator_approval=approval,
        approval_password=password,
        plan_sha256=plan_digest,
    )
    report = {
        "schema_version": 1,
        "status": "completed" if runner_report_payload["completed"] else "blocked",
        "approval_action": approval_action,
        "approval_file": str(approval_path),
        "plan_path": str(plan_file),
        "plan_sha256": plan_digest,
        "preflight_decisions": preflight,
        "runner_report": runner_report_payload,
    }
    _atomic_write_json(bootstrap_report, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the workspace autonomous loop from first interaction.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN_PATH))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--security-policy", default=str(DEFAULT_SECURITY_POLICY_PATH))
    parser.add_argument("--approval-file", default=str(DEFAULT_OPERATOR_APPROVAL_PATH))
    parser.add_argument("--log", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--bootstrap-report", default=str(DEFAULT_BOOTSTRAP_REPORT_PATH))
    parser.add_argument("--expires-hours", type=int, default=10)
    parser.add_argument("--categories", nargs="*")
    parser.add_argument("--password-env", default="SECURITY_APPROVAL_PASSWORD")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        password = os.environ.get(args.password_env)
        if password is None:
            password = getpass.getpass("Operator password: ")
        report = run_first_interaction(
            workspace=args.workspace,
            plan_path=args.plan,
            auto_policy_path=args.policy,
            security_policy_path=args.security_policy,
            approval_file=args.approval_file,
            runner_log_path=args.log,
            runner_report_path=args.report,
            bootstrap_report_path=args.bootstrap_report,
            password=password,
            expires_hours=args.expires_hours,
            categories=args.categories,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(
            json.dumps(
                {"status": "error", "error_type": type(exc).__name__, "message": str(exc)},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["status"] == "completed" else 1


def _preflight_plan(
    plan: list[dict[str, Any]],
    *,
    security_policy: dict[str, Any],
    workspace: Path,
    plan_sha256: str,
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for item in plan:
        decisions.append(
            decide_command(
                item["command"],
                policy=security_policy,
                cwd=item["cwd"],
                workspace=workspace,
                plan_sha256=plan_sha256,
            )
        )
    return decisions


def _approval_reusable(
    approval: dict[str, Any] | None,
    *,
    plan_sha256: str,
    workspace: Path,
    plan: list[dict[str, Any]],
    security_policy: dict[str, Any],
    password: str,
) -> bool:
    if approval is None:
        return False
    for item in plan:
        decision = decide_command(
            item["command"],
            policy=security_policy,
            cwd=item["cwd"],
            workspace=workspace,
            operator_approval=approval,
            approval_password=password,
            plan_sha256=plan_sha256,
        )
        if decision["decision"] not in {"allow", "deny"}:
            return False
        if decision["decision"] == "deny":
            return False
    return True


def _load_existing_approval(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return load_operator_approval(path)
    except Exception:
        return None


def _require_workspace_file(workspace: Path, relative_path: str) -> None:
    path = workspace / relative_path
    if not path.exists() or not path.is_file():
        raise FirstInteractionError(f"Required workspace file is missing: {relative_path}")


def _resolve_under_workspace(workspace: Path, path: str | Path) -> Path:
    candidate = (workspace / path).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise FirstInteractionError(f"Path escapes workspace: {path}") from exc
    return candidate


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, path)


if __name__ == "__main__":
    raise SystemExit(main())
