from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .contracts import ProjectState, Task, TaskResult


class StateStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.runtime_dir = self.root / "runtime"

    def runtime_path(self, relative_path: str) -> Path:
        path = (self.runtime_dir / relative_path).resolve()
        if self.runtime_dir.resolve() not in path.parents and path != self.runtime_dir.resolve():
            raise ValueError(f"path escapes runtime directory: {relative_path}")
        return path

    def read_json(self, relative_path: str) -> dict[str, Any]:
        path = self.runtime_path(relative_path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"expected object JSON in {path}")
        return payload

    def write_json(self, relative_path: str, payload: dict[str, Any]) -> Path:
        path = self.runtime_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)
            handle.write("\n")
        os.replace(temp, path)
        return path

    def append_jsonl(self, relative_path: str, payload: dict[str, Any]) -> Path:
        path = self.runtime_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
            handle.write("\n")
        return path

    def load_project_state(self) -> ProjectState:
        return ProjectState.from_mapping(self.read_json("project_state.json"))

    def load_task_queue(self) -> list[Task]:
        path = self.runtime_path("task_queue.json")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("task_queue.json must contain a list")
        return [Task.from_mapping(item) for item in payload]

    def record_task_result(self, result: TaskResult) -> Path:
        return self.append_jsonl("task_results.jsonl", result.to_dict())
