"""CLI bridge for agents to use HABLA internal tools.

This module intentionally uses only the Python standard library so a Codex
worker can call it without installing dependencies. It talks to the local
backend API, prints JSON to stdout, and appends an invocation audit line under
runtime/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:5001"
AUDIT_LOG = Path("runtime/agent_tool_invocations.jsonl")
FROZEN_SNIPER_CONFIRMATION = "FROZEN_SNIPER"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_audit(entry: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n")


def request_json(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout_seconds: int = 30,
) -> tuple[int, dict[str, Any]]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            return int(response.status), json.loads(raw) if raw else {}
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"ok": False, "error": "non_json_error", "message": raw}
        return int(error.code), payload
    except TimeoutError as error:
        return 0, {"ok": False, "error": "timeout", "message": str(error), "timedOut": True}
    except URLError as error:
        return 0, {"ok": False, "error": "connection_failed", "message": str(error.reason)}


def project_path(project: str, suffix: str) -> str:
    return f"/api/projects/{quote(project, safe='')}{suffix}"


def truncate_text(value: Any, limit: int = 220) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def compact_event(event: Any) -> dict[str, Any] | None:
    if not isinstance(event, dict):
        return None
    return {
        "state": event.get("state"),
        "action": event.get("action"),
        "reason": truncate_text(event.get("reason")),
        "message": truncate_text(event.get("message")),
        "projectSlug": event.get("projectSlug"),
        "incidentId": event.get("incidentId"),
        "incidentStatus": event.get("incidentStatus"),
        "focusPath": event.get("focusPath"),
        "snapshotSummary": event.get("snapshotSummary"),
    }


def compact_finding(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": finding.get("id"),
        "status": finding.get("status"),
        "severity": finding.get("severity"),
        "source": finding.get("source"),
        "state": finding.get("state"),
        "relativePath": finding.get("relativePath") or finding.get("focusPath"),
        "message": truncate_text(finding.get("message")),
        "reason": truncate_text(finding.get("reason")),
        "observationScore": finding.get("observationScore"),
        "firstSeenAt": finding.get("firstSeenAt"),
        "lastSeenAt": finding.get("lastSeenAt"),
    }


def compact_report(report: Any, sample_limit: int = 5) -> dict[str, Any] | None:
    if not isinstance(report, dict):
        return None
    compact: dict[str, Any] = {}
    if isinstance(report.get("summary"), dict):
        compact["summary"] = report["summary"]
    for key in ("status", "validation", "totals", "stats", "projectId", "generatedAt"):
        value = report.get(key)
        if key in report and not isinstance(value, (list, dict)):
            compact[key] = value
    findings = report.get("findings")
    if isinstance(findings, list):
        active = [item for item in findings if isinstance(item, dict) and item.get("status") == "active"]
        source = active if active else [item for item in findings if isinstance(item, dict)]
        compact["findingSamples"] = [compact_finding(item) for item in source[:sample_limit]]
        compact["findingSampleCount"] = min(len(source), sample_limit)
        compact["findingTotalCount"] = len(findings)
    return compact or None


def compact_observer_status(payload: dict[str, Any]) -> dict[str, Any]:
    observer = payload.get("observer") if isinstance(payload.get("observer"), dict) else {}
    memory = observer.get("memory") if isinstance(observer.get("memory"), dict) else {}
    timeline = observer.get("timeline") if isinstance(observer.get("timeline"), list) else []
    return {
        "enabled": observer.get("enabled"),
        "state": observer.get("state"),
        "mode": observer.get("mode"),
        "humanPinned": observer.get("humanPinned"),
        "activeProjectSlug": observer.get("activeProjectSlug"),
        "manualPin": observer.get("manualPin"),
        "incident": observer.get("incident"),
        "lastDecision": memory.get("lastDecision"),
        "timelineEventCount": len(timeline),
        "latestTimelineEvent": compact_event(timeline[-1]) if timeline else None,
    }


def compact_payload(command: str, status_code: int, payload: dict[str, Any], full: bool) -> dict[str, Any]:
    if full:
        return {"statusCode": status_code, **payload}

    compact: dict[str, Any] = {
        "statusCode": status_code,
        "ok": payload.get("ok"),
        "command": command,
        "outputMode": "compact",
    }
    for key in ("error", "message", "projectId", "reportPath", "artifactPath", "busy"):
        if key in payload:
            compact[key] = truncate_text(payload.get(key))

    if command == "observer-status":
        compact["observer"] = compact_observer_status(payload)
    elif command == "findings":
        compact["report"] = compact_report(payload.get("report"))
        compact["fullReportHint"] = "Use --full only when full evidence is required."
    elif command in {"scanner", "integrity", "sniper"}:
        compact["report"] = compact_report(payload.get("report"))
        compact["observerEvent"] = compact_event(payload.get("observerEvent"))
        compact["fullReportHint"] = "Use --full only when full evidence is required."
    elif command == "observe":
        compact["event"] = compact_event(payload.get("event") or payload.get("observerEvent"))
        compact["observer"] = compact_observer_status(payload)
    else:
        for key in ("service", "status", "version"):
            if key in payload:
                compact[key] = payload.get(key)
    return compact


def run_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    base_url = args.base_url
    timeout_seconds = int(getattr(args, "timeout_seconds", 30))
    if args.command == "health":
        return request_json(base_url, "GET", "/api/health", timeout_seconds=timeout_seconds)
    if args.command == "observer-status":
        return request_json(base_url, "GET", "/api/observer/status", timeout_seconds=timeout_seconds)
    if args.command == "observe":
        return request_json(base_url, "POST", "/api/observer/observe-once", {"source": "agent_tools"}, timeout_seconds=timeout_seconds)
    if args.command == "scanner":
        return request_json(base_url, "POST", project_path(args.project, "/code-scanner"), {}, timeout_seconds=timeout_seconds)
    if args.command == "integrity":
        return request_json(base_url, "POST", project_path(args.project, "/integrity/scan"), {}, timeout_seconds=timeout_seconds)
    if args.command == "findings":
        return request_json(base_url, "GET", project_path(args.project, "/observer-findings"), timeout_seconds=timeout_seconds)
    if args.command == "sniper":
        payload: dict[str, Any] = {"dryRun": bool(args.dry_run)}
        if args.confirm:
            payload["confirm"] = args.confirm
        return request_json(base_url, "POST", project_path(args.project, "/integrity/frozen-sniper"), payload, timeout_seconds=timeout_seconds)
    return 2, {"ok": False, "error": "unsupported_command", "command": args.command}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use HABLA internal Observer/Scanner/Sniper tools from an agent.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend base URL. Defaults to local HABLA backend.")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="HTTP timeout per backend request.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_output_flag(command_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        command_parser.add_argument("--full", action="store_true", help="Print the full backend JSON response.")
        return command_parser

    add_output_flag(subparsers.add_parser("health", help="Check backend health."))
    add_output_flag(subparsers.add_parser("observer-status", help="Read Observer state without starting a new mission."))
    add_output_flag(subparsers.add_parser("observe", help="Ask Observer for one explicit observation."))

    scanner = add_output_flag(subparsers.add_parser("scanner", help="Run final code scanner for a project."))
    scanner.add_argument("project")

    integrity = add_output_flag(subparsers.add_parser("integrity", help="Run file integrity scanner for a project."))
    integrity.add_argument("project")

    findings = add_output_flag(subparsers.add_parser("findings", help="Build/read Observer findings for a project."))
    findings.add_argument("project")

    sniper = add_output_flag(subparsers.add_parser("sniper", help="Run Frozen Sniper recovery for a project."))
    sniper.add_argument("project")
    sniper.add_argument("--dry-run", action="store_true", help="Preview recovery without modifying project files.")
    sniper.add_argument("--confirm", default="", help=f"Required value for non-dry-run: {FROZEN_SNIPER_CONFIRMATION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    status_code, payload = run_command(args)
    audit = {
        "timestamp": utc_now(),
        "tool": args.command,
        "project": getattr(args, "project", ""),
        "statusCode": status_code,
        "ok": bool(payload.get("ok")),
        "error": payload.get("error"),
        "artifactPath": payload.get("artifactPath") or payload.get("reportPath"),
        "outputMode": "full" if bool(getattr(args, "full", False)) else "compact",
    }
    write_audit(audit)
    output = compact_payload(args.command, status_code, payload, bool(getattr(args, "full", False)))
    print(json.dumps(output, ensure_ascii=True, indent=2))
    return 0 if 200 <= status_code < 300 and payload.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
