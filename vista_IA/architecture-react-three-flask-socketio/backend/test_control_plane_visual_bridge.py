import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_runtime import AgentRuntime, AgentSession, build_lace_cycle_plan
from agent_runtime import is_material_project_path, is_runtime_control_path, normalize_project_relative_path
from orchestrator.directive_generator import generate_directive
from orchestrator.live_reviewer import build_reviewer_status
from orchestrator.planner import create_task
from orchestrator.recovery import decide_recovery
from orchestrator.state_store import StateStore
from orchestrator.task_queue import TaskQueue
from orchestrator.validator import validate_task_execution


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
        "10 ciclos obligatorios",
    ]
)


def build_runtime(app_root: Path, visual_events: list[dict], *, lace_policy_source: Path | None = None) -> AgentRuntime:
    return AgentRuntime(
        app_root=app_root,
        workspace_root=app_root / "workspace",
        projects_root=app_root / "workspace" / "projects",
        codex_cmd=sys.executable,
        prompt_converter=lambda _requirement: {
            "available": True,
            "prompt": "HABLA BASIC TEST",
            "state": {
                "knowledgeType": "PROYECTO_CODIGO",
                "toolRequired": "filesystem",
                "strategy": "construir_y_validar",
                "safeToAnswer": True,
                "blocked": False,
                "debug": [],
                "confidence": {"global": 90},
            },
        },
        graph_provider=lambda: {"nodes": [], "edges": []},
        graph_sync=lambda _force: {"nodes": [], "edges": []},
        terminal_emitter=lambda _payload: None,
        session_emitter=lambda _payload: None,
        visual_event_handler=visual_events.append,
        reviewer_event_handler=lambda _payload: None,
        lace_policy_source=lace_policy_source,
    )


def minimal_directive(workspace: Path) -> dict:
    task = {
        "id": "TASK-VISUAL-001",
        "title": "Build CRM shell",
        "goal": "Create the CRM shell and sync it visually.",
        "status": "pending",
        "priority": 10,
        "dependencies": [],
        "expected_files": ["frontend/index.html", "frontend/app.js"],
        "validation_commands": ["python3 -c 'print(1)'"],
        "timeout_seconds": 300,
        "max_retries": 1,
        "mode": "long-run",
        "checkpoint_key": "task-visual-001",
    }
    context = {
        "context_type": "directive_context",
        "repo_root": str(REPO_ROOT),
        "system_root": str(REPO_ROOT),
        "task_workspace_root": str(workspace),
        "degraded": False,
        "runtime_errors": [],
        "active_task": task,
        "sprint": {"number": None, "objective": "", "deliverables": [], "acceptance": [], "out_of_scope_deliverables": []},
        "checkpoint": {"checkpoint_key": None, "source": "none", "path": None},
        "audit": {"inputs": {"policy_file": str(REPO_ROOT / "AGENTS.md"), "plan_file": str(REPO_ROOT / "PLANS.md")}},
    }
    guide = {
        "task_id": task["id"],
        "guide_type": "habla_basic_procedure",
        "directive_generator_ready": True,
        "objective": {"operational_goal": task["goal"]},
        "procedure": {
            "objetivo_operativo_actual": {"task_id": task["id"], "goal": task["goal"]},
            "alcance_controlado": {"sprint_deliverables": [], "sprint_acceptance": [], "out_of_scope_deliverables": []},
            "restricciones_activas": ["No inventar progreso visual."],
            "evidencia_requerida": {"expected_files": task["expected_files"]},
            "validacion_esperada": {"validation_commands": task["validation_commands"]},
            "checkpoint_de_partida": {"checkpoint_key": None},
            "riesgos_o_bloqueos_conocidos": [],
            "criterio_de_cierre": ["Archivos esperados existen y validan."],
        },
    }
    return generate_directive(context, guide)


def build_valid_lace_cycle(cycle_number: int) -> str:
    return f"""
[CICLO-{cycle_number} PROBLEMAS]
THOUGHT: Revise el estado real del proyecto y detecte una brecha concreta en el ciclo {cycle_number}.
TRIANGULACION: tecnico = falta evidencia directa; funcional = el flujo queda incompleto; humano = el cierre no seria claro.
CONFIANZA: logica = media, ui = media, rendimiento = alta, errores = media, seguridad = media.
AUTO-CRITICA: cerrar sin este ciclo dejaria deuda visible.

Problemas priorizados:
1. La mejora del ciclo {cycle_number} no esta consolidada - severidad: alta

[CICLO-{cycle_number} MEJORA]
THOUGHT: Voy a cerrar la brecha del ciclo {cycle_number} con evidencia verificable.
ACTION: Actualizar la evidencia LACE del ciclo {cycle_number}.
OBSERVATION esperada: El ciclo {cycle_number} queda documentado y verificable.

[CICLO-{cycle_number} COMPLETADO]
OBSERVATION real: El ciclo {cycle_number} quedo validado con evidencia escrita.
Coincide con OBSERVATION esperada? SI
Problemas resueltos: La brecha prioritaria del ciclo {cycle_number} quedo cubierta.
Estado ahora vs antes: El proyecto tiene una mejora verificable frente al estado previo.
El proyecto mejoro objetivamente? SI

MEMORIA EPISODICA:
- Que funciono: validar el ciclo contra evidencia en disco.
- Que no funciono: declarar cierre solo por terminar tareas normales.
- Que evitar en el proximo ciclo: progreso sin evidencia real.

Proximo ciclo - que atacare: siguiente brecha verificable.
""".strip()


def write_lace_log(project_dir: Path, completed_cycles: int, required_cycles: int = 10) -> Path:
    log_path = project_dir / "LACE_LOG.md"
    log_path.write_text(
        (
            "# LACE_LOG.md\n\n"
            "[COMPRENSION INICIAL]\n"
            "Construir CRM con evidencia visual y ciclos LACE.\n\n"
            f"[PLAN PARA {required_cycles} CICLOS]\n"
            f"{build_lace_cycle_plan(required_cycles)}\n\n"
            "[BASE]\n"
            "Construccion inicial completada.\n"
            "Estado actual: existen tareas normales completadas con evidencia real.\n\n"
            + "\n\n".join(build_valid_lace_cycle(cycle) for cycle in range(1, completed_cycles + 1))
            + "\n"
        ),
        encoding="utf-8",
    )
    return log_path


def build_completed_task(task_id: str, dependency: str | None = None) -> dict:
    return {
        "id": task_id,
        "title": f"Normal task {task_id}",
        "goal": f"Complete normal task {task_id}",
        "status": "completed",
        "priority": 10,
        "dependencies": [dependency] if dependency else [],
        "expected_files": [f"artifacts/{task_id}.txt"],
        "validation_commands": ["python3 -c 'print(1)'"],
        "timeout_seconds": 3600,
        "max_retries": 1,
        "mode": "long-run",
        "checkpoint_key": f"{task_id.lower()}-checkpoint",
    }


def seed_completed_runtime(runtime: AgentRuntime, project_dir: Path, *, task_count: int, completed_cycles: int) -> tuple[StateStore, AgentSession]:
    runtime_dir = project_dir / "runtime"
    runtime._ensure_control_plane_runtime(runtime_dir, project_dir.name, "long-run")
    store = StateStore(runtime_dir)
    tasks = []
    previous = None
    for index in range(1, task_count + 1):
        task_id = f"RUNTIME-20260513-{index:03d}"
        task = build_completed_task(task_id, previous)
        tasks.append(task)
        previous = task_id
    TaskQueue(store, bootstrap_empty=True).enqueue_many(tasks)
    state = store.load_project_state()
    state["status"] = "completed"
    state["mode"] = "long-run"
    state["completed_tasks"] = [task["id"] for task in tasks]
    state["updated_at"] = state["created_at"]
    store.save_project_state(state)
    log_path = write_lace_log(project_dir, completed_cycles, required_cycles=10)
    session = AgentSession(
        session_id="agent-lace-gate",
        project_name="CRM LACE Gate",
        project_slug=project_dir.name,
        project_dir=project_dir,
        requirement="Construir CRM long-run con LACE.",
        prompt="",
        command=[],
        event_file=runtime_dir / "logs" / "agent-lace-gate-events.jsonl",
        terminal_file=runtime_dir / "logs" / "agent-lace-gate-terminal.log",
        control_plane_enabled=True,
        control_plane_runtime_dir=str(runtime_dir),
        runtime_mode="long-run",
        lace_log_path=log_path,
        lace_policy_path=project_dir / "LACE.md",
        lace_required_cycles=10,
    )
    runtime.sessions[session.session_id] = session
    runtime._sync_lace_runtime(session.session_id)
    return store, session


def seed_canonical_lace_cycle_evidence(store: StateStore, project_dir: Path, cycles: range) -> None:
    queue = TaskQueue(store, bootstrap_empty=True)
    existing = queue.list()
    previous = existing[-1]["id"] if existing else None
    tasks = []
    for cycle_number in cycles:
        task_id = f"LACE-20260513-{cycle_number:03d}"
        cycle_doc = f"docs/lace_cycles/ciclo-{cycle_number:02d}.md"
        task = {
            "id": task_id,
            "title": f"Completar ciclo LACE {cycle_number:02d}",
            "goal": f"Completar ciclo LACE {cycle_number:02d} con evidencia canonica.",
            "status": "completed",
            "priority": max(1, 100 - cycle_number),
            "dependencies": [previous] if previous else [],
            "expected_files": ["LACE_LOG.md", cycle_doc],
            "validation_commands": ["python3 -c 'print(1)'"],
            "timeout_seconds": 3600,
            "max_retries": 2,
            "mode": "long-run",
            "checkpoint_key": f"lace-cycle-{cycle_number:03d}-checkpoint",
        }
        tasks.append(task)
        previous = task_id
    if tasks:
        queue.enqueue_many(tasks)

    for cycle_number in cycles:
        task_id = f"LACE-20260513-{cycle_number:03d}"
        result = {
            "task_id": task_id,
            "completed": True,
            "files_created": [f"docs/lace_cycles/ciclo-{cycle_number:02d}.md"],
            "files_modified": ["LACE_LOG.md"],
            "validation_ran": ["python3 -c 'print(1)'"],
            "validation_passed": True,
            "blockers": [],
            "next_recommendation": "Continuar con el siguiente ciclo LACE.",
        }
        store.append_task_history(result)
        store.save_checkpoint(
            f"lace-cycle-{cycle_number:03d}-checkpoint",
            {
                "task_result": result,
                "validation": {"validation_passed": True},
            },
        )
        doc_path = project_dir / "docs" / "lace_cycles" / f"ciclo-{cycle_number:02d}.md"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(
            (
                f"# Ciclo {cycle_number:02d}\n\n"
                "- Estado: validated\n"
                "- Valido para cierre LACE: si\n"
                "- Validacion registrada: si\n"
            ),
            encoding="utf-8",
        )


def seed_clean_lace_quality_gates(project_dir: Path) -> None:
    runtime_dir = project_dir / "runtime"
    artifacts_dir = runtime_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "final_code_scanner_report.json").write_text(
        json.dumps(
            {
                "scanner": {
                    "visual_playback": "magnifier_line_by_line_to_last_line",
                    "scrolls_to_last_line": True,
                },
                "summary": {"filesScanned": 3, "linesScanned": 120, "charactersScanned": 2000},
                "validation": {"passed": True, "blockers": []},
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    (artifacts_dir / "file_integrity_report.json").write_text(
        json.dumps(
            {
                "summary": {"totalFindings": 0, "modifiedFiles": 0, "deletedFiles": 0, "untrackedFiles": 0},
                "validation": {"passed": True, "blockers": []},
                "findings": [],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    (artifacts_dir / "observer_findings.json").write_text(
        json.dumps(
            {
                "summary": {"totalFindings": 0, "activeFindings": 0, "resolvedFindings": 0},
                "findings": [],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    (runtime_dir / "sandbox.json").write_text(
        json.dumps(
            {
                "status": "running",
                "running": True,
                "ready": True,
                "url": "http://127.0.0.1:9000/",
                "embedUrl": "http://127.0.0.1:9000/",
                "healthcheck": {"ready": True, "statusCode": 200, "reason": "http_ready"},
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )


class ControlPlaneVisualBridgeTest(unittest.TestCase):
    def test_directive_contains_mandatory_visual_bridge_commands(self) -> None:
        with TemporaryDirectory() as tmpdir:
            directive = minimal_directive(Path(tmpdir))
            rendered = directive["rendered_instruction"]

            self.assertIn("Bridge visual obligatorio", rendered)
            for token in ("phase", "upsert-node", "connect-nodes", "focus-node", "upsert-step", "connect-steps", "sync-file"):
                self.assertIn(token, rendered)
            self.assertIn("backend/vista_agent_bridge.py", rendered)
            self.assertEqual(directive["operational_directive"]["visual_bridge"]["task_workspace_root"], str(Path(tmpdir).resolve()))

    def test_control_plane_worker_env_points_bridge_and_session_event_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "crm-demo"
            event_file = project_dir / "runtime" / "logs" / "agent-test-events.jsonl"
            session = AgentSession(
                session_id="agent-test",
                project_name="CRM Demo",
                project_slug="crm-demo",
                project_dir=project_dir,
                requirement="Build CRM",
                prompt="",
                command=[],
                event_file=event_file,
                terminal_file=project_dir / "runtime" / "logs" / "agent-test-terminal.log",
                control_plane_enabled=True,
                control_plane_runtime_dir=str(project_dir / "runtime"),
                runtime_mode="long-run",
            )
            runtime.sessions[session.session_id] = session

            env = runtime._control_plane_worker_env(
                session_id=session.session_id,
                workspace=project_dir,
                runtime_dir=project_dir / "runtime",
            )

            self.assertEqual(env["VISTA_AGENT_SESSION_ID"], "agent-test")
            self.assertEqual(env["VISTA_AGENT_PROJECT_SLUG"], "crm-demo")
            self.assertEqual(env["VISTA_AGENT_PROJECT_DIR"], str(project_dir.resolve()))
            self.assertEqual(env["VISTA_AGENT_EVENT_FILE"], str(event_file))
            self.assertIn("backend/vista_agent_bridge.py", env["VISTA_AGENT_BRIDGE"])

    def test_task_result_files_emit_sync_file_fallback(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "crm-demo"
            target = project_dir / "frontend" / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("<main>CRM</main>\n", encoding="utf-8")
            event_file = project_dir / "runtime" / "logs" / "agent-test-events.jsonl"
            session = AgentSession(
                session_id="agent-test",
                project_name="CRM Demo",
                project_slug="crm-demo",
                project_dir=project_dir,
                requirement="Build CRM",
                prompt="",
                command=[],
                event_file=event_file,
                terminal_file=project_dir / "runtime" / "logs" / "agent-test-terminal.log",
                control_plane_enabled=True,
                control_plane_runtime_dir=str(project_dir / "runtime"),
                runtime_mode="long-run",
            )
            runtime.sessions[session.session_id] = session

            runtime._emit_control_plane_sync_file_events(
                "agent-test",
                project_dir,
                {"task_id": "TASK-001", "files_created": ["frontend/index.html"], "files_modified": []},
            )

            self.assertTrue(any(event.get("op") == "sync_file" and event.get("relativePath") == "frontend/index.html" for event in visual_events))
            self.assertIn("sync_file", event_file.read_text(encoding="utf-8"))

    def test_smoke_recovery_split_continues_with_recovery_budget(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "drone-smoke-recovery"
            project_dir.mkdir(parents=True, exist_ok=True)
            runtime_dir = project_dir / "runtime"
            runtime._ensure_control_plane_runtime(runtime_dir, project_dir.name, "smoke")
            store = StateStore(runtime_dir)
            expected_file = "runtime/artifacts/runtime-001.json"
            TaskQueue(store, bootstrap_empty=True).enqueue_many(
                [
                    {
                        "id": "RUNTIME-001",
                        "title": "Crear juego drone",
                        "goal": "Crear juego drone 2D con DQN; arrancar sandbox",
                        "status": "pending",
                        "priority": 10,
                        "dependencies": [],
                        "expected_files": [expected_file],
                        "validation_commands": [
                            "python3 -B -c \"from pathlib import Path; assert Path('runtime/artifacts/runtime-001.json').exists()\""
                        ],
                        "timeout_seconds": 300,
                        "max_retries": 3,
                        "mode": "smoke",
                        "checkpoint_key": "runtime-001-checkpoint",
                    }
                ]
            )

            def command_builder(directive: dict) -> list[str]:
                task_id = directive["task"]["id"]
                if task_id == "RUNTIME-001":
                    payload = {
                        "task_result": {
                            "task_id": "RUNTIME-001",
                            "completed": False,
                            "files_created": [],
                            "files_modified": [],
                            "validation_ran": [],
                            "validation_passed": False,
                            "blockers": ["Task timed out after 300 seconds"],
                            "next_recommendation": "Retry with a smaller task or let recovery split the scope.",
                        },
                        "execution": {"timed_out": True},
                    }
                    return [sys.executable, "-c", f"print({json.dumps(payload)!r})"]
                payload = {
                    "task_result": {
                        "task_id": task_id,
                        "completed": True,
                        "files_created": [expected_file],
                        "files_modified": [],
                        "validation_ran": [],
                        "validation_passed": True,
                        "blockers": [],
                        "next_recommendation": "done",
                    }
                }
                code = (
                    "import json; from pathlib import Path; "
                    f"p=Path({expected_file!r}); p.parent.mkdir(parents=True, exist_ok=True); "
                    "p.write_text('{\"status\":\"ok\"}\\n', encoding='utf-8'); "
                    f"print({json.dumps(payload)!r})"
                )
                return [sys.executable, "-c", code]

            sequence = runtime.run_control_plane_until_idle(
                "Crear juego drone 2D con DQN y sandbox",
                mode="smoke",
                runtime_dir=runtime_dir,
                workspace=project_dir,
                directive_repo_root=REPO_ROOT,
                task_workspace_root=project_dir,
                command_builder=command_builder,
            )

            queue = TaskQueue(store).list()
            statuses = {task["id"]: task["status"] for task in queue}
            state = store.load_project_state()
            self.assertEqual(sequence["status"], "completed")
            self.assertEqual(sequence["stopped_reason"], "queue_idle")
            self.assertEqual(sequence["tasks_executed"], 3)
            self.assertTrue(all(status == "completed" for status in statuses.values()))
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["blocked_tasks"], [])
            self.assertTrue((project_dir / expected_file).exists())

    def test_split_task_with_existing_valid_evidence_skips_worker_relaunch(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "drone-existing-evidence"
            styles_path = project_dir / "frontend" / "styles.css"
            styles_path.parent.mkdir(parents=True, exist_ok=True)
            styles_path.write_text("body { margin: 0; }\n", encoding="utf-8")
            runtime_dir = project_dir / "runtime"
            runtime._ensure_control_plane_runtime(runtime_dir, project_dir.name, "build")
            store = StateStore(runtime_dir)
            TaskQueue(store, bootstrap_empty=True).enqueue_many(
                [
                    {
                        "id": "RUNTIME-001-SPLIT-002",
                        "title": "Build styles split",
                        "goal": "Produce expected file frontend/styles.css after recovery.",
                        "status": "pending",
                        "priority": 8,
                        "dependencies": [],
                        "expected_files": ["frontend/styles.css"],
                        "validation_commands": [
                            "python3 -B -c \"from pathlib import Path; assert Path('frontend/styles.css').is_file()\""
                        ],
                        "timeout_seconds": 300,
                        "max_retries": 3,
                        "mode": "build",
                        "checkpoint_key": "runtime-001-split-002-checkpoint",
                    }
                ]
            )

            def failing_command_builder(_directive: dict) -> list[str]:
                return [sys.executable, "-c", "raise SystemExit(97)"]

            sequence = runtime.run_control_plane_until_idle(
                "Produce styles after split recovery",
                mode="build",
                runtime_dir=runtime_dir,
                workspace=project_dir,
                directive_repo_root=REPO_ROOT,
                task_workspace_root=project_dir,
                command_builder=failing_command_builder,
            )

            queue = TaskQueue(store).list()
            history = store.load_task_history()
            self.assertEqual(sequence["status"], "completed")
            self.assertEqual(sequence["tasks_executed"], 1)
            self.assertTrue(sequence["results"][0]["skipped_worker"])
            self.assertTrue(sequence["results"][0]["task_result"]["validation_passed"])
            self.assertEqual(queue[0]["status"], "completed")
            self.assertTrue(history[-1]["result"]["completed"])

    def test_three_validation_failures_trigger_selective_blanqueo_protocol(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            runtime.repo_root = app_root
            project_dir = app_root / "workspace" / "projects" / "broken-build"
            (project_dir / "src").mkdir(parents=True, exist_ok=True)
            (project_dir / "src" / "main.py").write_text("print('draft')\n", encoding="utf-8")
            (project_dir / "node_modules").mkdir(parents=True, exist_ok=True)
            (project_dir / "node_modules" / "broken.js").write_text("x", encoding="utf-8")
            runtime_dir = project_dir / "runtime"
            runtime._ensure_control_plane_runtime(runtime_dir, project_dir.name, "build")
            store = StateStore(runtime_dir)
            TaskQueue(store, bootstrap_empty=True).enqueue_many(
                [
                    {
                        "id": "RUNTIME-BLANQUEO-001",
                        "title": "Build broken app",
                        "goal": "Produce a functional app that currently fails validation.",
                        "status": "pending",
                        "priority": 10,
                        "dependencies": [],
                        "expected_files": ["frontend/app.js"],
                        "validation_commands": [
                            "python3 -B -c \"from pathlib import Path; assert Path('frontend/app.js').is_file()\""
                        ],
                        "timeout_seconds": 300,
                        "max_retries": 5,
                        "mode": "build",
                        "checkpoint_key": "runtime-blanqueo-001-checkpoint",
                    }
                ]
            )

            def always_fails(_directive: dict) -> list[str]:
                payload = {
                    "task_result": {
                        "task_id": "RUNTIME-BLANQUEO-001",
                        "completed": False,
                        "files_created": [],
                        "files_modified": [],
                        "validation_ran": [],
                        "validation_passed": False,
                        "blockers": ["app no funcional end-to-end"],
                        "next_recommendation": "repair",
                    },
                    "execution": {"returncode": 1},
                }
                return [sys.executable, "-c", f"print({json.dumps(payload)!r})"]

            sequence = runtime.run_control_plane_until_idle(
                "Build app with repeated validation failures",
                mode="build",
                runtime_dir=runtime_dir,
                workspace=project_dir,
                directive_repo_root=REPO_ROOT,
                task_workspace_root=project_dir,
                command_builder=always_fails,
                max_tasks=3,
            )

            failures = store.load_failures()
            decisions = [
                event["failure"]
                for event in failures
                if isinstance(event.get("failure"), dict)
                and event["failure"].get("type") == "BLANQUEO_DECISION"
            ]
            queue = TaskQueue(store).list()
            post_tasks = [task for task in queue if task["id"] == "POST-BLANQUEO-RECOVERY"]

            self.assertEqual(sequence["tasks_executed"], 3)
            self.assertEqual(len(decisions), 1)
            self.assertEqual(decisions[0]["scope"], "selective")
            self.assertTrue(decisions[0]["allowed"])
            self.assertFalse((project_dir / "node_modules").exists())
            self.assertTrue((project_dir / "src" / "main.py").exists())
            self.assertTrue(post_tasks)
            self.assertTrue(any((runtime_dir / "logs").glob("blanqueo_decision_*.md")))
            self.assertTrue(any((app_root / "backups" / "blanqueo").glob("*/manifest.json")))
            self.assertEqual(sequence["results"][-1]["blanqueo"]["cleanup"]["scope"], "selective")

    def test_control_plane_session_keeps_lace_and_habla_visible_in_directive(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            lace_policy = app_root / "policy" / "LACE.md"
            lace_policy.parent.mkdir(parents=True, exist_ok=True)
            lace_policy.write_text(LACE_POLICY_TEXT, encoding="utf-8")
            runtime = build_runtime(app_root, visual_events, lace_policy_source=lace_policy)

            class FakeThread:
                def __init__(self, target, args=(), daemon=None):
                    self.target = target
                    self.args = args
                    self.daemon = daemon

                def start(self) -> None:
                    return None

            original_thread = sys.modules["threading"].Thread
            try:
                sys.modules["threading"].Thread = FakeThread
                payload = runtime.start_session(
                    requirement="Construir CRM long-run con frontend, shared y pruebas.",
                    project_name="crm-demo",
                    mode="long-run",
                    bootstrap=False,
                    ensure_new_project=True,
                )
            finally:
                sys.modules["threading"].Thread = original_thread

            session = runtime.sessions[payload["sessionId"]]
            self.assertEqual(session.complexity_estimate["difficulty"], "extradificil")
            self.assertEqual(session.lace_required_cycles, session.complexity_estimate["recommended_lace_cycles"])
            self.assertEqual(session.lace_required_cycles, 8)
            self.assertTrue(session.habla_available)
            self.assertEqual(session.active_task["mode"], "long-run")
            self.assertEqual(session.active_task["timeout_seconds"], 3600)
            self.assertIn("Bridge visual obligatorio", session.prompt)
            self.assertIn("LACE_LOG.md", session.prompt)
            self.assertIn("HABLA BASIC", session.prompt)
            self.assertIn("Complejidad operativa", session.prompt)
            self.assertIn("No ejecutes todos los ciclos LACE dentro de una sola tarea", session.prompt)
            self.assertTrue((session.project_dir / "LACE_LOG.md").exists())

    def test_task_defaults_use_mode_specific_timeouts(self) -> None:
        base = {
            "task_id": "TASK-TIMEOUT",
            "title": "Mode timeout",
            "goal": "Validate mode timeout assignment.",
            "priority": 10,
            "expected_files": ["README.md"],
        }

        self.assertEqual(create_task(**base, mode="smoke")["timeout_seconds"], 300)
        self.assertEqual(create_task(**base, mode="build")["timeout_seconds"], 900)
        self.assertEqual(create_task(**base, mode="long-run")["timeout_seconds"], 3600)

    def test_ui_and_backend_propagate_explicit_runtime_mode(self) -> None:
        app_source = (REPO_ROOT / "backend" / "app.py").read_text(encoding="utf-8")
        studio_source = (REPO_ROOT / "frontend" / "src" / "components" / "AgentStudio.jsx").read_text(encoding="utf-8")
        studio_utils_source = (REPO_ROOT / "frontend" / "src" / "components" / "agentStudioUtils.js").read_text(encoding="utf-8")
        workbench_source = (REPO_ROOT / "frontend" / "src" / "components" / "CodeWorkbench.jsx").read_text(encoding="utf-8")

        self.assertIn("runtimeMode", app_source)
        self.assertIn("mode=runtime_mode", app_source)
        self.assertIn('export const DEFAULT_AGENT_RUNTIME_MODE = "build"', studio_utils_source)
        self.assertIn("export const RUNTIME_MODE_PRESETS", studio_utils_source)
        self.assertIn('value: "smoke"', studio_utils_source)
        self.assertIn('value: "medium"', studio_utils_source)
        self.assertIn('value: "long-run"', studio_utils_source)
        self.assertIn("runtimeMode,", studio_source)
        self.assertIn("session_completed", app_source)
        self.assertIn("session_completed_with_warnings", app_source)
        self.assertIn('"session_blocked"', workbench_source)
        self.assertIn('"session_failed"', workbench_source)
        self.assertIn('"session_stopped"', workbench_source)
        self.assertIn("Typewriter final", workbench_source)
        self.assertIn("keepAtTop", workbench_source)

    def test_lace_closure_gate_enqueues_missing_cycles_instead_of_completing(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "lace-crm"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, session = seed_completed_runtime(runtime, project_dir, task_count=6, completed_cycles=6)
            seed_canonical_lace_cycle_evidence(store, project_dir, range(1, 7))

            gate = runtime._apply_lace_closure_gate(
                runtime_dir=project_dir / "runtime",
                workspace=project_dir,
                runtime_mode="long-run",
                session_id=session.session_id,
                allow_enqueue=True,
            )

            queue = TaskQueue(store).list()
            state = store.load_project_state()
            lace_tasks = [task for task in queue if task["id"].startswith("LACE-") and task["status"] == "pending"]
            self.assertEqual(gate["status"], "enqueued")
            self.assertEqual(gate["missing_cycles"], [7, 8, 9, 10])
            self.assertEqual([task["expected_files"][1] for task in lace_tasks], [
                "docs/lace_cycles/ciclo-07.md",
                "docs/lace_cycles/ciclo-08.md",
                "docs/lace_cycles/ciclo-09.md",
                "docs/lace_cycles/ciclo-10.md",
            ])
            self.assertTrue(all(task["timeout_seconds"] == 3600 for task in lace_tasks))
            self.assertNotEqual(state["status"], "completed")

    def test_lace_closure_gate_early_exits_after_min_cycles_when_quality_gates_clear(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "lace-crm-adaptive"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, session = seed_completed_runtime(runtime, project_dir, task_count=2, completed_cycles=2)
            seed_canonical_lace_cycle_evidence(store, project_dir, range(1, 3))
            seed_clean_lace_quality_gates(project_dir)
            state = store.load_project_state()
            state["status"] = "blocked"
            state["blocked_tasks"] = ["lace_cycles_pending"]
            store.save_project_state(state)

            gate = runtime._apply_lace_closure_gate(
                runtime_dir=project_dir / "runtime",
                workspace=project_dir,
                runtime_mode="long-run",
                session_id=session.session_id,
                allow_enqueue=True,
            )

            self.assertEqual(gate["status"], "clear")
            self.assertEqual(gate["configured_required_cycles"], 10)
            self.assertEqual(gate["required_cycles"], 2)
            self.assertEqual(gate["completed_cycles"], 2)
            self.assertEqual(gate["missing_cycles"], [])
            self.assertTrue(gate["adaptive_lace"]["early_exit"])
            self.assertEqual(gate["adaptive_lace"]["reason"], "quality_gates_clear_early_exit")
            self.assertTrue(gate["quality_gates"]["passed"])
            state = store.load_project_state()
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["blocked_tasks"], [])

    def test_lace_closure_gate_requires_minimum_two_cycles_even_when_quality_gates_clear(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "lace-crm-minimum"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, session = seed_completed_runtime(runtime, project_dir, task_count=1, completed_cycles=1)
            seed_canonical_lace_cycle_evidence(store, project_dir, range(1, 2))
            seed_clean_lace_quality_gates(project_dir)

            gate = runtime._apply_lace_closure_gate(
                runtime_dir=project_dir / "runtime",
                workspace=project_dir,
                runtime_mode="long-run",
                session_id=session.session_id,
                allow_enqueue=True,
            )

            self.assertEqual(gate["status"], "enqueued")
            self.assertEqual(gate["configured_required_cycles"], 10)
            self.assertEqual(gate["required_cycles"], 2)
            self.assertEqual(gate["completed_cycles"], 1)
            self.assertEqual(gate["missing_cycles"], [2])
            self.assertEqual(gate["adaptive_lace"]["reason"], "quality_gates_clear_minimum_pending")
            self.assertTrue(gate["quality_gates"]["passed"])

    def test_reconciles_blocked_lace_parent_after_split_descendants_validate(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "lace-recovered-split"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, _session = seed_completed_runtime(runtime, project_dir, task_count=1, completed_cycles=0)
            seed_canonical_lace_cycle_evidence(store, project_dir, range(1, 7))
            write_lace_log(project_dir, completed_cycles=7, required_cycles=10)
            cycle_doc = project_dir / "docs" / "lace_cycles" / "ciclo-07.md"
            cycle_doc.parent.mkdir(parents=True, exist_ok=True)
            cycle_doc.write_text(
                "# Ciclo 07\n\n- Estado: completed\n- Valido para cierre LACE: si\n",
                encoding="utf-8",
            )
            queue = TaskQueue(store)
            queue.enqueue_many(
                [
                    {
                        "id": "LACE-20260513-007",
                        "title": "Completar ciclo LACE 07",
                        "goal": "Completar ciclo LACE 07 con evidencia canonica.",
                        "status": "blocked",
                        "priority": 93,
                        "dependencies": ["LACE-20260513-006"],
                        "expected_files": ["LACE_LOG.md", "docs/lace_cycles/ciclo-07.md"],
                        "validation_commands": [
                            "python3 -B -c \"from pathlib import Path; doc=Path('docs/lace_cycles/ciclo-07.md'); log=Path('LACE_LOG.md'); assert log.exists(); assert doc.exists(); assert 'valido para cierre lace: si' in doc.read_text(encoding='utf-8').lower()\""
                        ],
                        "timeout_seconds": 3600,
                        "max_retries": 2,
                        "mode": "long-run",
                        "checkpoint_key": "lace-cycle-007-checkpoint",
                    },
                    {
                        "id": "LACE-20260513-008",
                        "title": "Completar ciclo LACE 08",
                        "goal": "Completar ciclo LACE 08 con evidencia canonica.",
                        "status": "pending",
                        "priority": 92,
                        "dependencies": ["LACE-20260513-007"],
                        "expected_files": ["LACE_LOG.md", "docs/lace_cycles/ciclo-08.md"],
                        "validation_commands": ["python3 -c 'print(1)'"],
                        "timeout_seconds": 3600,
                        "max_retries": 2,
                        "mode": "long-run",
                        "checkpoint_key": "lace-cycle-008-checkpoint",
                    },
                    {
                        "id": "LACE-20260513-007-SPLIT-001",
                        "title": "Completar ciclo LACE 07 split 1",
                        "goal": "Actualizar LACE_LOG.md.",
                        "status": "blocked",
                        "priority": 92,
                        "dependencies": ["LACE-20260513-006"],
                        "expected_files": ["LACE_LOG.md"],
                        "validation_commands": [
                            "python3 -B -c \"from pathlib import Path; assert Path('LACE_LOG.md').exists()\""
                        ],
                        "timeout_seconds": 3600,
                        "max_retries": 2,
                        "mode": "long-run",
                        "checkpoint_key": "lace-20260513-007-split-001-checkpoint",
                    },
                    {
                        "id": "LACE-20260513-007-SPLIT-002",
                        "title": "Completar ciclo LACE 07 split 2",
                        "goal": "Actualizar docs/lace_cycles/ciclo-07.md.",
                        "status": "blocked",
                        "priority": 91,
                        "dependencies": ["LACE-20260513-006"],
                        "expected_files": ["docs/lace_cycles/ciclo-07.md"],
                        "validation_commands": [
                            "python3 -B -c \"from pathlib import Path; assert Path('docs/lace_cycles/ciclo-07.md').exists()\""
                        ],
                        "timeout_seconds": 3600,
                        "max_retries": 2,
                        "mode": "long-run",
                        "checkpoint_key": "lace-20260513-007-split-002-checkpoint",
                    },
                    {
                        "id": "LACE-20260513-007-SPLIT-001-SPLIT-001",
                        "title": "Completar ciclo LACE 07 split 1.1",
                        "goal": "Recuperar LACE_LOG.md.",
                        "status": "completed",
                        "priority": 91,
                        "dependencies": ["LACE-20260513-006"],
                        "expected_files": ["LACE_LOG.md"],
                        "validation_commands": ["python3 -c 'print(1)'"],
                        "timeout_seconds": 3600,
                        "max_retries": 2,
                        "mode": "long-run",
                        "checkpoint_key": "lace-20260513-007-split-001-split-001-checkpoint",
                    },
                    {
                        "id": "LACE-20260513-007-SPLIT-002-SPLIT-001",
                        "title": "Completar ciclo LACE 07 split 2.1",
                        "goal": "Recuperar doc ciclo 07.",
                        "status": "completed",
                        "priority": 90,
                        "dependencies": ["LACE-20260513-006"],
                        "expected_files": ["docs/lace_cycles/ciclo-07.md"],
                        "validation_commands": ["python3 -c 'print(1)'"],
                        "timeout_seconds": 3600,
                        "max_retries": 2,
                        "mode": "long-run",
                        "checkpoint_key": "lace-20260513-007-split-002-split-001-checkpoint",
                    },
                ]
            )
            state = store.load_project_state()
            state["status"] = "completed"
            state["blocked_tasks"] = [
                "LACE-20260513-007",
                "LACE-20260513-007-SPLIT-001",
                "LACE-20260513-007-SPLIT-002",
            ]
            store.save_project_state(state)

            reconciled = runtime._reconcile_recovered_split_tasks(store, TaskQueue(store), project_dir)

            queue = TaskQueue(store)
            statuses = {task["id"]: task["status"] for task in queue.list()}
            self.assertTrue(reconciled)
            self.assertEqual(statuses["LACE-20260513-007"], "completed")
            self.assertEqual(statuses["LACE-20260513-007-SPLIT-001"], "completed")
            self.assertEqual(statuses["LACE-20260513-007-SPLIT-002"], "completed")
            self.assertEqual(queue.next_ready_task()["id"], "LACE-20260513-008")
            state = store.load_project_state()
            self.assertEqual(state["status"], "running")
            self.assertEqual(state["blocked_tasks"], [])
            self.assertIn("LACE-20260513-007", state["completed_tasks"])
            self.assertTrue((project_dir / "runtime" / "checkpoints" / "lace-cycle-007-checkpoint.json").exists())
            self.assertTrue(
                any(
                    event.get("result", {}).get("task_id") == "LACE-20260513-007"
                    and event.get("result", {}).get("completed") is True
                    for event in store.load_task_history()
                )
            )

    def test_completed_queue_accepts_incremental_work_on_same_project(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "incremental-autopilot"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, _session = seed_completed_runtime(runtime, project_dir, task_count=2, completed_cycles=0)
            initial_task_count = len(TaskQueue(store).list())

            prepared = runtime._prepare_control_plane_directive(
                "Crear una demo C++ de autopiloto con CMakeLists.txt, src/main.cpp y README.md.",
                runtime_mode="long-run",
                runtime_dir=project_dir / "runtime",
                directive_repo_root=REPO_ROOT,
                task_workspace_root=project_dir,
            )

            queue = TaskQueue(store)
            state = store.load_project_state()
            self.assertGreater(len(queue.list()), initial_task_count)
            self.assertEqual(state["status"], "running")
            self.assertEqual(state["blocked_tasks"], [])
            self.assertEqual(state["failed_tasks"], [])
            self.assertIsNotNone(queue.next_ready_task())
            self.assertEqual(prepared["task"]["id"], queue.next_ready_task()["id"])

    def test_lace_closure_gate_allows_completion_only_with_all_cycles_valid(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "lace-crm-complete"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, session = seed_completed_runtime(runtime, project_dir, task_count=6, completed_cycles=0)
            seed_canonical_lace_cycle_evidence(store, project_dir, range(1, 11))
            state = store.load_project_state()
            state["status"] = "blocked"
            state["blocked_tasks"] = ["lace_cycles_pending"]
            state["failed_tasks"] = ["lace-closure-gate"]
            state["checkpoints"] = [*state.get("checkpoints", []), "lace-closure-gate-blocked"]
            store.save_project_state(state)
            store.save_checkpoint(
                "lace-closure-gate-blocked",
                {"reason": "stale_false_lace_cycles_pending"},
            )

            gate = runtime._apply_lace_closure_gate(
                runtime_dir=project_dir / "runtime",
                workspace=project_dir,
                runtime_mode="long-run",
                session_id=session.session_id,
                allow_enqueue=True,
            )

            self.assertEqual(gate["status"], "clear")
            self.assertEqual(gate["completed_cycles"], 10)
            self.assertEqual(gate["missing_cycles"], [])
            state = store.load_project_state()
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["current_task_id"], None)
            self.assertEqual(state["blocked_tasks"], [])
            self.assertEqual(state["failed_tasks"], [])
            self.assertNotIn("lace-closure-gate-blocked", state["checkpoints"])
            self.assertFalse((project_dir / "runtime" / "checkpoints" / "lace-closure-gate-blocked.json").exists())
            self.assertTrue((project_dir / "runtime" / "checkpoints" / "lace-closure-gate-completed.json").exists())

    def test_final_visual_outcome_uses_canonical_completed_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "canonical-complete"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, _session = seed_completed_runtime(runtime, project_dir, task_count=6, completed_cycles=0)
            seed_canonical_lace_cycle_evidence(store, project_dir, range(1, 11))
            state = store.load_project_state()
            state["status"] = "completed"
            state["current_task_id"] = None
            state["blocked_tasks"] = []
            state["failed_tasks"] = []
            store.save_project_state(state)

            outcome = runtime._derive_canonical_control_plane_outcome(
                project_dir / "runtime",
                sequence_status="failed",
                sequence_stopped_reason="control_plane_task_failed",
            )

            self.assertTrue(outcome["completed"])
            self.assertEqual(outcome["session_status"], "completed")
            self.assertEqual(outcome["event_op"], "session_completed")
            self.assertEqual(outcome["event_status"], "completed")
            self.assertIsNone(outcome["error_code"])

    def test_final_visual_outcome_reports_completed_with_warnings_for_nonfatal_inconsistency(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "canonical-warning"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, _session = seed_completed_runtime(runtime, project_dir, task_count=6, completed_cycles=0)
            seed_canonical_lace_cycle_evidence(store, project_dir, range(1, 11))
            state = store.load_project_state()
            state["status"] = "completed"
            state["current_task_id"] = None
            state["blocked_tasks"] = []
            state["failed_tasks"] = []
            store.save_project_state(state)
            store.append_failure({"task_id": "stale-runtime-event", "failure_type": "historical_nonfatal"})

            outcome = runtime._derive_canonical_control_plane_outcome(
                project_dir / "runtime",
                sequence_status="completed",
                sequence_stopped_reason="queue_idle",
            )

            self.assertTrue(outcome["completed"])
            self.assertEqual(outcome["session_status"], "completed")
            self.assertEqual(outcome["event_op"], "session_completed_with_warnings")
            self.assertEqual(outcome["event_status"], "completed")
            self.assertIsNone(outcome["error_code"])

    def test_stop_requested_overrides_canonical_failures(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "canonical-stopped"
            project_dir.mkdir(parents=True, exist_ok=True)
            store, _session = seed_completed_runtime(runtime, project_dir, task_count=1, completed_cycles=0)
            state = store.load_project_state()
            state["status"] = "failed"
            state["failed_tasks"] = ["RUNTIME-STUCK-001"]
            store.save_project_state(state)

            outcome = runtime._derive_canonical_control_plane_outcome(
                project_dir / "runtime",
                sequence_status="stopped",
                sequence_stopped_reason="stop_requested",
            )

            self.assertFalse(outcome["completed"])
            self.assertEqual(outcome["session_status"], "stopped")
            self.assertEqual(outcome["event_op"], "session_stopped")
            self.assertEqual(outcome["error_code"], "control_plane_stopped")

    def test_recover_stale_running_tasks_requeues_interrupted_task(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "stale-running"
            project_dir.mkdir(parents=True, exist_ok=True)
            runtime_dir = project_dir / "runtime"
            runtime._ensure_control_plane_runtime(runtime_dir, project_dir.name, "build")
            store = StateStore(runtime_dir)
            task = create_task(
                task_id="RUNTIME-STUCK-001",
                title="Interrupted task",
                goal="Recover an interrupted running task.",
                priority=10,
                expected_files=["README.md"],
                validation_commands=["python3 -c 'print(1)'"],
                mode="build",
            )
            queue = TaskQueue(store, bootstrap_empty=True)
            queue.enqueue(task)
            queue.mark_task_status(task["id"], "running")
            state = store.load_project_state()
            state["status"] = "running"
            state["current_task_id"] = task["id"]
            state["failed_tasks"] = [task["id"]]
            state["blocked_tasks"] = [task["id"]]
            store.save_project_state(state)

            recovered = runtime._recover_stale_running_tasks(store, TaskQueue(store))

            queue_after = TaskQueue(store).list()
            state_after = store.load_project_state()
            self.assertTrue(recovered)
            self.assertEqual(queue_after[0]["status"], "pending")
            self.assertEqual(state_after["status"], "running")
            self.assertIsNone(state_after["current_task_id"])
            self.assertEqual(state_after["failed_tasks"], [])
            self.assertEqual(state_after["blocked_tasks"], [])
            self.assertTrue(any(key.startswith("stale-running-recovered-") for key in store.list_checkpoints()))

    def test_validator_rejects_directory_as_expected_file_evidence(self) -> None:
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            (workspace / "frontend").mkdir(parents=True)
            task = create_task(
                task_id="TASK-DIR-001",
                title="Directory evidence",
                goal="Do not accept a directory as file evidence.",
                priority=10,
                expected_files=["frontend"],
                validation_commands=["python3 -c 'from pathlib import Path; assert Path(\"frontend\").exists()'"],
                mode="build",
            )
            result = {
                "task_id": task["id"],
                "completed": True,
                "files_created": [],
                "files_modified": ["frontend"],
                "validation_ran": [],
                "validation_passed": True,
                "blockers": [],
                "next_recommendation": "",
            }

            validation = validate_task_execution(task, result, workspace=workspace)

            self.assertFalse(validation["task_result"]["completed"])
            self.assertFalse(validation["task_result"]["validation_passed"])
            self.assertIn("Expected evidence path is not a file: frontend", validation["task_result"]["blockers"])

    def test_runtime_path_normalizer_preserves_dotfile_metadata_as_internal(self) -> None:
        self.assertEqual(normalize_project_relative_path(".agent-project.json"), ".agent-project.json")
        self.assertTrue(is_runtime_control_path(".agent-project.json"))
        self.assertTrue(is_runtime_control_path("agent-project.json"))
        self.assertFalse(is_material_project_path(".agent-project.json"))

    def test_validator_rejects_agent_project_metadata_as_expected_file_evidence(self) -> None:
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True)
            (workspace / ".agent-project.json").write_text('{"name":"internal"}\n', encoding="utf-8")
            task = create_task(
                task_id="TASK-META-001",
                title="Metadata evidence",
                goal="Do not accept agent metadata as product evidence.",
                priority=10,
                expected_files=[".agent-project.json"],
                validation_commands=["python3 -c 'from pathlib import Path; assert Path(\".agent-project.json\").is_file()'"],
                mode="build",
            )
            result = {
                "task_id": task["id"],
                "completed": True,
                "files_created": [".agent-project.json"],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": True,
                "blockers": [],
                "next_recommendation": "",
            }

            validation = validate_task_execution(task, result, workspace=workspace)

            self.assertFalse(validation["task_result"]["completed"])
            self.assertIn(
                "Expected file targets control-plane state: .agent-project.json",
                validation["task_result"]["blockers"],
            )

    def test_control_plane_expected_files_replace_metadata_with_material_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "metadata-repair"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            (project_dir / ".agent-project.json").write_text('{"name":"internal"}\n', encoding="utf-8")
            (project_dir / "frontend" / "app.js").write_text("console.log('product');\n", encoding="utf-8")
            task = create_task(
                task_id="TASK-META-REPAIR-001",
                title="Repair metadata evidence",
                goal="Replace metadata with material product files.",
                priority=10,
                expected_files=[".agent-project.json", "agent-project.json"],
                validation_commands=["python3 -c 'print(1)'"],
                mode="build",
            )

            normalized = runtime._normalize_control_plane_planned_tasks([task], project_dir)

            self.assertEqual(normalized[0]["expected_files"], ["frontend/app.js"])
            self.assertIn("frontend/app.js", normalized[0]["validation_commands"][0])

    def test_control_plane_normalization_preserves_extra_validation_commands(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "tkinter-validation"
            project_dir.mkdir(parents=True, exist_ok=True)
            task = create_task(
                task_id="TASK-TK-001",
                title="Build Tkinter app",
                goal="Create a bounded Tkinter script.",
                priority=10,
                expected_files=["src/suma_random_tkinter.py"],
                validation_commands=[
                    "python3 -B -c \"from pathlib import Path; missing=[p for p in ['src/suma_random_tkinter.py'] if not Path(p).is_file()]; assert not missing, missing\"",
                    "python3 -m py_compile src/suma_random_tkinter.py",
                    "python3 -B -c \"from pathlib import Path; too_long=[p for p in ['src/suma_random_tkinter.py'] if len(Path(p).read_text(encoding='utf-8').splitlines()) > 100]; assert not too_long, too_long\"",
                ],
                mode="smoke",
            )

            normalized = runtime._normalize_control_plane_planned_tasks([task], project_dir)

            self.assertEqual(normalized[0]["expected_files"], ["src/suma_random_tkinter.py"])
            self.assertIn("python3 -m py_compile src/suma_random_tkinter.py", normalized[0]["validation_commands"])
            self.assertTrue(any("too_long" in command for command in normalized[0]["validation_commands"]))

    def test_frontend_canvas_tasks_get_browser_render_validation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "canvas-validation"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            (project_dir / "frontend" / "index.html").write_text(
                '<canvas id="world"></canvas><script type="module" src="./app.js"></script>',
                encoding="utf-8",
            )
            (project_dir / "frontend" / "app.js").write_text(
                'import * as THREE from "three"; new THREE.WebGLRenderer({canvas: document.querySelector("#world")});',
                encoding="utf-8",
            )
            task = create_task(
                task_id="TASK-CANVAS-001",
                title="Build canvas app",
                goal="Create a browser-rendered canvas app.",
                priority=10,
                expected_files=["frontend/index.html", "frontend/app.js", "frontend/styles.css"],
                validation_commands=["python3 -c 'print(1)'"],
                mode="build",
            )

            normalized = runtime._normalize_control_plane_planned_tasks([task], project_dir)

            self.assertTrue(
                any("browser_render_smoke.py" in command for command in normalized[0]["validation_commands"])
            )

    def test_frontend_split_existing_evidence_requires_browser_validation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "frontend-existing-evidence"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            (project_dir / "frontend" / "index.html").write_text('<canvas id="world"></canvas>', encoding="utf-8")
            (project_dir / "frontend" / "app.js").write_text('new THREE.WebGLRenderer();', encoding="utf-8")
            runtime_dir = project_dir / "runtime"
            runtime._ensure_control_plane_runtime(runtime_dir, project_dir.name, "build")
            store = StateStore(runtime_dir)
            weak_task = {
                "id": "TASK-CANVAS-001-SPLIT-001",
                "title": "Repair app split",
                "goal": "Repair frontend/app.js",
                "status": "pending",
                "priority": 10,
                "dependencies": [],
                "expected_files": ["frontend/app.js"],
                "validation_commands": ["python3 -c 'print(1)'"],
                "timeout_seconds": 300,
                "max_retries": 1,
                "mode": "build",
                "checkpoint_key": "task-canvas-001-split-001",
            }
            strong_task = dict(weak_task)
            strong_task["validation_commands"] = runtime._merge_control_plane_validation_commands(
                ["frontend/app.js"],
                [],
                workspace_path=project_dir,
            )

            self.assertFalse(
                runtime._control_plane_task_can_close_from_existing_evidence(
                    store,
                    weak_task,
                    workspace=project_dir,
                )
            )
            self.assertTrue(
                runtime._control_plane_task_can_close_from_existing_evidence(
                    store,
                    strong_task,
                    workspace=project_dir,
                )
            )

    def test_recovery_does_not_split_split_tasks_recursively(self) -> None:
        task = create_task(
            task_id="TASK-ROOT-001-SPLIT-001",
            title="Already split",
            goal="Complete smaller scope after a timeout.",
            priority=10,
            expected_files=["frontend/app.js"],
            validation_commands=["python3 -c 'print(1)'"],
            mode="build",
        )
        decision = decide_recovery(
            task,
            {
                "task_result": {
                    "task_id": task["id"],
                    "completed": False,
                    "files_created": [],
                    "files_modified": [],
                    "validation_ran": [],
                    "validation_passed": False,
                    "blockers": ["Worker process timed out after 300 seconds"],
                    "next_recommendation": "Retry with a smaller task.",
                }
            },
            retry_count=0,
            allow_split=True,
        )

        self.assertEqual(decision["action"], "retry")

    def test_visual_events_file_is_consumed_and_control_plane_sync_is_filtered(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "visual-consume"
            (project_dir / "runtime" / "logs").mkdir(parents=True, exist_ok=True)
            session = AgentSession(
                session_id="agent-visual-consume",
                project_name="Visual Consume",
                project_slug=project_dir.name,
                project_dir=project_dir,
                requirement="consume visual events",
                prompt="",
                command=[],
                event_file=project_dir / "runtime" / "logs" / "agent-visual-consume-events.jsonl",
                terminal_file=project_dir / "runtime" / "logs" / "agent-visual-consume-terminal.log",
                control_plane_enabled=True,
                control_plane_runtime_dir=str(project_dir / "runtime"),
                runtime_mode="build",
            )
            runtime.sessions[session.session_id] = session
            events = [
                {"op": "sync_file", "relativePath": "runtime/project_state.json"},
                {"op": "sync_file", "relativePath": ".agent-project.json"},
                {"op": "sync_file", "relativePath": "agent-project.json"},
                {"op": "sync_file", "relativePath": "frontend/app.js", "codeLanguage": "javascript"},
            ]
            session.event_file.write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )

            runtime._consume_visual_events(session.session_id)

            self.assertEqual([event["relativePath"] for event in visual_events], ["frontend/app.js"])
            self.assertEqual(runtime.sessions[session.session_id].visual_event_count, 1)
            self.assertIsNotNone(runtime.sessions[session.session_id].first_visual_event_at)

    def test_project_state_transition_can_persist_stopped(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app_root = Path(tmpdir) / "app"
            visual_events: list[dict] = []
            runtime = build_runtime(app_root, visual_events)
            project_dir = app_root / "workspace" / "projects" / "stopped-state"
            project_dir.mkdir(parents=True, exist_ok=True)
            runtime_dir = project_dir / "runtime"
            runtime._ensure_control_plane_runtime(runtime_dir, project_dir.name, "build")
            store = StateStore(runtime_dir)
            task = create_task(
                task_id="TASK-STOP-001",
                title="Stop task",
                goal="Persist stopped state.",
                priority=10,
                expected_files=["README.md"],
                validation_commands=["python3 -c 'print(1)'"],
                mode="build",
            )

            runtime._save_project_state_transition(store, task, "stopped", checkpoint_key="task-stop-001-stopped")

            state = store.load_project_state()
            self.assertEqual(state["status"], "stopped")
            self.assertIsNone(state["current_task_id"])
            self.assertIn("task-stop-001-stopped", state["checkpoints"])

    def test_live_reviewer_does_not_report_visual_progress_without_evidence(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            runtime = project / "runtime"
            (runtime / "logs").mkdir(parents=True, exist_ok=True)
            (runtime / "project_state.json").write_text(
                json.dumps({"current_task_id": "TASK-001", "status": "running", "mode": "long-run"}),
                encoding="utf-8",
            )
            (runtime / "task_queue.json").write_text(
                json.dumps([
                    {
                        "id": "TASK-001",
                        "title": "Build app",
                        "goal": "Build app",
                        "status": "running",
                        "priority": 1,
                        "dependencies": [],
                        "expected_files": ["frontend/index.html"],
                        "validation_commands": [],
                        "timeout_seconds": 300,
                        "max_retries": 1,
                        "mode": "long-run",
                        "checkpoint_key": "task-001",
                    }
                ]),
                encoding="utf-8",
            )

            status = build_reviewer_status(project_root=project, runtime_dir=runtime)

            self.assertEqual(status["expected_files_found"], [])
            self.assertEqual(status["expected_files_missing"], ["frontend/index.html"])

    def test_live_reviewer_panel_is_defined_in_agent_studio(self) -> None:
        source = (REPO_ROOT / "frontend" / "src" / "components" / "AgentStudio.jsx").read_text(encoding="utf-8")
        panel_source = (REPO_ROOT / "frontend" / "src" / "components" / "LiveReviewerPanel.jsx").read_text(encoding="utf-8")
        self.assertIn('import LiveReviewerPanel from "./LiveReviewerPanel.jsx"', source)
        self.assertIn("export default function LiveReviewerPanel", panel_source)
        self.assertIn("<LiveReviewerPanel", source)


if __name__ == "__main__":
    unittest.main()
