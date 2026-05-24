import json
import tempfile
import unittest
from pathlib import Path

from backend.agent_worker_adapters import (
    ControlPlaneSessionWorkerAdapter,
    LegacyPtySessionWorkerAdapter,
    select_session_worker_adapter,
)
from orchestrator.contracts import ContractError
from orchestrator.directive_generator import DirectiveGenerationError, persist_directive
from orchestrator.executor import execute_task_with_details
from orchestrator.recovery import recover_task
from orchestrator.state_store import StateStore
from orchestrator.task_queue import TaskQueue, save_queue
from orchestrator.worker_adapter import WorkerProcessExecution


def create_task() -> dict:
    return {
        "id": "RUNTIME-BOUNDARY-001",
        "title": "Runtime boundary",
        "goal": "Runtime and worker boundaries must be explicit.",
        "status": "pending",
        "priority": 1,
        "dependencies": [],
        "expected_files": ["evidence.txt"],
        "validation_commands": ["python3 -c 'print(1)'"],
        "timeout_seconds": 30,
        "max_retries": 1,
        "mode": "build",
        "checkpoint_key": None,
    }


class FakeWorkerAdapter:
    name = "fake_worker_adapter"

    def execute(self, task, **_kwargs):
        payload = {
            "task_result": {
                "task_id": task["id"],
                "completed": True,
                "files_created": ["evidence.txt"],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": True,
                "blockers": [],
                "next_recommendation": "fake ok",
            },
            "execution": {
                "task_id": task["id"],
                "timed_out": False,
                "returncode": 0,
                "duration_seconds": 0.01,
                "stdout": "",
                "stderr": "",
            },
        }
        return WorkerProcessExecution(
            adapter_name=self.name,
            command=["fake-worker"],
            stdout=json.dumps(payload),
            stderr="",
            returncode=0,
            duration_seconds=0.01,
            timed_out=False,
            stopped_by_request=False,
        )


def create_directive(project_root: Path, runtime_dir: Path) -> dict:
    return {
        "schema_version": 1,
        "directive_type": "worker_operational_directive",
        "generated_at": "2026-05-19T00:00:00Z",
        "task_id": "RUNTIME-BOUNDARY-001",
        "sprint": {"number": 1, "objective": "test"},
        "traceability": {"source_hash": "a" * 64, "runtime_dir": str(runtime_dir)},
        "repository": {
            "system_root": str(project_root),
            "task_workspace_root": str(project_root),
            "mandatory_root": str(project_root),
            "forbidden_paths": [],
        },
        "task": {
            "id": "RUNTIME-BOUNDARY-001",
            "title": "Runtime boundary",
            "goal": "test",
            "expected_files": ["evidence.txt"],
            "validation_commands": [],
        },
        "operational_directive": {"summary": "test"},
        "rendered_instruction": "test",
    }


class RuntimeBoundaryTest(unittest.TestCase):
    def test_state_store_has_no_implicit_root_runtime_default(self) -> None:
        with self.assertRaises(TypeError):
            StateStore()  # type: ignore[call-arg]
        with self.assertRaises(ContractError):
            StateStore(None)  # type: ignore[arg-type]

    def test_state_store_project_runtime_constructor_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "workspace" / "projects" / "demo"
            store = StateStore.for_project_runtime(project_root)

        self.assertEqual(store.runtime_dir, (project_root / "runtime").resolve())

    def test_task_queue_and_recovery_require_explicit_store(self) -> None:
        with self.assertRaises(ContractError):
            TaskQueue()
        with self.assertRaises(ContractError):
            save_queue([])
        with self.assertRaises(ContractError):
            recover_task(create_task(), {"cause": "test"})

    def test_session_worker_adapter_selector_is_formal(self) -> None:
        self.assertIsInstance(select_session_worker_adapter(True), ControlPlaneSessionWorkerAdapter)
        self.assertIsInstance(select_session_worker_adapter(False), LegacyPtySessionWorkerAdapter)

    def test_executor_accepts_formal_worker_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = execute_task_with_details(
                create_task(),
                workspace=Path(temp_dir),
                worker_adapter=FakeWorkerAdapter(),
            )

        self.assertTrue(result["task_result"]["completed"])
        self.assertEqual(result["execution"]["worker_adapter"], "fake_worker_adapter")
        self.assertEqual(result["execution"]["worker_adapter_command"], ["fake-worker"])

    def test_directive_persistence_uses_active_runtime_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "workspace" / "projects" / "demo"
            runtime_dir = project_root / "runtime"
            directive = create_directive(project_root, runtime_dir)

            persisted = persist_directive(directive)

            json_path = Path(persisted["json_path"])
            self.assertTrue(json_path.is_file())
            self.assertTrue(json_path.resolve().is_relative_to((runtime_dir / "directives").resolve()))

    def test_directive_persistence_rejects_paths_outside_active_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "workspace" / "projects" / "demo"
            runtime_dir = project_root / "runtime"
            directive = create_directive(project_root, runtime_dir)

            with self.assertRaises(DirectiveGenerationError):
                persist_directive(directive, directives_dir=Path(temp_dir) / "runtime" / "directives")


if __name__ == "__main__":
    unittest.main()
