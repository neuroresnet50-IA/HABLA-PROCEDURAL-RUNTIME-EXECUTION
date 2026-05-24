from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from flask import jsonify, request


def register_editor_routes(
    app: Any,
    *,
    resolve_editor_project: Callable[[str], tuple[str, Any] | None],
    build_editor_lock_state: Callable[[str, Any], Dict[str, Any]],
    list_editor_files: Callable[[Any], List[Dict[str, Any]]],
    resolve_editor_file: Callable[..., tuple[str, Any] | None],
    editor_file_payload: Callable[[Any, str, Any], Dict[str, Any]],
    editor_max_file_bytes: int,
    append_file_write_ledger: Callable[..., None],
    load_json_file: Callable[[Any, Any], Any],
    now_provider: Callable[[], str],
    normalize_graph: Callable[[Dict[str, Any]], Dict[str, Any]],
    load_default_graph: Callable[[], Dict[str, Any]],
    sync_workspace_file: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]],
    save_graph_state: Callable[[Dict[str, Any]], None],
    socketio: Any,
    workspace_graph_path: Callable[[str, Any], str],
    node_id_for_path: Callable[[str], str],
    detect_code_language: Callable[[str], str | None],
    build_agent_repair_requirement: Callable[..., str],
    suggested_repair_files: Callable[[str, Dict[str, Any]], List[str]],
    queue_agent_repair_task: Callable[..., Dict[str, Any]],
    agent_runtime: Any,
    sync_runtime_graph: Callable[..., Any],
    observer_plane_provider: Callable[[], Any],
) -> None:
    @app.get("/api/projects/<project_id>/files")
    def get_project_editor_files(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        lock_state = build_editor_lock_state(project_slug, project_dir)
        return jsonify(
            {
                "ok": True,
                "projectId": project_slug,
                "projectPath": str(project_dir),
                "lock": lock_state,
                "files": list_editor_files(project_dir),
            }
        )

    @app.get("/api/projects/<project_id>/file")
    def get_project_editor_file(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        resolved_file = resolve_editor_file(project_dir, request.args.get("path"))
        if resolved_file is None:
            return jsonify({"ok": False, "error": "file_not_found"}), 404
        relative_path, file_path = resolved_file
        if file_path.stat().st_size > editor_max_file_bytes:
            return jsonify({"ok": False, "error": "file_too_large"}), 413
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return jsonify({"ok": False, "error": "binary_or_unsupported_file"}), 415
        except OSError as error:
            return jsonify({"ok": False, "error": "file_read_failed", "message": str(error)}), 500

        return jsonify(
            {
                "ok": True,
                "projectId": project_slug,
                "lock": build_editor_lock_state(project_slug, project_dir),
                "file": {
                    **editor_file_payload(project_dir, relative_path, file_path),
                    "content": content,
                },
            }
        )

    @app.put("/api/projects/<project_id>/file")
    def save_project_editor_file(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        lock_state = build_editor_lock_state(project_slug, project_dir)
        if lock_state.get("locked"):
            return jsonify({"ok": False, "error": "project_locked", "lock": lock_state}), 423

        payload = request.get_json(silent=True) or {}
        resolved_file = resolve_editor_file(project_dir, payload.get("path"))
        if resolved_file is None:
            return jsonify({"ok": False, "error": "file_not_found"}), 404
        relative_path, file_path = resolved_file
        content = str(payload.get("content") if payload.get("content") is not None else "")
        if len(content.encode("utf-8")) > editor_max_file_bytes:
            return jsonify({"ok": False, "error": "file_too_large"}), 413

        previous_content = ""
        try:
            previous_content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        except (UnicodeDecodeError, OSError):
            previous_content = ""

        try:
            file_path.write_text(content, encoding="utf-8")
            append_file_write_ledger(
                project_dir,
                project_slug=project_slug,
                relative_path=relative_path,
                source="habla_code_editor",
                reason="human_save_from_code_workbench",
                before_content=previous_content,
                after_content=content,
            )
        except OSError as error:
            return jsonify({"ok": False, "error": "file_write_failed", "message": str(error)}), 500

        metadata_path = project_dir / ".agent-project.json"
        metadata = load_json_file(metadata_path, {})
        if isinstance(metadata, dict):
            metadata["updatedAt"] = now_provider()
            try:
                metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
            except OSError:
                pass

        graph = normalize_graph(load_default_graph())
        graph = sync_workspace_file(
            graph,
            {
                "projectSlug": project_slug,
                "relativePath": relative_path,
                "sourcePath": relative_path,
                "status": "modified",
                "codeLanguage": detect_code_language(relative_path) or "text",
                "description": "Archivo editado por humano desde Neuro LACE Runtime Code Editor.",
            },
        )
        save_graph_state(graph)
        socketio.emit("architecture:update", graph)
        focus_path = workspace_graph_path(project_slug, relative_path)
        socketio.emit(
            "agent:visual",
            {
                "op": "human_edit",
                "projectSlug": project_slug,
                "focusPath": focus_path,
                "focusNodeId": node_id_for_path(focus_path),
                "message": f"Edicion humana guardada en {relative_path}",
                "phase": "code-editor",
                "status": "modified",
            },
        )

        return jsonify(
            {
                "ok": True,
                "projectId": project_slug,
                "lock": build_editor_lock_state(project_slug, project_dir),
                "file": {
                    **editor_file_payload(project_dir, relative_path, file_path),
                    "content": content,
                },
            }
        )

    @app.post("/api/projects/<project_id>/repair")
    def start_project_repair(project_id: str):
        resolved = resolve_editor_project(project_id)
        if resolved is None:
            return jsonify({"ok": False, "error": "project_not_found"}), 404
        project_slug, project_dir = resolved
        lock_state = build_editor_lock_state(project_slug, project_dir)
        if lock_state.get("locked"):
            return jsonify({"ok": False, "error": "project_locked", "lock": lock_state}), 423

        payload = request.get_json(silent=True) or {}
        resolved_file = resolve_editor_file(project_dir, payload.get("path"))
        if resolved_file is None:
            return jsonify({"ok": False, "error": "file_not_found"}), 404
        relative_path, _file_path = resolved_file
        evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}
        issue = {
            "line": payload.get("line") or 1,
            "severity": payload.get("severity") or "warning",
            "code": payload.get("code") or "visual_issue",
            "message": payload.get("message") or "Hallazgo visual seleccionado desde el editor.",
            "hint": payload.get("hint") or "",
            "evidence": evidence,
        }
        extra_instruction = str(payload.get("instruction") or "").strip()
        requirement = build_agent_repair_requirement(
            project_slug=project_slug,
            relative_path=relative_path,
            issue=issue,
            extra_instruction=extra_instruction,
        )
        repair_files = suggested_repair_files(relative_path, issue)
        try:
            repair_task = queue_agent_repair_task(
                project_slug=project_slug,
                project_dir=project_dir,
                relative_path=relative_path,
                repair_files=repair_files,
                requirement=requirement,
            )
        except Exception as error:
            return jsonify({"ok": False, "error": "repair_task_queue_failed", "message": str(error)}), 500

        metadata = load_json_file(project_dir / ".agent-project.json", {})
        project_name = str(metadata.get("name") or project_slug) if isinstance(metadata, dict) else project_slug
        session = agent_runtime.start_session(
            requirement=requirement,
            project_name=project_name,
            project_slug=project_slug,
            bootstrap=False,
            ensure_new_project=False,
            mode="build",
        )
        projects = agent_runtime.list_projects()
        sync_runtime_graph(save_state=True)
        socketio.emit("agent:projects", {"projects": projects})
        focus_path = workspace_graph_path(project_slug, relative_path)
        repair_visual_payload = {
            "op": "repair_session_start",
            "sessionId": session.get("sessionId"),
            "projectSlug": project_slug,
            "relativePath": relative_path,
            "focusPath": focus_path,
            "focusNodeId": node_id_for_path(focus_path),
            "message": f"Worker de reparacion lanzado para {relative_path}",
            "phase": "repair",
            "status": "running",
        }
        socketio.emit("agent:visual", repair_visual_payload)
        observer_plane = observer_plane_provider()
        observer_plane.record_external_event(repair_visual_payload)
        observer_plane.observe_once(force=True)
        return jsonify(
            {
                "ok": True,
                "session": session,
                "projects": projects,
                "repairTask": repair_task,
                "repairFiles": repair_files,
            }
        )
