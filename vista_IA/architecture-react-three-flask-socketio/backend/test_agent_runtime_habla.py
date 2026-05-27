from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch
import time

from agent_runtime import (
    AgentRuntime,
    AgentSession,
    LaceContext,
    build_lace_cycle_plan,
    initialize_lace_log,
    build_preferred_shell_path,
    resolve_codex_command_tokens,
)


LACE_POLICY_TEXT = "\n".join(
    [
        "CAPA 1 — INTERPRETACIÓN",
        "CAPA 2 — CLASIFICACIÓN SEMÁNTICA",
        "CAPA 3 — PLANIFICACIÓN DEL RAZONAMIENTO",
        "CAPA 4 — REACT",
        "CAPA 5 — RECUPERACIÓN Y EVIDENCIA",
        "CAPA 6 — TRIANGULACIÓN",
        "CAPA 7 — CONFIANZA POR COMPONENTE",
        "CAPA 8 — AUTO-CRÍTICA",
        "CAPA 9 — MEMORIA EPISÓDICA",
        "CAPA 10 — RESPUESTA",
    ]
)


def fake_habla_payload(_requirement: str) -> dict:
    return {
        "available": True,
        "prompt": "PROTOCOLO HABLA DE PRUEBA",
        "state": {
            "knowledgeType": "HECHO_ESTABLE",
            "toolRequired": "memory_optional",
            "strategy": "memoria_con_verificacion_opcional",
            "triangulatedText": "La respuesta se apoya en memoria y contraste inicial.",
            "answerPreview": "Respuesta tentativa de prueba.",
            "safeToAnswer": True,
            "blocked": False,
            "directive": "Responde con limites y sin inventar datos.",
            "confidence": {
                "dato": 85,
                "fecha": 80,
                "fuente": 60,
                "calculo": 0,
                "inferencia": 20,
                "global": 49.0,
            },
            "debug": ["CLASSIFY => HECHO_ESTABLE / memory_optional", "THOUGHT => usar memoria interna"],
            "sources": [
                {
                    "source": "memoria_llm",
                    "value": None,
                    "text": "Conocimiento estable recuperado desde memoria interna.",
                    "confidenceHint": 40,
                }
            ],
        },
    }


def fake_blocked_calculo_payload(_requirement: str) -> dict:
    return {
        "available": True,
        "prompt": "PROTOCOLO HABLA BLOQUEADO",
        "state": {
            "knowledgeType": "CALCULO",
            "toolRequired": "calculator",
            "strategy": "calcular_exactamente",
            "triangulatedText": "Sin valores numéricos para triangular.",
            "answerPreview": "No puedo responder con seguridad suficiente.",
            "safeToAnswer": False,
            "blocked": True,
            "blockReason": "No se obtuvo evidencia suficiente después de los intentos.",
            "directive": "Responde al usuario en español, como chat natural, pero respetando todas las reglas anteriores.",
            "debug": ["PLANNER => pregunta atómica", "OBSERVATION => vacío con calculator"],
            "sources": [],
            "confidence": {
                "dato": 99,
                "fecha": 100,
                "fuente": 100,
                "calculo": 99,
                "inferencia": 0,
                "global": 99.5,
            },
        },
    }


class AgentRuntimeHablaTest(unittest.TestCase):
    def build_runtime(
        self,
        app_root: Path,
        visual_events: list[dict],
        *,
        lace_policy_source: Path | None = None,
        graph_provider=None,
        prompt_converter=fake_habla_payload,
    ) -> AgentRuntime:
        workspace_root = app_root / "workspace"
        projects_root = workspace_root / "projects"
        return AgentRuntime(
            app_root=app_root,
            workspace_root=workspace_root,
            projects_root=projects_root,
            codex_cmd="codex",
            prompt_converter=prompt_converter,
            graph_provider=graph_provider or (lambda: {"nodes": [], "edges": []}),
            graph_sync=lambda _force: {"nodes": [], "edges": []},
            terminal_emitter=lambda _payload: None,
            session_emitter=lambda _payload: None,
            visual_event_handler=visual_events.append,
            lace_policy_source=lace_policy_source,
        )

    def test_resolve_habla_payload_accepts_structured_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [])
            prompt, available, state = runtime._resolve_habla_payload("Construye una CLI")
            self.assertEqual(prompt, "PROTOCOLO HABLA DE PRUEBA")
            self.assertTrue(available)
            self.assertEqual(state["knowledgeType"], "HECHO_ESTABLE")
            self.assertEqual(state["toolRequired"], "memory_optional")

    def test_build_preferred_shell_path_removes_snap_codex_entries(self) -> None:
        raw_path = (
            "/home/neurodriver/snap/codex/34/tmp/arg0/codex-arg0demo"
            ":/snap/codex/34/bin"
            ":/usr/local/bin"
            ":/usr/bin"
        )
        preferred = build_preferred_shell_path(raw_path)
        self.assertNotIn("/snap/codex/34/bin", preferred)
        self.assertNotIn("/home/neurodriver/snap/codex/34/tmp/arg0/codex-arg0demo", preferred)
        self.assertIn("/usr/local/bin", preferred)
        self.assertIn("/usr/bin", preferred)

    def test_resolve_codex_command_tokens_prefers_non_snap_binary(self) -> None:
        with patch("agent_runtime.shutil.which") as mock_which:
            mock_which.side_effect = lambda command, path=None: (
                "/usr/local/bin/codex"
                if command == "codex" and path and "/usr/local/bin" in path and "/snap/codex/" not in path
                else "/snap/codex/34/bin/codex"
            )
            resolved = resolve_codex_command_tokens(
                "codex",
                path_value="/home/neurodriver/snap/codex/34/tmp/arg0/codex-arg0demo:/snap/codex/34/bin:/usr/local/bin:/usr/bin",
            )
        self.assertEqual(resolved[0], "/usr/local/bin/codex")

    def test_build_codex_command_accepts_composite_override(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [])
            runtime.codex_cmd = "python3 -m codex"
            runtime.codex_command_tokens = resolve_codex_command_tokens(runtime.codex_cmd, path_value="")
            command = runtime._build_codex_command(Path(tmpdir) / "project", "haz algo")
        self.assertEqual(command[:3], ["python3", "-m", "codex"])
        self.assertIn("exec", command)

    def test_build_codex_command_defaults_to_workspace_write_inner_exec(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [])
            command = runtime._build_codex_command(Path(tmpdir) / "project", "haz algo")
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        self.assertIn("-s", command)
        sandbox_index = command.index("-s")
        self.assertEqual(command[sandbox_index + 1], "workspace-write")
        self.assertIn("-C", command)
        cd_index = command.index("-C")
        self.assertEqual(command[cd_index + 2], "exec")
        self.assertNotIn("--full-auto", command)

    def test_build_codex_command_respects_inner_exec_env_override(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch.dict(
                "os.environ",
                {
                    "VISTA_CODEX_EXEC_SANDBOX_MODE": "workspace-write",
                    "VISTA_CODEX_EXEC_APPROVAL_POLICY": "on-request",
                    "VISTA_CODEX_EXEC_USE_FULL_AUTO": "0",
                },
                clear=False,
            ):
                runtime = self.build_runtime(Path(tmpdir) / "app", [])
            command = runtime._build_codex_command(Path(tmpdir) / "project", "haz algo")
        approval_index = command.index("-a")
        sandbox_index = command.index("-s")
        exec_index = command.index("exec")
        self.assertLess(approval_index, exec_index)
        self.assertLess(sandbox_index, exec_index)
        self.assertEqual(command[approval_index + 1], "on-request")
        self.assertEqual(command[sandbox_index + 1], "workspace-write")

    def test_code_generation_requirement_bypasses_blocking_habla_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [], prompt_converter=fake_blocked_calculo_payload)
            prompt, available, state = runtime._resolve_habla_payload(
                "Crea una mini aplicacion web con HTML, CSS y JavaScript y agrega pruebas."
            )

            self.assertTrue(available)
            self.assertIn("EJECUCION DE PROYECTO DE CODIGO", prompt)
            self.assertEqual(state["knowledgeType"], "PROYECTO_CODIGO")
            self.assertEqual(state["toolRequired"], "filesystem")
            self.assertEqual(state["strategy"], "construir_y_validar")
            self.assertTrue(state["safeToAnswer"])
            self.assertFalse(state["blocked"])
            self.assertEqual(state["blockReason"], "")
            self.assertIn("coding_task_bypass_habla_block", " ".join(state.get("debug") or []))

    def test_create_project_can_force_unique_slug(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [])
            first = runtime.create_project("smoke-ui")
            second = runtime.create_project("smoke-ui", ensure_unique=True)

            self.assertEqual(first["slug"], "smoke-ui")
            self.assertEqual(second["slug"], "smoke-ui-2")
            self.assertEqual(second["name"], "smoke-ui-2")
            self.assertTrue((runtime.projects_root / "smoke-ui").exists())
            self.assertTrue((runtime.projects_root / "smoke-ui-2").exists())

    def test_create_project_without_bootstrap_keeps_project_empty(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [])
            project = runtime.create_project("from-zero", bootstrap=False, ensure_unique=True)
            project_dir = runtime.projects_root / project["slug"]

            self.assertTrue((project_dir / "src").exists())
            self.assertFalse((project_dir / "README.md").exists())
            self.assertFalse((project_dir / "src" / "main.js").exists())
            self.assertFalse((project_dir / "src" / "service.js").exists())

    def test_create_project_without_bootstrap_does_not_delete_existing_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [])
            project = runtime.create_project("existing-project")
            project_dir = runtime.projects_root / project["slug"]

            runtime.create_project("existing-project", bootstrap=False)

            self.assertTrue((project_dir / "README.md").exists())
            self.assertTrue((project_dir / "src" / "main.js").exists())
            self.assertTrue((project_dir / "src" / "service.js").exists())

    def test_start_session_respects_explicit_existing_project_slug(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [])
            existing = runtime.create_project("Mini UI 01", bootstrap=False, preferred_slug="mini-ui-01")

            class FakeThread:
                def __init__(self, target, args=(), daemon=None):
                    self.target = target
                    self.args = args
                    self.daemon = daemon

                def start(self) -> None:
                    return None

            with patch("agent_runtime.threading.Thread", FakeThread):
                session_payload = runtime.start_session(
                    requirement="Continua el proyecto existente.",
                    project_name="Nombre temporal ignorado",
                    project_slug="mini-ui-01",
                    bootstrap=False,
                    ensure_new_project=False,
                )

            self.assertEqual(session_payload["projectSlug"], "mini-ui-01")
            self.assertEqual(session_payload["projectDir"], existing["path"])
            self.assertFalse((runtime.projects_root / "mini-ui-01-2").exists())

    def test_runtime_session_lifecycle_events_are_persisted_without_duplicate_reconsume(self) -> None:
        with TemporaryDirectory() as tmpdir:
            visual_events: list[dict] = []
            runtime = self.build_runtime(Path(tmpdir) / "app", visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            event_file = project_dir / ".vista" / "runtime-events.jsonl"
            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una CLI",
                prompt="prompt completo",
                command=["codex"],
                status="running",
                event_file=event_file,
            )
            runtime.sessions[session.session_id] = session

            runtime._emit_visual_runtime_event(
                session,
                op="session_complete",
                message="La sesion termino correctamente.",
                status="completed",
                phase="complete",
            )

            event_lines = event_file.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(event_lines), 1)
            persisted = json.loads(event_lines[0])
            self.assertEqual(persisted["op"], "session_complete")
            self.assertEqual(persisted["status"], "completed")

            initial_event_count = len(visual_events)
            runtime._consume_visual_events(session.session_id)
            self.assertEqual(len(visual_events), initial_event_count)

            payload = runtime.get_session(session.session_id)
            self.assertIsNotNone(payload)
            self.assertEqual(payload["visualEventCount"], 0)

    def test_idle_timeout_schedules_retry_before_marking_session_failed(self) -> None:
        with TemporaryDirectory() as tmpdir:
            visual_events: list[dict] = []
            runtime = self.build_runtime(Path(tmpdir) / "app", visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            vista_dir = project_dir / ".vista"
            vista_dir.mkdir(parents=True, exist_ok=True)
            event_file = vista_dir / "retry-events.jsonl"
            event_file.write_text(
                json.dumps(
                    {
                        "op": "sync_file",
                        "relativePath": "frontend/app.js",
                        "description": "Ultimo controlador materializado",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            class DummyProcess:
                def __init__(self) -> None:
                    self.terminated = False

                def poll(self):
                    return None

                def terminate(self) -> None:
                    self.terminated = True

            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Continua el proyecto.",
                prompt="prompt completo",
                command=["codex"],
                status="running",
                process=DummyProcess(),
                event_file=event_file,
                lace_cycle_states=[
                    {
                        "cycle": 4,
                        "stage": "improving",
                        "focus": "documentacion",
                        "description": "Ciclo 04 aplicando mejora documental.",
                        "isCurrent": True,
                    }
                ],
            )
            runtime.sessions[session.session_id] = session

            runtime._fail_session(
                session.session_id,
                error_code="session_idle_timeout",
                message="La sesion quedo en silencio demasiado tiempo sin salida de terminal ni eventos del bridge.",
                returncode=125,
            )

            payload = runtime.get_session(session.session_id)
            self.assertIsNotNone(payload)
            self.assertEqual(payload["status"], "running")
            self.assertTrue(payload["retryPending"])
            self.assertEqual(payload["retryCount"], 1)
            self.assertIn("frontend/app.js", payload["lastRetryCheckpoint"])
            self.assertIn("ciclo 04", payload["lastRetryCheckpoint"])
            self.assertTrue(session.process.terminated)
            self.assertTrue(any(event.get("phase") == "retry" for event in visual_events))

    def test_prepare_retry_attempt_rebuilds_prompt_from_checkpoint(self) -> None:
        with TemporaryDirectory() as tmpdir:
            visual_events: list[dict] = []
            runtime = self.build_runtime(Path(tmpdir) / "app", visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            (project_dir / ".vista").mkdir(parents=True, exist_ok=True)
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            (project_dir / "frontend" / "app.js").write_text("console.log('ok');\n", encoding="utf-8")
            lace_policy_path = project_dir / "LACE.md"
            lace_policy_path.write_text(LACE_POLICY_TEXT, encoding="utf-8")
            lace_log_path = project_dir / "LACE_LOG.md"
            initialize_lace_log(
                lace_log_path,
                project_prompt="Continua el proyecto.",
                policy_path=lace_policy_path,
                required_cycles=2,
            )
            event_file = project_dir / ".vista" / "retry-events.jsonl"
            event_file.write_text(
                json.dumps(
                    {
                        "op": "focus_node",
                        "relativePath": "frontend/app.js",
                        "description": "Controlador actual",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Continua el proyecto.",
                prompt="prompt viejo",
                command=["codex", "exec", "prompt viejo"],
                status="running",
                event_file=event_file,
                lace_policy_path=lace_policy_path,
                lace_log_path=lace_log_path,
                lace_required_cycles=2,
                retry_count=1,
                retry_limit=5,
                retry_pending=True,
                last_retry_reason="session_idle_timeout",
                last_retry_checkpoint="ciclo 01 en improving; focus_node en frontend/app.js",
            )
            runtime.sessions[session.session_id] = session

            payload = runtime._prepare_retry_attempt(session.session_id)

            self.assertIsNotNone(payload)
            live_session = runtime.sessions[session.session_id]
            self.assertFalse(live_session.retry_pending)
            self.assertEqual(live_session.status, "queued")
            self.assertIn("REINTENTO AUTOMATICO POR TIMEOUT DEL RUNTIME", live_session.prompt)
            self.assertIn("frontend/app.js", live_session.prompt)
            self.assertEqual(live_session.command[-1], live_session.prompt)

    def test_write_habla_preflight_and_session_dict_include_habla(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(app_root, visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            lace_log_path = project_dir / "LACE_LOG.md"
            lace_log_path.write_text("# LACE_LOG.md\n", encoding="utf-8")
            lace_context = LaceContext(
                policy_text=LACE_POLICY_TEXT,
                directive="No cierres antes de completar ciclos reales.",
                policy_path=project_dir / "LACE.md",
                log_path=lace_log_path,
                required_cycles=10,
            )
            preflight_path = runtime._write_habla_preflight(
                project_dir=project_dir,
                requirement="Construye una CLI",
                habla_prompt="PROTOCOLO HABLA DE PRUEBA",
                habla_available=True,
                habla_state=fake_habla_payload("x")["state"],
                lace_context=lace_context,
            )
            content = preflight_path.read_text(encoding="utf-8")
            self.assertIn("Prompt HABLA BASIC", content)
            self.assertIn("knowledgeType: HECHO_ESTABLE", content)
            self.assertIn("ciclos maximos: 10", content)
            self.assertIn("salida temprana", content)

            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una CLI",
                prompt="prompt completo",
                command=["codex"],
                habla_prompt="PROTOCOLO HABLA DE PRUEBA",
                habla_available=True,
                habla_preflight_path=preflight_path,
                lace_log_path=lace_log_path,
                lace_required_cycles=10,
                habla_state=fake_habla_payload("x")["state"],
            )
            payload = session.to_dict()
            self.assertTrue(payload["habla"]["available"])
            self.assertEqual(payload["habla"]["state"]["knowledgeType"], "HECHO_ESTABLE")
            self.assertEqual(payload["hablaPreflightPath"], str(preflight_path))

    def test_emit_preflight_visuals_emits_habla_and_lace_nodes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(app_root, visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            preflight_path = project_dir / "docs" / "habla-session.md"
            preflight_path.parent.mkdir(parents=True, exist_ok=True)
            preflight_path.write_text("# HABLA\n", encoding="utf-8")
            lace_log_path = project_dir / "LACE_LOG.md"
            lace_log_path.write_text("# LACE_LOG.md\n", encoding="utf-8")
            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una CLI",
                prompt="prompt completo",
                command=["codex"],
                habla_prompt="PROTOCOLO HABLA DE PRUEBA",
                habla_available=True,
                habla_preflight_path=preflight_path,
                lace_log_path=lace_log_path,
                lace_required_cycles=10,
                habla_state=fake_habla_payload("x")["state"],
            )

            runtime.sessions[session.session_id] = session
            runtime._emit_preflight_visuals(session)

            ops = [event["op"] for event in visual_events]
            self.assertIn("phase", ops)
            self.assertIn("upsert_node", ops)
            self.assertIn("sync_file", ops)
            self.assertIn("upsert_edge", ops)
            self.assertTrue(any(event.get("relativePath") == "docs/habla-session.md" for event in visual_events))
            self.assertTrue(any(event.get("relativePath") == "LACE_LOG.md" for event in visual_events))

    def test_runtime_scaffolding_events_do_not_count_as_real_agent_visual_activity(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(app_root, visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una CLI",
                prompt="prompt completo",
                command=["codex"],
            )
            runtime.sessions[session.session_id] = session

            runtime._dispatch_runtime_payload(
                session.session_id,
                {
                    "op": "upsert_node",
                    "relativePath": "docs/lace_cycles/ciclo-01.md",
                    "message": "Ciclo reservado",
                },
                count_visual=True,
                track_activity=False,
            )

            snapshot = runtime.get_session(session.session_id)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot["visualEventCount"], 0)
            self.assertIsNone(snapshot["firstVisualEventAt"])
            self.assertIsNone(snapshot["lastVisualEventAt"])
            self.assertEqual(snapshot["progressPercent"], 0)
            self.assertEqual(snapshot["progressLabel"], "En cola")

    def test_sync_lace_log_from_bridge_does_not_count_as_code_materialization(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(app_root, visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una CLI",
                prompt="prompt completo",
                command=["codex"],
                status="running",
            )
            runtime.sessions[session.session_id] = session

            runtime._dispatch_runtime_payload(
                session.session_id,
                {
                    "op": "sync_file",
                    "relativePath": "LACE_LOG.md",
                    "sourcePath": "LACE_LOG.md",
                },
                count_visual=True,
                track_activity=True,
            )

            snapshot = runtime.get_session(session.session_id)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot["progressPercent"], 26)
            self.assertEqual(snapshot["progressLabel"], "Sincronizando bitacoras y contexto de trabajo")

    def test_sync_lace_runtime_fails_session_when_only_scaffolding_exists_without_real_activity(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(app_root, visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            lace_log_path = project_dir / "LACE_LOG.md"
            lace_log_path.write_text("# LACE_LOG.md\n", encoding="utf-8")
            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una app",
                prompt="prompt completo",
                command=["codex"],
                status="running",
                lace_log_path=lace_log_path,
                lace_required_cycles=10,
            )
            session.start_monotonic = time.monotonic() - 120
            runtime.sessions[session.session_id] = session

            runtime._sync_lace_runtime(session.session_id)

            snapshot = runtime.get_session(session.session_id)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot["status"], "failed")
            self.assertEqual(snapshot["errorCode"], "agent_start_timeout")
            self.assertEqual(snapshot["returncode"], 123)

    def test_sync_lace_runtime_updates_cycle_visuals_one_by_one(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(app_root, visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            lace_log_path = project_dir / "LACE_LOG.md"
            lace_log_path.write_text(
                (
                    "# LACE_LOG.md\n\n"
                    "[COMPRENSIÓN DEL PROYECTO]\n"
                    "Construir una CLI real.\n\n"
                    "[PLAN PARA 2 CICLOS]\n"
                    f"{build_lace_cycle_plan(2)}\n\n"
                    "[BASE] Construcción inicial completada.\n"
                    "Estado actual: Existe una base funcional verificable.\n\n"
                    "[CICLO-1 PROBLEMAS]\n"
                    "THOUGHT: Revisé el flujo y detecté un hueco concreto.\n"
                    "TRIANGULACIÓN: técnico: faltaba una rama; funcional: el flujo era incompleto; humano: la salida no era clara.\n"
                    "CONFIANZA: lógica media, UI media, rendimiento alta, errores media, seguridad media.\n"
                    "AUTO-CRÍTICA: Cerrar ahora ocultaría una debilidad visible.\n\n"
                    "Problemas priorizados:\n"
                    "1. Falta una mejora concreta — severidad: alta\n\n"
                    "[CICLO-1 MEJORA]\n"
                    "THOUGHT: Voy a cerrar la brecha detectada.\n"
                    "ACTION: Implementar una mejora verificable.\n"
                    "OBSERVATION esperada: El flujo queda estable.\n\n"
                    "[CICLO-1 COMPLETADO]\n"
                    "OBSERVATION real: La mejora quedó validada con evidencia escrita.\n"
                    "¿Coincide con OBSERVATION esperada? SI\n"
                    "Problemas resueltos: La brecha prioritaria quedó cubierta.\n"
                    "Estado ahora vs antes: El proyecto es mejor que antes.\n"
                    "¿El proyecto mejoró objetivamente? SI\n\n"
                    "MEMORIA EPISÓDICA:\n"
                    "- Qué funcionó: Validar explícitamente.\n"
                    "- Qué no funcionó: Un primer enfoque superficial.\n"
                    "- Qué evitar en el próximo ciclo: Cerrar sin contrastar.\n\n"
                    "Próximo ciclo — qué atacaré: Revisión final.\n"
                ),
                encoding="utf-8",
            )
            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una CLI",
                prompt="prompt completo",
                command=["codex"],
                habla_prompt="PROTOCOLO HABLA DE PRUEBA",
                habla_available=True,
                lace_log_path=lace_log_path,
                lace_required_cycles=2,
                habla_state=fake_habla_payload("x")["state"],
            )
            runtime.sessions[session.session_id] = session
            runtime._initialize_lace_cycle_visuals(session)
            runtime._sync_lace_runtime(session.session_id)

            payload = runtime.get_session(session.session_id)
            self.assertEqual(len(payload["laceCycles"]), 1)
            self.assertEqual(payload["laceCycles"][0]["stage"], "validated")
            self.assertTrue(payload["laceCycles"][0]["valid"])
            cycle_file = project_dir / "docs" / "lace_cycles" / "ciclo-01.md"
            missing_cycle_file = project_dir / "docs" / "lace_cycles" / "ciclo-02.md"
            self.assertTrue(cycle_file.exists())
            self.assertFalse(missing_cycle_file.exists())
            self.assertIn("Valido para cierre LACE: si", cycle_file.read_text(encoding="utf-8"))
            self.assertTrue(any(event.get("phase") == "lace-cycle-01-validated" for event in visual_events))

    def test_initialize_lace_cycle_visuals_does_not_create_placeholders_from_init_log(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(app_root, visual_events)
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            lace_log_path = project_dir / "LACE_LOG.md"
            initialize_lace_log(
                lace_log_path,
                project_prompt="Construir una CLI real.",
                policy_path=project_dir / "LACE.md",
                required_cycles=3,
            )
            session = AgentSession(
                session_id="agent-test",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una CLI",
                prompt="prompt completo",
                command=["codex"],
                lace_log_path=lace_log_path,
                lace_required_cycles=3,
            )
            runtime.sessions[session.session_id] = session

            runtime._initialize_lace_cycle_visuals(session)

            payload = runtime.get_session(session.session_id)
            self.assertEqual(payload["laceCycles"], [])
            self.assertFalse((project_dir / "docs" / "lace_cycles" / "ciclo-01.md").exists())
            self.assertFalse(any(event.get("relativePath") == "docs/lace_cycles/ciclo-01.md" for event in visual_events))

    def test_prompt_for_existing_project_includes_resume_rules_and_pending_paths(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "demo-agent"
            (project_dir / ".vista").mkdir(parents=True, exist_ok=True)
            initialize_lace_log(
                project_dir / "LACE_LOG.md",
                project_prompt="Construir una CLI real.",
                policy_path=project_dir / "LACE.md",
                required_cycles=3,
            )
            (project_dir / "LACE_LOG.md").write_text(
                (project_dir / "LACE_LOG.md").read_text(encoding="utf-8")
                + "\n[HABLA INICIAL]\nListo.\n\n[PRE-BASE]\nTHOUGHT: crear archivos reales.\n",
                encoding="utf-8",
            )
            (project_dir / ".vista" / "resume-events.jsonl").write_text(
                "\n".join(
                    [
                        '{"op":"upsert_node","relativePath":"src/main.js"}',
                        '{"op":"upsert_node","relativePath":"frontend/index.html"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            prompt = runtime._build_codex_prompt(
                requirement="Continua este proyecto",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                habla_prompt="PROTOCOLO HABLA DE PRUEBA",
                habla_available=True,
                habla_state=fake_habla_payload("x")["state"],
                lace_context=None,
                smoke_mode=False,
                continuing_existing_project=True,
            )

            self.assertIn("Contexto de continuidad del proyecto:", prompt)
            self.assertIn("src/main.js", prompt)
            self.assertIn("frontend/index.html", prompt)
            self.assertIn("No vuelvas a escribir `[COMPRENSIÓN DEL PROYECTO]`, `HABLA INICIAL` o `[PRE-BASE]`", prompt)
            self.assertIn("Runtime Sandbox", prompt)
            self.assertIn("package.json con script dev/start", prompt)

    def test_start_session_reuses_existing_running_session_for_same_project(self) -> None:
        with TemporaryDirectory() as tmpdir:
            runtime = self.build_runtime(Path(tmpdir) / "app", [])
            project_dir = runtime.projects_root / "demo-agent"
            project_dir.mkdir(parents=True, exist_ok=True)
            active_session = AgentSession(
                session_id="agent-existing",
                project_name="Demo Agent",
                project_slug="demo-agent",
                project_dir=project_dir,
                requirement="Construye una CLI",
                prompt="prompt completo",
                command=["codex"],
                status="running",
            )
            runtime.sessions[active_session.session_id] = active_session

            payload = runtime.start_session(
                requirement="Continua este proyecto",
                project_name="demo-agent",
                bootstrap=False,
                ensure_new_project=False,
            )

            self.assertEqual(payload["sessionId"], "agent-existing")
            self.assertEqual(len(runtime.sessions), 1)

    def test_start_session_marks_smoke_mode_and_skips_lace_bootstrap(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            app_root.mkdir(parents=True, exist_ok=True)
            visual_events: list[dict] = []
            lace_policy_path = app_root / "policy" / "LACE.md"
            lace_policy_path.parent.mkdir(parents=True, exist_ok=True)
            lace_policy_path.write_text(LACE_POLICY_TEXT, encoding="utf-8")
            runtime = self.build_runtime(app_root, visual_events, lace_policy_source=lace_policy_path)

            class FakeThread:
                def __init__(self, target, args=(), daemon=None):
                    self.target = target
                    self.args = args
                    self.daemon = daemon

                def start(self) -> None:
                    return None

            requirement = (
                "Crea docs/internal-smoke.md con una nota breve de verificacion. "
                "En src/service.js agrega export function smokeCheck() que retorne un objeto con status: \"ok\", project y checkedAt. "
                "En src/main.js invoca smokeCheck() y muestra su resultado con console.log. "
                "Haz cambios minimos, reales y conectados. Sin romper runProjectService existente."
            )

            with patch("agent_runtime.threading.Thread", FakeThread):
                session_payload = runtime.start_session(requirement=requirement, project_name="demo-agent", mode="smoke")

            session = runtime.sessions[session_payload["sessionId"]]
            project_dir = runtime.projects_root / "demo-agent"
            self.assertTrue(session_payload["smokeMode"])
            self.assertIsNone(session_payload["laceRequiredCycles"])
            self.assertTrue(session.smoke_mode)
            self.assertEqual(session.lace_required_cycles, 0)
            self.assertEqual(session.status, "preparing")
            self.assertEqual(session.prompt, "")
            self.assertEqual(session.command, [])
            self.assertFalse((project_dir / "LACE.md").exists())
            self.assertFalse((project_dir / "LACE_LOG.md").exists())

    def test_prompt_summary_is_scoped_to_target_project_scene(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(
                app_root,
                visual_events,
                graph_provider=lambda: {
                    "nodes": [
                        {
                            "id": "a",
                            "path": "workspace/projects/target/src/main.js",
                            "layer": "frontend",
                            "layerLabel": "Frontend",
                            "workspaceScene": "target",
                        },
                        {
                            "id": "b",
                            "path": "workspace/projects/other/src/main.js",
                            "layer": "frontend",
                            "layerLabel": "Frontend",
                            "workspaceScene": "other",
                        },
                    ],
                    "edges": [],
                },
            )
            prompt = runtime._build_codex_prompt(
                requirement="Crear smoke",
                project_name="target",
                project_slug="target",
                project_dir=app_root / "workspace" / "projects" / "target",
                habla_prompt="PROTOCOLO HABLA DE PRUEBA",
                habla_available=True,
                habla_state=fake_habla_payload("x")["state"],
                lace_context=None,
                smoke_mode=True,
                continuing_existing_project=False,
            )

            self.assertIn("workspace/projects/target/src/main.js", prompt)
            self.assertNotIn("workspace/projects/other/src/main.js", prompt)

    def test_prompt_summary_for_empty_new_project_does_not_fall_back_to_workspace(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = self.build_runtime(
                app_root,
                visual_events,
                graph_provider=lambda: {
                    "metadata": {"projectName": "Workspace"},
                    "nodes": [
                        {
                            "id": "b",
                            "path": "workspace/projects/other/src/main.js",
                            "layer": "frontend",
                            "layerLabel": "Frontend",
                            "workspaceScene": "other",
                        },
                    ],
                    "edges": [],
                    "scenes": [],
                },
            )
            prompt = runtime._build_codex_prompt(
                requirement="Crear proyecto nuevo desde cero",
                project_name="nuevo-vacio",
                project_slug="nuevo-vacio",
                project_dir=app_root / "workspace" / "projects" / "nuevo-vacio",
                habla_prompt="PROTOCOLO HABLA DE PRUEBA",
                habla_available=True,
                habla_state=fake_habla_payload("x")["state"],
                lace_context=None,
                smoke_mode=True,
                continuing_existing_project=False,
            )

            self.assertIn("No hay nodos cargados en el editor visual.", prompt)
            self.assertNotIn("workspace/projects/other/src/main.js", prompt)


if __name__ == "__main__":
    unittest.main()
