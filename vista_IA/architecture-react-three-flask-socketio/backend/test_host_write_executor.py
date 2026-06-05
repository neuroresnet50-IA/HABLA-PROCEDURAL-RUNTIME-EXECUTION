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

from orchestrator.executor import execute_task_with_details
from orchestrator.host_write_executor import execute_host_write_task, should_use_host_write_executor
from orchestrator.recovery import decide_recovery
from orchestrator.validator import validate_task_execution


def build_task(**overrides):
    task = {
        "id": "HOST-WRITE-001",
        "title": "Host write smoke",
        "goal": "Create the file docs/faro.txt. Its complete contents must be exactly FARO_OK.",
        "status": "pending",
        "priority": 10,
        "dependencies": [],
        "expected_files": ["docs/faro.txt"],
        "validation_commands": [],
        "timeout_seconds": 30,
        "max_retries": 0,
        "mode": "build",
        "checkpoint_key": None,
    }
    task.update(overrides)
    return task


class ExplodingWorkerAdapter:
    name = "exploding"

    def execute(self, *args, **kwargs):  # pragma: no cover - should never be called.
        raise AssertionError("codex_worker route must not run for host_write simple tasks")


class HostWriteExecutorTest(unittest.TestCase):
    def test_exact_file_content_and_validator(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            task = build_task()

            result = execute_host_write_task(task, workspace)
            validation = validate_task_execution(task, result, workspace=workspace)

            self.assertEqual(result["execution_strategy"], "host_write")
            self.assertTrue(result["materialized"])
            self.assertFalse(result["completed"])
            self.assertTrue((workspace / "docs" / "faro.txt").is_file())
            self.assertEqual((workspace / "docs" / "faro.txt").read_text(encoding="utf-8"), "FARO_OK")
            self.assertTrue(validation["task_result"]["completed"])
            self.assertTrue(validation["task_result"]["validation_passed"])

    def test_path_traversal_is_blocked(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()
            task = build_task(expected_files=["../escape.txt"], goal="Create the file ../escape.txt. Its complete contents must be exactly BAD.")

            result = execute_host_write_task(task, workspace)

            self.assertFalse(result["completed"])
            self.assertTrue(result["blockers"])
            self.assertFalse((workspace.parent / "escape.txt").exists())

    def test_absolute_path_is_blocked(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            absolute = Path(tmpdir) / "escape.txt"
            task = build_task(expected_files=[str(absolute)], goal=f"Create the file {absolute}. Its complete contents must be exactly BAD.")

            result = execute_host_write_task(task, workspace)

            self.assertFalse(result["completed"])
            self.assertTrue(any("Unsafe expected file path" in blocker for blocker in result["blockers"]))
            self.assertFalse(absolute.exists())

    def test_protected_runtime_file_is_blocked(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            runtime_state = workspace / "runtime" / "project_state.json"
            runtime_state.parent.mkdir(parents=True)
            runtime_state.write_text("ORIGINAL\n", encoding="utf-8")
            task = build_task(
                expected_files=["runtime/project_state.json"],
                goal="Create the file runtime/project_state.json. Its complete contents must be exactly BAD.",
            )

            result = execute_host_write_task(task, workspace)

            self.assertFalse(result["completed"])
            self.assertEqual(runtime_state.read_text(encoding="utf-8"), "ORIGINAL\n")

    def test_selector_accepts_simple_and_rejects_complex(self):
        simple = build_task(kind="simple_file_write")
        complex_task = build_task(
            id="HOST-WRITE-COMPLEX",
            title="Refactor backend",
            goal="Refactor backend Flask modules and update docs/faro.txt.",
        )

        self.assertTrue(should_use_host_write_executor(simple))
        self.assertFalse(should_use_host_write_executor(complex_task))

    def test_selector_accepts_docs_plan_even_when_title_has_complex_marker(self):
        task = build_task(
            id="HOST-WRITE-DOCS-PLAN",
            title="Refactorizar conceptualmente un modulo grande en tres capas",
            goal=(
                "Refactorizar conceptualmente un modulo grande en tres capas con responsabilidades claras.; "
                "Escribe la solucion o plan en docs/advanced_programming_case_002.md, "
                "manten el cambio pequeno, registra evidencia y no modifiques archivos no relacionados."
            ),
            expected_files=["docs/advanced_programming_case_002.md"],
        )

        self.assertTrue(should_use_host_write_executor(task))
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            execution = execute_task_with_details(task, workspace=workspace, worker_adapter=ExplodingWorkerAdapter())
            validation = validate_task_execution(task, execution, workspace=workspace)

            self.assertEqual(execution["execution"]["execution_strategy"], "host_write")
            self.assertTrue((workspace / "docs" / "advanced_programming_case_002.md").is_file())
            self.assertTrue(validation["task_result"]["completed"])
            self.assertTrue(validation["task_result"]["validation_passed"])

    def test_executor_uses_host_write_without_worker_then_validator_closes(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            task = build_task()

            execution = execute_task_with_details(task, workspace=workspace, worker_adapter=ExplodingWorkerAdapter())
            validation = validate_task_execution(task, execution, workspace=workspace)

            self.assertEqual(execution["execution"]["execution_strategy"], "host_write")
            self.assertFalse(execution["task_result"]["completed"])
            self.assertTrue((workspace / "docs" / "faro.txt").is_file())
            self.assertTrue(validation["task_result"]["completed"])

    def test_validator_rejects_completed_without_expected_files(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            task = build_task(expected_files=[])
            result = {
                "task_id": task["id"],
                "completed": True,
                "files_created": [],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": True,
                "blockers": [],
                "next_recommendation": "fake success",
            }

            validation = validate_task_execution(task, result, workspace=workspace)

            self.assertFalse(validation["task_result"]["completed"])
            self.assertFalse(validation["task_result"]["validation_passed"])
            self.assertTrue(any("expected_files is empty" in blocker for blocker in validation["task_result"]["blockers"]))

    def test_recovery_recommends_host_write_only_for_simple_bwrap(self):
        simple = build_task()
        complex_task = build_task(
            id="HOST-WRITE-BWRAP-COMPLEX",
            title="Complex backend refactor",
            goal="Refactor backend Flask runtime and debug worker infrastructure.",
        )
        failure = {
            "task_result": {
                "task_id": simple["id"],
                "completed": False,
                "files_created": [],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": False,
                "blockers": ["bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"],
                "next_recommendation": "",
            }
        }
        simple_decision = decide_recovery(simple, failure, retry_count=0)
        complex_failure = {**failure, "task_result": {**failure["task_result"], "task_id": complex_task["id"]}}
        complex_decision = decide_recovery(complex_task, complex_failure, retry_count=0)

        self.assertEqual(simple_decision["action"], "block")
        self.assertTrue(simple_decision["retryWithHostWriteExecutor"])
        self.assertEqual(simple_decision["nextRecommendation"], "retry_with_host_write_executor")
        self.assertEqual(complex_decision["action"], "block")
        self.assertFalse(complex_decision["retryWithHostWriteExecutor"])
        self.assertEqual(complex_decision["nextRecommendation"], "fix_worker_sandbox_or_use_no_bwrap")
        self.assertFalse(complex_decision["retry"])
        self.assertFalse(complex_decision["split"])


if __name__ == "__main__":
    unittest.main()
