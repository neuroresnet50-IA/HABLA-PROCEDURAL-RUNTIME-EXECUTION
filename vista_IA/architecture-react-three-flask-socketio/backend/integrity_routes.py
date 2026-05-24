from __future__ import annotations

import json
from typing import Any, Callable, Dict

from flask import jsonify, request


def register_integrity_routes(
    app: Any,
    *,
    resolve_editor_project: Callable[[str], tuple[str, Any] | None],
    build_editor_lock_state: Callable[[str, Any], Dict[str, Any]],
    observe_with_tool_event: Callable[..., Dict[str, Any] | None],
    runtime_action_lock: Callable[[Dict[str, Any], str], Any],
    code_scanner_locks: Dict[str, Any],
    integrity_action_locks: Dict[str, Any],
    load_json_file: Callable[[Any, Any], Any],
    build_code_scanner_report: Callable[[str, Any], Dict[str, Any]],
    persist_code_scanner_report: Callable[[Any, Dict[str, Any]], Dict[str, str]],
    build_agent_file_manifest: Callable[..., Dict[str, Any]],
    persist_agent_file_manifest: Callable[[Any, Dict[str, Any]], Any],
    file_integrity_report_path: Callable[[Any], Any],
    observer_findings_report_path: Callable[[Any], Any],
    frozen_sniper_report_path: Callable[[Any], Any],
    build_file_integrity_report: Callable[..., Dict[str, Any]],
    build_frozen_sniper_recovery: Callable[..., Dict[str, Any]],
    build_observer_project_runtime_snapshot: Callable[[str], Dict[str, Any]],
    build_observer_findings_report: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]],
    socketio: Any,
    code_scanner_report_name: str,
    agent_file_manifest_name: str,
    file_integrity_report_name: str,
    frozen_sniper_report_name: str,
    frozen_sniper_confirmation: str,
) -> None:
    @app.post("/api/projects/<project_id>/code-scanner")
    def run_project_code_scanner(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        observer_event = observe_with_tool_event(
            "scanner_requested",
            project_slug=project_slug,
            reason="Scanner solicitado: Observer coordina la revision como herramienta.",
            persistent=False,
        )
        action_lock = runtime_action_lock(code_scanner_locks, project_slug)
        if not action_lock.acquire(blocking=False):
            existing_report = load_json_file(project_dir / "runtime" / "artifacts" / code_scanner_report_name, {})
            return (
                jsonify(
                    {
                        "ok": True,
                        "busy": True,
                        "error": "code_scanner_busy",
                        "message": "Scanner final ya esta en ejecucion para este proyecto.",
                        "projectId": project_slug,
                        "report": existing_report if isinstance(existing_report, dict) else {},
                    }
                ),
                202,
            )
        lock_state = build_editor_lock_state(project_slug, project_dir)
        try:
            if lock_state.get("locked"):
                return jsonify({"ok": False, "error": "project_locked", "lock": lock_state}), 423
            report = build_code_scanner_report(project_slug, project_dir)
            paths = persist_code_scanner_report(project_dir, report)
            observer_event = observe_with_tool_event(
                "scanner_completed",
                project_slug=project_slug,
                reason="Scanner completo: Observer revisa la evidencia generada.",
                persistent=False,
            ) or observer_event
        except OSError as error:
            return jsonify({"ok": False, "error": "scanner_persist_failed", "message": str(error)}), 500
        finally:
            action_lock.release()

        socketio.emit(
            "agent:visual",
            {
                "op": "code_scanner_complete",
                "projectSlug": project_slug,
                "message": "Scanner final aprobado." if report["validation"]["passed"] else "Scanner final bloqueado; revisa blockers.",
                "phase": "final-code-scanner",
                "status": "passed" if report["validation"]["passed"] else "blocked",
                "relativePath": f"runtime/artifacts/{code_scanner_report_name}",
            },
        )
        return jsonify(
            {
                "ok": True,
                "projectId": project_slug,
                "lock": lock_state,
                "report": report,
                "observerEvent": observer_event,
                **paths,
            }
        )

    @app.get("/api/projects/<project_id>/integrity/report")
    def get_project_integrity_report(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        report = load_json_file(file_integrity_report_path(project_dir), {})
        if not isinstance(report, dict) or not report:
            report = build_file_integrity_report(project_slug, project_dir, persist=False)
        return jsonify({"ok": True, "projectId": project_slug, "report": report})

    @app.get("/api/projects/<project_id>/observer-findings")
    def get_project_observer_findings(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        report_path = observer_findings_report_path(project_dir)
        existing_report = load_json_file(report_path, {})
        runtime_snapshot = build_observer_project_runtime_snapshot(project_slug)
        snapshot = {
            "graph": {"nodes": [], "edges": []},
            "lint": {"findings": []},
            "sessions": [],
            "active_project_slug": project_slug,
            "project_runtime": runtime_snapshot,
        }
        report = build_observer_findings_report(snapshot, existing_report if isinstance(existing_report, dict) else {})
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return jsonify({"ok": True, "projectId": project_slug, "report": report, "reportPath": str(report_path)})

    @app.post("/api/projects/<project_id>/integrity/scan")
    def scan_project_integrity(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        observer_event = observe_with_tool_event(
            "integrity_scan_requested",
            project_slug=project_slug,
            reason="Scan de integridad solicitado: Observer administra la revision de evidencia.",
            persistent=False,
        )
        action_lock = runtime_action_lock(integrity_action_locks, project_slug)
        if not action_lock.acquire(blocking=False):
            existing_report = load_json_file(file_integrity_report_path(project_dir), {})
            return (
                jsonify(
                    {
                        "ok": True,
                        "busy": True,
                        "error": "integrity_scan_busy",
                        "message": "Observer ya esta verificando integridad para este proyecto.",
                        "projectId": project_slug,
                        "report": existing_report if isinstance(existing_report, dict) else {},
                        "reportPath": str(file_integrity_report_path(project_dir)),
                    }
                ),
                202,
            )
        try:
            report = build_file_integrity_report(project_slug, project_dir, persist=True)
            observer_event = observe_with_tool_event(
                "integrity_scan_completed",
                project_slug=project_slug,
                reason="Scan de integridad completo: Observer revisa hallazgos generados.",
                persistent=False,
            ) or observer_event
        finally:
            action_lock.release()
        socketio.emit(
            "agent:visual",
            {
                "op": "file_integrity_scan_complete",
                "projectSlug": project_slug,
                "phase": "observer:file-integrity",
                "status": "passed" if report.get("validation", {}).get("passed") else "warning",
                "message": (
                    "Observer no detecto cambios externos."
                    if report.get("validation", {}).get("passed")
                    else f"Observer detecto {report.get('summary', {}).get('totalFindings', 0)} cambio(s) externos."
                ),
                "relativePath": f"runtime/artifacts/{file_integrity_report_name}",
                "report": report,
            },
        )
        return jsonify(
            {
                "ok": True,
                "projectId": project_slug,
                "report": report,
                "reportPath": str(file_integrity_report_path(project_dir)),
                "observerEvent": observer_event,
            }
        )

    @app.post("/api/projects/<project_id>/integrity/baseline")
    def accept_project_integrity_baseline(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        action_lock = runtime_action_lock(integrity_action_locks, project_slug)
        if not action_lock.acquire(blocking=False):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "integrity_action_busy",
                        "message": "Hay una accion de integridad activa para este proyecto.",
                    }
                ),
                409,
            )
        lock_state = build_editor_lock_state(project_slug, project_dir)
        try:
            if lock_state.get("locked"):
                return jsonify({"ok": False, "error": "project_locked", "lock": lock_state}), 423
            scanner_report = build_code_scanner_report(project_slug, project_dir)
            if not scanner_report.get("validation", {}).get("passed"):
                return jsonify({"ok": False, "error": "baseline_scanner_failed", "report": scanner_report}), 400
            manifest = build_agent_file_manifest(
                project_slug,
                scanner_report,
                project_dir=project_dir,
                source="human_accepted_integrity_baseline",
            )
            manifest_path = persist_agent_file_manifest(project_dir, manifest)
            integrity_report = build_file_integrity_report(project_slug, project_dir, persist=True)
        finally:
            action_lock.release()
        socketio.emit(
            "agent:visual",
            {
                "op": "file_integrity_baseline_accepted",
                "projectSlug": project_slug,
                "phase": "observer:file-integrity",
                "status": "baseline",
                "message": "Humano acepto nueva baseline de integridad del codigo.",
                "relativePath": f"runtime/artifacts/{agent_file_manifest_name}",
            },
        )
        return jsonify(
            {
                "ok": True,
                "projectId": project_slug,
                "manifest": manifest,
                "manifestPath": str(manifest_path),
                "report": integrity_report,
            }
        )

    @app.post("/api/projects/<project_id>/integrity/frozen-sniper")
    def run_project_frozen_sniper(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        observer_event = observe_with_tool_event(
            "frozen_sniper_requested",
            project_slug=project_slug,
            reason="Frozen Sniper solicitado: Observer coordina recuperacion con herramienta.",
            persistent=False,
        )
        action_lock = runtime_action_lock(integrity_action_locks, project_slug)
        if not action_lock.acquire(blocking=False):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "integrity_action_busy",
                        "message": "Hay una accion de integridad activa para este proyecto.",
                    }
                ),
                409,
            )
        lock_state = build_editor_lock_state(project_slug, project_dir)
        try:
            if lock_state.get("locked"):
                return jsonify({"ok": False, "error": "project_locked", "lock": lock_state}), 423
            payload = request.get_json(silent=True) or {}
            dry_run = bool(payload.get("dryRun"))
            confirmation = str(payload.get("confirm") or "")
            if not dry_run and confirmation != frozen_sniper_confirmation:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "frozen_sniper_confirmation_required",
                            "message": f"Confirma con {frozen_sniper_confirmation} para restaurar/quarantinar archivos.",
                            "requiredConfirmation": frozen_sniper_confirmation,
                        }
                    ),
                    409,
                )
            report = build_frozen_sniper_recovery(project_slug, project_dir, dry_run=dry_run)
            observer_event = observe_with_tool_event(
                "frozen_sniper_completed",
                project_slug=project_slug,
                reason="Frozen Sniper completo: Observer revisa la evidencia de recuperacion.",
                persistent=False,
            ) or observer_event
        finally:
            action_lock.release()
        socketio.emit(
            "agent:visual",
            {
                "op": "frozen_sniper_recovery_complete",
                "projectSlug": project_slug,
                "phase": "observer:frozen-sniper",
                "status": "passed" if report.get("validation", {}).get("passed") else "warning",
                "message": (
                    f"Frozen Sniper restauro {report.get('summary', {}).get('restoredFiles', 0)} archivo(s) "
                    f"y puso en cuarentena {report.get('summary', {}).get('quarantinedFiles', 0)}."
                ),
                "relativePath": f"runtime/artifacts/{frozen_sniper_report_name}",
                "report": report,
            },
        )
        return jsonify(
            {
                "ok": report.get("validation", {}).get("passed", False),
                "projectId": project_slug,
                "report": report,
                "reportPath": str(frozen_sniper_report_path(project_dir)),
                "observerEvent": observer_event,
                "afterIntegrityReport": report.get("afterIntegrityReport"),
            }
        )
