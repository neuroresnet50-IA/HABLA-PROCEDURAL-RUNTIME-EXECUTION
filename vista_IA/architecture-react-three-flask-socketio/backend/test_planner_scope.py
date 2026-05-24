import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.contracts import ContractError
from orchestrator.planner import MULTI_MODULE_REQUIRED_FILES, plan_project, validate_plan_scope


MULTI_MODULE_PROMPT = """
Construye una plataforma long-run multi-módulo para CRM + ERP + analytics.
Debe incluir frontend compartido, schemas por dominio, módulos reutilizables,
tests por dominio, test de integración y documentación de arquitectura.
"""

SCRIPT_ONLY_PROMPT = """
Crea solo un script Python pequeño para probar reparación visual.
Archivo exacto:
- src/calculadora_descuentos.py
Debe quedar quebrado a propósito para que el sistema detecte el punto rojo.
Validación mínima: python3 -m py_compile src/calculadora_descuentos.py
"""


def planned_files(tasks: list[dict]) -> set[str]:
    return {path for task in tasks for path in task["expected_files"]}


class PlannerScopeTest(unittest.TestCase):
    def test_multi_module_prompt_generates_full_scope_even_with_small_max_tasks(self) -> None:
        tasks = plan_project(
            MULTI_MODULE_PROMPT,
            mode="long-run",
            max_tasks=3,
            task_id_prefix="SCOPE",
        )

        files = planned_files(tasks)
        self.assertGreaterEqual(len(tasks), 7)
        self.assertTrue(set(MULTI_MODULE_REQUIRED_FILES).issubset(files))
        self.assertTrue(all(task["mode"] == "long-run" for task in tasks))
        self.assertTrue(all(task["timeout_seconds"] == 3600 for task in tasks))

    def test_multi_module_expected_files_include_domain_schemas_modules_and_tests(self) -> None:
        tasks = plan_project(MULTI_MODULE_PROMPT, mode="long-run", task_id_prefix="SCOPE")
        files = planned_files(tasks)

        for expected in (
            "shared/crm_schema.json",
            "shared/erp_schema.json",
            "shared/analytics_schema.json",
            "src/crm.js",
            "src/erp.js",
            "src/analytics.js",
            "tests/crm_smoke.test.js",
            "tests/erp_smoke.test.js",
            "tests/analytics_smoke.test.js",
            "tests/integration_smoke.test.js",
            "docs/architecture.md",
            "docs/usage.md",
        ):
            self.assertIn(expected, files)

    def test_scope_gate_rejects_crm_only_plan_for_multi_module_prompt(self) -> None:
        crm_only_tasks = plan_project("Construye un CRM con frontend y pruebas.", mode="long-run")

        with self.assertRaisesRegex(ContractError, "multi-module scope gate failed"):
            validate_plan_scope(MULTI_MODULE_PROMPT, crm_only_tasks)

    def test_long_run_script_only_prompt_does_not_expand_to_product_blueprint(self) -> None:
        tasks = plan_project(SCRIPT_ONLY_PROMPT, mode="long-run", task_id_prefix="SCRIPT")
        files = planned_files(tasks)
        validation_commands = [command for task in tasks for command in task["validation_commands"]]

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["expected_files"], ["src/calculadora_descuentos.py"])
        self.assertIn("src/calculadora_descuentos.py", files)
        self.assertNotIn("frontend/index.html", files)
        self.assertNotIn("frontend/app.js", files)
        self.assertNotIn("shared/project_schema.json", files)
        self.assertIn("python3 -m py_compile src/calculadora_descuentos.py", validation_commands)

    def test_script_only_prompt_ignores_python_paths_inside_negative_instructions(self) -> None:
        prompt = (
            "Crea solo un script Python pequeno. "
            "Archivo exacto: src/calculadora_descuentos.py. "
            "No crees src/reglas_descuento.py todavia; esa ausencia es intencional."
        )

        tasks = plan_project(prompt, mode="build", task_id_prefix="SCRIPT")

        self.assertEqual(tasks[0]["expected_files"], ["src/calculadora_descuentos.py"])

    def test_workspace_project_paths_are_not_expected_file_deliverables(self) -> None:
        prompt = (
            "sesion-20260516011354 SUMA DE NUMEROS "
            "workspace/projects/sesion-20260516011354-suma-de-numeros "
            "4 archivos detectados en el proyecto seleccionado; cerrar y arrancar sandbox."
        )

        tasks = plan_project(prompt, mode="smoke", task_id_prefix="RUNTIME")
        files = planned_files(tasks)
        validation_commands = [command for task in tasks for command in task["validation_commands"]]

        self.assertFalse(any(path.startswith("workspace/projects/") for path in files))
        self.assertTrue(all(Path(path).suffix for path in files))
        self.assertTrue(all("Path(p).is_file()" in command for command in validation_commands))

    def test_agent_project_metadata_is_not_expected_file_deliverable(self) -> None:
        prompt = (
            "Implementar .agent-project.json y agent-project.json no debe contar como producto. "
            "Crear frontend/app.js como archivo real."
        )

        tasks = plan_project(prompt, mode="build", task_id_prefix="META")
        files = planned_files(tasks)

        self.assertNotIn(".agent-project.json", files)
        self.assertNotIn("agent-project.json", files)
        self.assertIn("frontend/app.js", files)

    def test_game_sandbox_prompt_generates_static_frontend_deliverables(self) -> None:
        tasks = plan_project(
            "HAGAN UN JUEGO PONG BASICO Y LO LANZAN EN EL SANBOX PARA TESTEARLO",
            mode="smoke",
            task_id_prefix="RUNTIME",
        )

        self.assertEqual(tasks[0]["expected_files"], ["frontend/index.html", "frontend/styles.css", "frontend/app.js"])
        self.assertTrue(all("Path(p).is_file()" in command for command in tasks[0]["validation_commands"]))

    def test_tkinter_sum_prompt_generates_python_product_file(self) -> None:
        tasks = plan_project(
            "CREAME UN PROGRAMA QUE SUME NUMEROS DEBE DE SER RAMDOM Y UI TKINTER FAIL RAPIDO NO MAS DE 100 LINEAS DE CODIGO",
            mode="smoke",
            task_id_prefix="RUNTIME",
        )

        self.assertEqual(tasks[0]["expected_files"], ["src/suma_random_tkinter.py"])
        self.assertIn("python3 -m py_compile src/suma_random_tkinter.py", tasks[0]["validation_commands"])
        self.assertTrue(any("too_long" in command and "> 100" in command for command in tasks[0]["validation_commands"]))
        self.assertTrue(all("runtime/artifacts" not in path for path in tasks[0]["expected_files"]))


if __name__ == "__main__":
    unittest.main()
