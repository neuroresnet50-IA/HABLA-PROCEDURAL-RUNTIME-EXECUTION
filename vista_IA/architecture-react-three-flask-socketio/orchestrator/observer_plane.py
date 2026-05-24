"""Observer plane: real read-only state machine plus behavior tree.

The observer does not execute project work. It reads persisted runtime, graph,
lint, and session evidence, then emits UI actions that explain what it is
looking at and why.
"""

from __future__ import annotations

import json
import hashlib
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


OBSERVER_FINDINGS_REPORT_NAME = "observer_findings.json"
OBSERVER_TERMINAL_STATUSES = {"completed", "blocked", "expired", "cancelled", "waiting_human"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_dict(values: Any) -> dict[str, Any] | None:
    for value in _as_list(values):
        if isinstance(value, dict):
            return value
    return None


def _active_sessions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    active_statuses = {"queued", "starting", "running"}
    sessions = []
    for session in _as_list(snapshot.get("sessions")):
        if not isinstance(session, dict):
            continue
        status = str(session.get("status") or "").lower()
        if status in active_statuses:
            sessions.append(session)
    return sessions


def _lint_findings(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    lint = snapshot.get("lint") if isinstance(snapshot.get("lint"), dict) else {}
    return [finding for finding in _as_list(lint.get("findings")) if isinstance(finding, dict)]


def _graph_nodes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    graph = snapshot.get("graph") if isinstance(snapshot.get("graph"), dict) else {}
    return [node for node in _as_list(graph.get("nodes")) if isinstance(node, dict)]


def _graph_edges(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    graph = snapshot.get("graph") if isinstance(snapshot.get("graph"), dict) else {}
    return [edge for edge in _as_list(graph.get("edges")) if isinstance(edge, dict)]


def _project_runtime(snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime = snapshot.get("project_runtime") if isinstance(snapshot.get("project_runtime"), dict) else {}
    return runtime


def _scanner_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime = _project_runtime(snapshot)
    scanner = runtime.get("scannerReport") if isinstance(runtime.get("scannerReport"), dict) else {}
    return scanner


def _sandbox_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime = _project_runtime(snapshot)
    sandbox = runtime.get("sandbox") if isinstance(runtime.get("sandbox"), dict) else {}
    return sandbox


def _project_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime = _project_runtime(snapshot)
    state = runtime.get("projectState") if isinstance(runtime.get("projectState"), dict) else {}
    return state


def _integrity_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime = _project_runtime(snapshot)
    report = runtime.get("integrityReport") if isinstance(runtime.get("integrityReport"), dict) else {}
    return report


def _integrity_findings(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    report = _integrity_report(snapshot)
    return [finding for finding in _as_list(report.get("findings")) if isinstance(finding, dict)]


def _scanner_report_passed(snapshot: dict[str, Any]) -> bool:
    scanner = _scanner_report(snapshot)
    validation = scanner.get("validation") if isinstance(scanner.get("validation"), dict) else {}
    scanner_meta = scanner.get("scanner") if isinstance(scanner.get("scanner"), dict) else {}
    return bool(
        scanner
        and validation.get("passed") is True
        and scanner_meta.get("visual_playback") == "magnifier_line_by_line_to_last_line"
        and scanner_meta.get("scrolls_to_last_line") is True
    )


def _sandbox_ready(snapshot: dict[str, Any]) -> bool:
    sandbox = _sandbox_state(snapshot)
    return bool(sandbox.get("running") and sandbox.get("ready") and (sandbox.get("embedUrl") or sandbox.get("url")))


def _runtime_gate_state(snapshot: dict[str, Any]) -> str:
    runtime = _project_runtime(snapshot)
    if not runtime:
        return ""
    project_state = _project_state(snapshot)
    status = str(project_state.get("status") or runtime.get("projectStatus") or "").lower()
    if status != "completed":
        return ""
    if not _scanner_report_passed(snapshot):
        return "verifying_scanner"
    if not _sandbox_ready(snapshot):
        return "verifying_sandbox"
    return ""


def _integrity_gate_state(snapshot: dict[str, Any]) -> str:
    findings = _integrity_findings(snapshot)
    if not findings:
        return ""
    finding_types = {str(finding.get("type") or "") for finding in findings}
    if "file_deleted" in finding_types:
        return "external_file_deletion_detected"
    if "untracked_file" in finding_types:
        return "untracked_file_detected"
    if any(finding_type.startswith("char_") for finding_type in finding_types):
        return "char_level_tamper_detected"
    return "external_file_change_detected"


def _project_slug_from_path(path: str) -> str:
    normalized = str(path or "").replace("\\", "/")
    marker = "workspace/projects/"
    if marker not in normalized:
        return ""
    tail = normalized.split(marker, 1)[-1]
    return tail.split("/", 1)[0].strip()


def _node_project_slug(node: dict[str, Any]) -> str:
    explicit = str(node.get("workspaceProject") or node.get("workspaceScene") or "").strip()
    return explicit or _project_slug_from_path(str(node.get("path") or ""))


def _finding_project_slug(finding: dict[str, Any]) -> str:
    explicit = str(finding.get("projectSlug") or finding.get("workspaceProject") or finding.get("workspaceScene") or "").strip()
    return explicit or _project_slug_from_path(str(finding.get("path") or finding.get("focusPath") or ""))


def _filter_snapshot_to_active_project(snapshot: dict[str, Any]) -> dict[str, Any]:
    active_project = str(snapshot.get("active_project_slug") or "").strip()
    if not active_project:
        return snapshot

    graph = snapshot.get("graph") if isinstance(snapshot.get("graph"), dict) else {}
    nodes = [node for node in _graph_nodes(snapshot) if _node_project_slug(node) == active_project]
    node_ids = {str(node.get("id")) for node in nodes if node.get("id")}
    if nodes:
        edges = [
            edge
            for edge in _graph_edges(snapshot)
            if str(edge.get("from") or edge.get("source") or "") in node_ids
            and str(edge.get("to") or edge.get("target") or "") in node_ids
        ]
    else:
        edges = []

    lint = snapshot.get("lint") if isinstance(snapshot.get("lint"), dict) else {}
    findings = [
        finding
        for finding in _lint_findings(snapshot)
        if _finding_project_slug(finding) == active_project or str(finding.get("nodeId") or "") in node_ids
    ]
    filtered_sessions = [
        session
        for session in _as_list(snapshot.get("sessions"))
        if isinstance(session, dict) and str(session.get("projectSlug") or "") == active_project
    ]

    return {
        **snapshot,
        "graph": {**graph, "nodes": nodes, "edges": edges},
        "lint": {**lint, "findings": findings},
        "sessions": filtered_sessions,
    }


def workspace_relative_path(path: str) -> str:
    normalized = str(path or "").replace("\\", "/")
    marker = "workspace/projects/"
    if marker not in normalized:
        return normalized
    tail = normalized.split(marker, 1)[-1]
    parts = tail.split("/", 1)
    return parts[1] if len(parts) == 2 else tail


def _json_sha256(payload: Any) -> str:
    material = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _observer_signature(action: dict[str, Any], state: str) -> str:
    evidence = action.get("evidence") if isinstance(action.get("evidence"), dict) else {}
    material = {
        "projectSlug": action.get("projectSlug"),
        "state": state,
        "behavior": action.get("behavior"),
        "action": action.get("action"),
        "source": action.get("phase"),
        "focusPath": action.get("focusPath") or action.get("relativePath"),
        "message": action.get("message"),
        "findingType": evidence.get("findingType") or evidence.get("code") or evidence.get("severity"),
    }
    return _json_sha256(material)


def _root_cause_for_state(state: str) -> str:
    if state == "waiting_worker":
        return "active_worker_running"
    if state == "verifying_scanner":
        return "project_completed_without_scanner"
    if state == "verifying_sandbox":
        return "project_completed_without_sandbox"
    if state in {
        "external_file_deletion_detected",
        "untracked_file_detected",
        "char_level_tamper_detected",
        "external_file_change_detected",
    }:
        return "integrity_failed_external_change"
    if state == "detecting_issue":
        return "lint_blocker"
    if state in {"scanning_map", "checking_flow", "observing_code"}:
        return "visual_observation"
    return "no_new_evidence" if state == "idle" else state


def _integrity_state_for_type(finding_type: str) -> str:
    if finding_type == "file_deleted":
        return "external_file_deletion_detected"
    if finding_type == "untracked_file":
        return "untracked_file_detected"
    if finding_type.startswith("char_"):
        return "char_level_tamper_detected"
    return "external_file_change_detected"


def _severity_score(severity: str) -> int:
    return {"error": 84, "warning": 62, "info": 34}.get(str(severity or "").lower(), 50)


def _integrity_score(finding_type: str, severity: str) -> int:
    if finding_type == "file_deleted":
        return 100
    if finding_type.startswith("char_"):
        return 98
    if finding_type in {"file_modified", "file_unreadable"}:
        return 94
    if finding_type == "untracked_file":
        return 78
    return max(72, _severity_score(severity))


def _observer_findings_artifact_path(snapshot: dict[str, Any]) -> Path | None:
    runtime = _project_runtime(snapshot)
    runtime_dir = str(runtime.get("runtimeDir") or "").strip()
    if not runtime_dir:
        return None
    return Path(runtime_dir) / "artifacts" / OBSERVER_FINDINGS_REPORT_NAME


def _build_observer_finding(
    *,
    project_slug: str,
    source: str,
    state: str,
    behavior: str,
    severity: str,
    score: int,
    message: str,
    reason: str,
    relative_path: str = "",
    focus_path: str = "",
    ui_action: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    proposed_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_payload = evidence or {}
    identity = {
        "projectSlug": project_slug,
        "source": source,
        "state": state,
        "behavior": behavior,
        "relativePath": relative_path,
        "focusPath": focus_path,
        "evidence": {
            "code": evidence_payload.get("code"),
            "findingType": evidence_payload.get("findingType"),
            "line": evidence_payload.get("line"),
            "column": evidence_payload.get("column"),
            "expectedSha256": evidence_payload.get("expectedSha256"),
            "actualSha256": evidence_payload.get("actualSha256"),
        },
    }
    fingerprint = _json_sha256(identity)
    return {
        "id": f"observer-{fingerprint[:16]}",
        "fingerprintSha256": fingerprint,
        "projectSlug": project_slug,
        "source": source,
        "state": state,
        "behavior": behavior,
        "severity": severity,
        "observationScore": max(0, min(100, int(score or 0))),
        "message": message,
        "reason": reason,
        "relativePath": relative_path,
        "focusPath": focus_path or relative_path,
        "uiAction": ui_action or {},
        "evidence": evidence_payload,
        "proposedActions": proposed_actions or [],
    }


def current_observer_findings(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    runtime = _project_runtime(snapshot)
    project_slug = str(runtime.get("projectSlug") or snapshot.get("active_project_slug") or "").strip()
    findings: list[dict[str, Any]] = []

    report = _integrity_report(snapshot)
    for finding in _integrity_findings(snapshot):
        finding_type = str(finding.get("type") or "external_file_change")
        relative_path = workspace_relative_path(str(finding.get("path") or ""))
        severity = str(finding.get("severity") or ("warning" if finding_type == "untracked_file" else "error"))
        findings.append(
            _build_observer_finding(
                project_slug=project_slug or str(finding.get("projectSlug") or ""),
                source="integrity",
                state=_integrity_state_for_type(finding_type),
                behavior="inspect_file_integrity",
                severity=severity,
                score=_integrity_score(finding_type, severity),
                message=str(finding.get("message") or "Observer detecto cambio externo no registrado."),
                reason="El hash actual del archivo no coincide con la baseline y no hay escritura interna registrada.",
                relative_path=relative_path,
                focus_path=relative_path,
                ui_action={"type": "code-scan", "targetId": "code-workbench"},
                evidence={
                    "findingType": finding_type,
                    "line": finding.get("line"),
                    "column": finding.get("column"),
                    "length": finding.get("length"),
                    "expectedSha256": finding.get("expectedSha256"),
                    "actualSha256": finding.get("actualSha256"),
                    "expectedText": finding.get("expectedText"),
                    "actualText": finding.get("actualText"),
                    "summary": report.get("summary") if isinstance(report, dict) else {},
                    "reportPath": runtime.get("integrityReportPath"),
                },
                proposed_actions=[
                    {"id": "refresh_graph", "label": "Refrescar grafo", "requiresApproval": False, "payload": {}},
                    {"id": "audit_map", "label": "Reauditar mapa", "requiresApproval": False, "payload": {"scene": project_slug}},
                ],
            )
        )

    runtime_state = _runtime_gate_state(snapshot)
    project_state = _project_state(snapshot)
    if runtime_state == "verifying_scanner":
        scanner = _scanner_report(snapshot)
        validation = scanner.get("validation") if isinstance(scanner.get("validation"), dict) else {}
        scanner_meta = scanner.get("scanner") if isinstance(scanner.get("scanner"), dict) else {}
        findings.append(
            _build_observer_finding(
                project_slug=project_slug,
                source="scanner",
                state="verifying_scanner",
                behavior="verify_scanner_evidence",
                severity="error",
                score=88,
                message="Scanner final no certificado para un proyecto marcado completed.",
                reason="El proyecto figura completed, pero falta evidencia valida del scanner end-to-end.",
                relative_path="runtime/artifacts/final_code_scanner_report.json",
                focus_path=str(runtime.get("scannerReportPath") or "runtime/artifacts/final_code_scanner_report.json"),
                ui_action={"type": "code-scan", "targetId": "code-workbench"},
                evidence={
                    "projectStatus": project_state.get("status") or runtime.get("projectStatus"),
                    "scannerReportExists": bool(scanner),
                    "validationPassed": validation.get("passed"),
                    "visualPlayback": scanner_meta.get("visual_playback"),
                    "scrollsToLastLine": scanner_meta.get("scrolls_to_last_line"),
                    "blockers": _as_list(validation.get("blockers")),
                },
            )
        )
    elif runtime_state == "verifying_sandbox":
        sandbox = _sandbox_state(snapshot)
        healthcheck = sandbox.get("healthcheck") if isinstance(sandbox.get("healthcheck"), dict) else {}
        findings.append(
            _build_observer_finding(
                project_slug=project_slug,
                source="sandbox",
                state="verifying_sandbox",
                behavior="verify_sandbox_evidence",
                severity="error",
                score=82,
                message="Sandbox real incompleto despues de scanner aprobado.",
                reason="Despues del scanner aprobado debe existir servidor sandbox real con URL y healthcheck listo.",
                relative_path="runtime/sandbox.json",
                focus_path=str(runtime.get("sandboxPath") or "runtime/sandbox.json"),
                ui_action={"type": "flow-zoom", "targetId": "algorithm-flow-section"},
                evidence={
                    "sandboxStatus": sandbox.get("status"),
                    "running": sandbox.get("running"),
                    "ready": sandbox.get("ready"),
                    "embedUrl": sandbox.get("embedUrl") or sandbox.get("url"),
                    "healthcheck": healthcheck,
                },
            )
        )

    for finding in _lint_findings(snapshot):
        severity = str(finding.get("severity") or "warning")
        focus_path = str(finding.get("path") or "")
        findings.append(
            _build_observer_finding(
                project_slug=project_slug or _finding_project_slug(finding),
                source="lint",
                state="detecting_issue",
                behavior="inspect_visual_issue",
                severity=severity,
                score=_severity_score(severity),
                message=str(finding.get("message") or "Observer detecto hallazgo de mapa/codigo."),
                reason="La auditoria del mapa reporto hallazgos reales.",
                relative_path=workspace_relative_path(focus_path),
                focus_path=focus_path,
                ui_action={"type": "map-click", "targetId": "architecture-map-section"},
                evidence={
                    "code": finding.get("code"),
                    "severity": severity,
                    "line": finding.get("line"),
                    "nodeId": finding.get("nodeId"),
                    "stepId": finding.get("stepId"),
                },
            )
        )

    return sorted(findings, key=lambda item: (-int(item.get("observationScore") or 0), str(item.get("id") or "")))


def build_observer_findings_report(snapshot: dict[str, Any], existing_report: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = _project_runtime(snapshot)
    project_slug = str(runtime.get("projectSlug") or snapshot.get("active_project_slug") or "").strip()
    now = utc_now()
    current = current_observer_findings(snapshot)
    current_by_id = {str(finding.get("id")): finding for finding in current if finding.get("id")}
    previous_findings = []
    if isinstance(existing_report, dict):
        previous_findings = [finding for finding in _as_list(existing_report.get("findings")) if isinstance(finding, dict)]
    previous_by_id = {str(finding.get("id")): finding for finding in previous_findings if finding.get("id")}

    merged: list[dict[str, Any]] = []
    for finding_id, finding in current_by_id.items():
        previous = previous_by_id.get(finding_id) or {}
        merged.append(
            {
                **finding,
                "status": "active",
                "firstSeenAt": previous.get("firstSeenAt") or now,
                "lastSeenAt": now,
                "occurrenceCount": int(previous.get("occurrenceCount") or 0) + 1,
                "resolvedAt": None,
            }
        )

    for finding in previous_findings:
        finding_id = str(finding.get("id") or "")
        if not finding_id or finding_id in current_by_id:
            continue
        status = str(finding.get("status") or "active")
        merged.append(
            {
                **finding,
                "status": "resolved",
                "resolvedAt": finding.get("resolvedAt") or (now if status == "active" else None),
            }
        )

    merged = sorted(
        merged,
        key=lambda item: (
            0 if item.get("status") == "active" else 1,
            -int(item.get("observationScore") or 0),
            str(item.get("lastSeenAt") or ""),
        ),
    )[:500]
    active = [finding for finding in merged if finding.get("status") == "active"]
    by_severity: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for finding in active:
        severity = str(finding.get("severity") or "info")
        source = str(finding.get("source") or "observer")
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1
    return {
        "schema_version": 1,
        "report_type": "observer_findings",
        "projectId": project_slug,
        "generatedAt": now,
        "summary": {
            "totalFindings": len(merged),
            "activeFindings": len(active),
            "resolvedFindings": len(merged) - len(active),
            "observationScore": max([int(finding.get("observationScore") or 0) for finding in active], default=0),
            "bySeverity": by_severity,
            "bySource": by_source,
        },
        "findings": merged,
    }


def persist_observer_findings(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    path = _observer_findings_artifact_path(snapshot)
    if path is None:
        return None
    existing = read_json(path, {})
    report = build_observer_findings_report(snapshot, existing if isinstance(existing, dict) else {})
    write_json(path, report)
    return report


DEFAULT_BEHAVIOR_TREE = {
    "version": 1,
    "rules": [
        {
            "id": "repair_pre_scan",
            "label": "Pre-scan de reparacion",
            "state": "preparing_repair",
            "action": "scan_code",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "monitor_worker",
            "label": "Monitorear worker activo",
            "state": "waiting_worker",
            "action": "scan_runtime",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "inspect_visual_issue",
            "label": "Inspeccionar punto rojo",
            "state": "detecting_issue",
            "action": "click_issue",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "verify_scanner_evidence",
            "label": "Verificar scanner final end-to-end",
            "state": "verifying_scanner",
            "action": "inspect_scanner_evidence",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "verify_sandbox_evidence",
            "label": "Verificar sandbox real end-to-end",
            "state": "verifying_sandbox",
            "action": "inspect_sandbox_evidence",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "detect_external_file_change",
            "label": "Detectar cambios externos de archivos",
            "state": "external_file_change_detected",
            "action": "inspect_file_integrity",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "detect_external_file_deletion",
            "label": "Detectar eliminaciones externas",
            "state": "external_file_deletion_detected",
            "action": "inspect_file_integrity",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "detect_untracked_file",
            "label": "Detectar archivos no registrados",
            "state": "untracked_file_detected",
            "action": "inspect_file_integrity",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "detect_char_level_tamper",
            "label": "Detectar manipulacion caracter por caracter",
            "state": "char_level_tamper_detected",
            "action": "inspect_file_integrity",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "inspect_flow",
            "label": "Revisar diagrama de flujo",
            "state": "checking_flow",
            "action": "zoom_flow",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "scan_map",
            "label": "Escanear mapa conceptual",
            "state": "scanning_map",
            "action": "zoom_map",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "observe_code",
            "label": "Observar codigo",
            "state": "observing_code",
            "action": "scan_code",
            "enabled": True,
            "requiresApproval": False,
        },
        {
            "id": "propose_repair",
            "label": "Proponer reparacion con autorizacion humana",
            "state": "detecting_issue",
            "action": "prepare_repair",
            "enabled": True,
            "requiresApproval": True,
        },
    ],
}


def default_behavior_tree() -> dict[str, Any]:
    return deepcopy(DEFAULT_BEHAVIOR_TREE)


def normalize_behavior_tree(value: Any) -> dict[str, Any]:
    base = default_behavior_tree()
    incoming_rules = {
        str(rule.get("id")): rule
        for rule in _as_list(value.get("rules") if isinstance(value, dict) else [])
        if isinstance(rule, dict) and rule.get("id")
    }
    next_rules = []
    for rule in base["rules"]:
        incoming = incoming_rules.get(str(rule["id"])) or {}
        next_rules.append(
            {
                **rule,
                "enabled": bool(incoming.get("enabled", rule["enabled"])),
                "requiresApproval": bool(incoming.get("requiresApproval", rule["requiresApproval"])),
            }
        )
    return {"version": 1, "rules": next_rules}


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


class ObserverMemory:
    """Persist observer memory and timeline as auditable runtime evidence."""

    def __init__(self, *, memory_path: str | Path | None = None, timeline_path: str | Path | None = None, timeline_limit: int = 80) -> None:
        self.memory_path = Path(memory_path) if memory_path is not None else None
        self.timeline_path = Path(timeline_path) if timeline_path is not None else None
        self.timeline_limit = max(10, int(timeline_limit or 80))
        self.data = self._load_memory()

    def _load_memory(self) -> dict[str, Any]:
        fallback = {
            "visited_nodes": [],
            "visited_issues": [],
            "seen_files": [],
            "seen_workers": [],
            "repair_attempts": [],
            "last_decision": None,
            "updated_at": None,
        }
        if self.memory_path is None:
            return fallback
        payload = read_json(self.memory_path, fallback)
        if not isinstance(payload, dict):
            return fallback
        return {**fallback, **payload}

    def remember_event(self, event: dict[str, Any]) -> None:
        self.data["updated_at"] = utc_now()
        self.data["last_decision"] = {
            "state": event.get("state"),
            "action": event.get("action"),
            "behavior": event.get("behavior"),
            "reason": event.get("reason"),
            "message": event.get("message"),
            "timestamp": event.get("timestamp"),
        }
        self._remember_unique("visited_nodes", event.get("focusNodeId"))
        self._remember_unique("seen_files", event.get("relativePath") or event.get("focusPath"))

        evidence = event.get("evidence") if isinstance(event.get("evidence"), dict) else {}
        if event.get("behavior") == "inspect_visual_issue":
            issue_key = ":".join(
                str(value or "")
                for value in (event.get("focusPath"), evidence.get("code"), evidence.get("line"))
            )
            self._remember_unique("visited_issues", issue_key)
        if event.get("behavior") == "monitor_worker":
            self._remember_unique("seen_workers", evidence.get("sessionId") or evidence.get("currentTaskId"))
        if event.get("behavior") == "repair_pre_scan":
            self._remember_unique("repair_attempts", event.get("relativePath") or event.get("focusPath"))

        self._append_timeline(event)
        self.persist()

    def _remember_unique(self, key: str, value: Any) -> None:
        normalized = str(value or "").strip()
        if not normalized:
            return
        items = [str(item) for item in _as_list(self.data.get(key))]
        if normalized in items:
            items.remove(normalized)
        items.insert(0, normalized)
        self.data[key] = items[: self.timeline_limit]

    def _append_timeline(self, event: dict[str, Any]) -> None:
        if self.timeline_path is None:
            return
        self.timeline_path.parent.mkdir(parents=True, exist_ok=True)
        compact_event = {
            "timestamp": event.get("timestamp") or utc_now(),
            "state": event.get("state"),
            "behavior": event.get("behavior"),
            "action": event.get("action"),
            "message": event.get("message"),
            "reason": event.get("reason"),
            "projectSlug": event.get("projectSlug"),
            "focusPath": event.get("focusPath"),
            "focusNodeId": event.get("focusNodeId"),
            "stepId": event.get("stepId"),
            "proposedActions": event.get("proposedActions") or [],
            "snapshotSummary": event.get("snapshotSummary") or {},
        }
        with self.timeline_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(compact_event, ensure_ascii=True) + "\n")

    def persist(self) -> None:
        if self.memory_path is not None:
            write_json(self.memory_path, self.data)

    def timeline(self, project_slug: str | None = None) -> list[dict[str, Any]]:
        if self.timeline_path is None or not self.timeline_path.exists():
            return []
        normalized_project = str(project_slug or "").strip()
        events: list[dict[str, Any]] = []
        try:
            lines = self.timeline_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if normalized_project and str(event.get("projectSlug") or "") != normalized_project:
                continue
            events.append(event)
        return events[-self.timeline_limit :]

    def summary(self, project_slug: str | None = None) -> dict[str, Any]:
        normalized_project = str(project_slug or "").strip()
        if normalized_project:
            events = self.timeline(normalized_project)
            nodes = {str(event.get("focusNodeId") or "") for event in events if event.get("focusNodeId")}
            issues = {
                ":".join(str(value or "") for value in (event.get("focusPath"), event.get("stepId"), event.get("message")))
                for event in events
                if event.get("behavior") == "inspect_visual_issue"
            }
            files = {str(event.get("focusPath") or "") for event in events if event.get("focusPath")}
            workers = {
                str((event.get("snapshotSummary") or {}).get("activeSessionCount") or "")
                for event in events
                if event.get("behavior") == "monitor_worker"
            }
            repair_attempts = {str(event.get("focusPath") or "") for event in events if event.get("behavior") == "repair_pre_scan"}
            last_event = events[-1] if events else None
            return {
                "visitedNodeCount": len(nodes),
                "visitedIssueCount": len(issues),
                "seenFileCount": len(files),
                "seenWorkerCount": len([item for item in workers if item]),
                "repairAttemptCount": len(repair_attempts),
                "lastDecision": {
                    "state": last_event.get("state"),
                    "action": last_event.get("action"),
                    "behavior": last_event.get("behavior"),
                    "reason": last_event.get("reason"),
                    "message": last_event.get("message"),
                    "timestamp": last_event.get("timestamp"),
                }
                if last_event
                else None,
                "updatedAt": last_event.get("timestamp") if last_event else None,
            }
        return {
            "visitedNodeCount": len(_as_list(self.data.get("visited_nodes"))),
            "visitedIssueCount": len(_as_list(self.data.get("visited_issues"))),
            "seenFileCount": len(_as_list(self.data.get("seen_files"))),
            "seenWorkerCount": len(_as_list(self.data.get("seen_workers"))),
            "repairAttemptCount": len(_as_list(self.data.get("repair_attempts"))),
            "lastDecision": self.data.get("last_decision"),
            "updatedAt": self.data.get("updated_at"),
        }


@dataclass(frozen=True)
class ObserverConfig:
    poll_seconds: float = 5.0
    min_emit_interval_seconds: float = 2.0
    idle_emit_interval_seconds: float = 20.0
    max_incident_runtime_seconds: float = 180.0
    max_incident_ticks: int = 30
    max_repeated_events: int = 3
    incident_cooldown_seconds: float = 60.0


@dataclass
class ObserverContext:
    state: str = "idle"
    tick_count: int = 0
    last_event_at: float = 0.0
    recent_external_event: dict[str, Any] | None = None
    last_signature: str = ""
    state_entered_at: float = field(default_factory=time.monotonic)
    incident: dict[str, Any] | None = None
    incident_started_at: float = field(default_factory=time.monotonic)
    signature_cooldowns: dict[str, float] = field(default_factory=dict)


class ObserverStateMachine:
    """Resolve the observer state from actual runtime evidence."""

    def next_state(self, snapshot: dict[str, Any], context: ObserverContext) -> str:
        external = context.recent_external_event or {}
        op = str(external.get("op") or "").lower()
        if op == "repair_session_start":
            return "preparing_repair"

        active_sessions = _active_sessions(snapshot)
        if active_sessions:
            return "waiting_worker"

        integrity_gate_state = _integrity_gate_state(snapshot)
        if integrity_gate_state:
            return integrity_gate_state

        runtime_gate_state = _runtime_gate_state(snapshot)
        if runtime_gate_state:
            return runtime_gate_state

        findings = _lint_findings(snapshot)
        if findings:
            return "detecting_issue"

        nodes = _graph_nodes(snapshot)
        edges = _graph_edges(snapshot)
        if nodes and edges:
            return "scanning_map" if context.tick_count % 2 == 0 else "checking_flow"
        if nodes:
            return "observing_code"
        return "idle"


class ObserverBehaviorTree:
    """Choose one concrete UI action for the current state."""

    def __init__(self, behavior_tree: dict[str, Any] | None = None) -> None:
        self.behavior_tree = normalize_behavior_tree(behavior_tree or default_behavior_tree())

    def set_behavior_tree(self, behavior_tree: dict[str, Any]) -> dict[str, Any]:
        self.behavior_tree = normalize_behavior_tree(behavior_tree)
        return self.behavior_tree

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.behavior_tree)

    def rule_enabled(self, rule_id: str) -> bool:
        for rule in self.behavior_tree.get("rules", []):
            if str(rule.get("id")) == rule_id:
                return bool(rule.get("enabled", True))
        return True

    def choose_action(self, state: str, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        if state == "preparing_repair" and self.rule_enabled("repair_pre_scan"):
            return self._repair_action(snapshot, context)
        if state == "waiting_worker" and self.rule_enabled("monitor_worker"):
            return self._worker_action(snapshot, context)
        if state == "detecting_issue" and self.rule_enabled("inspect_visual_issue"):
            return self._issue_action(snapshot, context)
        if state == "verifying_scanner" and self.rule_enabled("verify_scanner_evidence"):
            return self._scanner_evidence_action(snapshot, context)
        if state == "verifying_sandbox" and self.rule_enabled("verify_sandbox_evidence"):
            return self._sandbox_evidence_action(snapshot, context)
        if state == "external_file_deletion_detected" and self.rule_enabled("detect_external_file_deletion"):
            return self._integrity_action(snapshot, context)
        if state == "untracked_file_detected" and self.rule_enabled("detect_untracked_file"):
            return self._integrity_action(snapshot, context)
        if state == "char_level_tamper_detected" and self.rule_enabled("detect_char_level_tamper"):
            return self._integrity_action(snapshot, context)
        if state == "external_file_change_detected" and self.rule_enabled("detect_external_file_change"):
            return self._integrity_action(snapshot, context)
        if state == "checking_flow" and self.rule_enabled("inspect_flow"):
            return self._flow_action(snapshot, context)
        if state == "scanning_map" and self.rule_enabled("scan_map"):
            return self._map_action(snapshot, context)
        if state == "observing_code" and self.rule_enabled("observe_code"):
            return self._code_action(snapshot, context)
        return self._idle_action(snapshot, context)

    def _repair_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        external = context.recent_external_event or {}
        relative_path = str(external.get("relativePath") or external.get("path") or "")
        project_slug = str(external.get("projectSlug") or snapshot.get("active_project_slug") or "")
        return {
            "behavior": "repair_pre_scan",
            "action": "scan_code",
            "phase": "observer:pre-repair",
            "message": f"Observer real escaneando {relative_path or 'archivo seleccionado'} antes de reparar.",
            "reason": "El usuario lanzo una reparacion agentica y existe evento repair_session_start.",
            "projectSlug": project_slug,
            "relativePath": relative_path,
            "focusPath": external.get("focusPath"),
            "focusNodeId": external.get("focusNodeId"),
            "uiAction": {"type": "code-scan", "targetId": "code-workbench"},
        }

    def _worker_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        session = _first_dict(_active_sessions(snapshot)) or {}
        project_slug = str(session.get("projectSlug") or snapshot.get("active_project_slug") or "")
        current_task = session.get("currentTaskId") or session.get("currentTask") or snapshot.get("current_task_id")
        return {
            "behavior": "monitor_worker",
            "action": "scan_runtime",
            "phase": "observer:worker",
            "message": f"Observer real monitoreando worker activo{f' en {current_task}' if current_task else ''}.",
            "reason": "Hay una sesion/worker con estado running, queued o starting.",
            "projectSlug": project_slug,
            "uiAction": {"type": "page-scroll", "targetId": "code-workbench"},
            "evidence": {"sessionId": session.get("sessionId"), "currentTaskId": current_task, "status": session.get("status")},
        }

    def _issue_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        findings = _lint_findings(snapshot)
        finding = findings[context.tick_count % len(findings)]
        focus_path = str(finding.get("path") or "")
        relative_path = workspace_relative_path(focus_path)
        return {
            "behavior": "inspect_visual_issue",
            "action": "click_issue",
            "phase": "observer:issue",
            "message": str(finding.get("message") or "Observer real inspeccionando punto rojo."),
            "reason": "La auditoria del mapa reporto hallazgos reales.",
            "projectSlug": str(snapshot.get("active_project_slug") or finding.get("projectSlug") or ""),
            "relativePath": relative_path,
            "focusPath": focus_path,
            "focusNodeId": finding.get("nodeId"),
            "stepId": finding.get("stepId"),
            "uiAction": {"type": "map-click", "targetId": "architecture-map-section"},
            "evidence": {"code": finding.get("code"), "severity": finding.get("severity"), "line": finding.get("line")},
            "proposedActions": self._issue_proposals(finding, focus_path, relative_path),
        }

    def _scanner_evidence_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        runtime = _project_runtime(snapshot)
        scanner = _scanner_report(snapshot)
        validation = scanner.get("validation") if isinstance(scanner.get("validation"), dict) else {}
        scanner_meta = scanner.get("scanner") if isinstance(scanner.get("scanner"), dict) else {}
        project_slug = str(runtime.get("projectSlug") or snapshot.get("active_project_slug") or "")
        blockers = _as_list(validation.get("blockers"))
        if not scanner:
            detail = "no existe runtime/artifacts/final_code_scanner_report.json"
        elif validation.get("passed") is not True:
            detail = "; ".join(str(item) for item in blockers if item) or "validation.passed no es true"
        else:
            detail = "el reporte no certifica magnifier_line_by_line_to_last_line hasta la ultima linea"
        return {
            "behavior": "verify_scanner_evidence",
            "action": "inspect_scanner_evidence",
            "phase": "observer:scanner-evidence",
            "message": f"Observer detecto cierre incompleto: scanner final no certificado ({detail}).",
            "reason": "El proyecto figura completed, pero falta evidencia valida del scanner end-to-end.",
            "projectSlug": project_slug,
            "relativePath": "runtime/artifacts/final_code_scanner_report.json",
            "focusPath": runtime.get("scannerReportPath") or "runtime/artifacts/final_code_scanner_report.json",
            "uiAction": {"type": "code-scan", "targetId": "code-workbench"},
            "evidence": {
                "projectStatus": (_project_state(snapshot).get("status") or runtime.get("projectStatus")),
                "scannerReportExists": bool(scanner),
                "validationPassed": validation.get("passed"),
                "visualPlayback": scanner_meta.get("visual_playback"),
                "scrollsToLastLine": scanner_meta.get("scrolls_to_last_line"),
                "blockers": blockers,
            },
            "proposedActions": [
                {
                    "id": "audit_map",
                    "label": "Reauditar mapa",
                    "requiresApproval": False,
                    "payload": {"scene": project_slug},
                },
                {
                    "id": "refresh_graph",
                    "label": "Refrescar grafo",
                    "requiresApproval": False,
                    "payload": {},
                },
            ],
        }

    def _sandbox_evidence_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        runtime = _project_runtime(snapshot)
        sandbox = _sandbox_state(snapshot)
        healthcheck = sandbox.get("healthcheck") if isinstance(sandbox.get("healthcheck"), dict) else {}
        project_slug = str(runtime.get("projectSlug") or snapshot.get("active_project_slug") or "")
        missing = []
        if not sandbox.get("running"):
            missing.append("running")
        if not sandbox.get("ready"):
            missing.append("ready")
        if not (sandbox.get("embedUrl") or sandbox.get("url")):
            missing.append("embedUrl")
        return {
            "behavior": "verify_sandbox_evidence",
            "action": "inspect_sandbox_evidence",
            "phase": "observer:sandbox-evidence",
            "message": f"Observer detecto scanner aprobado, pero sandbox real incompleto: falta {', '.join(missing) or 'healthcheck valido'}.",
            "reason": "Despues del scanner aprobado debe existir un servidor sandbox real con URL y healthcheck listo.",
            "projectSlug": project_slug,
            "relativePath": "runtime/sandbox.json",
            "focusPath": runtime.get("sandboxPath") or "runtime/sandbox.json",
            "uiAction": {"type": "flow-zoom", "targetId": "algorithm-flow-section"},
            "evidence": {
                "scannerPassed": True,
                "sandboxStatus": sandbox.get("status"),
                "running": sandbox.get("running"),
                "ready": sandbox.get("ready"),
                "embedUrl": sandbox.get("embedUrl") or sandbox.get("url"),
                "healthcheck": healthcheck,
            },
            "proposedActions": [
                {
                    "id": "frozen_sniper_recovery",
                    "label": "Frozen Sniper: congelar evidencia y recuperar",
                    "requiresApproval": True,
                    "payload": {"projectSlug": project_slug, "reportPath": runtime.get("integrityReportPath")},
                },
                {
                    "id": "refresh_graph",
                    "label": "Refrescar grafo",
                    "requiresApproval": False,
                    "payload": {},
                }
            ],
        }

    def _integrity_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        runtime = _project_runtime(snapshot)
        report = _integrity_report(snapshot)
        findings = _integrity_findings(snapshot)
        finding = findings[context.tick_count % len(findings)] if findings else {}
        project_slug = str(runtime.get("projectSlug") or snapshot.get("active_project_slug") or finding.get("projectSlug") or "")
        relative_path = workspace_relative_path(str(finding.get("path") or ""))
        finding_type = str(finding.get("type") or "external_file_change")
        return {
            "behavior": "inspect_file_integrity",
            "action": "inspect_file_integrity",
            "phase": "observer:file-integrity",
            "message": str(finding.get("message") or "Observer detecto cambio externo no registrado."),
            "reason": "El hash actual del archivo no coincide con la baseline que dejaron los agentes y no hay escritura interna registrada.",
            "projectSlug": project_slug,
            "relativePath": relative_path,
            "focusPath": relative_path,
            "uiAction": {"type": "code-scan", "targetId": "code-workbench"},
            "evidence": {
                "findingType": finding_type,
                "line": finding.get("line"),
                "column": finding.get("column"),
                "expectedSha256": finding.get("expectedSha256"),
                "actualSha256": finding.get("actualSha256"),
                "expectedText": finding.get("expectedText"),
                "actualText": finding.get("actualText"),
                "summary": report.get("summary") if isinstance(report, dict) else {},
                "reportPath": runtime.get("integrityReportPath"),
            },
            "proposedActions": [
                {
                    "id": "refresh_graph",
                    "label": "Refrescar grafo",
                    "requiresApproval": False,
                    "payload": {},
                },
                {
                    "id": "audit_map",
                    "label": "Reauditar mapa",
                    "requiresApproval": False,
                    "payload": {"scene": project_slug},
                },
            ],
        }

    def _issue_proposals(self, finding: dict[str, Any], focus_path: str, relative_path: str) -> list[dict[str, Any]]:
        proposals = [
            {
                "id": "audit_map",
                "label": "Reauditar mapa",
                "requiresApproval": False,
                "payload": {"scene": finding.get("projectSlug") or ""},
            },
            {
                "id": "refresh_graph",
                "label": "Refrescar grafo",
                "requiresApproval": False,
                "payload": {},
            },
        ]
        if self.rule_enabled("propose_repair"):
            proposals.append(
                {
                    "id": "prepare_repair",
                    "label": "Preparar reparacion",
                    "requiresApproval": True,
                    "payload": {
                        "path": relative_path,
                        "focusPath": focus_path,
                        "line": finding.get("line") or 1,
                        "code": finding.get("code") or "visual_issue",
                        "message": finding.get("message") or "Hallazgo visual seleccionado.",
                    },
                }
            )
        return proposals

    def _flow_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        nodes = [node for node in _graph_nodes(snapshot) if isinstance(node.get("algorithm"), dict)]
        node = nodes[context.tick_count % len(nodes)] if nodes else {}
        steps = _as_list((node.get("algorithm") or {}).get("steps") if isinstance(node.get("algorithm"), dict) else [])
        step = steps[context.tick_count % len(steps)] if steps else {}
        return {
            "behavior": "inspect_flow",
            "action": "zoom_flow",
            "phase": "observer:flow",
            "message": f"Observer real revisando flujo de {node.get('name') or 'bloque'}",
            "reason": "El mapa tiene nodos con algoritmo interno verificable.",
            "focusNodeId": node.get("id"),
            "focusPath": node.get("path"),
            "stepId": step.get("id") if isinstance(step, dict) else None,
            "projectSlug": node.get("workspaceProject") or node.get("workspaceScene") or snapshot.get("active_project_slug"),
            "uiAction": {"type": "flow-zoom", "targetId": "algorithm-flow-section"},
        }

    def _map_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        nodes = _graph_nodes(snapshot)
        node = nodes[context.tick_count % len(nodes)] if nodes else {}
        return {
            "behavior": "scan_map",
            "action": "zoom_map",
            "phase": "observer:map",
            "message": f"Observer real enfocando {node.get('name') or 'nodo'} en el mapa.",
            "reason": "Existen nodos y conexiones reales en el grafo actual.",
            "focusNodeId": node.get("id"),
            "focusPath": node.get("path"),
            "projectSlug": node.get("workspaceProject") or node.get("workspaceScene") or snapshot.get("active_project_slug"),
            "uiAction": {"type": "map-zoom", "targetId": "architecture-map-section"},
        }

    def _code_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        node = _graph_nodes(snapshot)[context.tick_count % len(_graph_nodes(snapshot))]
        return {
            "behavior": "observe_code",
            "action": "scan_code",
            "phase": "observer:code",
            "message": f"Observer real leyendo estructura de {node.get('name') or 'archivo'}.",
            "reason": "Hay archivos visibles en el grafo actual.",
            "focusNodeId": node.get("id"),
            "focusPath": node.get("path"),
            "projectSlug": node.get("workspaceProject") or node.get("workspaceScene") or snapshot.get("active_project_slug"),
            "uiAction": {"type": "code-scan", "targetId": "code-workbench"},
        }

    def _idle_action(self, snapshot: dict[str, Any], context: ObserverContext) -> dict[str, Any]:
        return {
            "behavior": "idle_watch",
            "action": "observe_idle",
            "phase": "observer:idle",
            "message": "Observer real en espera: no hay worker activo ni hallazgos visibles.",
            "reason": "No se encontro trabajo activo ni alertas en la evidencia actual.",
            "projectSlug": str(snapshot.get("active_project_slug") or ""),
            "uiAction": {"type": "micro-modal", "targetId": "layers-section"},
        }


class ObserverPlane:
    """Read evidence, update state, and emit observer UI actions."""

    def __init__(
        self,
        *,
        snapshot_provider: Callable[[], dict[str, Any]],
        event_handler: Callable[[dict[str, Any]], None] | None = None,
        config: ObserverConfig | None = None,
        memory_path: str | Path | None = None,
        timeline_path: str | Path | None = None,
        behavior_path: str | Path | None = None,
        incident_dir: str | Path | None = None,
    ) -> None:
        self.snapshot_provider = snapshot_provider
        self.event_handler = event_handler
        self.config = config or ObserverConfig()
        self.context = ObserverContext()
        self.state_machine = ObserverStateMachine()
        self.behavior_path = Path(behavior_path) if behavior_path is not None else None
        behavior_tree = read_json(self.behavior_path, default_behavior_tree()) if self.behavior_path is not None else default_behavior_tree()
        self.behavior_tree = ObserverBehaviorTree(behavior_tree)
        self.memory = ObserverMemory(memory_path=memory_path, timeline_path=timeline_path)
        if incident_dir is not None:
            self.incident_dir = Path(incident_dir)
        elif memory_path is not None:
            self.incident_dir = Path(memory_path).parent / "incidents"
        else:
            self.incident_dir = None
        self.enabled = True
        self._running = False

    def _incident_path(self, incident: dict[str, Any] | None = None) -> Path | None:
        if self.incident_dir is None:
            return None
        current = incident if isinstance(incident, dict) else self.context.incident
        incident_id = str((current or {}).get("incidentId") or "").strip()
        if not incident_id:
            return None
        return self.incident_dir / f"{incident_id}.json"

    def _persist_incident(self) -> None:
        path = self._incident_path()
        if path is not None and isinstance(self.context.incident, dict):
            write_json(path, self.context.incident)

    def _incident_status(self) -> dict[str, Any] | None:
        incident = self.context.incident
        if not isinstance(incident, dict):
            return None
        return {
            "incidentId": incident.get("incidentId"),
            "projectSlug": incident.get("projectSlug"),
            "trigger": incident.get("trigger"),
            "status": incident.get("status"),
            "phase": incident.get("phase"),
            "rootCause": incident.get("rootCause"),
            "stopReason": incident.get("stopReason"),
            "counters": incident.get("counters") or {},
            "deadlineAt": incident.get("deadlineAt"),
        }

    def _new_incident(self, snapshot: dict[str, Any], state: str, action: dict[str, Any], signature: str) -> dict[str, Any]:
        project_slug = str(action.get("projectSlug") or snapshot.get("active_project_slug") or "").strip()
        seed = _json_sha256({"projectSlug": project_slug, "signature": signature, "createdAt": utc_now()})[:8]
        now = datetime.now(timezone.utc)
        incident_id = "OBS-" + now.strftime("%Y%m%d-%H%M%S") + f"-{seed}"
        deadline_at = datetime.fromtimestamp(
            now.timestamp() + max(1.0, float(self.config.max_incident_runtime_seconds)),
            timezone.utc,
        ).isoformat().replace("+00:00", "Z")
        return {
            "schemaVersion": 1,
            "incidentId": incident_id,
            "projectSlug": project_slug,
            "trigger": str((self.context.recent_external_event or {}).get("op") or "observer_tick"),
            "status": "open",
            "phase": "inspecting",
            "createdAt": now.isoformat().replace("+00:00", "Z"),
            "updatedAt": now.isoformat().replace("+00:00", "Z"),
            "deadlineAt": deadline_at,
            "budgets": {
                "maxRuntimeSeconds": self.config.max_incident_runtime_seconds,
                "maxTicks": self.config.max_incident_ticks,
                "maxRepeatedEvents": self.config.max_repeated_events,
                "cooldownSeconds": self.config.incident_cooldown_seconds,
            },
            "counters": {"ticks": 0, "repeatedEvents": 0, "timeouts": 0},
            "fingerprintsSeen": {},
            "rootCause": _root_cause_for_state(state),
            "evidencePaths": [],
            "proposedActions": [],
            "stopReason": "",
            "lastSignature": signature,
        }

    def _ensure_incident(self, snapshot: dict[str, Any], state: str, action: dict[str, Any], signature: str, now: float) -> dict[str, Any] | None:
        if state == "idle":
            return None
        incident = self.context.incident
        if isinstance(incident, dict) and str(incident.get("status") or "") not in OBSERVER_TERMINAL_STATUSES:
            return incident
        self.context.incident = self._new_incident(snapshot, state, action, signature)
        self.context.incident_started_at = now
        self._persist_incident()
        return self.context.incident

    def _close_incident(self, status: str, stop_reason: str, signature: str | None = None) -> dict[str, Any] | None:
        incident = self.context.incident
        if not isinstance(incident, dict):
            return None
        incident["status"] = status
        incident["phase"] = status
        incident["stopReason"] = stop_reason
        incident["updatedAt"] = utc_now()
        if signature:
            incident["lastSignature"] = signature
            self.context.signature_cooldowns[signature] = time.monotonic() + max(0.0, float(self.config.incident_cooldown_seconds))
        self._persist_incident()
        return incident

    def _signature_in_cooldown(self, signature: str, now: float) -> bool:
        expiry = self.context.signature_cooldowns.get(signature)
        if expiry is None:
            return False
        if now >= expiry:
            self.context.signature_cooldowns.pop(signature, None)
            return False
        return True

    def _incident_budget_expired(self, now: float) -> str:
        incident = self.context.incident
        if not isinstance(incident, dict) or str(incident.get("status") or "") in OBSERVER_TERMINAL_STATUSES:
            return ""
        counters = incident.get("counters") if isinstance(incident.get("counters"), dict) else {}
        if int(counters.get("ticks") or 0) >= max(1, int(self.config.max_incident_ticks)):
            return "max_ticks"
        if (now - self.context.incident_started_at) >= max(1.0, float(self.config.max_incident_runtime_seconds)):
            return "max_runtime_seconds"
        return ""

    def _record_incident_emit(self, signature: str, event: dict[str, Any]) -> None:
        incident = self.context.incident
        if not isinstance(incident, dict):
            return
        counters = incident.get("counters") if isinstance(incident.get("counters"), dict) else {}
        counters["ticks"] = int(counters.get("ticks") or 0) + 1
        incident["counters"] = counters
        fingerprints = incident.get("fingerprintsSeen") if isinstance(incident.get("fingerprintsSeen"), dict) else {}
        fingerprints[signature] = int(fingerprints.get(signature) or 0) + 1
        incident["fingerprintsSeen"] = fingerprints
        incident["rootCause"] = _root_cause_for_state(str(event.get("state") or ""))
        incident["proposedActions"] = event.get("proposedActions") or []
        incident["updatedAt"] = str(event.get("timestamp") or utc_now())
        incident["lastSignature"] = signature
        event["incidentId"] = incident.get("incidentId")
        event["incidentStatus"] = incident.get("status")
        event["incident"] = self._incident_status()
        self._persist_incident()

    def _terminal_event(self, snapshot: dict[str, Any], previous_state: str, status: str, stop_reason: str, signature: str) -> dict[str, Any]:
        incident = self._close_incident(status, stop_reason, signature) or {}
        findings_report = persist_observer_findings(snapshot)
        findings_summary = findings_report.get("summary") if isinstance(findings_report, dict) else {}
        return {
            "type": "observer_action",
            "op": "observer_action",
            "timestamp": utc_now(),
            "source": "observer_plane",
            "state": status,
            "previousState": previous_state,
            "behavior": "incident_closed",
            "action": "wait_human" if status == "waiting_human" else "close_incident",
            "phase": "observer:incident-closed",
            "message": "Observer detuvo el incidente: dejo evidencia y no repetira el mismo barrido.",
            "reason": stop_reason,
            "status": status,
            "projectSlug": incident.get("projectSlug") or snapshot.get("active_project_slug"),
            "uiAction": {"type": "show-observer-summary", "targetId": "observer-panel"},
            "evidence": {"stopReason": stop_reason, "incidentId": incident.get("incidentId")},
            "proposedActions": [],
            "snapshotSummary": {
                "nodeCount": len(_graph_nodes(snapshot)),
                "edgeCount": len(_graph_edges(snapshot)),
                "findingCount": len(_lint_findings(snapshot)),
                "integrityFindingCount": len(_integrity_findings(snapshot)),
                "observerFindingCount": int((findings_summary or {}).get("activeFindings") or 0),
                "observationScore": int((findings_summary or {}).get("observationScore") or 0),
                "activeSessionCount": len(_active_sessions(snapshot)),
            },
            "stopReason": stop_reason,
            "incidentId": incident.get("incidentId"),
            "incidentStatus": status,
            "incident": self._incident_status(),
        }

    def record_external_event(self, payload: dict[str, Any]) -> None:
        if isinstance(payload, dict):
            self.context.recent_external_event = dict(payload)

    def update_behavior_tree(self, behavior_tree: dict[str, Any]) -> dict[str, Any]:
        next_tree = self.behavior_tree.set_behavior_tree(behavior_tree)
        if self.behavior_path is not None:
            write_json(self.behavior_path, next_tree)
        return next_tree

    def status(self) -> dict[str, Any]:
        snapshot = self.snapshot_provider()
        snapshot = _filter_snapshot_to_active_project(snapshot if isinstance(snapshot, dict) else {})
        active_project = str(snapshot.get("active_project_slug") or "").strip()
        return {
            "enabled": self.enabled,
            "state": self.context.state,
            "tickCount": self.context.tick_count,
            "behaviorTree": self.behavior_tree.to_dict(),
            "activeProjectSlug": active_project,
            "memory": self.memory.summary(active_project),
            "timeline": self.memory.timeline(active_project),
            "incident": self._incident_status(),
        }

    def observe_once(self, *, force: bool = False) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        snapshot = self.snapshot_provider()
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        snapshot = _filter_snapshot_to_active_project(snapshot)
        previous_state = self.context.state
        next_state = self.state_machine.next_state(snapshot, self.context)
        if next_state != previous_state:
            self.context.state = next_state
            self.context.state_entered_at = time.monotonic()

        action = self.behavior_tree.choose_action(next_state, snapshot, self.context)
        signature = _observer_signature(action, next_state)
        now = time.monotonic()
        if self._signature_in_cooldown(signature, now):
            return None

        incident = self._ensure_incident(snapshot, next_state, action, signature, now)
        budget_reason = self._incident_budget_expired(now)
        if budget_reason:
            event = self._terminal_event(snapshot, previous_state, "expired", budget_reason, signature)
            self.memory.remember_event(event)
            event["memorySummary"] = self.memory.summary()
            self.context.last_signature = signature
            self.context.last_event_at = now
            if self.event_handler is not None:
                self.event_handler(event)
            return event

        if isinstance(incident, dict):
            fingerprints = incident.get("fingerprintsSeen") if isinstance(incident.get("fingerprintsSeen"), dict) else {}
            if int(fingerprints.get(signature) or 0) >= max(1, int(self.config.max_repeated_events)):
                counters = incident.get("counters") if isinstance(incident.get("counters"), dict) else {}
                counters["repeatedEvents"] = int(counters.get("repeatedEvents") or 0) + 1
                incident["counters"] = counters
                event = self._terminal_event(snapshot, previous_state, "waiting_human", "repeated_finding_suppressed", signature)
                self.memory.remember_event(event)
                event["memorySummary"] = self.memory.summary()
                self.context.last_signature = signature
                self.context.last_event_at = now
                if self.event_handler is not None:
                    self.event_handler(event)
                return event

        repeated_signature = signature == self.context.last_signature
        min_interval = self.config.idle_emit_interval_seconds if next_state == "idle" or repeated_signature else self.config.min_emit_interval_seconds
        should_emit = force or not repeated_signature or (now - self.context.last_event_at) >= min_interval
        self.context.tick_count += 1
        if not should_emit:
            return None

        findings_report = persist_observer_findings(snapshot)
        findings_summary = findings_report.get("summary") if isinstance(findings_report, dict) else {}
        event = {
            "type": "observer_action",
            "op": "observer_action",
            "timestamp": utc_now(),
            "source": "observer_plane",
            "state": next_state,
            "previousState": previous_state,
            "behavior": action.get("behavior"),
            "action": action.get("action"),
            "phase": action.get("phase"),
            "message": action.get("message"),
            "reason": action.get("reason"),
            "status": "active" if next_state != "idle" else "idle",
            "projectSlug": action.get("projectSlug"),
            "relativePath": action.get("relativePath"),
            "focusPath": action.get("focusPath"),
            "focusNodeId": action.get("focusNodeId"),
            "stepId": action.get("stepId"),
            "uiAction": action.get("uiAction") or {},
            "evidence": action.get("evidence") or {},
            "proposedActions": action.get("proposedActions") or [],
            "snapshotSummary": {
                "nodeCount": len(_graph_nodes(snapshot)),
                "edgeCount": len(_graph_edges(snapshot)),
                "findingCount": len(_lint_findings(snapshot)),
                "integrityFindingCount": len(_integrity_findings(snapshot)),
                "observerFindingCount": int(findings_summary.get("activeFindings") or 0),
                "observationScore": int(findings_summary.get("observationScore") or 0),
                "activeSessionCount": len(_active_sessions(snapshot)),
            },
        }
        if findings_summary:
            event["observerFindingsSummary"] = findings_summary
        self._record_incident_emit(signature, event)
        self.memory.remember_event(event)
        event["memorySummary"] = self.memory.summary()
        self.context.last_signature = signature
        self.context.last_event_at = now
        if self.event_handler is not None:
            self.event_handler(event)
        return event

    def run_forever(self, stop_event: Any = None, sleep_fn: Callable[[float], None] = time.sleep) -> None:
        if self._running:
            return
        self._running = True
        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    return
                self.observe_once()
                sleep_fn(max(0.25, self.config.poll_seconds))
        finally:
            self._running = False
