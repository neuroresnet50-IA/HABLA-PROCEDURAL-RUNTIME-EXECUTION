import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as backend_app
from project_graph import build_project_graph


class WorkspaceVisualSyncRegressionTest(unittest.TestCase):
    def test_project_graph_ignores_workspace_runtime_internal_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            project_dir = project_root / "workspace" / "projects" / "demo-app"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            (project_dir / "runtime" / "directives").mkdir(parents=True, exist_ok=True)
            (project_dir / ".vista").mkdir(parents=True, exist_ok=True)

            (project_dir / "frontend" / "app.js").write_text("export function initApp() {}\n", encoding="utf-8")
            (project_dir / "runtime" / "project_state.json").write_text('{"status":"running"}\n', encoding="utf-8")
            (project_dir / "runtime" / "directives" / "TASK-001.json").write_text('{"id":"TASK-001"}\n', encoding="utf-8")
            (project_dir / ".vista" / "events.jsonl").write_text('{"op":"sync_file"}\n', encoding="utf-8")

            graph = build_project_graph(project_root)
            node_paths = {node["path"] for node in graph["nodes"]}

            self.assertIn("workspace/projects/demo-app/frontend/app.js", node_paths)
            self.assertNotIn("workspace/projects/demo-app/runtime/project_state.json", node_paths)
            self.assertNotIn("workspace/projects/demo-app/runtime/directives/TASK-001.json", node_paths)
            self.assertNotIn("workspace/projects/demo-app/.vista/events.jsonl", node_paths)

    def test_project_graph_ignores_persisted_editor_state_and_truncates_large_code(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            backend_dir = project_root / "backend"
            backend_dir.mkdir(parents=True, exist_ok=True)
            (backend_dir / "editor_state.json").write_text('{"nodes": []}\n', encoding="utf-8")
            large_source = "PAYLOAD = '" + ("x" * 300000) + "'\n"
            (backend_dir / "large_module.py").write_text(large_source, encoding="utf-8")

            graph = build_project_graph(project_root)
            node_paths = {node["path"] for node in graph["nodes"]}
            self.assertNotIn("backend/editor_state.json", node_paths)

            large_node = next(node for node in graph["nodes"] if node["path"] == "backend/large_module.py")
            self.assertTrue(large_node["codeTruncated"])
            self.assertLess(len(large_node["code"]), len(large_source))

    def test_sync_workspace_file_infers_javascript_dependencies_and_flow(self) -> None:
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            source_dir = project_dir / "src"
            source_dir.mkdir(parents=True, exist_ok=True)

            (source_dir / "taskService.js").write_text("export function addTask() {}\n", encoding="utf-8")
            (source_dir / "storage.js").write_text("export function saveTasks() {}\n", encoding="utf-8")
            (source_dir / "ui.js").write_text("export function renderState() {}\n", encoding="utf-8")
            app_path = source_dir / "app.js"
            app_path.write_text(
                (
                    "import { addTask } from './taskService.js';\n"
                    "import { saveTasks } from './storage.js';\n"
                    "import { renderState } from './ui.js';\n\n"
                    "export function initApp() {}\n"
                    "function handleSubmit() {}\n"
                    "function persistSession() {}\n"
                    "function render() {}\n"
                ),
                encoding="utf-8",
            )

            graph = {"metadata": {}, "nodes": [], "edges": []}
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                graph = backend_app.sync_workspace_file(
                    graph,
                    {
                        "projectSlug": "demo-app",
                        "relativePath": "src/app.js",
                        "sourcePath": str(app_path),
                        "codeLanguage": "javascript",
                    },
                )

            node_paths = {node["path"] for node in graph["nodes"]}
            app_graph_path = backend_app.workspace_graph_path("demo-app", "src/app.js")
            task_graph_path = backend_app.workspace_graph_path("demo-app", "src/taskService.js")
            storage_graph_path = backend_app.workspace_graph_path("demo-app", "src/storage.js")
            ui_graph_path = backend_app.workspace_graph_path("demo-app", "src/ui.js")

            self.assertIn(app_graph_path, node_paths)
            self.assertIn(task_graph_path, node_paths)
            self.assertIn(storage_graph_path, node_paths)
            self.assertIn(ui_graph_path, node_paths)

            edge_pairs = {(edge["from"], edge["to"]) for edge in graph["edges"]}
            app_node_id = backend_app.node_id_for_path(app_graph_path)
            self.assertIn((app_node_id, backend_app.node_id_for_path(task_graph_path)), edge_pairs)
            self.assertIn((app_node_id, backend_app.node_id_for_path(storage_graph_path)), edge_pairs)
            self.assertIn((app_node_id, backend_app.node_id_for_path(ui_graph_path)), edge_pairs)

            app_node = next(node for node in graph["nodes"] if node["path"] == app_graph_path)
            algorithm = app_node["algorithm"]
            step_ids = {step["id"] for step in algorithm["steps"]}
            self.assertTrue({"init", "handle-submit", "persist-session", "render"}.issubset(step_ids))
            self.assertGreaterEqual(len(algorithm["edges"]), 3)

    def test_sync_workspace_file_infers_html_dependencies(self) -> None:
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            frontend_dir = project_dir / "frontend"
            source_dir = project_dir / "src"
            frontend_dir.mkdir(parents=True, exist_ok=True)
            source_dir.mkdir(parents=True, exist_ok=True)

            (frontend_dir / "styles.css").write_text("body { color: black; }\n", encoding="utf-8")
            (source_dir / "app.js").write_text("export function initApp() {}\n", encoding="utf-8")
            html_path = frontend_dir / "index.html"
            html_path.write_text(
                (
                    "<!doctype html>\n"
                    "<html>\n"
                    "  <head>\n"
                    "    <link rel=\"stylesheet\" href=\"./styles.css\" />\n"
                    "  </head>\n"
                    "  <body>\n"
                    "    <script type=\"module\" src=\"../src/app.js\"></script>\n"
                    "  </body>\n"
                    "</html>\n"
                ),
                encoding="utf-8",
            )

            graph = {"metadata": {}, "nodes": [], "edges": []}
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                graph = backend_app.sync_workspace_file(
                    graph,
                    {
                        "projectSlug": "demo-app",
                        "relativePath": "frontend/index.html",
                        "sourcePath": str(html_path),
                        "codeLanguage": "html",
                    },
                )

            edge_lookup = {
                (edge["from"], edge["to"]): edge["type"]
                for edge in graph["edges"]
            }
            html_graph_path = backend_app.workspace_graph_path("demo-app", "frontend/index.html")
            css_graph_path = backend_app.workspace_graph_path("demo-app", "frontend/styles.css")
            app_graph_path = backend_app.workspace_graph_path("demo-app", "src/app.js")

            self.assertEqual(
                edge_lookup[(backend_app.node_id_for_path(html_graph_path), backend_app.node_id_for_path(css_graph_path))],
                "style",
            )
            self.assertEqual(
                edge_lookup[(backend_app.node_id_for_path(html_graph_path), backend_app.node_id_for_path(app_graph_path))],
                "import",
            )


if __name__ == "__main__":
    unittest.main()
