import unittest

from orchestrator.contracts import ContractError, validate_project_state


def base_project_state() -> dict:
    return {
        "schema_version": 1,
        "project_id": "demo",
        "status": "running",
        "mode": "build",
        "current_task_id": None,
        "completed_tasks": [],
        "failed_tasks": [],
        "blocked_tasks": [],
        "checkpoints": [],
        "created_at": "2026-05-15T20:00:00Z",
        "updated_at": "2026-05-15T20:00:00Z",
    }


class ProjectStateRuntimeMetadataTest(unittest.TestCase):
    def test_accepts_runtime_visual_metadata_fields(self):
        state = base_project_state()
        state["live_app"] = {
            "url": "http://127.0.0.1:5174/",
            "pid": 42767,
            "status": "http_200_verified",
            "left_running": True,
        }
        state["pending_control_plane_work"] = {
            "lace_cycles": [2, 3, 4, 5, 6, 7, 8, 9, 10],
            "reason": "LACE cycles remain separate bounded tasks.",
        }

        normalized = validate_project_state(state)

        self.assertEqual(normalized["live_app"]["url"], "http://127.0.0.1:5174/")
        self.assertEqual(normalized["pending_control_plane_work"]["lace_cycles"], [2, 3, 4, 5, 6, 7, 8, 9, 10])

    def test_still_rejects_unregistered_project_state_fields(self):
        state = base_project_state()
        state["surprise_field"] = True

        with self.assertRaisesRegex(ContractError, "unsupported fields"):
            validate_project_state(state)


if __name__ == "__main__":
    unittest.main()
