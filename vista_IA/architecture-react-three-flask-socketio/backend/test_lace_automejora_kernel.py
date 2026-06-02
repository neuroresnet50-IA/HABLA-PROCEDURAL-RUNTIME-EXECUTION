from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent_runtime import AgentRuntime, get_lace_required_cycles, validate_lace_log
from orchestrator.state_store import StateStore
from orchestrator.task_queue import TaskQueue


def build_runtime(app_root: Path) -> AgentRuntime:
    return AgentRuntime(
        app_root=app_root,
        workspace_root=app_root / "workspace",
        projects_root=app_root / "workspace" / "projects",
        codex_cmd="codex",
        prompt_converter=None,
        graph_provider=lambda: {},
        graph_sync=lambda force=False: {},
        terminal_emitter=lambda event: None,
        session_emitter=lambda event: None,
        visual_event_handler=lambda event: None,
    )


def base_task(task_id: str = "RUNTIME-BASE-001", *, mode: str = "build") -> dict:
    return {
        "id": task_id,
        "title": "Base task",
        "goal": "Crear base verificable.",
        "status": "completed",
        "priority": 10,
        "dependencies": [],
        "expected_files": ["docs/base.md"],
        "validation_commands": [],
        "timeout_seconds": 30,
        "max_retries": 0,
        "mode": mode,
        "checkpoint_key": f"{task_id.lower()}-checkpoint",
    }


def prepare_project(root: Path, *, mode: str = "build", recommended: int = 8) -> tuple[AgentRuntime, Path, StateStore]:
    runtime = build_runtime(root)
    project = runtime.projects_root / f"lace-{mode.replace('-', '_')}"
    project.mkdir(parents=True, exist_ok=True)
    runtime_dir = project / "runtime"
    runtime._ensure_control_plane_runtime(runtime_dir, project.name, mode)
    store = StateStore(runtime_dir)
    TaskQueue(store, bootstrap_empty=True).enqueue(base_task(mode=mode))
    (project / "docs").mkdir(parents=True, exist_ok=True)
    (project / "docs" / "base.md").write_text("base\n", encoding="utf-8")
    store.append_task_history({
        "task_id": "RUNTIME-BASE-001",
        "completed": True,
        "files_created": ["docs/base.md"],
        "files_modified": [],
        "validation_ran": [],
        "validation_passed": True,
        "blockers": [],
        "next_recommendation": "ok",
    })
    state = store.load_project_state()
    state["status"] = "completed"
    state["mode"] = mode
    state["current_task_id"] = None
    state["completed_tasks"] = ["RUNTIME-BASE-001"]
    state["failed_tasks"] = []
    state["blocked_tasks"] = []
    store.save_project_state(state)
    (runtime_dir / "complexity_estimate.json").write_text(
        json.dumps({"difficulty": "Extradificil", "recommended_lace_cycles": recommended, "max_tasks": 32}),
        encoding="utf-8",
    )
    (project / "LACE_LOG.md").write_text(valid_lace_log(0, max(recommended, 1)), encoding="utf-8")
    return runtime, project, store


def valid_lace_log(completed: int, required: int) -> str:
    parts = [
        "# LACE_LOG.md\n",
        "[COMPRENSIÓN DEL PROYECTO]\nConstruir una app real con evidencia.\n",
        f"[PLAN PARA {required} CICLOS]\n" + "\n".join(f"{i}. Revisar area {i}." for i in range(1, required + 1)) + "\n",
        "[BASE] Construccion inicial completada.\nEstado actual: Base funcional verificable.\n",
    ]
    for i in range(1, completed + 1):
        parts.append(cycle_sections(i))
    return "\n".join(parts)


def cycle_sections(i: int) -> str:
    return f"""
[CICLO-{i} PROBLEMAS]
THOUGHT: Revise el estado real del ciclo {i} y encontre una brecha concreta.
TRIANGULACIÓN: tecnico: evidencia en disco; funcional: flujo verificable; humano: resultado visible.
CONFIANZA: logica media, funcional media, seguridad media.
AUTO-CRÍTICA: Cerrar sin este ciclo ocultaria deuda verificable.
1. Falta evidencia canonica del ciclo {i} - severidad: alta

[CICLO-{i} MEJORA]
THOUGHT: Aplicare una mejora verificable para el ciclo {i}.
ACTION: Registrar documento, checkpoint y validacion del ciclo {i}.
OBSERVATION esperada: El cierre LACE cuenta el ciclo {i} solo con evidencia completa.

[CICLO-{i} COMPLETADO]
OBSERVATION real: La evidencia canonica del ciclo {i} existe en disco.
¿Coincide con OBSERVATION esperada? SI
Problemas resueltos: La brecha canonica del ciclo {i} quedo cubierta.
Estado ahora vs antes: El proyecto tiene mas evidencia verificable que antes.
¿El proyecto mejoró objetivamente? SI

MEMORIA EPISÓDICA:
- Qué funcionó: usar validacion por filesystem.
- Qué no funcionó: confiar en texto suelto.
- Qué evitar en el próximo ciclo: cerrar sin checkpoint.

Próximo ciclo — qué atacaré: siguiente revision verificable.
"""


def write_cycle_doc(project: Path, i: int, *, markers: bool = True, valid_header: bool = True) -> Path:
    doc = project / "docs" / "lace_cycles" / f"ciclo-{i:02d}.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    body = cycle_sections(i) if markers else "Sin marcadores canonicos.\n"
    header = f"# Ciclo {i:02d}\n\n- Estado: validated\n"
    if valid_header:
        header += "- Valido para cierre LACE: si\n"
    doc.write_text(header + "\n" + body, encoding="utf-8")
    return doc


def seed_canonical_cycle(store: StateStore, project: Path, i: int, *, doc: bool = True, checkpoint: bool = True, markers: bool = True, validator: bool = True) -> None:
    queue = TaskQueue(store, bootstrap_empty=True)
    existing = queue.list()
    task_id = f"LACE-20260601-{i:03d}"
    if not any(task["id"] == task_id for task in existing):
        queue.enqueue({
            "id": task_id,
            "title": f"LACE Automejora Ciclo {i}",
            "goal": f"Completar ciclo LACE {i}.",
            "status": "completed",
            "priority": max(1, 100 - i),
            "dependencies": [existing[-1]["id"]] if existing else [],
            "expected_files": [f"docs/lace_cycles/ciclo-{i:02d}.md"],
            "validation_commands": [],
            "timeout_seconds": 30,
            "max_retries": 0,
            "mode": "build",
            "checkpoint_key": f"lace-cycle-{i:03d}-checkpoint",
        })
    if doc:
        write_cycle_doc(project, i, markers=markers)
    result = {
        "task_id": task_id,
        "completed": True,
        "files_created": [f"docs/lace_cycles/ciclo-{i:02d}.md"],
        "files_modified": [],
        "validation_ran": [],
        "validation_passed": bool(validator),
        "blockers": [] if validator else ["validator failed"],
        "next_recommendation": "ok",
    }
    store.append_task_history(result)
    if checkpoint:
        store.save_checkpoint(f"lace-cycle-{i:03d}-checkpoint", {"task_result": result, "validation": {"task_result": result}})


class LaceAutomejoraKernelTest(unittest.TestCase):
    def test_01_build_requiere_lace(self):
        with TemporaryDirectory() as tmp:
            runtime, project, _ = prepare_project(Path(tmp), mode="build", recommended=8)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["status"], "blocked")
            self.assertEqual(gate["required_cycles"], 8)
            self.assertEqual(gate["completed_cycles"], 0)

    def test_02_medium_requiere_lace(self):
        with TemporaryDirectory() as tmp:
            runtime, project, _ = prepare_project(Path(tmp), mode="medium", recommended=8)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="medium", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["status"], "blocked")

    def test_03_long_run_requiere_lace(self):
        with TemporaryDirectory() as tmp:
            runtime, project, _ = prepare_project(Path(tmp), mode="long-run", recommended=8)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="long-run", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["status"], "blocked")

    def test_04_smoke_salta_lace(self):
        with TemporaryDirectory() as tmp:
            runtime, project, _ = prepare_project(Path(tmp), mode="smoke", recommended=8)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="smoke", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["status"], "not_applicable")
            self.assertEqual(get_lace_required_cycles(project / "runtime", runtime_mode="smoke"), 0)

    def test_05_state_completed_no_tapa_lace(self):
        with TemporaryDirectory() as tmp:
            runtime, project, _ = prepare_project(Path(tmp), mode="build", recommended=8)
            outcome = runtime._derive_canonical_control_plane_outcome(project / "runtime", sequence_status="completed", sequence_stopped_reason="queue_idle")
            self.assertFalse(outcome["completed"])
            self.assertEqual(outcome["outcome"], "blocked_lace_closure")

    def test_06_lace_log_no_canonico(self):
        with TemporaryDirectory() as tmp:
            runtime, project, _ = prepare_project(Path(tmp), mode="build", recommended=2)
            (project / "LACE_LOG.md").write_text(valid_lace_log(2, 2), encoding="utf-8")
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["completed_cycles"], 0)
            self.assertTrue(gate["cycle_evidence"]["1"]["lace_log_only_valid"])

    def test_07_encola_tareas_lace(self):
        with TemporaryDirectory() as tmp:
            runtime, project, store = prepare_project(Path(tmp), mode="build", recommended=3)
            seed_canonical_cycle(store, project, 1)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=True)
            self.assertEqual(gate["status"], "enqueued")
            self.assertEqual(gate["missing_cycles"], [2, 3])
            ids = [task["id"] for task in TaskQueue(store).list()]
            self.assertTrue(any(task_id.endswith("-002") for task_id in ids if task_id.startswith("LACE-")))
            self.assertTrue(any(task_id.endswith("-003") for task_id in ids if task_id.startswith("LACE-")))

    def test_08_doc_ciclo_requerido(self):
        with TemporaryDirectory() as tmp:
            runtime, project, store = prepare_project(Path(tmp), mode="build", recommended=1)
            seed_canonical_cycle(store, project, 1, doc=False)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["completed_cycles"], 0)

    def test_09_checkpoint_requerido(self):
        with TemporaryDirectory() as tmp:
            runtime, project, store = prepare_project(Path(tmp), mode="build", recommended=1)
            seed_canonical_cycle(store, project, 1, checkpoint=False)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["completed_cycles"], 0)

    def test_10_marcadores_requeridos(self):
        with TemporaryDirectory() as tmp:
            runtime, project, store = prepare_project(Path(tmp), mode="build", recommended=1)
            seed_canonical_cycle(store, project, 1, markers=False)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["completed_cycles"], 0)

    def test_11_validator_requerido(self):
        with TemporaryDirectory() as tmp:
            runtime, project, store = prepare_project(Path(tmp), mode="build", recommended=1)
            seed_canonical_cycle(store, project, 1, validator=False)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["completed_cycles"], 0)

    def test_12_cierre_ok_con_ciclos_validos(self):
        with TemporaryDirectory() as tmp:
            runtime, project, store = prepare_project(Path(tmp), mode="build", recommended=2)
            seed_canonical_cycle(store, project, 1)
            seed_canonical_cycle(store, project, 2)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["status"], "clear")
            self.assertEqual(gate["closure_status"], "ok")

    def test_13_early_exit_justificada(self):
        with TemporaryDirectory() as tmp:
            runtime, project, store = prepare_project(Path(tmp), mode="build", recommended=8)
            for cycle in range(1, 4):
                seed_canonical_cycle(store, project, cycle)
            artifacts = project / "runtime" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "final_code_scanner_report.json").write_text(json.dumps({"scanner": {"visual_playback": "magnifier_line_by_line_to_last_line", "scrolls_to_last_line": True}, "validation": {"passed": True, "blockers": []}}), encoding="utf-8")
            (artifacts / "file_integrity_report.json").write_text(json.dumps({"summary": {"totalFindings": 0}, "validation": {"passed": True, "blockers": []}}), encoding="utf-8")
            (artifacts / "observer_findings.json").write_text(json.dumps({"summary": {"activeFindings": 0}}), encoding="utf-8")
            (project / "runtime" / "sandbox.json").write_text(json.dumps({"running": True, "ready": True, "embedUrl": "http://127.0.0.1:5600", "healthcheck": {"ready": True, "statusCode": 200}}), encoding="utf-8")
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["status"], "clear")
            self.assertTrue(gate["adaptive_lace"]["early_exit"])
            self.assertEqual(gate["required_cycles"], 3)

    def test_14_early_exit_sin_justificacion_bloquea(self):
        with TemporaryDirectory() as tmp:
            runtime, project, store = prepare_project(Path(tmp), mode="build", recommended=8)
            for cycle in range(1, 4):
                seed_canonical_cycle(store, project, cycle)
            gate = runtime._apply_lace_closure_gate(runtime_dir=project / "runtime", workspace=project, runtime_mode="build", session_id=None, allow_enqueue=False)
            self.assertEqual(gate["status"], "blocked")
            self.assertEqual(gate["required_cycles"], 8)
            self.assertEqual(gate["completed_cycles"], 3)


if __name__ == "__main__":
    unittest.main()
