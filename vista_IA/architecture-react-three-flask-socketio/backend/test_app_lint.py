import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as backend_app


class ArchitectureLintEndpointRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = backend_app.app.test_client()

    def test_habla_preflight_uses_v5_engine_as_primary_brain(self) -> None:
        self.assertEqual(backend_app.HABLA_ENGINE_CLASS_NAME, "HablaEngineV5")
        self.assertIn("habla_agentic_engine_v5_1_lace_visual", str(backend_app.HABLA_ROOT))
        self.assertIsNotNone(backend_app.HABLA_LACE_POLICY_PATH)

        with TemporaryDirectory() as tmpdir:
            with patch.object(backend_app, "RUNTIME_ROOT", Path(tmpdir) / ".runtime"):
                payload = backend_app.build_habla_payload("Construye una app con validacion real.")

        self.assertTrue(payload["available"])
        state = payload["state"]
        self.assertEqual(state["runtime"], "HablaEngineV5")
        self.assertEqual(state["engineVersion"], "v5.1")
        self.assertTrue(state["lacePolicyLoaded"])
        self.assertIn("LACE v2.0 ESTA ACTIVO", state["directive"])
        self.assertIn("habla_agentic_engine_v5_1_lace_visual", state["engineRoot"])

    def test_habla_status_endpoint_exposes_primary_engine_and_lace_policy(self) -> None:
        response = self.client.get("/api/runtime/habla-status")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])

        habla = payload["habla"]
        self.assertTrue(habla["available"])
        self.assertTrue(habla["primaryEngine"])
        self.assertEqual(habla["runtime"], "HablaEngineV5")
        self.assertEqual(habla["engineVersion"], "v5.1")
        self.assertTrue(habla["lacePolicyExists"])
        self.assertTrue(habla["lacePolicyLoaded"])
        self.assertEqual(habla["agentRuntime"]["lacePolicySource"], habla["lacePolicyPath"])
        self.assertIn("habla_agentic_engine_v5_1_lace_visual", habla["engineRoot"])

    def test_lint_endpoint_merges_semantic_issues_into_report_findings(self) -> None:
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

        with TemporaryDirectory() as tmpdir:
            with (
                patch.object(backend_app, "PROJECT_ROOT", Path(tmpdir)),
                patch.object(backend_app, "load_default_graph", return_value=graph),
                patch.object(backend_app, "list_analysis_sessions", return_value=[]),
                patch.object(backend_app.agent_runtime, "list_sessions", return_value=[]),
            ):
                response = self.client.get("/api/architecture/lint")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])

        findings = payload["report"]["findings"]
        unresolved = next(
            finding for finding in findings
            if finding["code"] == "unresolved_import" and finding["path"] == graph["nodes"][0]["path"]
        )

        self.assertEqual(unresolved["nodeId"], "node-main")
        self.assertEqual(unresolved["source"], "semantic")
        self.assertIn("./MissingPanel.jsx", str(unresolved["message"]))
        self.assertEqual(payload["report"]["summary"]["total"], len(findings))
        self.assertTrue(any(issue["issueType"] == "unresolved_import" for issue in payload["issues"]))

    def test_lint_endpoint_respects_scene_filter_for_semantic_issues(self) -> None:
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

        with TemporaryDirectory() as tmpdir:
            with (
                patch.object(backend_app, "PROJECT_ROOT", Path(tmpdir)),
                patch.object(backend_app, "load_default_graph", return_value=graph),
                patch.object(backend_app, "list_analysis_sessions", return_value=[]),
                patch.object(backend_app.agent_runtime, "list_sessions", return_value=[]),
            ):
                response = self.client.get("/api/architecture/lint?scene=otra-escena")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(any(finding["code"] == "unresolved_import" for finding in payload["report"]["findings"]))

    def test_repair_prompt_targets_missing_relative_python_module(self) -> None:
        issue = {
            "line": 3,
            "severity": "error",
            "code": "python_relative_import_missing",
            "message": "No se encontro el modulo relativo reglas_descuento.",
            "evidence": {"module": "reglas_descuento", "level": 1},
        }

        files = backend_app.suggested_repair_files("src/calculadora_descuentos.py", issue)
        prompt = backend_app.build_agent_repair_requirement(
            project_slug="test-punto-rojo",
            relative_path="src/calculadora_descuentos.py",
            issue=issue,
            extra_instruction="Repara el import faltante.",
        )

        self.assertEqual(files, ["src/calculadora_descuentos.py", "src/reglas_descuento.py"])
        self.assertIn("MODO REPARACION AGENTICA EN VIVO", prompt)
        self.assertIn("src/reglas_descuento.py", prompt)
        self.assertIn("python3 -m py_compile src/calculadora_descuentos.py src/reglas_descuento.py", prompt)

    def test_repair_endpoint_launches_existing_project_worker(self) -> None:
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "workspace" / "projects"
            project_dir = projects_root / "repair-demo"
            source_dir = project_dir / "src"
            source_dir.mkdir(parents=True)
            (source_dir / "calculadora_descuentos.py").write_text(
                "from .reglas_descuento import REGLAS_DESCUENTO\n",
                encoding="utf-8",
            )

            with (
                patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root),
                patch.object(backend_app, "sync_runtime_graph", return_value={"nodes": [], "edges": []}),
                patch.object(backend_app.socketio, "emit"),
                patch.object(backend_app.agent_runtime, "list_projects", return_value=[]),
                patch.object(
                    backend_app.agent_runtime,
                    "start_session",
                    return_value={"sessionId": "agent-repair-001", "projectSlug": "repair-demo", "status": "running"},
                ) as start_session,
            ):
                response = self.client.post(
                    "/api/projects/repair-demo/repair",
                    json={
                        "path": "src/calculadora_descuentos.py",
                        "line": 1,
                        "code": "python_relative_import_missing",
                        "message": "Import relativo faltante",
                        "evidence": {"module": "reglas_descuento", "level": 1},
                    },
                )

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["repairFiles"], ["src/calculadora_descuentos.py", "src/reglas_descuento.py"])
            self.assertEqual(payload["repairTask"]["status"], "pending")
            self.assertEqual(payload["repairTask"]["expected_files"], ["src/calculadora_descuentos.py", "src/reglas_descuento.py"])
            _, kwargs = start_session.call_args
            self.assertEqual(kwargs["project_slug"], "repair-demo")
            self.assertFalse(kwargs["bootstrap"])
            self.assertFalse(kwargs["ensure_new_project"])
            self.assertEqual(kwargs["mode"], "build")
            persisted_queue = backend_app.StateStore(project_dir / "runtime").load_task_queue()
            self.assertEqual(len(persisted_queue), 1)
            self.assertEqual(persisted_queue[0]["id"], payload["repairTask"]["id"])


if __name__ == "__main__":
    unittest.main()
