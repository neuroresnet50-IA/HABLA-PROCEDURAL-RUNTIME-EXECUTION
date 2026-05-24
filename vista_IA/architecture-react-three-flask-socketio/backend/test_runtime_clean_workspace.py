import unittest
import sys
from pathlib import Path
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
