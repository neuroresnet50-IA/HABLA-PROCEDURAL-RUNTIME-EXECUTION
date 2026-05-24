import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
for path in (ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import app as backend_app
from orchestrator.complexity_estimator import estimate_complexity
from orchestrator.directive_generator import generate_directive


class ComplexityEstimatorRegressionTest(unittest.TestCase):
    def test_simple_patch_uses_minimum_operational_budget(self) -> None:
        estimate = estimate_complexity(
            "Parche minimo de un archivo sin refactor para corregir un bug puntual.",
            runtime_mode="build",
            project_file_count=3,
        )

        self.assertEqual(estimate["difficulty"], "facil")
        self.assertEqual(estimate["recommended_agents"], 1)
        self.assertEqual(estimate["recommended_lace_cycles"], 2)
        self.assertEqual(estimate["max_tasks"], 3)
        self.assertIn("marcadores de trabajo puntual/minimo", estimate["reasons"])

    def test_medium_mode_is_real_difficult_floor_when_task_is_not_minimal(self) -> None:
        estimate = estimate_complexity(
            "Construir varios modulos backend API con pruebas e integridad.",
            runtime_mode="medium",
            project_file_count=80,
        )

        self.assertEqual(estimate["difficulty"], "dificil")
        self.assertGreaterEqual(estimate["recommended_agents"], 4)
        self.assertGreaterEqual(estimate["recommended_lace_cycles"], 5)
        self.assertIn("modo medium fija piso de complejidad 50", estimate["reasons"])
        self.assertNotIn("incluye capa visual/frontend", estimate["reasons"])

    def test_long_run_complex_work_allocates_extra_difficult_budget(self) -> None:
        estimate = estimate_complexity(
            "Construir plataforma 3D WebGL realtime con backend API, base de datos, auth, scanner, integrity, e2e y sandbox para sistema completo.",
            runtime_mode="long-run",
            project_file_count=250,
        )

        self.assertEqual(estimate["difficulty"], "extradificil")
        self.assertGreaterEqual(estimate["recommended_agents"], 6)
        self.assertGreaterEqual(estimate["recommended_lace_cycles"], 8)
        self.assertLessEqual(estimate["recommended_lace_cycles"], 10)
        self.assertIn("scanner", estimate["required_tools"])
        self.assertIn("sandbox", estimate["required_tools"])

    def test_subagent_recommendation_uses_same_complexity_estimate(self) -> None:
        recommendation = backend_app.build_subagent_recommendation(
            {
                "requirement": "Parche minimo de un archivo sin refactor para corregir un bug puntual.",
                "runtimeMode": "build",
            }
        )
        estimate = recommendation["complexityEstimate"]

        self.assertEqual(recommendation["difficulty"], estimate["difficulty"])
        self.assertEqual(recommendation["recommendedAgents"], estimate["recommended_agents"])
        self.assertEqual(recommendation["recommendedLaceCycles"], estimate["recommended_lace_cycles"])
        self.assertEqual(recommendation["recommendedMaxTasks"], estimate["max_tasks"])
        self.assertIn("ciclo(s) LACE", recommendation["summary"])

    def test_directive_renders_complexity_budget_for_worker(self) -> None:
        estimate = estimate_complexity(
            "Parche minimo de un archivo sin refactor para corregir un bug puntual.",
            runtime_mode="build",
            project_file_count=3,
        )
        with TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir) / "runtime"
            context = {
                "context_type": "directive_context",
                "repo_root": str(ROOT),
                "system_root": str(ROOT),
                "task_workspace_root": str(ROOT),
                "runtime_dir": str(runtime_dir),
                "degraded": False,
                "runtime_errors": [],
                "audit": {"inputs": {"policy_file": str(ROOT / "AGENTS.md"), "plan_file": str(ROOT / "PLANS.md")}},
                "checkpoint": {"checkpoint_key": "start", "source": "test", "path": ""},
                "sprint": {"number": 99, "objective": "Validar complejidad", "deliverables": ["README.md"]},
                "complexity_estimate": estimate,
                "active_task": {
                    "id": "TASK-COMPLEXITY",
                    "title": "Validar presupuesto",
                    "goal": "Demostrar que la complejidad entra a la directiva.",
                    "mode": "build",
                    "timeout_seconds": estimate["timeout_seconds"],
                    "max_retries": estimate["max_retries"],
                    "expected_files": ["README.md"],
                    "validation_commands": ["pytest -q"],
                    "checkpoint_key": "start",
                },
            }
            guide = {
                "guide_type": "HABLA_BASIC_TEST",
                "task_id": "TASK-COMPLEXITY",
                "directive_generator_ready": True,
                "procedure": {
                    "objetivo_operativo_actual": {"goal": "test"},
                    "restricciones_activas": [],
                    "alcance_controlado": {},
                    "evidencia_requerida": {"expected_files": ["README.md"]},
                    "validacion_esperada": {"validation_commands": ["pytest -q"]},
                    "checkpoint_de_partida": {"checkpoint_key": "start"},
                    "riesgos_o_bloqueos_conocidos": [],
                    "criterio_de_cierre": ["pytest -q pasa"],
                },
            }

            directive = generate_directive(context, guide)

        rendered = directive["rendered_instruction"]
        self.assertEqual(directive["operational_directive"]["complexity_estimate"], estimate)
        self.assertIn("Complejidad operativa", rendered)
        self.assertIn("Agentes recomendados: 1", rendered)
        self.assertIn("Ciclos LACE recomendados: 2", rendered)
        self.assertIn("Presupuesto: 3 tareas", rendered)


if __name__ == "__main__":
    unittest.main()
