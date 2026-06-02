from __future__ import annotations

import json
from datetime import datetime, timezone

from orchestrator.contracts import validate_task, validate_task_queue, validate_task_result
from orchestrator.state_store import StateStore


def _task(task_id: str = "TASK-001") -> dict[str, object]:
    return {
        "id": task_id,
        "title": "Crear archivo",
        "goal": "Crear evidencia persistente",
        "status": "pending",
        "priority": 10,
        "dependencies": [],
        "expected_files": ["README.md"],
        "validation_commands": ["python3 -m pytest -q"],
        "timeout_seconds": 900,
        "max_retries": 3,
        "mode": "build",
        "checkpoint_key": None,
    }


def test_contracts_validate_minimum_task_and_result() -> None:
    task = validate_task(_task())
    result = validate_task_result(
        {
            "task_id": task["id"],
            "completed": False,
            "files_created": [],
            "files_modified": [],
            "validation_ran": [],
            "validation_passed": False,
            "blockers": ["pendiente"],
            "next_recommendation": "continuar",
        }
    )

    assert task["mode"] == "build"
    assert result["task_id"] == "TASK-001"


def test_state_store_loads_and_saves_queue_in_temp_runtime(tmp_path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    now = datetime.now(timezone.utc).isoformat()
    (runtime / "project_state.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_id": "demo",
                "status": "running",
                "mode": "build",
                "current_task_id": None,
                "completed_tasks": [],
                "failed_tasks": [],
                "blocked_tasks": [],
                "checkpoints": [],
                "created_at": now,
                "updated_at": now,
            }
        ),
        encoding="utf-8",
    )
    (runtime / "task_queue.json").write_text(json.dumps([_task()]), encoding="utf-8")

    store = StateStore(runtime)
    assert store.load_project_state()["project_id"] == "demo"
    assert validate_task_queue(store.load_task_queue())[0]["id"] == "TASK-001"

    queue = [_task("TASK-002")]
    store.save_task_queue(queue)
    assert json.loads((runtime / "task_queue.json").read_text(encoding="utf-8"))[0]["id"] == "TASK-002"
