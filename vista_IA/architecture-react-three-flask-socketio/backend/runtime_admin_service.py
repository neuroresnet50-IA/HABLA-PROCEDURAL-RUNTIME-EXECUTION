from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List


class RuntimeAdminService:
    def __init__(
        self,
        *,
        agent_runtime: Any,
        projects_root_provider: Callable[[], Path],
        observer_memory_file: Path,
        observer_timeline_file: Path,
        email_command_root: Path,
        save_analysis_state: Callable[[Dict[str, Any]], None],
        create_blank_view_graph: Callable[[], Dict[str, Any]],
        save_graph_state: Callable[[Dict[str, Any]], None],
        normalize_graph: Callable[[Dict[str, Any]], Dict[str, Any]],
        observer_plane_provider: Callable[[], Any],
        socketio: Any,
    ) -> None:
        self.agent_runtime = agent_runtime
        self.projects_root_provider = projects_root_provider
        self.observer_memory_file = observer_memory_file
        self.observer_timeline_file = observer_timeline_file
        self.email_command_root = email_command_root
        self.save_analysis_state = save_analysis_state
        self.create_blank_view_graph = create_blank_view_graph
        self.save_graph_state = save_graph_state
        self.normalize_graph = normalize_graph
        self.observer_plane_provider = observer_plane_provider
        self.socketio = socketio

    @staticmethod
    def remove_children(path: Path) -> int:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return 0
        removed = 0
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)
            removed += 1
        return removed

    @staticmethod
    def remove_existing_files(paths: List[Path]) -> int:
        removed = 0
        for path in paths:
            try:
                if path.exists() and path.is_file():
                    path.unlink()
                    removed += 1
            except OSError:
                continue
        return removed

    def clear_workspace_state(self) -> Dict[str, Any]:
        active_statuses = {"queued", "starting", "running"}
        stopped_sessions: List[str] = []
        for session in self.agent_runtime.list_sessions():
            session_id = str(session.get("sessionId") or "")
            if session_id and str(session.get("status") or "").lower() in active_statuses:
                self.agent_runtime.stop_session(session_id)
                stopped_sessions.append(session_id)

        if hasattr(self.agent_runtime, "lock") and hasattr(self.agent_runtime, "sessions"):
            with self.agent_runtime.lock:  # type: ignore[attr-defined]
                self.agent_runtime.sessions.clear()  # type: ignore[attr-defined]

        removed_projects = self.remove_children(self.projects_root_provider())
        self.save_analysis_state({"analyses": []})
        blank_graph = self.create_blank_view_graph()
        self.save_graph_state(blank_graph)

        removed_runtime_files = self.remove_existing_files(
            [
                self.observer_memory_file,
                self.observer_timeline_file,
                self.email_command_root / "commands.json",
                self.email_command_root / "events.jsonl",
                self.email_command_root / "state.json",
            ]
        )
        try:
            observer_plane = self.observer_plane_provider()
            observer_plane.memory.data = observer_plane.memory._load_memory()  # type: ignore[attr-defined]
            observer_plane.context.recent_external_event = None
            observer_plane.context.last_signature = ""
            observer_plane.context.tick_count = 0
        except Exception:
            pass

        projects = self.agent_runtime.list_projects()
        self.socketio.emit("agent:projects", {"projects": projects})
        self.socketio.emit("reverse:sessions", {"sessions": []})
        self.socketio.emit("architecture:update", self.normalize_graph(blank_graph))
        self.socketio.emit(
            "agent:visual",
            {
                "op": "workspace_cleaned",
                "phase": "cleanup",
                "status": "completed",
                "message": "Workspace blanqueado con autorizacion HABLA.",
            },
        )
        return {
            "ok": True,
            "stoppedSessions": stopped_sessions,
            "removedProjects": removed_projects,
            "removedRuntimeFiles": removed_runtime_files,
            "projects": projects,
            "graph": self.normalize_graph(blank_graph),
        }
