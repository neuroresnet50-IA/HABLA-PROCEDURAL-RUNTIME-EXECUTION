"""Automatic internal-tool invocation policy for control-plane tasks.

This module coordinates Observer/Scanner/Integrity/Findings/Sniper calls around
task execution. It is deliberately small and injectable so tests can exercise
the policy without requiring a live backend server.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol

try:
    from .agent_tools import run_command
except ImportError:  # pragma: no cover - supports direct script execution.
    from agent_tools import run_command  # type: ignore


DEFAULT_TOOL_TIMEOUT_SECONDS = 1
TOOL_LOG_NAME = "tool_invocation_policy.jsonl"


class ToolRunner(Protocol):
    def invoke(
        self,
        tool: str,
        *,
        project: str = "",
        dry_run: bool = False,
        confirm: str = "",
    ) -> dict[str, Any]:
        """Invoke one internal tool and return a JSON-compatible result."""


@dataclass
class AgentToolsRunner:
    """Default runner backed by orchestrator.agent_tools."""

    base_url: str = "http://127.0.0.1:5001"
    timeout_seconds: int = DEFAULT_TOOL_TIMEOUT_SECONDS

    def invoke(
        self,
        tool: str,
        *,
        project: str = "",
        dry_run: bool = False,
        confirm: str = "",
    ) -> dict[str, Any]:
        timeout_seconds = self.timeout_seconds
        if tool == "observer-status":
            configured = str(os.environ.get("HABLA_OBSERVER_STATUS_TIMEOUT_SECONDS") or "1").strip()
            try:
                timeout_seconds = max(1, min(timeout_seconds, int(float(configured))))
            except ValueError:
                timeout_seconds = min(timeout_seconds, 1)
        args = SimpleNamespace(
            command=tool,
            project=project,
            dry_run=dry_run,
            confirm=confirm,
            base_url=self.base_url,
            timeout_seconds=timeout_seconds,
            full=False,
        )
        status_code, payload = run_command(args)
        return {"statusCode": status_code, **payload}


class ToolInvocationPolicy:
    """Run internal tools at bounded task lifecycle phases."""

    def __init__(
        self,
        *,
        runtime_dir: str | Path,
        workspace: str | Path,
        project_slug: str | None = None,
        runner: ToolRunner | None = None,
        strict_closure: bool = False,
    ) -> None:
        self.runtime_dir = Path(runtime_dir)
        self.workspace = Path(workspace).resolve()
        self.project_slug = project_slug or self.workspace.name
        self.runner = runner or AgentToolsRunner(
            timeout_seconds=int(os.environ.get("HABLA_TOOL_POLICY_TIMEOUT_SECONDS", DEFAULT_TOOL_TIMEOUT_SECONDS))
        )
        self.strict_closure = strict_closure

    def run_preflight(self, task: dict[str, Any]) -> dict[str, Any]:
        invocations = [self._invoke("observer-status", phase="preflight", task=task, required=False)]
        if self._has_integrity_baseline():
            invocations.append(self._invoke("integrity", phase="preflight", task=task, required=False))
            invocations.append(self._invoke("findings", phase="preflight", task=task, required=False))
        return self._phase_report("preflight", task, invocations, closure_allowed=True)

    def run_postflight(self, task: dict[str, Any], task_result: dict[str, Any]) -> dict[str, Any]:
        invocations = [
            self._invoke("integrity", phase="postflight", task=task, required=False),
            self._invoke("findings", phase="postflight", task=task, required=False),
        ]
        return self._phase_report(
            "postflight",
            task,
            invocations,
            closure_allowed=True,
            task_result=task_result,
        )

    def run_task_completion_gate(self, task: dict[str, Any], task_result: dict[str, Any]) -> dict[str, Any]:
        invocations = [
            self._invoke("scanner", phase="task_completion_gate", task=task, required=self.strict_closure),
            self._invoke("findings", phase="task_completion_gate", task=task, required=False),
        ]
        closure_allowed = self._required_invocations_ok(invocations)
        return self._phase_report(
            "task_completion_gate",
            task,
            invocations,
            closure_allowed=closure_allowed,
            task_result=task_result,
        )

    def run_recovery_preview(self, task: dict[str, Any], task_result: dict[str, Any]) -> dict[str, Any]:
        invocations = [
            self._invoke("findings", phase="recovery_preview", task=task, required=False),
            self._invoke("sniper", phase="recovery_preview", task=task, dry_run=True, required=False),
        ]
        return self._phase_report(
            "recovery_preview",
            task,
            invocations,
            closure_allowed=True,
            task_result=task_result,
        )

    def run_project_completion_gate(self, task: dict[str, Any] | None = None) -> dict[str, Any]:
        phase_task = task or {"id": "PROJECT-COMPLETION", "mode": "build"}
        invocations = [
            self._invoke("scanner", phase="project_completion_gate", task=phase_task, required=self.strict_closure),
            self._invoke("integrity", phase="project_completion_gate", task=phase_task, required=False),
            self._invoke("findings", phase="project_completion_gate", task=phase_task, required=False),
        ]
        closure_allowed = self._required_invocations_ok(invocations)
        return self._phase_report(
            "project_completion_gate",
            phase_task,
            invocations,
            closure_allowed=closure_allowed,
        )

    def _invoke(
        self,
        tool: str,
        *,
        phase: str,
        task: dict[str, Any],
        dry_run: bool = False,
        required: bool = False,
    ) -> dict[str, Any]:
        started_at = _utc_now()
        task_id = str(task.get("id") or "unknown-task")
        try:
            payload = self.runner.invoke(tool, project=self.project_slug, dry_run=dry_run)
        except Exception as exc:  # Tools must leave evidence instead of crashing task execution.
            message = str(exc)
            timed_out = "timed out" in message.lower() or type(exc).__name__ in {"TimeoutError", "socket.timeout"}
            payload = {
                "statusCode": 0,
                "ok": False,
                "error": "internal_tool_timeout" if timed_out else type(exc).__name__,
                "message": (
                    f"Optional internal tool {tool} timed out; continuing runtime startup."
                    if timed_out
                    else message
                ),
                "timedOut": timed_out,
            }
        invocation = {
            "schema_version": 1,
            "timestamp": started_at,
            "phase": phase,
            "taskId": task_id,
            "projectSlug": self.project_slug,
            "tool": tool,
            "dryRun": dry_run,
            "required": required,
            "ok": _payload_ok(payload),
            "statusCode": payload.get("statusCode"),
            "summary": _compact_tool_payload(payload),
            "artifactPath": payload.get("artifactPath") or payload.get("reportPath"),
            "error": payload.get("error"),
            "timedOut": bool(payload.get("timedOut")),
        }
        self._persist_invocation(invocation)
        return invocation

    def _phase_report(
        self,
        phase: str,
        task: dict[str, Any],
        invocations: list[dict[str, Any]],
        *,
        closure_allowed: bool,
        task_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        active_findings = max((_active_findings_count(item) for item in invocations), default=0)
        report = {
            "schema_version": 1,
            "timestamp": _utc_now(),
            "phase": phase,
            "taskId": str(task.get("id") or "unknown-task"),
            "projectSlug": self.project_slug,
            "closureAllowed": bool(closure_allowed),
            "activeFindings": active_findings,
            "warnings": _warnings(invocations),
            "blockers": _blockers(invocations),
            "invocations": invocations,
        }
        if task_result is not None:
            report["taskResult"] = {
                "completed": bool(task_result.get("completed")),
                "validation_passed": bool(task_result.get("validation_passed")),
                "blocker_count": len(task_result.get("blockers") or []),
            }
        self._persist_phase_report(report)
        return report

    def _has_integrity_baseline(self) -> bool:
        candidates = [
            self.workspace / "runtime" / "artifacts" / "agent_file_manifest.json",
            self.workspace / "runtime" / "artifacts" / "file_integrity_report.json",
            self.runtime_dir / "artifacts" / "agent_file_manifest.json",
            self.runtime_dir / "artifacts" / "file_integrity_report.json",
        ]
        return any(path.exists() for path in candidates)

    def _required_invocations_ok(self, invocations: list[dict[str, Any]]) -> bool:
        return all(item.get("ok") is True for item in invocations if item.get("required"))

    def _persist_invocation(self, invocation: dict[str, Any]) -> None:
        log_path = self.runtime_dir / TOOL_LOG_NAME
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(invocation, ensure_ascii=True, sort_keys=True) + "\n")

    def _persist_phase_report(self, report: dict[str, Any]) -> None:
        artifacts_dir = self.runtime_dir / "artifacts" / "tool_invocations"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{_safe_segment(report['taskId'])}-{_safe_segment(report['phase'])}-{_timestamp_token()}.json"
        path = artifacts_dir / filename
        path.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        latest_path = self.runtime_dir / "artifacts" / "tool_invocation_policy_latest.json"
        latest_path.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["artifactPath"] = str(path)


def _payload_ok(payload: dict[str, Any]) -> bool:
    status_code = payload.get("statusCode")
    return bool(payload.get("ok", True) is not False and isinstance(status_code, int) and 200 <= status_code < 300)


def _compact_tool_payload(payload: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {
        "ok": payload.get("ok"),
        "statusCode": payload.get("statusCode"),
    }
    for key in ("error", "message", "projectId", "reportPath", "artifactPath", "busy"):
        if key in payload:
            compact[key] = payload.get(key)
    report = payload.get("report")
    if isinstance(report, dict):
        summary = report.get("summary")
        if isinstance(summary, dict):
            compact["summary"] = summary
    observer = payload.get("observer")
    if isinstance(observer, dict):
        compact["observer"] = {
            "enabled": observer.get("enabled"),
            "state": observer.get("state"),
            "incident": observer.get("incident"),
            "activeProjectSlug": observer.get("activeProjectSlug"),
        }
    event = payload.get("observerEvent")
    if isinstance(event, dict):
        compact["observerEvent"] = {
            "state": event.get("state"),
            "action": event.get("action"),
            "reason": event.get("reason"),
            "incidentId": event.get("incidentId"),
            "incidentStatus": event.get("incidentStatus"),
        }
    return compact


def _active_findings_count(invocation: dict[str, Any]) -> int:
    summary = invocation.get("summary") if isinstance(invocation, dict) else None
    if not isinstance(summary, dict):
        return 0
    report_summary = summary.get("summary")
    if not isinstance(report_summary, dict):
        return 0
    value = report_summary.get("activeFindings")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _warnings(invocations: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for item in invocations:
        if item.get("ok") is not True:
            if item.get("timedOut"):
                warnings.append(f"{item.get('phase')}:{item.get('tool')} timed out; continuing")
            else:
                warnings.append(f"{item.get('phase')}:{item.get('tool')} did not return ok=true")
    active = max((_active_findings_count(item) for item in invocations), default=0)
    if active:
        warnings.append(f"Observer findings active: {active}")
    return warnings


def _blockers(invocations: list[dict[str, Any]]) -> list[str]:
    return [
        f"Required tool failed: {item.get('tool')} statusCode={item.get('statusCode')}"
        for item in invocations
        if item.get("required") and item.get("ok") is not True
    ]


def _safe_segment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "unknown")).strip("-") or "unknown"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
