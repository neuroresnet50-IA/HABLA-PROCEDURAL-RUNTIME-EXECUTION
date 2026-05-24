import json
import unittest
from pathlib import Path

from orchestrator.contracts import (
    ALLOWED_PROJECT_STATUSES,
    OPTIONAL_PROJECT_STATE_FIELDS,
    validate_project_state,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ProjectStateSchemaContractTest(unittest.TestCase):
    def test_schema_status_enum_matches_python_contract(self) -> None:
        schema = _load_schema()
        self.assertEqual(
            set(schema["properties"]["status"]["enum"]),
            set(ALLOWED_PROJECT_STATUSES),
        )

    def test_schema_includes_optional_project_state_fields(self) -> None:
        schema = _load_schema()
        properties = set(schema["properties"])
        for field_name in OPTIONAL_PROJECT_STATE_FIELDS:
            self.assertIn(field_name, properties)

    def test_human_alignment_state_is_represented_in_contract_and_schema(self) -> None:
        state = {
            "schema_version": 1,
            "project_id": "audit-demo",
            "status": "human_alignment_pending",
            "mode": "build",
            "current_task_id": None,
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "checkpoints": [],
            "created_at": "2026-05-19T00:00:00Z",
            "updated_at": "2026-05-19T00:00:00Z",
            "pending_human_alignment_tasks": ["HUMAN_ALIGNMENT_REVIEW-001-001"],
        }
        schema = _load_schema()

        normalized = validate_project_state(state)

        self.assertEqual(normalized["status"], "human_alignment_pending")
        self.assertIn("human_alignment_pending", schema["properties"]["status"]["enum"])
        self.assertEqual(schema["properties"]["pending_human_alignment_tasks"]["type"], "array")
        self.assertTrue(schema["properties"]["pending_human_alignment_tasks"]["uniqueItems"])

    def test_queue_clear_metadata_is_represented_in_contract_and_schema(self) -> None:
        state = {
            "schema_version": 1,
            "project_id": "queue-demo",
            "status": "stopped",
            "mode": "build",
            "current_task_id": None,
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "checkpoints": [],
            "created_at": "2026-05-21T00:00:00Z",
            "updated_at": "2026-05-21T00:01:00Z",
            "last_queue_clear_at": "2026-05-21T00:01:00Z",
            "last_queue_clear_force": True,
            "last_queue_clear_removed_task_ids": ["RUNTIME-1"],
        }
        schema = _load_schema()

        normalized = validate_project_state(state)

        self.assertTrue(normalized["last_queue_clear_force"])
        self.assertEqual(normalized["last_queue_clear_removed_task_ids"], ["RUNTIME-1"])
        self.assertEqual(schema["properties"]["last_queue_clear_force"]["type"], "boolean")
        self.assertTrue(schema["properties"]["last_queue_clear_removed_task_ids"]["uniqueItems"])


def _load_schema() -> dict:
    return json.loads((REPO_ROOT / "schemas" / "project_state.schema.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
