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


class HarnessAutopilotPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        with backend_app.cyberlace_training_runs_lock:
            backend_app.cyberlace_training_runs.clear()

    def tearDown(self) -> None:
        with backend_app.cyberlace_training_runs_lock:
            backend_app.cyberlace_training_runs.clear()

    def test_public_state_recovers_disk_only_active_run_as_interrupted(self):
        with TemporaryDirectory() as tmpdir:
            runs_dir = Path(tmpdir) / "training_runs"
            with patch.object(backend_app, "CYBERLACE_TRAINING_RUNS_DIR", runs_dir):
                backend_app._training_run_update(
                    "run-one",
                    status="running",
                    phase="runtime-dispatch",
                    message="running",
                    cycles=3,
                    results=[{"cycle": 1, "passed": True}],
                )
                with backend_app.cyberlace_training_runs_lock:
                    backend_app.cyberlace_training_runs.clear()

                state = backend_app._training_run_public_state("run-one")

                self.assertIsNotNone(state)
                self.assertEqual(state["status"], "interrupted")
                self.assertTrue(state["resumable"])
                self.assertEqual(state["resumeFromCycle"], 2)
                self.assertEqual(state["interruptionReason"], "backend_process_restart_or_memory_loss")
                self.assertTrue((runs_dir / "run-one.json").is_file())
                events = (runs_dir / "run-one.jsonl").read_text(encoding="utf-8")
                self.assertIn('"type": "run_interrupted"', events)

    def test_autopilot_start_persists_run_and_blocks_second_active_run(self):
        with TemporaryDirectory() as tmpdir:
            runs_dir = Path(tmpdir) / "training_runs"
            client = backend_app.app.test_client()
            with (
                patch.object(backend_app, "CYBERLACE_TRAINING_RUNS_DIR", runs_dir),
                patch.object(backend_app.socketio, "start_background_task", lambda *args, **kwargs: None),
            ):
                response = client.post(
                    "/api/harness/training/autopilot-start",
                    json={"campaignId": "persist-smoke", "cycles": 2, "taskDelaySeconds": 1},
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                run = payload["run"]
                self.assertEqual(run["status"], "queued")
                self.assertEqual(run["resumeFromCycle"], 1)
                self.assertTrue((runs_dir / f"{run['runId']}.json").is_file())
                self.assertTrue((runs_dir / f"{run['runId']}.jsonl").is_file())

                disk_state = json.loads((runs_dir / f"{run['runId']}.json").read_text(encoding="utf-8"))
                self.assertEqual(disk_state["runId"], run["runId"])
                self.assertIn("runPath", disk_state)
                self.assertIn("eventsPath", disk_state)

                second = client.post(
                    "/api/harness/training/autopilot-start",
                    json={"campaignId": "persist-smoke-2", "cycles": 1, "taskDelaySeconds": 1},
                )
                self.assertEqual(second.status_code, 409)
                self.assertEqual(second.get_json()["error"], "training_run_active")


if __name__ == "__main__":
    unittest.main()
