import json
import unittest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as backend_app


class RuntimeCleanWorkspaceEndpointTest(unittest.TestCase):
    def test_requires_explicit_confirmation(self):
        client = backend_app.app.test_client()

        response = client.post("/api/runtime/clean-workspace", json={"authorizationKeyword": "HABLA"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "missing_delete_confirmation")

    def test_requires_habla_keyword(self):
        client = backend_app.app.test_client()

        response = client.post(
            "/api/runtime/clean-workspace",
            json={"confirmDeleteProjects": True, "authorizationKeyword": "NO"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "invalid_authorization_keyword")

    def test_calls_cleaner_after_double_validation(self):
        client = backend_app.app.test_client()

        decision = {
            "allowed": True,
            "scope": "total",
            "summary_markdown": "=== DECISION DE BLANQUEO ===",
        }
        with patch.object(
            backend_app,
            "clear_runtime_workspace_state",
            return_value={"ok": True, "removedProjects": 2, "projects": []},
        ) as cleaner, patch.object(
            backend_app,
            "decidir_y_justificar_blanqueo",
            return_value=decision,
        ) as decide, patch.object(
            backend_app,
            "record_blanqueo_decision",
            return_value={"decision_markdown": "runtime/logs/blanqueo_decision.md"},
        ) as audit, patch.object(
            backend_app,
            "create_blanqueo_backup",
            return_value={"backup_dir": "backups/blanqueo/test", "manifest": "backups/blanqueo/test/manifest.json"},
        ) as backup, patch.object(
            backend_app,
            "create_post_blanqueo_recovery",
            return_value={"queue_path": "runtime/task_queue.json"},
        ) as recovery:
            response = client.post(
                "/api/runtime/clean-workspace",
                json={"confirmDeleteProjects": True, "authorizationKeyword": "HABLA"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        self.assertEqual(response.get_json()["scope"], "total")
        decide.assert_called_once()
        audit.assert_called_once_with(decision, backend_app.PROJECT_ROOT / "runtime")
        backup.assert_called_once()
        cleaner.assert_called_once_with()
        recovery.assert_called_once()

    def test_clear_pending_queue_unblocks_project_when_blocked_task_removed(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            projects_root = root / "workspace" / "projects"
            runtime_root = root / ".runtime"
            project_dir = projects_root / "demo-project"
            runtime_dir = project_dir / "runtime"
            runtime_dir.mkdir(parents=True)
            (runtime_dir / "task_queue.json").write_text(
                json.dumps(
                    [
                        {"id": "DONE-001", "status": "completed", "expected_files": ["done.txt"]},
                        {"id": "BLOCKED-001", "status": "blocked", "expected_files": ["blocked.txt"]},
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (runtime_dir / "project_state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_id": "demo-project",
                        "status": "blocked",
                        "current_task_id": "BLOCKED-001",
                        "completed_tasks": ["DONE-001"],
                        "blocked_tasks": ["BLOCKED-001"],
                        "failed_tasks": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root), patch.object(
                backend_app, "RUNTIME_ROOT", runtime_root
            ):
                result = backend_app.clear_pending_project_queue("demo-project", statuses=["blocked"], force=False)

            self.assertTrue(result["ok"])
            self.assertEqual(result["removedTaskIds"], ["BLOCKED-001"])
            next_queue = json.loads((runtime_dir / "task_queue.json").read_text(encoding="utf-8"))
            next_state = json.loads((runtime_dir / "project_state.json").read_text(encoding="utf-8"))
            self.assertEqual([task["id"] for task in next_queue], ["DONE-001"])
            self.assertEqual(next_state["status"], "completed")
            self.assertIsNone(next_state["current_task_id"])
            self.assertEqual(next_state["blocked_tasks"], [])

    def test_total_medium_requires_policy_confirmation(self):
        client = backend_app.app.test_client()

        decision = {
            "allowed": False,
            "scope": "total",
            "requires_confirmation": True,
            "summary_markdown": "=== DECISION DE BLANQUEO ===\nProceder: no",
        }
        with patch.object(backend_app, "decidir_y_justificar_blanqueo", return_value=decision), patch.object(
            backend_app,
            "record_blanqueo_decision",
            return_value={"decision_markdown": "runtime/logs/blanqueo_decision.md"},
        ), patch.object(backend_app, "clear_runtime_workspace_state") as cleaner:
            response = client.post(
                "/api/runtime/clean-workspace",
                json={
                    "confirmDeleteProjects": True,
                    "authorizationKeyword": "HABLA",
                    "runtimeMode": "medium",
                    "cleanScope": "total",
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"], "blanqueo_confirmation_required")
        cleaner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
