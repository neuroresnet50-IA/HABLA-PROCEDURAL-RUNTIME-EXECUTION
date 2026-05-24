"""Disk-backed persistence for the project orchestration runtime."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .contracts import (
        ContractError,
        validate_project_state,
        validate_task_queue,
        validate_task_result,
    )
except ImportError:  # pragma: no cover - allows direct script execution during bootstraps.
    from contracts import (  # type: ignore
        ContractError,
        validate_project_state,
        validate_task_queue,
        validate_task_result,
    )


class StateStore:
    """Load and save state, queue, checkpoints, history, and failures."""

    def __init__(self, runtime_dir: str | Path) -> None:
        if runtime_dir is None or not str(runtime_dir).strip():
            raise ContractError(
                "StateStore requires an explicit runtime_dir; use "
                "StateStore.for_project_runtime(project_root) or "
                "StateStore.for_repo_runtime(repo_root) intentionally."
            )
        self.runtime_dir = Path(runtime_dir).expanduser().resolve()
        self.project_state_path = self.runtime_dir / "project_state.json"
        self.task_queue_path = self.runtime_dir / "task_queue.json"
        self.task_history_path = self.runtime_dir / "task_history.jsonl"
        self.failures_path = self.runtime_dir / "failures.jsonl"
        self.checkpoints_dir = self.runtime_dir / "checkpoints"

    @classmethod
    def for_project_runtime(cls, project_root: str | Path) -> "StateStore":
        """Return a store bound to a project-local runtime directory."""

        return cls(Path(project_root).expanduser().resolve() / "runtime")

    @classmethod
    def for_repo_runtime(cls, repo_root: str | Path | None = None) -> "StateStore":
        """Return the repository-level runtime store by explicit request."""

        root = Path(repo_root).expanduser().resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
        return cls(root / "runtime")

    def load_project_state(self) -> dict[str, Any]:
        return validate_project_state(_read_json(self.project_state_path))

    def save_project_state(self, state: dict[str, Any]) -> None:
        _atomic_write_json(self.project_state_path, validate_project_state(state))

    def load_task_queue(self) -> list[dict[str, Any]]:
        return validate_task_queue(_read_json(self.task_queue_path))

    def save_task_queue(self, queue: list[dict[str, Any]]) -> None:
        _atomic_write_json(self.task_queue_path, validate_task_queue(queue))

    def append_task_history(self, result: dict[str, Any]) -> dict[str, Any]:
        event = {
            "recorded_at": _utc_now(),
            "result": validate_task_result(result),
        }
        _append_jsonl(self.task_history_path, event)
        return event

    def load_task_history(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.task_history_path)

    def append_failure(self, failure: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(failure, dict):
            raise ContractError("Failure must be an object")
        event = {
            "recorded_at": _utc_now(),
            "failure": _json_safe(failure),
        }
        _append_jsonl(self.failures_path, event)
        return event

    def load_failures(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.failures_path)

    def save_checkpoint(self, checkpoint_key: str, payload: dict[str, Any]) -> Path:
        key = _safe_checkpoint_key(checkpoint_key)
        document = {
            "checkpoint_key": key,
            "created_at": _utc_now(),
            "payload": _json_safe(payload),
        }
        path = self.checkpoints_dir / f"{key}.json"
        _atomic_write_json(path, document)
        return path

    def load_checkpoint(self, checkpoint_key: str) -> dict[str, Any]:
        key = _safe_checkpoint_key(checkpoint_key)
        return _read_json(self.checkpoints_dir / f"{key}.json")

    def list_checkpoints(self) -> list[str]:
        if not self.checkpoints_dir.exists():
            return []
        return sorted(path.stem for path in self.checkpoints_dir.glob("*.json") if path.is_file())


def load_project_state(runtime_dir: str | Path) -> dict[str, Any]:
    return StateStore(runtime_dir).load_project_state()


def save_project_state(state: dict[str, Any], runtime_dir: str | Path) -> None:
    StateStore(runtime_dir).save_project_state(state)


def load_task_queue(runtime_dir: str | Path) -> list[dict[str, Any]]:
    return StateStore(runtime_dir).load_task_queue()


def save_task_queue(queue: list[dict[str, Any]], runtime_dir: str | Path) -> None:
    StateStore(runtime_dir).save_task_queue(queue)


def append_task_history(result: dict[str, Any], runtime_dir: str | Path) -> dict[str, Any]:
    return StateStore(runtime_dir).append_task_history(result)


def load_task_history(runtime_dir: str | Path) -> list[dict[str, Any]]:
    return StateStore(runtime_dir).load_task_history()


def append_failure(failure: dict[str, Any], runtime_dir: str | Path) -> dict[str, Any]:
    return StateStore(runtime_dir).append_failure(failure)


def load_failures(runtime_dir: str | Path) -> list[dict[str, Any]]:
    return StateStore(runtime_dir).load_failures()


def save_checkpoint(checkpoint_key: str, payload: dict[str, Any], runtime_dir: str | Path) -> Path:
    return StateStore(runtime_dir).save_checkpoint(checkpoint_key, payload)


def load_checkpoint(checkpoint_key: str, runtime_dir: str | Path) -> dict[str, Any]:
    return StateStore(runtime_dir).load_checkpoint(checkpoint_key)


def list_checkpoints(runtime_dir: str | Path) -> list[str]:
    return StateStore(runtime_dir).list_checkpoints()


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
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(safe_payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
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


def _safe_checkpoint_key(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("checkpoint_key must be a non-empty string")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if any(character not in allowed for character in value):
        raise ContractError("checkpoint_key may only contain letters, numbers, dot, dash, or underscore")
    if value in {".", ".."}:
        raise ContractError("checkpoint_key must not be a path traversal segment")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
