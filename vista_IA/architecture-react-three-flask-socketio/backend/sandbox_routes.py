from __future__ import annotations

from typing import Any, Callable, Dict, List

from flask import jsonify


def register_sandbox_routes(
    app: Any,
    *,
    resolve_editor_project: Callable[[str], tuple[str, Any] | None],
    refresh_sandbox_state: Callable[[str, Any], Dict[str, Any]],
    start_project_sandbox: Callable[[str, Any], Dict[str, Any]],
    terminate_sandbox_process: Callable[..., Dict[str, Any]],
    sandbox_log_tail: Callable[[Any, int], List[str]],
    socketio: Any,
) -> None:
    @app.get("/api/projects/<project_id>/sandbox")
    def get_project_sandbox(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        state = refresh_sandbox_state(project_slug, project_dir)
        return jsonify({"ok": True, "projectId": project_slug, "sandbox": state, "logs": sandbox_log_tail(project_dir, 40)})

    @app.post("/api/projects/<project_id>/sandbox/start")
    def start_project_sandbox_endpoint(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        try:
            state = start_project_sandbox(project_slug, project_dir)
        except RuntimeError as error:
            return jsonify({"ok": False, "error": str(error)}), 400
        except OSError as error:
            return jsonify({"ok": False, "error": "sandbox_start_failed", "message": str(error)}), 500

        socketio.emit(
            "agent:visual",
            {
                "op": "sandbox_started",
                "projectSlug": project_slug,
                "phase": "runtime-sandbox",
                "status": state.get("status"),
                "message": f"Sandbox runtime activo en {state.get('url')}",
                "url": state.get("url"),
                "pid": state.get("pid"),
                "port": state.get("port"),
            },
        )
        return jsonify({"ok": True, "projectId": project_slug, "sandbox": state, "logs": sandbox_log_tail(project_dir, 40)})

    @app.post("/api/projects/<project_id>/sandbox/stop")
    def stop_project_sandbox_endpoint(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        state = terminate_sandbox_process(project_slug, project_dir, reason="human_stop")
        socketio.emit(
            "agent:visual",
            {
                "op": "sandbox_stopped",
                "projectSlug": project_slug,
                "phase": "runtime-sandbox",
                "status": state.get("status"),
                "message": "Sandbox runtime detenido.",
                "pid": state.get("pid"),
                "port": state.get("port"),
            },
        )
        return jsonify({"ok": True, "projectId": project_slug, "sandbox": state, "logs": sandbox_log_tail(project_dir, 40)})
