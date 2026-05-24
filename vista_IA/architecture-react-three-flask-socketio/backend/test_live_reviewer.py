import json
import sys
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
from orchestrator.live_reviewer import (
    LiveReviewer,
    ReviewerConfig,
    append_reviewer_event,
    build_reviewer_status,
)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")


class LiveReviewerTest(unittest.TestCase):
    def make_project(self, root: Path) -> tuple[Path, Path]:
        project = root / "workspace" / "projects" / "crm-demo"
        runtime = project / "runtime"
        write_json(
            runtime / "project_state.json",
            {
                "schema_version": 1,
                "project_id": "crm-demo",
                "status": "running",
                "mode": "long-run",
                "current_task_id": "TASK-001",
                "completed_tasks": [],
                "failed_tasks": [],
                "blocked_tasks": [],
                "checkpoints": [],
                "created_at": "2026-05-13T00:00:00Z",
                "updated_at": "2026-05-13T00:00:00Z",
            },
        )
        write_json(
            runtime / "task_queue.json",
            [
                {
                    "id": "TASK-001",
                    "title": "Build CRM shell",
                    "goal": "Create CRM frontend shell",
                    "status": "running",
                    "priority": 20,
                    "dependencies": [],
                    "expected_files": ["frontend/index.html", "frontend/app.js"],
                    "validation_commands": ["python3 -c 'print(1)'"],
                    "timeout_seconds": 300,
                    "max_retries": 1,
                    "mode": "long-run",
                    "checkpoint_key": "task-001",
                },
                {
                    "id": "TASK-002",
                    "title": "Build CRM schema",
                    "goal": "Create schema",
                    "status": "pending",
                    "priority": 10,
                    "dependencies": ["TASK-001"],
                    "expected_files": ["shared/crm_schema.json"],
                    "validation_commands": ["python3 -c 'print(1)'"],
                    "timeout_seconds": 300,
                    "max_retries": 1,
                    "mode": "long-run",
                    "checkpoint_key": "task-002",
                },
            ],
        )
        return project, runtime

    def test_reviewer_emits_snapshot_and_persists_jsonl(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project, runtime = self.make_project(Path(tmpdir))
            reviewer = LiveReviewer(
                session_id="agent-1",
                project_id="crm-demo",
                project_root=project,
                runtime_dir=runtime,
                config=ReviewerConfig(snapshot_interval_seconds=1, stall_warning_seconds=999, hard_stall_warning_seconds=999),
            )

            events = reviewer.observe_once()

            self.assertTrue(any(event["type"] == "reviewer_snapshot" for event in events))
            self.assertTrue((runtime / "logs" / "agent-1-reviewer.jsonl").exists())
            snapshot = events[-1]["status"]
            self.assertEqual(snapshot["current_task_id"], "TASK-001")
            self.assertEqual(snapshot["tasks_total"], 2)

    def test_detects_expected_files_found_and_missing(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project, runtime = self.make_project(Path(tmpdir))
            target = project / "frontend" / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("<main>CRM</main>\n", encoding="utf-8")

            status = build_reviewer_status(project_root=project, runtime_dir=runtime)

            self.assertEqual(status["expected_files_found"], ["frontend/index.html"])
            self.assertEqual(status["expected_files_missing"], ["frontend/app.js"])

    def test_detects_task_transition(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project, runtime = self.make_project(Path(tmpdir))
            reviewer = LiveReviewer(session_id="agent-1", project_id="crm-demo", project_root=project, runtime_dir=runtime)
            reviewer.observe_once()
            state = json.loads((runtime / "project_state.json").read_text(encoding="utf-8"))
            state["current_task_id"] = "TASK-002"
            write_json(runtime / "project_state.json", state)
            queue = json.loads((runtime / "task_queue.json").read_text(encoding="utf-8"))
            queue[0]["status"] = "completed"
            queue[1]["status"] = "running"
            write_json(runtime / "task_queue.json", queue)

            events = reviewer.observe_once()

            self.assertTrue(any(event["type"] == "reviewer_task_transition" for event in events))

    def test_detects_new_checkpoint_and_validation_history(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project, runtime = self.make_project(Path(tmpdir))
            reviewer = LiveReviewer(session_id="agent-1", project_id="crm-demo", project_root=project, runtime_dir=runtime)
            reviewer.observe_once()
            write_json(runtime / "checkpoints" / "task-001.json", {"ok": True})
            append_jsonl(
                runtime / "task_history.jsonl",
                {"recorded_at": "2026-05-13T00:01:00Z", "result": {"task_id": "TASK-001", "completed": True, "validation_passed": True}},
            )

            events = reviewer.observe_once()
            event_types = {event["type"] for event in events}

            self.assertIn("reviewer_checkpoint_seen", event_types)
            self.assertIn("reviewer_validation_seen", event_types)

    def test_detects_duplicate_history_and_missing_worker_warning(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project, runtime = self.make_project(Path(tmpdir))
            duplicate = {"recorded_at": "2026-05-13T00:01:00Z", "result": {"task_id": "TASK-001", "completed": True, "validation_passed": True}}
            append_jsonl(runtime / "task_history.jsonl", duplicate)
            append_jsonl(runtime / "task_history.jsonl", duplicate)
            reviewer = LiveReviewer(
                session_id="agent-1",
                project_id="crm-demo",
                project_root=project,
                runtime_dir=runtime,
                worker_status_provider=lambda: {"worker_alive": False, "worker_pid": 999999},
            )

            events = reviewer.observe_once()
            warnings = [event for event in events if event["type"] == "reviewer_warning"]
            warning_codes = {event["evidence"]["warning"]["code"] for event in warnings}

            self.assertIn("duplicate_history_events", warning_codes)
            self.assertIn("worker_not_alive_while_task_running", warning_codes)

    def test_reviewer_events_endpoint_returns_ordered_events(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project, runtime = self.make_project(root)
            first = {
                "type": "reviewer_snapshot",
                "timestamp": "2026-05-13T00:00:02Z",
                "session_id": "agent-1",
                "project_id": "crm-demo",
                "source": "reviewer",
            }
            second = {
                "type": "reviewer_started",
                "timestamp": "2026-05-13T00:00:01Z",
                "session_id": "agent-1",
                "project_id": "crm-demo",
                "source": "reviewer",
            }
            append_reviewer_event(runtime / "logs" / "agent-1-reviewer.jsonl", first)
            append_reviewer_event(runtime / "logs" / "agent-1-reviewer.jsonl", second)

            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", project.parent):
                response = backend_app.app.test_client().get("/api/projects/crm-demo/reviewer-events")

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["ok"])
            self.assertEqual([event["timestamp"] for event in payload["events"]], ["2026-05-13T00:00:01Z", "2026-05-13T00:00:02Z"])


if __name__ == "__main__":
    unittest.main()
