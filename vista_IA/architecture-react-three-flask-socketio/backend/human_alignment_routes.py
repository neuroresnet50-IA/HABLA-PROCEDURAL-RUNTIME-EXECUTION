from __future__ import annotations

from typing import Any, Callable, Dict

from flask import jsonify, request

from human_alignment_review import (
    TECH_STACK_OPTIONS,
    create_human_alignment_review,
    list_human_alignment_reviews,
    submit_human_alignment_feedback,
)


def register_human_alignment_routes(
    app: Any,
    *,
    resolve_editor_project: Callable[[str], tuple[str, Any] | None],
    build_editor_lock_state: Callable[[str, Any], Dict[str, Any]],
    socketio: Any,
    agent_runtime: Any,
) -> None:
    @app.get("/api/projects/<project_id>/human-alignment-review")
    def get_project_human_alignment_review(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        runtime_dir = project_dir / "runtime"
        reviews = list_human_alignment_reviews(runtime_dir)
        return jsonify(
            {
                "ok": True,
                "projectId": project_slug,
                "reviews": reviews,
                "latestReview": reviews[-1] if reviews else None,
                "techStackOptions": TECH_STACK_OPTIONS,
                "lock": build_editor_lock_state(project_slug, project_dir),
            }
        )

    @app.post("/api/projects/<project_id>/human-alignment-review")
    def create_project_human_alignment_review(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        payload = request.get_json(silent=True) or {}
        try:
            result = create_human_alignment_review(
                project_root=project_dir,
                runtime_dir=project_dir / "runtime",
                source=str(payload.get("source") or "manual"),
                trigger=str(payload.get("trigger") or "manual_human_alignment_review"),
                reason=str(payload.get("reason") or "Revision de alineacion humana solicitada."),
                task_id=str(payload.get("taskId") or payload.get("task_id") or ""),
                session_id=str(payload.get("sessionId") or payload.get("session_id") or ""),
                dedupe=bool(payload.get("dedupe", True)),
            )
        except Exception as error:
            return jsonify({"ok": False, "error": "human_alignment_review_failed", "message": str(error)}), 500

        socketio.emit(
            "agent:visual",
            {
                "op": "human_alignment_review_created",
                "projectId": project_slug,
                "review": result.get("review"),
                "created": result.get("created"),
                "message": "HAR creado: esperando preferencias humanas antes de tocar codigo.",
            },
        )
        socketio.emit("agent:projects", {"projects": agent_runtime.list_projects()})
        return jsonify({"ok": True, "projectId": project_slug, **result})

    @app.post("/api/projects/<project_id>/human-alignment-review/<review_id>/feedback")
    def submit_project_human_alignment_feedback(project_id: str, review_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        lock_state = build_editor_lock_state(project_slug, project_dir)
        if lock_state.get("locked"):
            return jsonify({"ok": False, "error": "project_locked", "lock": lock_state}), 423

        payload = request.get_json(silent=True) or {}
        feedback = str(payload.get("feedback") or "").strip()
        if not feedback and not payload.get("requestedChanges"):
            return jsonify({"ok": False, "error": "missing_feedback"}), 400
        try:
            result = submit_human_alignment_feedback(
                project_root=project_dir,
                runtime_dir=project_dir / "runtime",
                review_id=review_id,
                feedback=feedback,
                requested_changes=payload.get("requestedChanges") or payload.get("requested_changes"),
                selected_stack_preferences=payload.get("selectedStackPreferences")
                or payload.get("selected_stack_preferences"),
            )
        except ValueError as error:
            return jsonify({"ok": False, "error": str(error)}), 404
        except Exception as error:
            return jsonify({"ok": False, "error": "human_alignment_feedback_failed", "message": str(error)}), 500

        socketio.emit(
            "agent:visual",
            {
                "op": "human_alignment_feedback_submitted",
                "projectId": project_slug,
                "review": result.get("review"),
                "tasks": result.get("tasks"),
                "message": "Feedback HAR convertido en tareas priorizadas.",
            },
        )
        socketio.emit("agent:projects", {"projects": agent_runtime.list_projects()})
        return jsonify({"ok": True, "projectId": project_slug, **result})
