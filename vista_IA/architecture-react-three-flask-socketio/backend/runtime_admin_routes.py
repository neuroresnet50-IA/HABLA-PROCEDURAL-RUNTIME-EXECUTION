from __future__ import annotations

from typing import Any, Callable, Dict

from flask import jsonify, request


def register_runtime_admin_routes(
    app: Any,
    *,
    default_reset_port: int,
    default_reset_host: str,
    clean_workspace_keyword: str,
    project_root: Any,
    workspace_root: Any,
    runtime_root: Any,
    normalize_runtime_mode: Callable[[Any], str],
    schedule_runtime_reset: Callable[..., Dict[str, Any]],
    decidir_y_justificar_blanqueo: Callable[..., Dict[str, Any]],
    record_blanqueo_decision: Callable[[Dict[str, Any], Any], Dict[str, Any]],
    create_blanqueo_backup: Callable[..., Dict[str, Any]],
    apply_selective_blanqueo: Callable[..., Dict[str, Any]],
    create_post_blanqueo_recovery: Callable[..., Dict[str, Any]],
    clear_runtime_workspace_state: Callable[[], Dict[str, Any]],
    agent_runtime: Any,
    socketio: Any,
) -> None:
    @app.post("/api/runtime/reset")
    def reset_runtime():
        payload = request.get_json(silent=True) or {}
        requested_port = int(payload.get("port") or default_reset_port)
        requested_host = str(payload.get("host") or default_reset_host).strip() or default_reset_host
        open_browser = bool(payload.get("openBrowser", True))
        reset_payload = schedule_runtime_reset(port=requested_port, host=requested_host, open_browser=open_browser)
        return jsonify({"ok": True, **reset_payload})

    @app.post("/api/runtime/clean-workspace")
    def clean_workspace():
        payload = request.get_json(silent=True) or {}
        if payload.get("confirmDeleteProjects") is not True:
            return jsonify({"ok": False, "error": "missing_delete_confirmation"}), 400
        if str(payload.get("authorizationKeyword") or "").strip() != clean_workspace_keyword:
            return jsonify({"ok": False, "error": "invalid_authorization_keyword"}), 400
        clean_scope = str(payload.get("cleanScope") or payload.get("scope") or "total").strip().lower()
        runtime_mode = normalize_runtime_mode(payload.get("runtimeMode") or payload.get("mode") or "build")
        audit_runtime_dir = project_root / "runtime"
        planned_backup_dir = project_root / "backups" / "blanqueo"
        decision = decidir_y_justificar_blanqueo(
            task_id=str(payload.get("taskId") or "MANUAL-BLANQUEO-WORKSPACE"),
            mode=runtime_mode,
            requested_scope=clean_scope,
            source=str(payload.get("source") or "human_button"),
            repair_attempts=int(payload.get("repairAttempts") or 0),
            compile_failed=bool(payload.get("compileFailed")),
            irrecoverable=bool(payload.get("irrecoverable")),
            selective_attempted=bool(payload.get("selectiveAttempted")),
            root_cause=str(payload.get("rootCause") or ""),
            attempted_repairs=payload.get("attemptedRepairs") or [],
            evidence=payload.get("evidence") or [],
            risk_of_not_cleaning=payload.get("riskOfNotCleaning") or [],
            expected_benefits=payload.get("expectedBenefits") or [],
            confirmation_phrase=str(payload.get("confirmationPhrase") or ""),
            planned_backup_dir=str(planned_backup_dir),
        )
        audit = record_blanqueo_decision(decision, audit_runtime_dir)
        if not decision.get("allowed"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "blanqueo_confirmation_required",
                        "decision": decision,
                        "audit": audit,
                        "decisionSummary": decision.get("summary_markdown", ""),
                    }
                ),
                409,
            )

        backup = create_blanqueo_backup(
            project_root=project_root,
            workspace_root=workspace_root,
            runtime_dirs=[runtime_root, audit_runtime_dir],
            backup_base=planned_backup_dir,
            decision=decision,
        )

        if decision.get("scope") == "selective":
            cleanup = apply_selective_blanqueo(workspace_root, runtime_dirs=[runtime_root])
            projects = agent_runtime.list_projects()
            socketio.emit(
                "agent:visual",
                {
                    "op": "workspace_cleaned",
                    "phase": "cleanup",
                    "status": "completed",
                    "message": "Blanqueo selectivo completado con backup y justificacion.",
                },
            )
            recovery = create_post_blanqueo_recovery(runtime_dir=audit_runtime_dir, decision=decision, backup=backup)
            return jsonify(
                {
                    "ok": True,
                    "scope": "selective",
                    "decision": decision,
                    "audit": audit,
                    "backup": backup,
                    "cleanup": cleanup,
                    "recovery": recovery,
                    "removedProjects": 0,
                    "projects": projects,
                }
            )

        cleanup = clear_runtime_workspace_state()
        recovery = create_post_blanqueo_recovery(runtime_dir=audit_runtime_dir, decision=decision, backup=backup)
        return jsonify(
            {
                "scope": "total",
                "decision": decision,
                "audit": audit,
                "backup": backup,
                "recovery": recovery,
                **cleanup,
            }
        )
