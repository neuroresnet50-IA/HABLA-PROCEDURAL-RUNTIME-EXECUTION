import json
import tempfile
import unittest
from pathlib import Path

from backend.human_alignment_review import (
    HAR_STATUS_TASKS_READY,
    HAR_STATUS_WAITING,
    TECH_STACK_OPTIONS,
    create_human_alignment_review,
    submit_human_alignment_feedback,
)
from orchestrator.contracts import validate_project_state, validate_task_queue


class HumanAlignmentReviewTest(unittest.TestCase):
    def test_review_records_summary_without_touching_source_then_queues_feedback_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            frontend = project / "frontend"
            runtime = project / "runtime"
            frontend.mkdir()
            runtime.mkdir()
            (frontend / "index.html").write_text("<div id='app'></div>", encoding="utf-8")
            (frontend / "app.js").write_text(
                "import * as THREE from 'three';\nconst reward = 1;\n",
                encoding="utf-8",
            )
            (frontend / "styles.css").write_text("body { margin: 0; }\n", encoding="utf-8")
            original_sources = {
                path.relative_to(project).as_posix(): path.read_text(encoding="utf-8")
                for path in frontend.iterdir()
            }
            (runtime / "project_state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "project_id": "demo-har",
                        "status": "completed",
                        "mode": "build",
                        "current_task_id": None,
                        "completed_tasks": ["BUILD-001"],
                        "failed_tasks": [],
                        "blocked_tasks": [],
                        "checkpoints": ["build-001-checkpoint"],
                        "created_at": "2026-05-18T08:00:00+00:00",
                        "updated_at": "2026-05-18T08:10:00+00:00",
                    }
                ),
                encoding="utf-8",
            )
            (runtime / "task_queue.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "BUILD-001",
                            "title": "Build demo",
                            "goal": "Build a Three.js demo",
                            "status": "completed",
                            "priority": 10,
                            "dependencies": [],
                            "expected_files": [
                                "frontend/index.html",
                                "frontend/app.js",
                                "frontend/styles.css",
                            ],
                            "validation_commands": ["python3 -B -c \"print('ok')\""],
                            "timeout_seconds": 900,
                            "max_retries": 3,
                            "mode": "build",
                            "checkpoint_key": "build-001-checkpoint",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (runtime / "task_history.jsonl").write_text(
                json.dumps(
                    {
                        "recorded_at": "2026-05-18T08:10:00Z",
                        "result": {
                            "task_id": "BUILD-001",
                            "completed": True,
                            "files_created": [],
                            "files_modified": ["frontend/app.js"],
                            "validation_ran": ["python3 -B -c \"print('ok')\""],
                            "validation_passed": True,
                            "blockers": [],
                            "next_recommendation": "Task evidence and validation commands passed.",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            created = create_human_alignment_review(
                project_root=project,
                runtime_dir=runtime,
                source="automatic",
                trigger="project_completed",
                reason="Proyecto completado; abrir HAR.",
                task_id="BUILD-001",
            )

            self.assertTrue(created["created"])
            review = created["review"]
            self.assertEqual(review["status"], HAR_STATUS_WAITING)
            self.assertIn("SQL Server", TECH_STACK_OPTIONS["databases"])
            self.assertIn("JavaScript", review["summary"]["detected_stack"]["languages"])
            self.assertIn("Three.js", review["summary"]["detected_stack"]["visualization"])
            self.assertTrue((runtime / "human_alignment_reviews" / f"{review['id']}.json").is_file())
            self.assertTrue((runtime / "human_alignment_reviews" / f"{review['id']}.md").is_file())

            duplicated = create_human_alignment_review(
                project_root=project,
                runtime_dir=runtime,
                source="automatic",
                trigger="project_completed",
                reason="Proyecto completado; abrir HAR.",
                task_id="BUILD-001",
            )
            self.assertFalse(duplicated["created"])
            self.assertEqual(duplicated["review"]["id"], review["id"])

            submitted = submit_human_alignment_feedback(
                project_root=project,
                runtime_dir=runtime,
                review_id=review["id"],
                feedback="Cambiar PostgreSQL por SQL Server y mantener Three.js.",
                selected_stack_preferences={"databases": ["SQL Server"]},
            )

            self.assertEqual(submitted["review"]["status"], HAR_STATUS_TASKS_READY)
            queue = json.loads((runtime / "task_queue.json").read_text(encoding="utf-8"))
            validate_task_queue(queue)
            har_tasks = [task for task in queue if task["id"].startswith(review["id"])]
            self.assertEqual(len(har_tasks), 1)
            self.assertIn("SQL Server", har_tasks[0]["goal"])
            state = json.loads((runtime / "project_state.json").read_text(encoding="utf-8"))
            validate_project_state(state)
            self.assertEqual(state["status"], "human_alignment_pending")
            self.assertEqual(state["pending_human_alignment_tasks"], [har_tasks[0]["id"]])
            for relative, expected in original_sources.items():
                self.assertEqual((project / relative).read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
