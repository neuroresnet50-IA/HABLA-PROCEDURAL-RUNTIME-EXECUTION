import sys
from pathlib import Path
import unittest

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ir_adapters.html_css_adapter import build_html_css_semantic_graph
from ir_adapters.javascript_adapter import build_javascript_semantic_graph
from ir_adapters.python_adapter import build_python_semantic_graph


class PythonAdapterTest(unittest.TestCase):
    def test_python_adapter_extracts_symbols_routes_and_events(self) -> None:
        parent_node = {
            "id": "node-api",
            "canonicalPath": "workspace/projects/demo/backend/api.py",
            "sourcePath": "/tmp/demo/backend/api.py",
            "projectId": "project:demo",
            "sceneId": "scene:demo",
            "layer": "backend",
            "originType": "agent",
            "readOnly": False,
            "language": "python",
            "nodeType": "module",
            "position": {"x": 10.0, "y": 20.0},
            "code": (
                "@app.route('/health', methods=['GET'])\n"
                "def health():\n"
                "    return 'ok'\n\n"
                "@socketio.on('refresh')\n"
                "def handle_refresh(payload):\n"
                "    return payload\n"
            ),
        }

        graph = build_python_semantic_graph([parent_node])

        self.assertTrue(any(node["nodeType"] == "function" and node["name"] == "health" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "route" and node["name"] == "GET /health" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "event_handler" and node["name"] == "refresh" for node in graph["nodes"]))
        self.assertTrue(any(edge["edgeType"] == "routes_to" for edge in graph["edges"]))
        self.assertTrue(any(edge["edgeType"] == "handles" for edge in graph["edges"]))
        self.assertEqual(graph["metadata"]["adapterCount"], 1)

    def test_python_adapter_tracks_exports_and_deferred_import_calls(self) -> None:
        parent_node = {
            "id": "node-main",
            "canonicalPath": "workspace/projects/demo/backend/main.py",
            "sourcePath": "/tmp/demo/backend/main.py",
            "projectId": "project:demo",
            "sceneId": "scene:demo",
            "layer": "backend",
            "originType": "agent",
            "readOnly": False,
            "language": "python",
            "nodeType": "module",
            "position": {"x": 10.0, "y": 20.0},
            "code": (
                "from .services.task_service import boot_task\n\n"
                "def bootstrap():\n"
                "    return boot_task()\n"
            ),
        }

        graph = build_python_semantic_graph([parent_node])
        bootstrap_node = next(node for node in graph["nodes"] if node["name"] == "bootstrap")
        adapter = graph["adapters"][0]

        self.assertEqual(bootstrap_node["metadata"]["exportNames"], ["bootstrap"])
        self.assertTrue(bootstrap_node["metadata"]["exported"])
        self.assertTrue(
            any(
                deferred["sourceId"] == bootstrap_node["id"]
                and deferred["moduleName"] == "services.task_service"
                and deferred["importedName"] == "boot_task"
                and deferred["level"] == 1
                for deferred in adapter["deferredCalls"]
            )
        )


class JavaScriptAdapterTest(unittest.TestCase):
    def test_javascript_adapter_extracts_semantic_symbols_calls_routes_and_jsx_events(self) -> None:
        parent_node = {
            "id": "node-ui",
            "canonicalPath": "workspace/projects/demo/frontend/client.js",
            "sourcePath": "/tmp/demo/frontend/client.js",
            "projectId": "project:demo",
            "sceneId": "scene:demo",
            "layer": "frontend",
            "originType": "agent",
            "readOnly": False,
            "language": "javascript",
            "nodeType": "module",
            "position": {"x": 10.0, "y": 20.0},
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
        }

        graph = build_javascript_semantic_graph([parent_node])
        node_ids = {node["name"]: node["id"] for node in graph["nodes"]}
        app_node = next(node for node in graph["nodes"] if node["name"] == "App")

        self.assertTrue(any(node["nodeType"] == "function" and node["name"] == "loadTasks" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "function" and node["name"] == "App.handleClick" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "method" and node["name"] == "Service.run" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "route" and node["name"] == "GET /tasks" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "event_handler" and node["name"] == "connect" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "event_handler" and node["name"] == "click@button" for node in graph["nodes"]))
        self.assertTrue(any(edge["edgeType"] == "routes_to" for edge in graph["edges"]))
        self.assertTrue(any(edge["edgeType"] == "handles" for edge in graph["edges"]))
        self.assertTrue(
            any(
                edge["edgeType"] == "calls"
                and edge["from"] == node_ids["App.handleClick"]
                and edge["to"] == node_ids["loadTasks"]
                for edge in graph["edges"]
            )
        )
        self.assertTrue(
            any(
                edge["edgeType"] == "calls"
                and edge["from"] == node_ids["Service.run"]
                and edge["to"] == node_ids["loadTasks"]
                for edge in graph["edges"]
            )
        )
        self.assertTrue(
            any(
                edge["edgeType"] == "handles"
                and edge["from"] == node_ids["click@button"]
                and edge["to"] == node_ids["App.handleClick"]
                for edge in graph["edges"]
            )
        )
        self.assertTrue(app_node["metadata"]["defaultExport"])
        self.assertIn("default", app_node["metadata"]["exportNames"])
        self.assertEqual(graph["metadata"]["adapterCount"], 1)


class HtmlCssAdapterTest(unittest.TestCase):
    def test_html_css_adapter_extracts_embedded_blocks_and_references(self) -> None:
        html_node = {
            "id": "node-html",
            "canonicalPath": "frontend/index.html",
            "sourcePath": "/tmp/demo/frontend/index.html",
            "projectId": "project:demo",
            "sceneId": "scene:demo",
            "layer": "frontend",
            "originType": "physical",
            "readOnly": False,
            "language": "html",
            "nodeType": "template",
            "position": {"x": 10.0, "y": 20.0},
            "name": "index.html",
            "code": (
                "<!doctype html>\n"
                "<html>\n"
                "  <head>\n"
                "    <link rel=\"stylesheet\" href=\"/src/App.css\" />\n"
                "    <style>.hero { background: url('./missing.png'); }</style>\n"
                "  </head>\n"
                "  <body onclick=\"boot()\">\n"
                "    <img src=\"https://cdn.example.com/logo.svg\" />\n"
                "    <script type=\"module\" src=\"/src/main.jsx\"></script>\n"
                "    <script>window.boot = () => true;</script>\n"
                "  </body>\n"
                "</html>\n"
            ),
        }
        js_node = {
            "id": "node-main",
            "canonicalPath": "frontend/src/main.jsx",
            "path": "frontend/src/main.jsx",
            "sourcePath": "/tmp/demo/frontend/src/main.jsx",
            "projectId": "project:demo",
            "sceneId": "scene:demo",
            "layer": "frontend",
            "originType": "physical",
            "readOnly": False,
            "language": "jsx",
            "nodeType": "module",
            "position": {"x": 50.0, "y": 20.0},
            "name": "main.jsx",
            "code": "console.log('boot')\n",
        }
        css_node = {
            "id": "node-css",
            "canonicalPath": "frontend/src/App.css",
            "path": "frontend/src/App.css",
            "sourcePath": "/tmp/demo/frontend/src/App.css",
            "projectId": "project:demo",
            "sceneId": "scene:demo",
            "layer": "frontend",
            "originType": "physical",
            "readOnly": False,
            "language": "css",
            "nodeType": "style_sheet",
            "position": {"x": 90.0, "y": 20.0},
            "name": "App.css",
            "code": "@import './theme.css';\n.card { background-image: url('https://cdn.example.com/bg.png'); }\n",
        }
        theme_node = {
            "id": "node-theme",
            "canonicalPath": "frontend/src/theme.css",
            "path": "frontend/src/theme.css",
            "sourcePath": "/tmp/demo/frontend/src/theme.css",
            "projectId": "project:demo",
            "sceneId": "scene:demo",
            "layer": "frontend",
            "originType": "physical",
            "readOnly": False,
            "language": "css",
            "nodeType": "style_sheet",
            "position": {"x": 120.0, "y": 20.0},
            "name": "theme.css",
            "code": ":root { color: white; }\n",
        }

        graph = build_html_css_semantic_graph([html_node, js_node, css_node, theme_node])

        self.assertTrue(any(node["nodeType"] == "script_block" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "style_sheet" and node["parentId"] == "node-html" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "event_handler" and node["name"] == "click@body" for node in graph["nodes"]))
        self.assertTrue(any(node["nodeType"] == "external_dependency" for node in graph["nodes"]))
        self.assertTrue(any(edge["edgeType"] == "imports" and edge["to"] == "node-main" for edge in graph["edges"]))
        self.assertTrue(any(edge["edgeType"] == "imports" and edge["to"] == "node-css" for edge in graph["edges"]))
        self.assertTrue(any(edge["edgeType"] == "imports" and edge["to"] == "node-theme" for edge in graph["edges"]))
        self.assertTrue(any(edge["edgeType"] == "links_to_external" for edge in graph["edges"]))
        self.assertTrue(any(issue["issueType"] == "missing_dependency" for issue in graph["issues"]))
        self.assertEqual(graph["metadata"]["adapterCount"], 3)


if __name__ == "__main__":
    unittest.main()
