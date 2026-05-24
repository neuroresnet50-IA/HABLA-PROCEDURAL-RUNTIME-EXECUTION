from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List


class ObserverRuntimeFacade:
    def __init__(
        self,
        *,
        projects_root_provider: Callable[[], Path],
        workspace_project_dir: Callable[[str], Path],
        normalize_project_slug: Callable[[Any], str],
        normalize_graph: Callable[[Dict[str, Any]], Dict[str, Any]],
        load_default_graph: Callable[[], Dict[str, Any]],
        load_json_file: Callable[[Path, Any], Any],
        list_sessions: Callable[[], List[Dict[str, Any]]],
        lint_graph: Callable[..., Dict[str, Any]],
        merge_lint_report: Callable[..., Dict[str, Any]],
        build_integrity_report: Callable[..., Dict[str, Any]],
        project_root: Path,
        active_session_statuses: set[str],
        code_scanner_report_name: str,
        typewriter_report_name: str,
        agent_file_manifest_name: str,
        file_integrity_report_name: str,
        observer_findings_report_name: str,
        sandbox_state_name: str,
        now_provider: Callable[[], str],
    ) -> None:
        self.projects_root_provider = projects_root_provider
        self.workspace_project_dir = workspace_project_dir
        self.normalize_project_slug = normalize_project_slug
        self.normalize_graph = normalize_graph
        self.load_default_graph = load_default_graph
        self.load_json_file = load_json_file
        self.list_sessions = list_sessions
        self.lint_graph = lint_graph
        self.merge_lint_report = merge_lint_report
        self.build_integrity_report = build_integrity_report
        self.project_root = project_root
        self.active_session_statuses = active_session_statuses
        self.code_scanner_report_name = code_scanner_report_name
        self.typewriter_report_name = typewriter_report_name
        self.agent_file_manifest_name = agent_file_manifest_name
        self.file_integrity_report_name = file_integrity_report_name
        self.observer_findings_report_name = observer_findings_report_name
        self.sandbox_state_name = sandbox_state_name
        self.now = now_provider

    def latest_workspace_project_slug(self) -> str:
        candidates: List[tuple[int, float, str]] = []
        projects_root = self.projects_root_provider()
        if not projects_root.exists():
            return ""
        for project_dir in projects_root.iterdir():
            if not project_dir.is_dir():
                continue
            slug = project_dir.name
            state_path = project_dir / "runtime" / "project_state.json"
            status_rank = 0
            stamp_path = state_path if state_path.exists() else project_dir
            try:
                mtime = stamp_path.stat().st_mtime
            except OSError:
                mtime = 0.0
            if state_path.exists():
                try:
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    state = {}
                status = str(state.get("status") or "").lower()
                current_task_id = str(state.get("current_task_id") or "").strip()
                if status in {"queued", "starting", "running"} or current_task_id:
                    status_rank = 2
                elif status == "completed":
                    status_rank = 1
            candidates.append((status_rank, mtime, slug))
        if not candidates:
            return ""
        candidates.sort(reverse=True)
        return candidates[0][2]

    def active_project_slug(self, sessions: List[Dict[str, Any]], graph: Dict[str, Any]) -> str:
        for session in reversed(sessions):
            if str(session.get("status") or "").lower() in self.active_session_statuses and session.get("projectSlug"):
                return str(session.get("projectSlug"))
        persisted_slug = self.latest_workspace_project_slug()
        if persisted_slug:
            return persisted_slug
        for node in graph.get("nodes") or []:
            project_slug = str((node or {}).get("workspaceProject") or (node or {}).get("workspaceScene") or "")
            if project_slug:
                return project_slug
        return ""

    def build_project_runtime_snapshot(self, project_slug: str) -> Dict[str, Any]:
        normalized_slug = self.normalize_project_slug(project_slug)
        if not normalized_slug:
            return {}
        project_dir = self.workspace_project_dir(normalized_slug).resolve()
        projects_root = self.projects_root_provider().resolve()
        try:
            project_dir.relative_to(projects_root)
        except ValueError:
            return {"projectSlug": normalized_slug, "projectExists": False}
        if not project_dir.exists() or not project_dir.is_dir():
            return {"projectSlug": normalized_slug, "projectExists": False}

        runtime_dir = project_dir / "runtime"
        project_state_path = runtime_dir / "project_state.json"
        scanner_report_path = runtime_dir / "artifacts" / self.code_scanner_report_name
        typewriter_report_path = runtime_dir / "artifacts" / self.typewriter_report_name
        manifest_path = runtime_dir / "artifacts" / self.agent_file_manifest_name
        integrity_report_path = runtime_dir / "artifacts" / self.file_integrity_report_name
        observer_findings_path = runtime_dir / "artifacts" / self.observer_findings_report_name
        sandbox_path = runtime_dir / self.sandbox_state_name
        project_state = self.load_json_file(project_state_path, {})
        scanner_report = self.load_json_file(scanner_report_path, {})
        typewriter_report = self.load_json_file(typewriter_report_path, {})
        sandbox_state = self.load_json_file(sandbox_path, {})
        observer_findings = self.load_json_file(observer_findings_path, {})
        integrity_report = self.build_integrity_report(normalized_slug, project_dir, persist=False)
        return {
            "projectSlug": normalized_slug,
            "projectExists": True,
            "projectDir": str(project_dir),
            "runtimeDir": str(runtime_dir),
            "projectStatePath": str(project_state_path),
            "scannerReportPath": str(scanner_report_path),
            "typewriterReportPath": str(typewriter_report_path),
            "manifestPath": str(manifest_path),
            "integrityReportPath": str(integrity_report_path),
            "observerFindingsPath": str(observer_findings_path),
            "sandboxPath": str(sandbox_path),
            "projectStatus": project_state.get("status") if isinstance(project_state, dict) else "",
            "currentTaskId": project_state.get("current_task_id") if isinstance(project_state, dict) else "",
            "projectState": project_state if isinstance(project_state, dict) else {},
            "scannerReport": scanner_report if isinstance(scanner_report, dict) else {},
            "scannerReportExists": scanner_report_path.exists(),
            "typewriterReport": typewriter_report if isinstance(typewriter_report, dict) else {},
            "typewriterReportExists": typewriter_report_path.exists(),
            "manifestExists": manifest_path.exists(),
            "integrityReport": integrity_report,
            "integrityReportExists": integrity_report_path.exists(),
            "observerFindings": observer_findings if isinstance(observer_findings, dict) else {},
            "observerFindingsExists": observer_findings_path.exists(),
            "sandbox": sandbox_state if isinstance(sandbox_state, dict) else {},
            "sandboxExists": sandbox_path.exists(),
        }

    def build_snapshot(self) -> Dict[str, Any]:
        graph = self.normalize_graph(self.load_default_graph())
        sessions = self.list_sessions()
        active_project_slug = self.active_project_slug(sessions, graph)
        scene_filter = active_project_slug or None
        try:
            lint_report = self.lint_graph(graph, self.project_root, scene_filter=scene_filter)
            lint_report = self.merge_lint_report(lint_report, graph=graph, scene_filter=scene_filter)
        except Exception as error:
            lint_report = {
                "generatedAt": self.now(),
                "scope": {"scene": scene_filter or "", "label": "Observer"},
                "summary": {"error": 0, "warning": 1, "info": 0, "total": 1},
                "findings": [
                    {
                        "severity": "warning",
                        "code": "observer_lint_failed",
                        "message": f"Observer no pudo auditar mapa: {error}",
                    }
                ],
            }
        current_task_id = ""
        for session in reversed(sessions):
            if str(session.get("status") or "").lower() in self.active_session_statuses:
                current_task_id = str(session.get("currentTaskId") or session.get("currentTask") or "")
                break
        return {
            "graph": graph,
            "sessions": sessions,
            "lint": lint_report,
            "active_project_slug": active_project_slug,
            "current_task_id": current_task_id,
            "project_runtime": self.build_project_runtime_snapshot(active_project_slug) if active_project_slug else {},
        }
