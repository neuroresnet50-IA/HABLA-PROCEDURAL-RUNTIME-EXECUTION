import json
import sys
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
from orchestrator.recovery import decide_recovery, recover_task
from orchestrator.state_store import StateStore
from orchestrator.task_queue import TaskQueue, save_queue
from orchestrator.worker_adapter import WorkerProcessExecution
from workers.codex_worker import run_task


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

    def test_recovery_blocks_bwrap_infrastructure_failure_without_split_or_retry(self) -> None:
        task = create_task()
        task["max_retries"] = 3
        failure = {
            "task_result": {
                "task_id": task["id"],
                "completed": False,
                "files_created": [],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": False,
                "blockers": ["Missing expected evidence files: evidence.txt"],
                "next_recommendation": "Retry with a smaller task or let recovery split the scope.",
            },
            "execution": {
                "stdout": "No pude completar la tarea: bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted",
                "stderr": "warning: Codex's Linux sandbox uses bubblewrap and needs access to create user namespaces.",
                "timed_out": False,
            },
        }

        decision = decide_recovery(task, failure, retry_count=0, allow_split=True)

        self.assertEqual(decision["action"], "block")
        self.assertTrue(decision["infrastructureFailure"])
        self.assertTrue(decision["fatalInfrastructureFailure"])
        self.assertIn("bwrap: loopback", decision["markers"])


    def test_recovery_defers_scanner_project_lock_without_split(self) -> None:
        task = create_task()
        task["max_retries"] = 3
        failure = {
            "task_result": {
                "task_id": task["id"],
                "completed": False,
                "files_created": [],
                "files_modified": ["evidence.txt"],
                "validation_ran": ["python3 -c 'print(1)'"] ,
                "validation_passed": False,
                "blockers": [
                    "Worker reported blocker: Scanner canonico bloqueado: statusCode=423, error=project_locked, reason=agent_session_active, sessionId=agent-test"
                ],
                "next_recommendation": "Fix blockers, rerun the isolated task if needed, then validate again.",
            }
        }

        decision = decide_recovery(task, failure, retry_count=0, allow_split=True)

        self.assertEqual(decision["action"], "block")
        self.assertTrue(decision["scannerDeferred"])
        self.assertTrue(decision["postflightLockContention"])
        self.assertFalse(decision["retry"])
        self.assertFalse(decision["split"])
        self.assertFalse(decision["extendTimeout"])
        self.assertEqual(decision["nextRecommendation"], "run_scanner_after_session_unlock")

    def test_codex_worker_defers_reported_scanner_project_lock_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task = create_task()
            payload = {
                "task_id": task["id"],
                "completed": False,
                "files_created": [],
                "files_modified": ["evidence.txt"],
                "validation_ran": ["python3 -c 'print(1)'"],
                "validation_passed": False,
                "blockers": [
                    "Scanner canonico bloqueado: statusCode=423, error=project_locked, reason=agent_session_active, sessionId=agent-test"
                ],
                "next_recommendation": "Retry scanner after active session closes.",
            }
            script = (
                "from pathlib import Path; import json; "
                "Path('evidence.txt').write_text('ok', encoding='utf-8'); "
                f"payload={payload!r}; "
                "print('TaskResult:' + chr(10) + '```json' + chr(10) + json.dumps(payload) + chr(10) + '```')"
            )

            result = run_task(task, workspace=Path(temp_dir), command=[sys.executable, "-c", script])

        self.assertTrue(result["task_result"]["completed"], result)
        self.assertEqual(result["task_result"]["blockers"], [])
        self.assertEqual(len(result["execution"].get("deferred_postflight_blockers") or []), 1)

    def test_codex_worker_preserves_child_reported_infrastructure_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            task = create_task()
            payload = {
                "task_id": task["id"],
                "completed": False,
                "files_created": [],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": False,
                "blockers": ["bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted"],
                "next_recommendation": "Fix worker sandbox before retrying.",
            }
            script = (
                "import json; "
                f"payload={payload!r}; "
                "print('TaskResult:\\n```json\\n' + json.dumps(payload) + '\\n```')"
            )

            result = run_task(task, workspace=Path(temp_dir), command=[sys.executable, "-c", script])

        blockers = result["task_result"]["blockers"]
        self.assertFalse(result["task_result"]["completed"])
        self.assertTrue(any("Worker reported blocker" in blocker for blocker in blockers))
        self.assertTrue(any("Worker infrastructure failure detected" in blocker for blocker in blockers))

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
