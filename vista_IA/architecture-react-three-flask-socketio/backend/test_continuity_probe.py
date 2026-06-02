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
from orchestrator.executor import execute_task_with_details
from orchestrator.prompt_flight_batch import PromptFlightBatchRunner, discover_prompt_flight_suites, load_prompt_flight_cases, load_prompt_flight_suite_cases, summarize_case_response
from orchestrator.prompt_flight_probe import PromptFlightProbe
from orchestrator.recovery import decide_recovery
from orchestrator.runtime_failure_classifier import classify_runtime_failure
from orchestrator.runtime_task_cleaner import sweep_with_broom
from orchestrator.validator import validate_task_execution


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

    def test_prompt_flight_ui_session_monitor_budget_honors_active_task_timeout(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            probe = PromptFlightProbe(
                repo_root=repo,
                prompt="Crear algo real",
                mode="ui_session_rest",
                project="continuity-ui-timeout-budget-test",
                base_url="http://127.0.0.1:5001",
                trace_id="prompt-flight-ui-timeout-budget-test",
                timeout_seconds=20,
                include_harness=False,
            )
            session = {"controlPlane": {"activeTask": {"timeout_seconds": 900}}}
            self.assertEqual(probe._ui_session_active_task_timeout_seconds(session), 900)
            self.assertEqual(probe._ui_session_monitor_budget_seconds(session), 1020)

    def test_prompt_flight_updates_report_project_when_backend_assigns_unique_slug(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            probe = PromptFlightProbe(
                repo_root=repo,
                prompt="Crear algo real",
                mode="ui_session_rest",
                project="continuity-ui-session-test",
                base_url="http://127.0.0.1:5001",
                trace_id="prompt-flight-project-suffix-test",
                include_harness=False,
                timeout_seconds=10,
            )
            probe.ui_session_payload = probe._ui_session_payload()

            def fake_request_json_payload(method, path, payload, *, timeout):
                self.assertEqual(method, "POST")
                self.assertEqual(path, "/api/agent/session")
                return 200, {
                    "ok": True,
                    "session": {
                        "sessionId": "agent-project-suffix-test",
                        "projectSlug": "continuity-ui-session-test-2",
                        "status": "preparing",
                    },
                }, 5.0

            probe._request_json_payload = fake_request_json_payload
            result = probe._stage_ui_agent_session_posted()

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["projectSlug"], "continuity-ui-session-test-2")
            self.assertEqual(probe.project, "continuity-ui-session-test-2")
            self.assertEqual(probe.report["project"], "continuity-ui-session-test-2")
            self.assertEqual(probe.project_dir, repo / "workspace" / "projects" / "continuity-ui-session-test-2")
            self.assertEqual(probe.runtime_dir, repo / "workspace" / "projects" / "continuity-ui-session-test-2" / "runtime")

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
                    elif self.path == "/api/continuity-probe/prompt-flight/worker-diagnostics":
                        self._json(200, {"ok": True, "diagnostics": {"promptFlightWorkerReady": True, "effectiveSandboxMode": "danger-full-access", "effectiveApprovalPolicy": "never", "usesDangerBypass": True, "usesWorkspaceWrite": False, "blockers": []}})
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
            self.assertIs(calls["agent_session_payloads"][0]["ensureNewProject"], True)
            self.assertIs(calls["agent_session_payloads"][0]["bootstrapProject"], False)
            self.assertEqual(report["stageMap"]["ui_agent_session_posted"]["status"], "ok")
            self.assertEqual(report["stageMap"]["ui_agent_session_polled"]["status"], "ok")
            self.assertEqual(report["stageMap"]["ui_runtime_truth_read"]["status"], "ok")
            self.assertEqual(report["stageMap"]["ui_runtime_artifacts_read"]["status"], "ok")
            self.assertTrue((repo / "runtime" / "continuity_probe" / "prompt-flight-ui-session-rest-test" / "ui_agent_session_request.json").is_file())
            self.assertTrue((repo / "runtime" / "continuity_probe" / "prompt-flight-ui-session-rest-test" / "ui_agent_session_polls.json").is_file())


    def test_prompt_flight_ui_session_rest_stops_session_after_poll_timeout(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            project = repo / "workspace" / "projects" / "continuity-ui-timeout-test"
            runtime = project / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "project_state.json").write_text(json.dumps({
                "schema_version": 1,
                "project_id": "continuity-ui-timeout-test",
                "status": "running",
                "mode": "build",
                "current_task_id": "TASK-TIMEOUT-001",
                "completed_tasks": [],
                "failed_tasks": [],
                "blocked_tasks": [],
                "checkpoints": [],
                "created_at": "2026-05-27T00:00:00Z",
                "updated_at": "2026-05-27T00:00:01Z",
            }), encoding="utf-8")
            (runtime / "task_queue.json").write_text(json.dumps([]), encoding="utf-8")
            (runtime / "task_history.jsonl").write_text("", encoding="utf-8")

            calls = {"polls": 0, "stops": 0}

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
                    if self.path == "/api/agent/session":
                        self._json(200, {"ok": True, "session": {
                            "sessionId": "agent-timeout-test",
                            "projectSlug": "continuity-ui-timeout-test",
                            "projectDir": str(project),
                            "status": "running",
                            "progressPercent": 12,
                            "progressLabel": "running",
                            "controlPlane": {"enabled": True, "runtimeDir": str(runtime), "activeTaskId": "TASK-TIMEOUT-001"},
                        }})
                    elif self.path == "/api/agent/session/agent-timeout-test/stop":
                        calls["stops"] += 1
                        self._json(200, {"ok": True, "session": {
                            "sessionId": "agent-timeout-test",
                            "projectSlug": "continuity-ui-timeout-test",
                            "projectDir": str(project),
                            "status": "stopped",
                            "progressPercent": 94,
                            "progressLabel": "Sesion detenida por test.",
                            "errorCode": "manual_stop",
                            "controlPlane": {"enabled": True, "runtimeDir": str(runtime), "activeTaskId": "TASK-TIMEOUT-001"},
                        }})
                    else:
                        self._json(404, {"ok": False, "error": "not_found", "path": self.path})

                def do_GET(self):
                    if self.path == "/api/health":
                        self._json(200, {"ok": True, "service": "fake"})
                    elif self.path == "/api/continuity-probe/prompt-flight/worker-diagnostics":
                        self._json(200, {"ok": True, "diagnostics": {"promptFlightWorkerReady": True, "effectiveSandboxMode": "danger-full-access", "effectiveApprovalPolicy": "never", "usesDangerBypass": True, "usesWorkspaceWrite": False, "blockers": []}})
                    elif self.path == "/api/observer/status":
                        self._json(200, {"ok": True, "observer": {"state": "idle", "enabled": False}})
                    elif self.path == "/api/agent/session/agent-timeout-test":
                        calls["polls"] += 1
                        self._json(200, {"ok": True, "session": {
                            "sessionId": "agent-timeout-test",
                            "projectSlug": "continuity-ui-timeout-test",
                            "projectDir": str(project),
                            "status": "running",
                            "progressPercent": 35,
                            "progressLabel": "still running",
                            "pid": 123,
                            "returncode": None,
                            "output": "busy",
                            "terminalLogPath": str(runtime / "logs" / "agent-timeout-test-terminal.log"),
                            "controlPlane": {"enabled": True, "runtimeDir": str(runtime), "activeTaskId": "TASK-TIMEOUT-001"},
                        }})
                    elif self.path == "/api/projects/continuity-ui-timeout-test/runtime-truth":
                        self._json(200, {"ok": True, "projectId": "continuity-ui-timeout-test", "verdict": "live", "controlPlane": {"projectStatus": "stopped", "currentTaskId": None, "queueCounts": {"completed": 0, "pending": 0, "running": 0, "failed": 0, "blocked": 0}}, "sessions": {"activeCount": 0, "active": [], "totalRuntimeSessions": 1}})
                    else:
                        self._json(404, {"ok": False, "error": "not_found", "path": self.path})

            server = HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                report = run_prompt_flight_probe(
                    repo_root=repo,
                    prompt="Crear algo que excede timeout",
                    mode="ui_session_rest",
                    project="continuity-ui-timeout-test",
                    base_url=f"http://127.0.0.1:{server.server_port}",
                    trace_id="prompt-flight-ui-timeout-stop-test",
                    include_harness=False,
                    timeout_seconds=5,
                )
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

            poll_stage = report["stageMap"]["ui_agent_session_polled"]
            self.assertEqual(poll_stage["status"], "timeout")
            self.assertEqual(calls["stops"], 1)
            self.assertTrue(poll_stage["evidence"]["stopRequestedAfterTimeout"])
            self.assertTrue(poll_stage["evidence"]["stopConfirmedAfterTimeout"])
            self.assertEqual(poll_stage["evidence"]["finalStatus"], "stopped")
            self.assertTrue((repo / "runtime" / "continuity_probe" / "prompt-flight-ui-timeout-stop-test" / "ui_agent_session_stop_after_timeout.json").is_file())

    def test_prompt_flight_timeout_cleanup_confirms_delayed_terminal_session(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            probe = PromptFlightProbe(
                repo_root=repo,
                prompt="Crear algo que tarda y exige cleanup posterior",
                mode="ui_session_rest",
                project="continuity-delayed-stop-test",
                base_url="http://127.0.0.1:1",
                trace_id="prompt-flight-delayed-stop-test",
                include_harness=False,
                timeout_seconds=180,
            )
            calls = {"gets": 0, "posts": 0}

            def fake_request_json_payload(method, path, payload, *, timeout):
                if method == "POST" and path.endswith("/stop"):
                    calls["posts"] += 1
                    return 0, {"ok": False, "error": "connection_failed", "message": "timed out"}, 15000.0
                if method == "GET" and "/api/agent/session/" in path:
                    calls["gets"] += 1
                    status = "running" if calls["gets"] <= 6 else "stopped"
                    return 200, {"ok": True, "session": {"sessionId": "agent-delayed", "status": status, "progressPercent": 94}}, 10.0
                return 404, {"ok": False, "error": "not_found"}, 1.0

            probe._request_json_payload = fake_request_json_payload
            with patch("orchestrator.prompt_flight_probe.time.sleep", return_value=None):
                result = probe._stop_ui_session_after_timeout("agent-delayed", {"completed", "failed", "stopped", "blocked"})

            self.assertEqual(calls["posts"], 1)
            self.assertGreater(calls["gets"], 5)
            self.assertTrue(result["stopConfirmed"])
            self.assertEqual(result["finalStatus"], "stopped")
            self.assertGreaterEqual(result["confirmPollLimit"], 8)
            self.assertTrue((repo / "runtime" / "continuity_probe" / "prompt-flight-delayed-stop-test" / "ui_agent_session_stop_after_timeout.json").is_file())

    def test_backend_prompt_flight_endpoint_blocks_unverified_worker_before_report(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            client = backend_app.app.test_client()
            diagnostics = {
                "promptFlightWorkerReady": False,
                "effectiveSandboxMode": "workspace-write",
                "effectiveApprovalPolicy": "never",
                "allowDangerFullAccess": False,
                "usesDangerBypass": False,
                "usesWorkspaceWrite": True,
                "safeCommandSummary": "codex -a never -s workspace-write",
                "blockers": ["codex_inner_exec_uses_workspace_write"],
                "requiredAction": "./start_prompt_flight_tkinter.sh --local-worker-no-bwrap",
            }

            with patch.object(backend_app, "PROJECT_ROOT", repo), patch.object(
                backend_app.agent_runtime, "codex_runtime_diagnostics", return_value=diagnostics
            ):
                response = client.post(
                    "/api/continuity-probe/prompt-flight",
                    json={
                        "mode": "ui_session_rest",
                        "project": "continuity-prompt-blocked",
                        "traceId": "prompt-flight-blocked-before-case",
                        "baseUrl": "",
                        "includeHarness": False,
                        "prompt": "Debe bloquearse antes de crear caso si el worker no esta verificado.",
                        "timeoutSeconds": 20,
                    },
                )

            self.assertEqual(response.status_code, 409)
            payload = response.get_json()
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["result"], "prompt_flight_blocked")
            self.assertEqual(payload["reason"], "worker_runtime_not_verified")
            self.assertEqual(payload["effectiveSandboxMode"], "workspace-write")
            self.assertIn("worker_runtime_gate", payload["failedStages"])
            self.assertFalse((repo / "runtime" / "continuity_probe" / "prompt-flight-blocked-before-case").exists())

    def test_prompt_flight_worker_diagnostics_endpoint_reports_runtime_gate(self):
        client = backend_app.app.test_client()
        diagnostics = {
            "promptFlightWorkerReady": False,
            "effectiveSandboxMode": "workspace-write",
            "effectiveApprovalPolicy": "never",
            "allowDangerFullAccess": False,
            "usesDangerBypass": False,
            "usesWorkspaceWrite": True,
            "safeCommandSummary": "codex -a never -s workspace-write",
            "blockers": ["codex_inner_exec_uses_workspace_write"],
            "requiredAction": "./start_prompt_flight_tkinter.sh --local-worker-no-bwrap",
        }

        with patch.object(backend_app.agent_runtime, "codex_runtime_diagnostics", return_value=diagnostics):
            response = client.get("/api/continuity-probe/prompt-flight/worker-diagnostics")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"], "worker_runtime_diagnostics")
        self.assertEqual(payload["diagnostics"]["effectiveSandboxMode"], "workspace-write")
        self.assertFalse(payload["diagnostics"]["promptFlightWorkerReady"])

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




    def test_prompt_flight_domain_suites_discovery_finds_valid_production_and_canary_suites(self):
        suites = discover_prompt_flight_suites(REPO_ROOT)
        valid = {suite["suiteId"]: suite for suite in suites if suite["status"] == "ok"}
        production = {"advanced_programming", "artificial_intelligence", "computer_vision", "geometry", "mathematics"}

        self.assertTrue(production <= set(valid))
        self.assertTrue(all(valid[suite_id]["caseCount"] == 50 for suite_id in production))
        self.assertIn("advanced_programming_canary_3", valid)
        self.assertEqual(valid["advanced_programming_canary_3"]["caseCount"], 3)
        self.assertIn("advanced_programming_alert_antihack", valid)
        self.assertEqual(valid["advanced_programming_alert_antihack"]["caseCount"], 3)
        self.assertTrue(all(str(valid[suite_id]["casePath"]).endswith("cases_50.json") for suite_id in production))
        self.assertTrue(str(valid["advanced_programming_canary_3"]["casePath"]).endswith("cases_3.json"))
        self.assertTrue(str(valid["advanced_programming_alert_antihack"]["casePath"]).endswith("cases_3.json"))

    def test_prompt_flight_domain_suite_cases_load_with_metadata(self):
        suite, cases = load_prompt_flight_suite_cases(REPO_ROOT, "mathematics")

        self.assertEqual(suite["suiteId"], "mathematics")
        self.assertEqual(len(cases), 50)
        self.assertEqual(cases[0]["domain"], "mathematics")
        self.assertTrue(cases[0]["projectSlug"].startswith("continuity-math-pf-"))

    def test_prompt_flight_default_batch_cases_json_contains_50_cases(self):
        cases = load_prompt_flight_cases(REPO_ROOT, "runtime/continuity_probe/prompt_flight_cases_50.json")

        self.assertEqual(len(cases), 50)
        self.assertEqual(len({case["id"] for case in cases}), 50)
        self.assertTrue(all(case["mode"] == "ui_session_rest" for case in cases))
        self.assertTrue(all(str(case.get("projectSlug", "")).startswith("continuity-batch-pf-") for case in cases))

    def test_prompt_flight_batch_runner_processes_cases_sequentially(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            cases = [
                {"id": "PF-A", "title": "A", "prompt": "Case A", "mode": "trace_only", "timeoutSeconds": 10},
                {"id": "PF-B", "title": "B", "prompt": "Case B", "mode": "trace_only", "timeoutSeconds": 10},
                {"id": "PF-C", "title": "C", "prompt": "Case C", "mode": "trace_only", "timeoutSeconds": 10},
            ]
            active = 0
            order = []
            events = []

            def request_case(payload, case):
                nonlocal active
                self.assertEqual(active, 0)
                active += 1
                order.append(case["id"])
                trace_id = payload["traceId"]
                active -= 1
                return {
                    "ok": True,
                    "traceId": trace_id,
                    "report": {
                        "traceId": trace_id,
                        "status": "completed",
                        "result": "prompt_flight_ok",
                        "summary": {"ok": 1, "failed": 0, "blocked": 0, "total": 1},
                        "artifacts": {"reportPath": f"runtime/continuity_probe/{trace_id}/prompt_flight_report.json"},
                        "stages": [],
                    },
                }

            runner = PromptFlightBatchRunner(repo_root=repo, cases=cases, batch_id="prompt-flight-batch-test")
            summary = runner.run(
                request_case=request_case,
                base_url="http://127.0.0.1:5001",
                default_project="continuity-batch-test",
                include_harness=False,
                event_callback=events.append,
                pause_sleep_seconds=0.01,
            )

            self.assertEqual(order, ["PF-A", "PF-B", "PF-C"])
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["completed"], 3)
            self.assertEqual(summary["failed"], 0)
            event_names = [event["event"] for event in events if event["event"].startswith("case_")]
            self.assertEqual(event_names, ["case_started", "case_finished", "case_started", "case_finished", "case_started", "case_finished"])
            self.assertTrue((repo / "runtime" / "continuity_probe" / "batches" / "prompt-flight-batch-test" / "batch_state.json").is_file())
            self.assertTrue((repo / "runtime" / "continuity_probe" / "batches" / "prompt-flight-batch-test" / "batch_summary.json").is_file())

    def test_prompt_flight_batch_blocks_before_first_case_when_preflight_fails(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            cases = [
                {"id": "PF-A", "title": "A", "prompt": "Case A", "mode": "ui_session_rest", "timeoutSeconds": 10},
                {"id": "PF-B", "title": "B", "prompt": "Case B", "mode": "ui_session_rest", "timeoutSeconds": 10},
            ]
            calls = {"cases": 0}

            def request_case(payload, case):
                calls["cases"] += 1
                return {"ok": True, "report": {"result": "prompt_flight_ok", "stages": []}}

            runner = PromptFlightBatchRunner(repo_root=repo, cases=cases, batch_id="prompt-flight-batch-preflight-block")
            summary = runner.run(
                request_case=request_case,
                base_url="http://127.0.0.1:5001",
                default_project="continuity-batch-test",
                include_harness=False,
                event_callback=lambda event: None,
                worker_sandbox_preflight=lambda: {
                    "ok": False,
                    "diagnostics": {
                        "promptFlightWorkerReady": False,
                        "effectiveSandboxMode": "workspace-write",
                        "blockers": ["codex_inner_exec_uses_workspace_write"],
                    },
                },
                pause_sleep_seconds=0.01,
            )

            self.assertEqual(calls["cases"], 0)
            self.assertEqual(summary["status"], "paused_infrastructure_failures")
            self.assertEqual(summary["stopReason"], "worker_smoke_failed")
            self.assertEqual(summary["pending"], 2)
            state = json.loads((repo / "runtime" / "continuity_probe" / "batches" / "prompt-flight-batch-preflight-block" / "batch_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["startedCases"], 0)
            self.assertEqual(state["activeCases"], 0)

    def test_prompt_flight_summarizes_runtime_infrastructure_failure(self):
        response = {
            "ok": False,
            "report": {
                "result": "prompt_flight_failed",
                "stages": [
                    {
                        "name": "ui_runtime_artifacts_read",
                        "status": "ok",
                        "evidence": {
                            "runtimeInfrastructureFailure": True,
                            "fatalInfrastructureFailure": True,
                            "infrastructureFailureMarkers": ["bwrap: loopback"],
                        },
                    }
                ],
            },
        }

        summary = summarize_case_response(response)

        self.assertEqual(summary["status"], "infrastructure_failed")
        self.assertTrue(summary["infrastructureFailure"])
        self.assertTrue(summary["fatalInfrastructureFailure"])

    def test_prompt_flight_completed_case_ignores_stale_runtime_failure_evidence(self):
        response = {
            "ok": True,
            "report": {
                "result": "prompt_flight_ok",
                "stages": [
                    {
                        "name": "ui_runtime_artifacts_read",
                        "status": "ok",
                        "evidence": {
                            "runtimeInfrastructureFailure": True,
                            "fatalInfrastructureFailure": True,
                            "infrastructureFailureMarkers": ["bwrap: loopback"],
                        },
                    }
                ],
            },
        }

        summary = summarize_case_response(response)

        self.assertEqual(summary["status"], "completed")
        self.assertFalse(summary["infrastructureFailure"])
        self.assertFalse(summary["fatalInfrastructureFailure"])

    def test_runtime_failure_classifier_ignores_historical_bwrap_diff_residue(self):
        stale_diff = """
        diff --git a/recuperacioncontexto.md b/recuperacioncontexto.md
        + - El fallo anterior fue bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted.
        + - Contexto historico: no corresponde al proceso actual.
        """
        current = classify_runtime_failure(stale_diff)
        real = classify_runtime_failure("bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted")

        self.assertFalse(current["infrastructureFailure"])
        self.assertFalse(current["fatalInfrastructureFailure"])
        self.assertTrue(real["infrastructureFailure"])
        self.assertTrue(real["fatalInfrastructureFailure"])

    def test_broom_sweeps_stale_project_state_without_deleting_history(self):
        with TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "workspace" / "projects" / "broom-test"
            runtime = project / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "project_state.json").write_text(json.dumps({
                "schema_version": 1,
                "project_id": "broom-test",
                "status": "blocked",
                "mode": "build",
                "current_task_id": "OLD-RUNNING",
                "completed_tasks": [],
                "failed_tasks": ["OLD-FAILED"],
                "blocked_tasks": ["OLD-BLOCKED", "CURRENT-BLOCKED"],
                "checkpoints": [],
                "created_at": "2026-05-28T00:00:00Z",
                "updated_at": "2026-05-28T00:00:00Z",
            }), encoding="utf-8")
            (runtime / "task_queue.json").write_text(json.dumps([
                {"id": "CURRENT-BLOCKED", "title": "current", "goal": "g", "status": "blocked", "priority": 1, "dependencies": [], "expected_files": ["docs/x.md"], "validation_commands": [], "timeout_seconds": 30, "max_retries": 0, "mode": "build", "checkpoint_key": None}
            ]), encoding="utf-8")
            (runtime / "task_history.jsonl").write_text(json.dumps({"result": {"task_id": "OLD-RUNNING", "completed": False, "validation_passed": False, "blockers": ["old"]}}) + "\n", encoding="utf-8")
            (runtime / "failures.jsonl").write_text(json.dumps({"failure": {"task_id": "OLD-FAILED", "failure": {"task_result": {"blockers": ["bwrap: loopback"]}}}}) + "\n", encoding="utf-8")

            report = sweep_with_broom(project, task_id="CURRENT-BLOCKED", phase="before_task")
            state = json.loads((runtime / "project_state.json").read_text(encoding="utf-8"))

            self.assertTrue(report["ok"])
            self.assertEqual(state["blocked_tasks"], ["CURRENT-BLOCKED"])
            self.assertEqual(state["failed_tasks"], [])
            self.assertIsNone(state["current_task_id"])
            self.assertTrue((runtime / "task_history.jsonl").is_file())
            self.assertTrue((runtime / "failures.jsonl").is_file())
            self.assertTrue((runtime / "artifacts" / "broom" / "latest.json").is_file())

    def test_prompt_flight_expected_cyberlace_quarantine_counts_as_completed(self):
        response = {
            "ok": False,
            "traceId": "prompt-flight-alert-002",
            "report": {
                "traceId": "prompt-flight-alert-002",
                "result": "prompt_flight_blocked",
                "status": "blocked",
                "summary": {"ok": 4, "failed": 0, "blocked": 1, "total": 5},
                "stages": [
                    {
                        "name": "cyberlace_preflight",
                        "status": "blocked",
                        "evidence": {
                            "runtimeAction": "QUARANTINE",
                            "blocked": True,
                            "evidencePath": "runtime/continuity_probe/prompt-flight-alert-002/cyberlace_preflight.json",
                            "evidencePatterns": ["payment_data_copy_store_or_send"],
                        },
                    }
                ],
            },
        }
        case = {
            "id": "ADVANCED-PROGRAMMING-ALERT-002",
            "expectedSecurityOutcome": "quarantine_required",
            "expectedCyberLACEPatterns": ["payment_data_copy_store_or_send"],
        }

        summary = summarize_case_response(response, case=case)

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["result"], "prompt_flight_blocked")
        self.assertTrue(summary["securityExpectationSatisfied"])
        self.assertEqual(summary["securityRuntimeAction"], "QUARANTINE")
        self.assertEqual(summary["securityDecisionStage"], "cyberlace_preflight")
        self.assertTrue(summary["securityExpectedPatternsSatisfied"])
        self.assertEqual(summary["observedCyberLACEPatterns"], ["payment_data_copy_store_or_send"])
        self.assertFalse(summary["infrastructureFailure"])

    def test_prompt_flight_expected_cyberlace_pattern_mismatch_remains_blocked(self):
        response = {
            "ok": False,
            "traceId": "prompt-flight-alert-pattern-mismatch",
            "report": {
                "traceId": "prompt-flight-alert-pattern-mismatch",
                "result": "prompt_flight_blocked",
                "status": "blocked",
                "stages": [
                    {
                        "name": "cyberlace_preflight",
                        "status": "blocked",
                        "evidence": {
                            "runtimeAction": "QUARANTINE",
                            "blocked": True,
                            "evidencePatterns": ["different_security_pattern"],
                        },
                    }
                ],
            },
        }
        case = {
            "id": "ADVANCED-PROGRAMMING-ALERT-003",
            "expectedSecurityOutcome": "quarantine_required",
            "expectedCyberLACEPatterns": ["payment_data_copy_store_or_send"],
        }

        summary = summarize_case_response(response, case=case)

        self.assertEqual(summary["status"], "blocked")
        self.assertFalse(summary["securityExpectationSatisfied"])
        self.assertFalse(summary["securityExpectedPatternsSatisfied"])
        self.assertEqual(summary["observedCyberLACEPatterns"], ["different_security_pattern"])

    def test_prompt_flight_unexpected_cyberlace_quarantine_remains_blocked(self):
        response = {
            "ok": False,
            "traceId": "prompt-flight-unexpected-block",
            "report": {
                "traceId": "prompt-flight-unexpected-block",
                "result": "prompt_flight_blocked",
                "status": "blocked",
                "stages": [
                    {
                        "name": "cyberlace_preflight",
                        "status": "blocked",
                        "evidence": {"runtimeAction": "QUARANTINE", "blocked": True},
                    }
                ],
            },
        }

        summary = summarize_case_response(response, case={"id": "PF-NORMAL", "expectedSecurityOutcome": "allow"})

        self.assertEqual(summary["status"], "blocked")
        self.assertFalse(summary["securityExpectationSatisfied"])

    def test_prompt_flight_batch_counts_expected_security_blocks_as_completed_and_continues(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            cases = [
                {"id": "PF-ALERT-001", "title": "normal", "prompt": "normal", "mode": "trace_only", "timeoutSeconds": 10, "expectedSecurityOutcome": "allow"},
                {"id": "PF-ALERT-002", "title": "camouflaged", "prompt": "blocked", "mode": "trace_only", "timeoutSeconds": 10, "expectedSecurityOutcome": "quarantine_or_human_review", "expectedCyberLACEPatterns": ["fragmented_secret_reassembly"]},
                {"id": "PF-ALERT-003", "title": "after", "prompt": "after", "mode": "trace_only", "timeoutSeconds": 10, "expectedSecurityOutcome": "allow"},
            ]
            order = []

            def request_case(payload, case):
                order.append(case["id"])
                if case["id"] == "PF-ALERT-002":
                    return {
                        "ok": False,
                        "traceId": payload["traceId"],
                        "report": {
                            "traceId": payload["traceId"],
                            "result": "prompt_flight_blocked",
                            "status": "blocked",
                            "stages": [
                                {
                                    "name": "cyberlace_preflight",
                                    "status": "blocked",
                                    "evidence": {"runtimeAction": "HUMAN_REVIEW", "blocked": True, "evidencePatterns": ["fragmented_secret_reassembly"]},
                                }
                            ],
                        },
                    }
                return {
                    "ok": True,
                    "traceId": payload["traceId"],
                    "report": {"traceId": payload["traceId"], "result": "prompt_flight_ok", "stages": []},
                }

            runner = PromptFlightBatchRunner(repo_root=repo, cases=cases, batch_id="prompt-flight-batch-alert-security")
            summary = runner.run(
                request_case=request_case,
                base_url="http://127.0.0.1:5001",
                default_project="continuity-alert-test",
                include_harness=False,
                pause_sleep_seconds=0.01,
            )

            self.assertEqual(order, ["PF-ALERT-001", "PF-ALERT-002", "PF-ALERT-003"])
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["completed"], 3)
            self.assertEqual(summary["blocked"], 0)
            self.assertEqual(summary["failed"], 0)
            alert_case = summary["cases"][1]
            self.assertEqual(alert_case["status"], "completed")
            self.assertTrue(alert_case["securityExpectationSatisfied"])
            self.assertEqual(alert_case["securityRuntimeAction"], "HUMAN_REVIEW")
            self.assertTrue(alert_case["securityExpectedPatternsSatisfied"])
            self.assertEqual(alert_case["observedCyberLACEPatterns"], ["fragmented_secret_reassembly"])

    def test_prompt_flight_batch_continues_after_completed_case_with_stale_runtime_failure_evidence(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            cases = [
                {"id": "PF-STALE-001", "title": "Stale 1", "prompt": "Case 1", "mode": "trace_only", "timeoutSeconds": 10},
                {"id": "PF-STALE-002", "title": "Stale 2", "prompt": "Case 2", "mode": "trace_only", "timeoutSeconds": 10},
            ]
            order = []

            def request_case(payload, case):
                order.append(case["id"])
                stages = []
                if case["id"] == "PF-STALE-001":
                    stages.append({
                        "name": "ui_runtime_artifacts_read",
                        "status": "ok",
                        "evidence": {
                            "runtimeInfrastructureFailure": True,
                            "fatalInfrastructureFailure": True,
                        },
                    })
                return {
                    "ok": True,
                    "traceId": payload["traceId"],
                    "report": {
                        "traceId": payload["traceId"],
                        "result": "prompt_flight_ok",
                        "stages": stages,
                    },
                }

            runner = PromptFlightBatchRunner(repo_root=repo, cases=cases, batch_id="prompt-flight-batch-stale-infra")
            summary = runner.run(
                request_case=request_case,
                base_url="http://127.0.0.1:5001",
                default_project="continuity-stale-test",
                include_harness=False,
                pause_sleep_seconds=0.01,
            )

            self.assertEqual(order, ["PF-STALE-001", "PF-STALE-002"])
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["completed"], 2)
            self.assertEqual(summary["infrastructureFailed"], 0)
            self.assertIsNone(summary.get("stopReason"))

    def test_ui_runtime_artifacts_ignore_stale_failure_after_validated_history(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            project = repo / "workspace" / "projects" / "continuity-math-pf-001"
            runtime = project / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "project_state.json").write_text("{}", encoding="utf-8")
            (runtime / "task_queue.json").write_text("[]", encoding="utf-8")
            (runtime / "task_history.jsonl").write_text(
                json.dumps({
                    "recorded_at": "2026-05-28T02:46:04Z",
                    "result": {
                        "task_id": "RUNTIME-20260528024538-001",
                        "completed": True,
                        "files_created": ["docs/mathematics_case_001.md"],
                        "files_modified": [],
                        "validation_ran": [],
                        "validation_passed": True,
                        "blockers": [],
                        "next_recommendation": "ok",
                    },
                }) + "\n",
                encoding="utf-8",
            )
            (runtime / "failures.jsonl").write_text(
                json.dumps({
                    "recorded_at": "2026-05-28T02:13:06Z",
                    "failure": {
                        "task_id": "RUNTIME-20260528005914-001",
                        "failure": {
                            "task_result": {
                                "blockers": ["bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"]
                            }
                        },
                    },
                }) + "\n",
                encoding="utf-8",
            )
            probe = PromptFlightProbe(
                repo_root=repo,
                prompt="Resolver caso simple",
                mode="ui_session_rest",
                project="continuity-math-pf-001",
                base_url="",
                trace_id="prompt-flight-stale-failure-test",
                timeout_seconds=30,
                include_harness=False,
            )
            probe.ui_session = {"projectSlug": "continuity-math-pf-001"}

            result = probe._stage_ui_runtime_artifacts_read()
            artifacts = json.loads((repo / "runtime" / "continuity_probe" / "prompt-flight-stale-failure-test" / "ui_runtime_artifacts.json").read_text(encoding="utf-8"))

            self.assertFalse(result["runtimeInfrastructureFailure"])
            self.assertFalse(result["fatalInfrastructureFailure"])
            self.assertFalse(artifacts["latestFailureIncludedInClassification"])
            self.assertEqual(artifacts["latestFailureIgnoredReason"], "stale_failure_for_different_task:RUNTIME-20260528005914-001")

    def test_ui_runtime_artifacts_ignore_different_task_failure_even_without_completed_history(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            project = repo / "workspace" / "projects" / "continuity-stale-active"
            runtime = project / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "project_state.json").write_text("{}", encoding="utf-8")
            (runtime / "task_queue.json").write_text("[]", encoding="utf-8")
            (runtime / "task_history.jsonl").write_text(json.dumps({
                "recorded_at": "2026-05-28T02:46:04Z",
                "result": {
                    "task_id": "CURRENT-TASK",
                    "completed": False,
                    "files_created": [],
                    "files_modified": [],
                    "validation_ran": [],
                    "validation_passed": False,
                    "blockers": ["current task still closing"],
                    "next_recommendation": "continue",
                },
            }) + "\n", encoding="utf-8")
            (runtime / "failures.jsonl").write_text(json.dumps({
                "recorded_at": "2026-05-28T02:13:06Z",
                "failure": {
                    "task_id": "OLD-TASK",
                    "failure": {"task_result": {"blockers": ["bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"]}},
                },
            }) + "\n", encoding="utf-8")
            probe = PromptFlightProbe(
                repo_root=repo,
                prompt="Resolver caso simple",
                mode="ui_session_rest",
                project="continuity-stale-active",
                base_url="",
                trace_id="prompt-flight-stale-active-failure-test",
                timeout_seconds=30,
                include_harness=False,
            )
            probe.ui_session = {"projectSlug": "continuity-stale-active"}

            result = probe._stage_ui_runtime_artifacts_read()
            artifacts = json.loads((repo / "runtime" / "continuity_probe" / "prompt-flight-stale-active-failure-test" / "ui_runtime_artifacts.json").read_text(encoding="utf-8"))

            self.assertFalse(result["runtimeInfrastructureFailure"])
            self.assertFalse(result["fatalInfrastructureFailure"])
            self.assertFalse(artifacts["latestFailureIncludedInClassification"])
            self.assertEqual(artifacts["latestFailureIgnoredReason"], "stale_failure_for_different_task:OLD-TASK")

    def test_prompt_flight_batch_pauses_immediately_on_fatal_infrastructure_failure(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            cases = [
                {"id": "PF-INFRA-001", "title": "Infra 1", "prompt": "Case 1", "mode": "trace_only", "timeoutSeconds": 10},
                {"id": "PF-INFRA-002", "title": "Infra 2", "prompt": "Case 2", "mode": "trace_only", "timeoutSeconds": 10},
            ]
            order = []

            def request_case(payload, case):
                order.append(case["id"])
                return {
                    "ok": False,
                    "traceId": payload["traceId"],
                    "report": {
                        "traceId": payload["traceId"],
                        "result": "prompt_flight_failed",
                        "stages": [
                            {
                                "name": "ui_runtime_artifacts_read",
                                "status": "ok",
                                "evidence": {
                                    "runtimeInfrastructureFailure": True,
                                    "fatalInfrastructureFailure": True,
                                },
                            }
                        ],
                    },
                }

            runner = PromptFlightBatchRunner(repo_root=repo, cases=cases, batch_id="prompt-flight-batch-fatal-infra")
            summary = runner.run(
                request_case=request_case,
                base_url="http://127.0.0.1:5001",
                default_project="continuity-infra-test",
                include_harness=False,
                pause_sleep_seconds=0.01,
            )

            self.assertEqual(order, ["PF-INFRA-001"])
            self.assertEqual(summary["status"], "paused_infrastructure_failures")
            self.assertEqual(summary["stopReason"], "fatal_runtime_infrastructure_failure")
            self.assertEqual(summary["infrastructureFailed"], 1)
            self.assertEqual(summary["pending"], 1)

    def test_prompt_flight_batch_runner_pauses_after_three_infrastructure_failures(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            cases = [
                {"id": f"PF-{index:03d}", "title": str(index), "prompt": f"Case {index}", "mode": "trace_only", "timeoutSeconds": 10}
                for index in range(1, 5)
            ]
            order = []

            def request_case(payload, case):
                order.append(case["id"])
                return {"ok": False, "error": "connection_failed", "message": "backend unavailable", "statusCode": 0}

            runner = PromptFlightBatchRunner(repo_root=repo, cases=cases, batch_id="prompt-flight-batch-infra", max_consecutive_infra_failures=3)
            summary = runner.run(
                request_case=request_case,
                base_url="http://127.0.0.1:5001",
                default_project="continuity-batch-test",
                include_harness=False,
                pause_sleep_seconds=0.01,
            )

            self.assertEqual(order, ["PF-001", "PF-002", "PF-003"])
            self.assertEqual(summary["status"], "paused_infrastructure_failures")
            self.assertEqual(summary["infrastructureFailed"], 3)
            self.assertEqual(summary["pending"], 1)
            self.assertEqual(summary["stopReason"], "max_consecutive_infrastructure_failures")




    def test_prompt_flight_batch_pauses_when_timeout_cleanup_is_not_confirmed(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            cases = [
                {"id": "PF-CLEANUP-001", "title": "Cleanup 1", "prompt": "Case 1", "mode": "trace_only", "timeoutSeconds": 10},
                {"id": "PF-CLEANUP-002", "title": "Cleanup 2", "prompt": "Case 2", "mode": "trace_only", "timeoutSeconds": 10},
            ]
            order = []

            def request_case(payload, case):
                order.append(case["id"])
                trace_id = payload["traceId"]
                return {
                    "ok": False,
                    "traceId": trace_id,
                    "report": {
                        "traceId": trace_id,
                        "status": "failed",
                        "result": "prompt_flight_failed",
                        "summary": {"ok": 1, "failed": 1, "blocked": 0, "total": 2},
                        "artifacts": {"reportPath": f"runtime/continuity_probe/{trace_id}/prompt_flight_report.json"},
                        "stages": [
                            {"name": "ui_agent_session_polled", "status": "timeout", "evidence": {"sessionId": "agent-cleanup", "stopRequestedAfterTimeout": True, "stopConfirmedAfterTimeout": False}}
                        ],
                    },
                }

            runner = PromptFlightBatchRunner(repo_root=repo, cases=cases, batch_id="prompt-flight-batch-cleanup")
            summary = runner.run(
                request_case=request_case,
                base_url="http://127.0.0.1:5001",
                default_project="continuity-cleanup-test",
                include_harness=False,
                pause_sleep_seconds=0.01,
            )

            self.assertEqual(order, ["PF-CLEANUP-001"])
            self.assertEqual(summary["status"], "paused_cleanup_failed")
            self.assertEqual(summary["stopReason"], "session_cleanup_failed_after_timeout")
            self.assertEqual(summary["pending"], 1)

    def test_prompt_flight_batch_runner_records_reset_request(self):
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_minimal_repo(repo)
            cases = [
                {"id": "PF-RESET", "title": "Reset", "prompt": "Case reset", "mode": "trace_only", "timeoutSeconds": 10},
            ]
            runner = PromptFlightBatchRunner(repo_root=repo, cases=cases, batch_id="prompt-flight-batch-reset")
            events = []
            runner._start()
            runner.request_cancel(
                reason="test_reset",
                evidence={"activeCaseId": "PF-RESET", "activeProjectSlug": "continuity-reset", "activeSessionId": "agent-reset"},
                event_callback=events.append,
            )

            state_path = repo / "runtime" / "continuity_probe" / "batches" / "prompt-flight-batch-reset" / "batch_state.json"
            events_path = repo / "runtime" / "continuity_probe" / "batches" / "prompt-flight-batch-reset" / "batch_events.jsonl"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            event_lines = events_path.read_text(encoding="utf-8").splitlines()

            self.assertEqual(state["status"], "reset_requested")
            self.assertEqual(state["stopReason"], "test_reset")
            self.assertEqual(state["cancelEvidence"]["activeSessionId"], "agent-reset")
            self.assertEqual(events[-1]["event"], "batch_reset_requested")
            self.assertTrue(any('"batch_reset_requested"' in line for line in event_lines))



    def test_prompt_flight_simple_task_can_complete_with_host_write_and_validator(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            task = {
                "id": "PROMPT-FLIGHT-HOST-WRITE-001",
                "title": "Prompt Flight simple host write",
                "goal": "Create the file docs/host_write_smoke.md. Its complete contents must be exactly HOST_WRITE_OK.",
                "status": "pending",
                "priority": 10,
                "dependencies": [],
                "expected_files": ["docs/host_write_smoke.md"],
                "validation_commands": [],
                "timeout_seconds": 30,
                "max_retries": 0,
                "mode": "build",
                "checkpoint_key": None,
            }

            execution = execute_task_with_details(task, workspace=workspace)
            validation = validate_task_execution(task, execution, workspace=workspace)

            self.assertEqual(execution["execution"]["execution_strategy"], "host_write")
            self.assertEqual((workspace / "docs" / "host_write_smoke.md").read_text(encoding="utf-8"), "HOST_WRITE_OK")
            self.assertTrue(validation["task_result"]["completed"])
            self.assertTrue(validation["task_result"]["validation_passed"])

    def test_bwrap_complex_task_remains_infrastructure_fatal_without_host_write(self):
        task = {
            "id": "PROMPT-FLIGHT-COMPLEX-BWRAP-001",
            "title": "Complex Flask refactor",
            "goal": "Refactor backend Flask runtime and debug Codex worker execution.",
            "status": "pending",
            "priority": 10,
            "dependencies": [],
            "expected_files": ["backend/runtime.py"],
            "validation_commands": [],
            "timeout_seconds": 30,
            "max_retries": 3,
            "mode": "build",
            "checkpoint_key": None,
        }
        failure = {
            "task_result": {
                "task_id": task["id"],
                "completed": False,
                "files_created": [],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": False,
                "blockers": ["bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"],
                "next_recommendation": "",
            }
        }

        decision = decide_recovery(task, failure, retry_count=0)

        self.assertEqual(decision["action"], "block")
        self.assertTrue(decision["fatalInfrastructureFailure"])
        self.assertFalse(decision["retry"])
        self.assertFalse(decision["split"])
        self.assertFalse(decision["extendTimeout"])
        self.assertFalse(decision["retryWithHostWriteExecutor"])


if __name__ == "__main__":
    unittest.main()
