import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import app as backend_app
from orchestrator.continuity_probe import run_continuity_probe, run_prompt_flight_probe


AGENTS_MD = """# AGENTS.md

## Propósito del repositorio
Orquestador autonomo de proyectos.

## Tesis central
Dividir proyectos en tareas verificables.

## Identidad del sistema
Sistema operativo de ejecucion con agentes reemplazables.

## Reglas maestras
1. Persistir estado real en disco.
2. Validar con evidencia.

## Reglas duras del runtime
1. El modo smoke solo viene de configuracion explicita.
2. Cada tarea debe ser verificable.

## Política de directivas operativas
1. Cargar AGENTS.md.
2. Cargar PLANS.md.

## Estructura esperada del proyecto
```text
runtime/
  project_state.json
```

## Política de implementación
- No inventar exito.

## Política de entrega por sprint
- Dejar artefactos persistidos.

## Benchmarks obligatorios
- smoke-01
"""

PLANS_MD = """# PLANS.md

## Visión del proyecto
Crear un orquestador verificable.

## Problema actual
1. Falta evidencia interna.

## Nueva tesis operativa
Usar tareas pequenas y persistentes.

## Resultado esperado
- Estado reanudable.

## FASE 1 — Base
### Objetivo
Crear base persistente.
### Alcance
- Runtime.
### Criterios de aceptación
- Evidencia real.

## orchestrator/state_store.py
Responsabilidad
- Persistir estado.

## workers/codex_worker.py
Responsabilidad
- Ejecutar una tarea.

## Sprint 1
Objetivo
Crear continuidad canaria.
Entregables
- src/continuity_probe.txt
Aceptación
- Archivo canario validado.

## Benchmarks oficiales
- smoke-01

## Regla de despliegue
No desplegar sin benchmarks.
"""


def write_minimal_repo(root: Path) -> None:
    (root / "AGENTS.md").write_text(AGENTS_MD, encoding="utf-8")
    (root / "PLANS.md").write_text(PLANS_MD, encoding="utf-8")
    (root / "workspace" / "projects").mkdir(parents=True, exist_ok=True)


class ContinuityProbeTest(unittest.TestCase):
    def test_active_canary_runs_worker_validator_history_and_checkpoint(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)

            report = run_continuity_probe(
                repo_root=repo,
                mode="active_canary",
                project="continuity-test-canary",
                base_url="",
                trace_id="continuity-test-trace",
                include_harness=False,
                timeout_seconds=20,
            )

            self.assertEqual(report["result"], "continuity_ok")
            checks = report["checks"]
            for name in (
                "prompt_input",
                "policy_loaded",
                "plan_loaded",
                "task_created",
                "queue_persisted",
                "directive_generated",
                "worker_executed",
                "validator_passed",
                "history_written",
                "checkpoint_written",
            ):
                self.assertEqual(checks[name]["status"], "ok", name)
            canary_file = repo / "workspace" / "projects" / "continuity-test-canary" / "src" / "continuity_probe.txt"
            self.assertIn("traceId=continuity-test-trace", canary_file.read_text(encoding="utf-8"))
            self.assertTrue((repo / "runtime" / "continuity_probe" / "continuity-test-trace" / "report.json").is_file())

    def test_backend_sync_endpoint_returns_report(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            client = backend_app.app.test_client()

            with patch.object(backend_app, "PROJECT_ROOT", repo):
                response = client.post(
                    "/api/continuity-probe/start",
                    json={
                        "sync": True,
                        "mode": "active_canary",
                        "project": "continuity-endpoint-canary",
                        "traceId": "continuity-endpoint-trace",
                        "baseUrl": "",
                        "includeHarness": False,
                        "timeoutSeconds": 20,
                    },
                )

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["traceId"], "continuity-endpoint-trace")
            self.assertEqual(payload["report"]["checks"]["worker_executed"]["status"], "ok")
            self.assertEqual(payload["report"]["checks"]["validator_passed"]["status"], "ok")

            with patch.object(backend_app, "PROJECT_ROOT", repo):
                status_response = client.get("/api/continuity-probe/status/continuity-endpoint-trace")
            self.assertEqual(status_response.status_code, 200)
            self.assertEqual(status_response.get_json()["run"]["result"], "continuity_ok")


    def test_prompt_flight_trace_only_persists_envelope_and_stage_latencies(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)

            report = run_prompt_flight_probe(
                repo_root=repo,
                prompt="Crear una tarea segura y medir el viaje interno por HABLA BASIC.",
                mode="trace_only",
                project="continuity-prompt-canary",
                base_url="",
                trace_id="prompt-flight-test-trace",
                include_harness=False,
                timeout_seconds=20,
            )

            self.assertEqual(report["result"], "prompt_flight_ok")
            stage_map = report["stageMap"]
            for name in (
                "prompt_received",
                "habla_basic_envelope",
                "cyberlace_preflight",
                "policy_loaded",
                "plan_loaded",
                "prompt_classified",
                "task_planned",
                "response_synthesized",
            ):
                self.assertEqual(stage_map[name]["status"], "ok", name)
                self.assertIn("durationMs", stage_map[name]["evidence"])
            self.assertEqual(stage_map["safe_canary_continuity"]["status"], "skipped")
            self.assertTrue((repo / "runtime" / "continuity_probe" / "prompt-flight-test-trace" / "habla_basic_envelope.json").is_file())
            self.assertTrue((repo / "runtime" / "continuity_probe" / "prompt-flight-test-trace" / "prompt_flight_report.json").is_file())

    def test_prompt_flight_real_session_guarded_runs_runtime_loop(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)

            report = run_prompt_flight_probe(
                repo_root=repo,
                prompt="Crear una respuesta canaria real y medir todo el viaje interno.",
                mode="real_session_guarded",
                project="continuity-real-session-test",
                base_url="",
                trace_id="prompt-flight-real-session-test",
                include_harness=False,
                timeout_seconds=30,
            )

            self.assertEqual(report["result"], "prompt_flight_ok")
            stage_map = report["stageMap"]
            for name in (
                "real_session_bootstrap",
                "task_queue_persisted",
                "directive_generated",
                "worker_executed",
                "validator_passed",
                "history_written",
                "checkpoint_written",
                "response_synthesized",
            ):
                self.assertEqual(stage_map[name]["status"], "ok", name)
                self.assertIn("durationMs", stage_map[name]["evidence"])

            project = repo / "workspace" / "projects" / "continuity-real-session-test"
            response_path = project / "src" / "prompt_flight_response.json"
            self.assertTrue(response_path.is_file())
            response_payload = json.loads(response_path.read_text(encoding="utf-8"))
            self.assertEqual(response_payload["traceId"], "prompt-flight-real-session-test")
            self.assertEqual(response_payload["processedBy"], "guarded_runtime_worker")
            self.assertTrue((project / "runtime" / "task_queue.json").is_file())
            self.assertTrue((project / "runtime" / "task_history.jsonl").is_file())
            self.assertTrue(list((project / "runtime" / "directives").glob("*.json")))
            self.assertTrue(list((project / "runtime" / "checkpoints").glob("*.json")))

    def test_prompt_flight_ui_session_rest_posts_to_agent_session_endpoint(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            project = repo / "workspace" / "projects" / "continuity-ui-session-test"
            runtime = project / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "project_state.json").write_text(json.dumps({
                "schema_version": 1,
                "project_id": "continuity-ui-session-test",
                "status": "completed",
                "mode": "build",
                "current_task_id": None,
                "completed_tasks": ["TASK-UI-001"],
                "failed_tasks": [],
                "blocked_tasks": [],
                "checkpoints": ["ui-checkpoint"],
                "created_at": "2026-05-27T00:00:00Z",
                "updated_at": "2026-05-27T00:00:01Z",
            }), encoding="utf-8")
            (runtime / "task_queue.json").write_text(json.dumps([
                {
                    "id": "TASK-UI-001",
                    "title": "UI task",
                    "goal": "Process real UI prompt",
                    "status": "completed",
                    "priority": 1,
                    "dependencies": [],
                    "expected_files": ["README.md"],
                    "validation_commands": [],
                    "timeout_seconds": 30,
                    "max_retries": 0,
                    "mode": "build",
                    "checkpoint_key": None,
                }
            ]), encoding="utf-8")
            (runtime / "task_history.jsonl").write_text(json.dumps({"result": {"task_id": "TASK-UI-001", "completed": True}}) + "\n", encoding="utf-8")
            (runtime / "checkpoints").mkdir(parents=True, exist_ok=True)
            (runtime / "checkpoints" / "ui-checkpoint.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
            (runtime / "directives").mkdir(parents=True, exist_ok=True)
            (runtime / "directives" / "TASK-UI-001.json").write_text(json.dumps({"task_id": "TASK-UI-001"}), encoding="utf-8")

            calls = {"agent_session_payloads": [], "polls": 0}

            class Handler(BaseHTTPRequestHandler):
                def _json(self, status, payload):
                    raw = json.dumps(payload).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)

                def log_message(self, *_args):
                    return

                def do_POST(self):
                    length = int(self.headers.get("Content-Length") or 0)
                    payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                    if self.path == "/api/agent/session":
                        calls["agent_session_payloads"].append(payload)
                        self._json(200, {
                            "ok": True,
                            "session": {
                                "sessionId": "agent-ui-session-test",
                                "projectName": payload.get("projectName"),
                                "projectSlug": payload.get("projectSlug"),
                                "projectDir": str(project),
                                "requirement": payload.get("requirement"),
                                "status": "preparing",
                                "progressPercent": 10,
                                "progressLabel": "Preparando runtime",
                                "output": "",
                                "controlPlane": {"enabled": True, "runtimeDir": str(runtime), "activeTaskId": None},
                            },
                        })
                    else:
                        self._json(404, {"ok": False, "error": "not_found"})

                def do_GET(self):
                    if self.path == "/api/health":
                        self._json(200, {"ok": True, "service": "fake"})
                    elif self.path == "/api/observer/status":
                        self._json(200, {"ok": True, "observer": {"state": "idle", "enabled": False}})
                    elif self.path == "/api/agent/session/agent-ui-session-test":
                        calls["polls"] += 1
                        status = "completed" if calls["polls"] >= 2 else "running"
                        self._json(200, {
                            "ok": True,
                            "session": {
                                "sessionId": "agent-ui-session-test",
                                "projectSlug": "continuity-ui-session-test",
                                "projectDir": str(project),
                                "requirement": "Crear algo real",
                                "status": status,
                                "progressPercent": 100 if status == "completed" else 35,
                                "progressLabel": "Sesion completada" if status == "completed" else "Ejecutando worker",
                                "pid": None,
                                "returncode": 0 if status == "completed" else None,
                                "output": "done",
                                "terminalLogPath": str(runtime / "logs" / "agent-ui-session-test-terminal.log"),
                                "controlPlane": {"enabled": True, "runtimeDir": str(runtime), "activeTaskId": "TASK-UI-001"},
                            },
                        })
                    elif self.path == "/api/projects/continuity-ui-session-test/runtime-truth":
                        self._json(200, {
                            "ok": True,
                            "projectId": "continuity-ui-session-test",
                            "verdict": "idle",
                            "controlPlane": {
                                "projectStatus": "completed",
                                "currentTaskId": None,
                                "queueCounts": {"completed": 1, "pending": 0, "running": 0, "failed": 0, "blocked": 0},
                            },
                            "sessions": {"activeCount": 0, "active": [], "totalRuntimeSessions": 1},
                        })
                    else:
                        self._json(404, {"ok": False, "error": "not_found", "path": self.path})

            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                report = run_prompt_flight_probe(
                    repo_root=repo,
                    prompt="Crear algo real",
                    mode="ui_session_rest",
                    project="continuity-ui-session-test",
                    base_url=base_url,
                    trace_id="prompt-flight-ui-session-rest-test",
                    include_harness=False,
                    timeout_seconds=10,
                )
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

            self.assertEqual(report["result"], "prompt_flight_ok")
            self.assertEqual(calls["agent_session_payloads"][0]["requirement"], "Crear algo real")
            self.assertEqual(calls["agent_session_payloads"][0]["runtimeMode"], "build")
            self.assertEqual(report["stageMap"]["ui_agent_session_posted"]["status"], "ok")
            self.assertEqual(report["stageMap"]["ui_agent_session_polled"]["status"], "ok")
            self.assertEqual(report["stageMap"]["ui_runtime_truth_read"]["status"], "ok")
            self.assertEqual(report["stageMap"]["ui_runtime_artifacts_read"]["status"], "ok")
            self.assertTrue((repo / "runtime" / "continuity_probe" / "prompt-flight-ui-session-rest-test" / "ui_agent_session_request.json").is_file())
            self.assertTrue((repo / "runtime" / "continuity_probe" / "prompt-flight-ui-session-rest-test" / "ui_agent_session_polls.json").is_file())

    def test_backend_prompt_flight_endpoint_returns_report(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            client = backend_app.app.test_client()

            with patch.object(backend_app, "PROJECT_ROOT", repo):
                response = client.post(
                    "/api/continuity-probe/prompt-flight",
                    json={
                        "mode": "trace_only",
                        "project": "continuity-prompt-endpoint",
                        "traceId": "prompt-flight-endpoint-trace",
                        "baseUrl": "",
                        "includeHarness": False,
                        "prompt": "Verificar recorrido interno sin ejecutar worker real.",
                        "timeoutSeconds": 20,
                    },
                )

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["traceId"], "prompt-flight-endpoint-trace")
            self.assertEqual(payload["report"]["stageMap"]["habla_basic_envelope"]["status"], "ok")
            self.assertEqual(payload["report"]["stageMap"]["safe_canary_continuity"]["status"], "skipped")

            with patch.object(backend_app, "PROJECT_ROOT", repo):
                report_response = client.get("/api/continuity-probe/prompt-flight/report/prompt-flight-endpoint-trace")
            self.assertEqual(report_response.status_code, 200)
            self.assertEqual(report_response.get_json()["report"]["result"], "prompt_flight_ok")



if __name__ == "__main__":
    unittest.main()
