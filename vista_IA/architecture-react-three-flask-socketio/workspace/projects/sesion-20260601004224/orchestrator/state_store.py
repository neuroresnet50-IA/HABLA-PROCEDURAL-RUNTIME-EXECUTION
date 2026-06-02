"""Project-local runtime persistence helpers.

The store is intentionally small for sprint 1: it can load and validate the
existing state/queue and exposes atomic save helpers for the control plane.
Workers should not call save methods for control-plane owned files.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    from .contracts import (
        ContractError,
        validate_project_state,
        validate_task_queue,
        validate_task_result,
    )
except ImportError:  # pragma: no cover
    from contracts import (  # type: ignore
        ContractError,
        validate_project_state,
        validate_task_queue,
        validate_task_result,
    )


class StateStore:
    """Read and write project runtime documents from disk."""

    def __init__(self, runtime_dir: str | Path) -> None:
        if not str(runtime_dir).strip():
            raise ContractError("runtime_dir is required")
        self.runtime_dir = Path(runtime_dir).expanduser().resolve()
        self.project_state_path = self.runtime_dir / "project_state.json"
        self.task_queue_path = self.runtime_dir / "task_queue.json"
        self.task_history_path = self.runtime_dir / "task_history.jsonl"
        self.failures_path = self.runtime_dir / "failures.jsonl"

    @classmethod
    def for_project_root(cls, project_root: str | Path) -> "StateStore":
        return cls(Path(project_root).expanduser().resolve() / "runtime")

    def load_project_state(self) -> dict[str, Any]:
        return validate_project_state(_read_json(self.project_state_path))

    def save_project_state(self, state: dict[str, Any]) -> None:
        _atomic_write_json(self.project_state_path, validate_project_state(state))

    def load_task_queue(self) -> list[dict[str, Any]]:
        return validate_task_queue(_read_json(self.task_queue_path))

    def save_task_queue(self, queue: list[dict[str, Any]]) -> None:
        _atomic_write_json(self.task_queue_path, validate_task_queue(queue))

    def append_task_history(self, result: dict[str, Any]) -> dict[str, Any]:
        event = {"result": validate_task_result(result)}
        _append_jsonl(self.task_history_path, event)
        return event

    def load_task_history(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.task_history_path)

    def append_failure(self, failure: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(failure, dict):
            raise ContractError("Failure must be an object")
        event = {"failure": _json_safe(failure)}
        _append_jsonl(self.failures_path, event)
        return event

    def load_failures(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.failures_path)


def load_project_state(runtime_dir: str | Path) -> dict[str, Any]:
    return StateStore(runtime_dir).load_project_state()


def load_task_queue(runtime_dir: str | Path) -> list[dict[str, Any]]:
    return StateStore(runtime_dir).load_task_queue()


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ContractError(f"Missing required runtime file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid JSON in {path}: {exc}") from exc


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_payload = _json_safe(payload)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(safe_payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_json_safe(event), ensure_ascii=True, sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ContractError(f"Invalid JSONL in {path}:{line_number}: {exc}") from exc
            if not isinstance(event, dict):
                raise ContractError(f"JSONL event in {path}:{line_number} must be an object")
            events.append(event)
    return events


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=True)
    except TypeError as exc:
        raise ContractError(f"Value is not JSON serializable: {exc}") from exc
    return value
