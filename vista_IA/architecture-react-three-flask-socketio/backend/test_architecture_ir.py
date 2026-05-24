import sys
from pathlib import Path
import unittest

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from architecture_ir import build_architecture_ir


class ArchitectureIRRegressionTest(unittest.TestCase):
    def test_build_architecture_ir_preserves_graph_and_adds_contract_fields(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Demo Agent",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-main",
                    "name": "main.py",
                    "path": "workspace/projects/demo-agent/src/main.py",
                    "workspaceProject": "demo-agent",
                    "workspaceScene": "demo-agent",
                    "layer": "backend",
                    "codeLanguage": "python",
                    "code": (
                        "def helper():\n"
                        "    return 1\n\n"
                        "def main():\n"
                        "    return helper()\n\n"
                        "class Service:\n"
                        "    def run(self):\n"
                        "        return self._private()\n\n"
                        "    def _private(self):\n"
                        "        return helper()\n"
                    ),
                    "algorithm": {"steps": [], "edges": []},
                },
                {
                    "id": "node-store",
                    "name": "store.json",
                    "path": "workspace/projects/demo-agent/backend/data/store.json",
                    "workspaceProject": "demo-agent",
                    "workspaceScene": "demo-agent",
                    "layer": "data",
                    "codeLanguage": "json",
                    "algorithm": {"steps": [], "edges": []},
                },
            ],
            "edges": [
                {
                    "id": "edge-main-store",
                    "from": "node-main",
                    "to": "node-store",
                    "type": "import",
                    "label": "lee estado",
                }
            ],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
            analysis_sessions=[{"id": "reverse-demo", "label": "Analisis demo", "createdAt": "2026-05-10T00:00:00+00:00"}],
            agent_sessions=[{"sessionId": "agent-1", "status": "running", "createdAt": "2026-05-10T00:00:00+00:00"}],
            issues=[
                {
                    "code": "python_relative_import_missing",
                    "severity": "error",
                    "path": "workspace/projects/demo-agent/src/main.py",
                    "nodeId": "node-main",
                    "line": 12,
                    "message": "Import no resuelto",
                    "hint": "corrige el import",
                }
            ],
        )

        self.assertEqual(ir["version"], "1.0")
        self.assertEqual(ir["project"]["id"], "project:demo-agent")
        self.assertEqual(len(ir["nodes"]), 2)
        self.assertEqual(len(ir["edges"]), 1)
        self.assertEqual(len(ir["issues"]), 1)
        self.assertEqual(len(ir["sessions"]), 2)
        self.assertEqual(len(ir["scenes"]), 1)
        self.assertGreaterEqual(ir["semanticGraph"]["metadata"]["nodeCount"], 5)
        self.assertGreaterEqual(ir["semanticGraph"]["metadata"]["edgeCount"], 5)

        main_node = next(node for node in ir["nodes"] if node["id"] == "node-main")
        store_node = next(node for node in ir["nodes"] if node["id"] == "node-store")
        edge = ir["edges"][0]
        issue = ir["issues"][0]
        semantic_nodes = ir["semanticGraph"]["nodes"]
        semantic_edges = ir["semanticGraph"]["edges"]

        self.assertEqual(main_node["nodeType"], "module")
        self.assertEqual(main_node["originType"], "agent")
        self.assertEqual(main_node["canonicalPath"], "workspace/projects/demo-agent/src/main.py")
        self.assertTrue(main_node["entryPoint"])
        self.assertEqual(store_node["nodeType"], "data_store")
        self.assertEqual(edge["edgeType"], "imports")
        self.assertEqual(issue["issueType"], "unresolved_import")
        self.assertEqual(issue["lineStart"], 12)
        self.assertTrue(any(node["nodeType"] == "function" and node["name"] == "helper" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "function" and node["name"] == "main" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "class" and node["name"] == "Service" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "method" and node["name"] == "Service.run" for node in semantic_nodes))
        self.assertTrue(any(edge["edgeType"] == "calls" for edge in semantic_edges))

    def test_build_architecture_ir_detects_python_routes_and_event_handlers(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Demo Backend",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-api",
                    "name": "api.py",
                    "path": "workspace/projects/demo-backend/backend/api.py",
                    "workspaceProject": "demo-backend",
                    "workspaceScene": "demo-backend",
                    "layer": "backend",
                    "codeLanguage": "python",
                    "code": (
                        "from flask import Flask\n"
                        "from flask_socketio import SocketIO\n\n"
                        "app = Flask(__name__)\n"
                        "socketio = SocketIO(app)\n\n"
                        "@app.get('/health')\n"
                        "def health():\n"
                        "    return 'ok'\n\n"
                        "@socketio.on('architecture:update')\n"
                        "def handle_update(payload):\n"
                        "    return payload\n\n"
                        "class Service:\n"
                        "    @socketio.on('service:refresh')\n"
                        "    def refresh(self, payload):\n"
                        "        return payload\n"
                    ),
                    "algorithm": {"steps": [], "edges": []},
                }
            ],
            "edges": [],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
        )

        semantic_nodes = ir["semanticGraph"]["nodes"]
        semantic_edges = ir["semanticGraph"]["edges"]

        self.assertTrue(any(node["nodeType"] == "route" and node["name"] == "GET /health" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "event_handler" and node["name"] == "architecture:update" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "event_handler" and node["name"] == "service:refresh" for node in semantic_nodes))
        self.assertTrue(any(edge["edgeType"] == "routes_to" for edge in semantic_edges))
        self.assertTrue(any(edge["edgeType"] == "handles" for edge in semantic_edges))

    def test_build_architecture_ir_links_python_inter_module_calls(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Demo Python Linked",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-main",
                    "name": "main.py",
                    "path": "workspace/projects/demo-python/backend/main.py",
                    "workspaceProject": "demo-python",
                    "workspaceScene": "demo-python",
                    "layer": "backend",
                    "codeLanguage": "python",
                    "code": (
                        "from .services.task_service import boot_task\n\n"
                        "def bootstrap():\n"
                        "    return boot_task()\n"
                    ),
                    "algorithm": {"steps": [], "edges": []},
                },
                {
                    "id": "node-task-service",
                    "name": "task_service.py",
                    "path": "workspace/projects/demo-python/backend/services/task_service.py",
                    "workspaceProject": "demo-python",
                    "workspaceScene": "demo-python",
                    "layer": "backend",
                    "codeLanguage": "python",
                    "code": "def boot_task():\n    return True\n",
                    "algorithm": {"steps": [], "edges": []},
                },
            ],
            "edges": [],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
        )

        semantic_nodes = ir["semanticGraph"]["nodes"]
        semantic_edges = ir["semanticGraph"]["edges"]
        node_ids = {node["name"]: node["id"] for node in semantic_nodes}

        self.assertTrue(
            any(
                edge["edgeType"] == "calls"
                and edge["from"] == node_ids["bootstrap"]
                and edge["to"] == node_ids["boot_task"]
                and edge["metadata"].get("interModule") is True
                for edge in semantic_edges
            )
        )

    def test_build_architecture_ir_reports_unresolved_javascript_imports(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Broken Frontend Import",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-main",
                    "name": "main.jsx",
                    "path": "workspace/projects/broken-frontend/frontend/src/main.jsx",
                    "workspaceProject": "broken-frontend",
                    "workspaceScene": "broken-frontend",
                    "layer": "frontend",
                    "codeLanguage": "jsx",
                    "code": (
                        "import MissingPanel from './MissingPanel.jsx';\n"
                        "export default function App() {\n"
                        "  return <MissingPanel />;\n"
                        "}\n"
                    ),
                    "algorithm": {"steps": [], "edges": []},
                }
            ],
            "edges": [],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
        )

        self.assertTrue(
            any(
                issue["issueType"] == "unresolved_import"
                and issue["metadata"].get("specifier") == "./MissingPanel.jsx"
                for issue in ir["issues"]
            )
        )
        self.assertTrue(
            any(
                issue["issueType"] == "unresolved_import"
                and issue["metadata"].get("specifier") == "./MissingPanel.jsx"
                for issue in ir["semanticGraph"]["issues"]
            )
        )

    def test_build_architecture_ir_reports_missing_python_symbols_in_resolved_modules(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Broken Python Symbol",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-main",
                    "name": "main.py",
                    "path": "workspace/projects/broken-python/backend/main.py",
                    "workspaceProject": "broken-python",
                    "workspaceScene": "broken-python",
                    "layer": "backend",
                    "codeLanguage": "python",
                    "code": (
                        "from .services.task_service import missing_task\n\n"
                        "def bootstrap():\n"
                        "    return missing_task()\n"
                    ),
                    "algorithm": {"steps": [], "edges": []},
                },
                {
                    "id": "node-task-service",
                    "name": "task_service.py",
                    "path": "workspace/projects/broken-python/backend/services/task_service.py",
                    "workspaceProject": "broken-python",
                    "workspaceScene": "broken-python",
                    "layer": "backend",
                    "codeLanguage": "python",
                    "code": "def boot_task():\n    return True\n",
                    "algorithm": {"steps": [], "edges": []},
                },
            ],
            "edges": [],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
        )

        self.assertTrue(
            any(
                issue["issueType"] == "type_resolution_failure"
                and issue["metadata"].get("importedName") == "missing_task"
                for issue in ir["issues"]
            )
        )
        self.assertTrue(
            any(
                issue["issueType"] == "type_resolution_failure"
                and issue["metadata"].get("importedName") == "missing_task"
                for issue in ir["semanticGraph"]["issues"]
            )
        )

    def test_build_architecture_ir_detects_javascript_roles(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Demo Frontend",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-ui",
                    "name": "client.js",
                    "path": "workspace/projects/demo-frontend/frontend/client.js",
                    "workspaceProject": "demo-frontend",
                    "workspaceScene": "demo-frontend",
                    "layer": "frontend",
                    "codeLanguage": "javascript",
                    "code": (
                        "export default function App() {\n"
                        "  const handleClick = () => loadTasks();\n"
                        "  return <button onClick={handleClick}>Go</button>;\n"
                        "}\n\n"
                        "const handleConnect = () => loadTasks();\n"
                        "function loadTasks() {\n"
                        "  return fetch('/tasks');\n"
                        "}\n\n"
                        "class Service {\n"
                        "  run() {\n"
                        "    return loadTasks();\n"
                        "  }\n"
                        "}\n\n"
                        "app.get('/tasks', loadTasks);\n"
                        "socket.on('connect', handleConnect);\n"
                    ),
                    "algorithm": {"steps": [], "edges": []},
                }
            ],
            "edges": [],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
        )

        semantic_nodes = ir["semanticGraph"]["nodes"]
        semantic_edges = ir["semanticGraph"]["edges"]
        node_ids = {node["name"]: node["id"] for node in semantic_nodes}

        self.assertTrue(any(node["nodeType"] == "function" and node["name"] == "loadTasks" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "function" and node["name"] == "handleConnect" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "function" and node["name"] == "App.handleClick" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "method" and node["name"] == "Service.run" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "route" and node["name"] == "GET /tasks" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "event_handler" and node["name"] == "connect" for node in semantic_nodes))
        self.assertTrue(any(node["nodeType"] == "event_handler" and node["name"] == "click@button" for node in semantic_nodes))
        self.assertTrue(any(edge["edgeType"] == "routes_to" for edge in semantic_edges))
        self.assertTrue(any(edge["edgeType"] == "handles" for edge in semantic_edges))
        self.assertTrue(
            any(
                edge["edgeType"] == "calls"
                and edge["from"] == node_ids["App.handleClick"]
                and edge["to"] == node_ids["loadTasks"]
                for edge in semantic_edges
            )
        )
        self.assertTrue(
            any(
                edge["edgeType"] == "calls"
                and edge["from"] == node_ids["Service.run"]
                and edge["to"] == node_ids["loadTasks"]
                for edge in semantic_edges
            )
        )
        self.assertTrue(
            any(
                edge["edgeType"] == "handles"
                and edge["from"] == node_ids["click@button"]
                and edge["to"] == node_ids["App.handleClick"]
                for edge in semantic_edges
            )
        )

    def test_build_architecture_ir_links_inter_module_calls_and_renders(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Demo Frontend Linked",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-main",
                    "name": "main.jsx",
                    "path": "workspace/projects/demo-frontend/frontend/src/main.jsx",
                    "workspaceProject": "demo-frontend",
                    "workspaceScene": "demo-frontend",
                    "layer": "frontend",
                    "codeLanguage": "jsx",
                    "code": (
                        "import App from './App.jsx';\n"
                        "import { bootTask } from './services/task.js';\n\n"
                        "function bootstrap() {\n"
                        "  return bootTask();\n"
                        "}\n\n"
                        "createRoot(document.getElementById('root')).render(<App />);\n"
                    ),
                    "algorithm": {"steps": [], "edges": []},
                },
                {
                    "id": "node-app",
                    "name": "App.jsx",
                    "path": "workspace/projects/demo-frontend/frontend/src/App.jsx",
                    "workspaceProject": "demo-frontend",
                    "workspaceScene": "demo-frontend",
                    "layer": "frontend",
                    "codeLanguage": "jsx",
                    "code": "export default function App() { return <section />; }\n",
                    "algorithm": {"steps": [], "edges": []},
                },
                {
                    "id": "node-task",
                    "name": "task.js",
                    "path": "workspace/projects/demo-frontend/frontend/src/services/task.js",
                    "workspaceProject": "demo-frontend",
                    "workspaceScene": "demo-frontend",
                    "layer": "frontend",
                    "codeLanguage": "javascript",
                    "code": "export function bootTask() { return true; }\n",
                    "algorithm": {"steps": [], "edges": []},
                },
            ],
            "edges": [],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
        )

        semantic_nodes = ir["semanticGraph"]["nodes"]
        semantic_edges = ir["semanticGraph"]["edges"]
        node_ids = {node["name"]: node["id"] for node in semantic_nodes}

        self.assertTrue(
            any(
                edge["edgeType"] == "calls"
                and edge["from"] == node_ids["bootstrap"]
                and edge["to"] == node_ids["bootTask"]
                and edge["metadata"].get("interModule") is True
                for edge in semantic_edges
            )
        )
        self.assertTrue(
            any(
                edge["edgeType"] == "renders"
                and edge["from"] == "node-main"
                and edge["to"] == node_ids["App"]
                and edge["metadata"].get("interModule") is True
                for edge in semantic_edges
            )
        )

    def test_build_architecture_ir_promotes_semantic_issues_to_root(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Broken Backend",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-broken",
                    "name": "broken.py",
                    "path": "workspace/projects/broken-backend/backend/broken.py",
                    "workspaceProject": "broken-backend",
                    "workspaceScene": "broken-backend",
                    "layer": "backend",
                    "codeLanguage": "python",
                    "code": "def broken(:\n    return 1\n",
                    "algorithm": {"steps": [], "edges": []},
                }
            ],
            "edges": [],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
        )

        self.assertTrue(any(issue["issueType"] == "parse_failure" for issue in ir["issues"]))
        self.assertTrue(any(issue["issueType"] == "parse_failure" for issue in ir["semanticGraph"]["issues"]))
        self.assertEqual(ir["metadata"]["issueCount"], len(ir["issues"]))

    def test_build_architecture_ir_detects_html_css_semantics(self) -> None:
        graph = {
            "metadata": {
                "projectName": "Demo Template",
                "updatedAt": "2026-05-10T00:00:00+00:00",
            },
            "nodes": [
                {
                    "id": "node-html",
                    "name": "index.html",
                    "path": "frontend/index.html",
                    "layer": "frontend",
                    "codeLanguage": "html",
                    "code": (
                        "<!doctype html>\n"
                        "<html>\n"
                        "  <head>\n"
                        "    <link rel=\"stylesheet\" href=\"/src/App.css\" />\n"
                        "  </head>\n"
                        "  <body>\n"
                        "    <script type=\"module\" src=\"/src/main.jsx\"></script>\n"
                        "  </body>\n"
                        "</html>\n"
                    ),
                    "algorithm": {"steps": [], "edges": []},
                },
                {
                    "id": "node-main",
                    "name": "main.jsx",
                    "path": "frontend/src/main.jsx",
                    "layer": "frontend",
                    "codeLanguage": "jsx",
                    "code": "console.log('boot')\n",
                    "algorithm": {"steps": [], "edges": []},
                },
                {
                    "id": "node-css",
                    "name": "App.css",
                    "path": "frontend/src/App.css",
                    "layer": "frontend",
                    "codeLanguage": "css",
                    "code": ".app { color: white; }\n",
                    "algorithm": {"steps": [], "edges": []},
                },
            ],
            "edges": [],
        }

        ir = build_architecture_ir(
            graph,
            project_root=Path("/tmp/architecture-react-three-flask-socketio"),
        )

        semantic_nodes = ir["semanticGraph"]["nodes"]
        semantic_edges = ir["semanticGraph"]["edges"]

        self.assertTrue(any(node["nodeType"] == "template" or node["id"] == "node-html" for node in ir["nodes"]))
        self.assertTrue(any(edge["edgeType"] == "imports" and edge["to"] == "node-main" for edge in semantic_edges))
        self.assertTrue(any(edge["edgeType"] == "imports" and edge["to"] == "node-css" for edge in semantic_edges))
        self.assertGreaterEqual(ir["semanticGraph"]["metadata"]["adapterCount"], 1)


if __name__ == "__main__":
    unittest.main()
