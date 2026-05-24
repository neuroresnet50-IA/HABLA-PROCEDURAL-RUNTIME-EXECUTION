import json
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator.executor import execute_task_with_details


class ExecutorPipeDrainTest(unittest.TestCase):
    def test_worker_stdout_is_drained_while_process_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            task = {
                "id": "PIPE-DRAIN-001",
                "title": "Drain large worker output",
                "goal": "Worker must finish even when the inner command emits large output.",
                "status": "pending",
                "priority": 1,
                "dependencies": [],
                "expected_files": ["evidence.txt"],
                "validation_commands": [
                    "python3 -B -c \"from pathlib import Path; assert Path('evidence.txt').is_file()\""
                ],
                "timeout_seconds": 10,
                "max_retries": 0,
                "mode": "smoke",
                "checkpoint_key": "pipe-drain-001-checkpoint",
            }
            command = [
                sys.executable,
                "-c",
                (
                    "from pathlib import Path; "
                    "Path('evidence.txt').write_text('ok', encoding='utf-8'); "
                    "print('x' * 250000)"
                ),
            ]

            result = execute_task_with_details(task, workspace=workspace, command=command)

            self.assertTrue(result["task_result"]["completed"])
            self.assertFalse(result["execution"]["timed_out"])
            payload = json.loads(result["execution"]["worker_process_stdout"])
            self.assertTrue(payload["execution"]["stdout"].startswith("[output truncated;"))


if __name__ == "__main__":
    unittest.main()
