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

from orchestrator.control_plane_artifact_executor import (
    COMPLEXITY_ESTIMATE_PATH,
    execute_control_plane_artifact_task,
    should_use_control_plane_artifact_executor,
)
from orchestrator.executor import execute_task_with_details
from orchestrator.host_write_executor import should_use_host_write_executor
from orchestrator.validator import validate_task_execution


def build_task(**overrides):
    task = {
        "id": "CONTROL-ARTIFACT-001",
        "title": "Disenar una cola FIFO persistente con estados pending",
        "goal": "Disenar una cola FIFO persistente con estados pending, running, completed y failed.",
        "status": "pending",
        "priority": 20,
        "dependencies": [],
        "expected_files": [COMPLEXITY_ESTIMATE_PATH],
        "validation_commands": [],
        "timeout_seconds": 900,
        "max_retries": 3,
        "mode": "build",
        "checkpoint_key": None,
    }
    task.update(overrides)
    return task


class ExplodingWorkerAdapter:
    name = "exploding"

    def execute(self, *args, **kwargs):  # pragma: no cover - should never be called.
        raise AssertionError("codex_worker route must not run for control_plane_artifact tasks")


class ControlPlaneArtifactExecutorTest(unittest.TestCase):
    def test_selector_accepts_only_complexity_estimate_artifact(self):
        self.assertTrue(should_use_control_plane_artifact_executor(build_task()))
        self.assertFalse(
            should_use_control_plane_artifact_executor(
                build_task(expected_files=["runtime/project_state.json"])
            )
        )
        self.assertFalse(
            should_use_control_plane_artifact_executor(
                build_task(expected_files=["docs/advanced_programming_case_001.md"])
            )
        )

    def test_executor_writes_complexity_estimate_and_validator_closes(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            task = build_task()

            result = execute_control_plane_artifact_task(task, workspace)
            validation = validate_task_execution(task, result, workspace=workspace)
            artifact_path = workspace / COMPLEXITY_ESTIMATE_PATH
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))

            self.assertEqual(result["execution_strategy"], "control_plane_artifact")
            self.assertTrue(artifact_path.is_file())
            self.assertEqual(payload["task_id"], task["id"])
            self.assertEqual(payload["fast_path"]["executor"], "control_plane_artifact_executor")
            self.assertTrue(payload["fast_path"]["codex_skipped"])
            self.assertTrue(validation["task_result"]["completed"])
            self.assertTrue(validation["task_result"]["validation_passed"])

    def test_execute_task_with_details_uses_fast_path_without_worker(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            task = build_task()

            execution = execute_task_with_details(
                task,
                workspace=workspace,
                worker_adapter=ExplodingWorkerAdapter(),
            )
            validation = validate_task_execution(task, execution, workspace=workspace)

            self.assertEqual(execution["execution"]["execution_strategy"], "control_plane_artifact")
            self.assertEqual(execution["execution"]["worker_adapter"], "control_plane_artifact_executor")
            self.assertEqual(execution["execution"]["worker_adapter_command"], [])
            self.assertTrue((workspace / COMPLEXITY_ESTIMATE_PATH).is_file())
            self.assertTrue(validation["task_result"]["completed"])

    def test_host_write_selector_still_owns_simple_docs_tasks(self):
        docs_task = build_task(
            id="CONTROL-ARTIFACT-DOCS-001",
            title="Prompt Flight docs",
            goal="Create the file docs/faro.txt. Its complete contents must be exactly FARO_OK.",
            expected_files=["docs/faro.txt"],
        )

        self.assertFalse(should_use_control_plane_artifact_executor(docs_task))
        self.assertTrue(should_use_host_write_executor(docs_task))


if __name__ == "__main__":
    unittest.main()
