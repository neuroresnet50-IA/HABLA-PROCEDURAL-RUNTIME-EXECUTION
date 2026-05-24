"""Live reviewer plane for observing long-running control-plane sessions.

The reviewer is deliberately read-only with one exception: it appends its own
supervision events to runtime/logs/<session>-reviewer.jsonl.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REVIEWER_EVENT_TYPES = {
    "reviewer_started",
    "reviewer_snapshot",
    "reviewer_observation",
    "reviewer_warning",
    "reviewer_evidence_found",
    "reviewer_task_transition",
    "reviewer_validation_seen",
    "reviewer_checkpoint_seen",
    "reviewer_worker_alive",
    "reviewer_possible_stall",
    "reviewer_completed",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ReviewerConfig:
    snapshot_interval_seconds: float = float(os.environ.get("LIVE_REVIEWER_SNAPSHOT_INTERVAL_SECONDS", "15"))
    stall_warning_seconds: float = float(os.environ.get("LIVE_REVIEWER_STALL_WARNING_SECONDS", "180"))
    hard_stall_warning_seconds: float = float(os.environ.get("LIVE_REVIEWER_HARD_STALL_WARNING_SECONDS", "600"))
    poll_seconds: float = float(os.environ.get("LIVE_REVIEWER_POLL_SECONDS", "1"))


class LiveReviewer:
    """Observe persisted runtime evidence and emit human supervision events."""

    def __init__(
        self,
        *,
        session_id: str,
        project_id: str,
        project_root: str | Path,
        runtime_dir: str | Path | None = None,
        event_handler: Callable[[dict[str, Any]], None] | None = None,
        worker_status_provider: Callable[[], dict[str, Any]] | None = None,
        config: ReviewerConfig | None = None,
    ) -> None:
        if not session_id:
            raise ValueError("session_id is required")
        if not project_id:
            raise ValueError("project_id is required")
        self.session_id = session_id
        self.project_id = project_id
        self.project_root = Path(project_root).resolve()
        self.runtime_dir = Path(runtime_dir or self.project_root / "runtime").resolve()
        self.config = config or ReviewerConfig()
        self.event_handler = event_handler
        self.worker_status_provider = worker_status_provider
        self.started_monotonic = time.monotonic()
        self.task_started_monotonic = self.started_monotonic
        self.last_task_id: str | None = None
        self.last_found: set[str] = set()
        self.last_history_count = 0
        self.last_checkpoint_names: set[str] = set()
        self.warning_keys: set[str] = set()
        self.last_stall_level: str | None = None
        self.event_path = self.runtime_dir / "logs" / f"{self.session_id}-reviewer.jsonl"

    def run_until_stopped(self, stop_event: Any) -> None:
        self.emit("reviewer_started", severity="info")
        next_snapshot_at = time.monotonic()
        while not stop_event.wait(max(0.1, self.config.poll_seconds)):
            if time.monotonic() >= next_snapshot_at:
                self.observe_once()
                next_snapshot_at = time.monotonic() + max(1.0, self.config.snapshot_interval_seconds)
        self.observe_once(force=True)
        self.emit("reviewer_completed", severity="success")

    def observe_once(self, *, force: bool = False) -> list[dict[str, Any]]:
        snapshot = build_reviewer_status(
            project_root=self.project_root,
            runtime_dir=self.runtime_dir,
            session_id=self.session_id,
            project_id=self.project_id,
            worker_status=self._worker_status(),
        )
        emitted: list[dict[str, Any]] = []

        current_task_id = snapshot.get("current_task_id")
        if current_task_id != self.last_task_id:
            if self.last_task_id is not None:
                self.task_started_monotonic = time.monotonic()
                emitted.append(
                    self.emit(
                        "reviewer_task_transition",
                        severity="info",
                        snapshot=snapshot,
                        evidence={"previous_task_id": self.last_task_id, "next_task_id": current_task_id},
                    )
                )
            self.last_task_id = current_task_id

        found = set(snapshot.get("expected_files_found") or [])
        new_found = sorted(found - self.last_found)
        if new_found:
            emitted.append(
                self.emit(
                    "reviewer_evidence_found",
                    severity="success",
                    snapshot=snapshot,
                    evidence={"new_files": new_found},
                )
            )
        self.last_found = found

        history_count = int(snapshot.get("history_count") or 0)
        if history_count > self.last_history_count:
            emitted.append(
                self.emit(
                    "reviewer_validation_seen",
                    severity="success" if snapshot.get("latest_history_validation_passed") else "warning",
                    snapshot=snapshot,
                    evidence={"previous_history_count": self.last_history_count, "history_count": history_count},
                )
            )
        self.last_history_count = history_count

        checkpoint_names = set(snapshot.get("checkpoint_names") or [])
        new_checkpoints = sorted(checkpoint_names - self.last_checkpoint_names)
        if new_checkpoints:
            emitted.append(
                self.emit(
                    "reviewer_checkpoint_seen",
                    severity="success",
                    snapshot=snapshot,
                    evidence={"new_checkpoints": new_checkpoints},
                )
            )
        self.last_checkpoint_names = checkpoint_names

        if snapshot.get("worker_alive") is True:
            emitted.append(self.emit("reviewer_worker_alive", severity="info", snapshot=snapshot))

        for warning in snapshot.get("warnings") or []:
            warning_key = str(warning.get("code") or warning.get("message") or warning)
            if warning_key in self.warning_keys:
                continue
            self.warning_keys.add(warning_key)
            emitted.append(
                self.emit(
                    "reviewer_warning",
                    severity=str(warning.get("severity") or "warning"),
                    snapshot=snapshot,
                    evidence={"warning": warning},
                )
            )

        stall_level = self._stall_level(snapshot)
        if stall_level and (force or stall_level != self.last_stall_level):
            self.last_stall_level = stall_level
            emitted.append(
                self.emit(
                    "reviewer_possible_stall",
                    severity="error" if stall_level == "hard" else "warning",
                    snapshot=snapshot,
                    evidence={"stall_level": stall_level},
                )
            )

        emitted.append(self.emit("reviewer_snapshot", severity="info", snapshot=snapshot))
        return emitted

    def emit(
        self,
        event_type: str,
        *,
        severity: str = "info",
        snapshot: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if event_type not in REVIEWER_EVENT_TYPES:
            raise ValueError(f"Unsupported reviewer event type: {event_type}")
        snapshot = snapshot or build_reviewer_status(
            project_root=self.project_root,
            runtime_dir=self.runtime_dir,
            session_id=self.session_id,
            project_id=self.project_id,
            worker_status=self._worker_status(),
        )
        elapsed = max(0.0, time.monotonic() - self.started_monotonic)
        task_elapsed = max(0.0, time.monotonic() - self.task_started_monotonic)
        payload_evidence = dict(evidence or {})
        payload_evidence.setdefault("runtime_dir", str(self.runtime_dir))
        payload_evidence.setdefault("project_root", str(self.project_root))
        payload_evidence.setdefault("task_status", snapshot.get("current_task_status"))
        payload_evidence.setdefault("queue_counts", snapshot.get("queue_counts"))
        payload_evidence.setdefault("latest_history", snapshot.get("latest_history"))
        payload_evidence.setdefault("latest_checkpoint", snapshot.get("latest_checkpoint"))

        event = {
            "type": event_type,
            "event_type": event_type,
            "timestamp": utc_now(),
            "session_id": self.session_id,
            "project_id": self.project_id,
            "current_task_id": snapshot.get("current_task_id"),
            "severity": severity if severity in {"info", "warning", "success", "error"} else "info",
            "message": _message_for_event(event_type, snapshot, payload_evidence),
            "evidence": payload_evidence,
            "elapsed_seconds": round(elapsed, 3),
            "task_elapsed_seconds": round(task_elapsed, 3),
            "expected_files_found": list(snapshot.get("expected_files_found") or []),
            "expected_files_missing": list(snapshot.get("expected_files_missing") or []),
            "worker_alive": snapshot.get("worker_alive"),
            "worker_pid": snapshot.get("worker_pid"),
            "last_disk_activity_at": snapshot.get("last_disk_activity_at"),
            "status": snapshot,
            "source": "reviewer",
        }
        append_reviewer_event(self.event_path, event)
        if self.event_handler is not None:
            self.event_handler(event)
        return event

    def _worker_status(self) -> dict[str, Any]:
        if self.worker_status_provider is None:
            return {}
        try:
            status = self.worker_status_provider()
        except Exception as error:  # pragma: no cover - defensive observer boundary.
            return {"worker_alive": None, "worker_pid": None, "error": str(error)}
        return status if isinstance(status, dict) else {}

    def _stall_level(self, snapshot: dict[str, Any]) -> str | None:
        last_epoch = snapshot.get("last_disk_activity_epoch")
        if not isinstance(last_epoch, (int, float)):
            return None
        silence = max(0.0, time.time() - float(last_epoch))
        if silence >= self.config.hard_stall_warning_seconds:
            return "hard"
        if silence >= self.config.stall_warning_seconds:
            return "soft"
        return None


def build_reviewer_status(
    *,
    project_root: str | Path,
    runtime_dir: str | Path | None = None,
    session_id: str | None = None,
    project_id: str | None = None,
    worker_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_path = Path(project_root).resolve()
    runtime_path = Path(runtime_dir or project_path / "runtime").resolve()
    worker = worker_status or {}
    project_state = _read_json(runtime_path / "project_state.json", default={})
    task_queue = _read_json(runtime_path / "task_queue.json", default=[])
    if not isinstance(task_queue, list):
        task_queue = []
    history = _read_jsonl(runtime_path / "task_history.jsonl")
    failures = _read_jsonl(runtime_path / "failures.jsonl")
    checkpoints = sorted((runtime_path / "checkpoints").glob("*.json")) if (runtime_path / "checkpoints").exists() else []
    directives = sorted((runtime_path / "directives").glob("*.json")) if (runtime_path / "directives").exists() else []
    logs = sorted((runtime_path / "logs").glob("*")) if (runtime_path / "logs").exists() else []

    current_task = _select_current_task(project_state, task_queue)
    expected_files = list(current_task.get("expected_files", [])) if current_task else []
    evidence = _expected_file_evidence(project_path, expected_files)
    latest_history = history[-1] if history else None
    latest_checkpoint = checkpoints[-1].name if checkpoints else None
    last_activity_epoch = _last_disk_activity_epoch(project_path, runtime_path, expected_files)
    warnings = _runtime_warnings(project_state, task_queue, history, worker)
    queue_counts = _queue_counts(task_queue)
    worker_pid = worker.get("worker_pid")
    worker_alive = worker.get("worker_alive")
    if worker_alive is None and worker_pid:
        worker_alive = _pid_alive(worker_pid)

    return {
        "schema_version": 1,
        "status_type": "live_reviewer_status",
        "session_id": session_id,
        "project_id": project_id,
        "project_root": str(project_path),
        "runtime_dir": str(runtime_path),
        "runtime_exists": runtime_path.exists(),
        "project_state": project_state if isinstance(project_state, dict) else {},
        "queue_counts": queue_counts,
        "tasks_total": len(task_queue),
        "tasks_completed": queue_counts.get("completed", 0),
        "current_task_id": current_task.get("id") if current_task else None,
        "current_task_title": current_task.get("title") if current_task else "",
        "current_task_status": current_task.get("status") if current_task else None,
        "expected_files": expected_files,
        "expected_files_found": evidence["found"],
        "expected_files_missing": evidence["missing"],
        "expected_file_records": evidence["records"],
        "history_count": len(history),
        "latest_history": latest_history,
        "latest_history_validation_passed": _latest_validation_passed(latest_history),
        "failure_count": len(failures),
        "checkpoint_count": len(checkpoints),
        "checkpoint_names": [path.name for path in checkpoints],
        "latest_checkpoint": latest_checkpoint,
        "directive_count": len(directives),
        "latest_directive": directives[-1].name if directives else None,
        "log_count": len(logs),
        "worker_alive": worker_alive,
        "worker_pid": worker_pid,
        "last_disk_activity_at": _iso_from_epoch(last_activity_epoch),
        "last_disk_activity_epoch": last_activity_epoch,
        "warnings": warnings,
    }


def append_reviewer_event(path: str | Path, event: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")


def load_reviewer_events(
    project_root: str | Path,
    *,
    session_id: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    runtime_dir = Path(project_root).resolve() / "runtime"
    logs_dir = runtime_dir / "logs"
    if not logs_dir.exists():
        return []
    pattern = f"{session_id}-reviewer.jsonl" if session_id else "*-reviewer.jsonl"
    events: list[dict[str, Any]] = []
    for path in sorted(logs_dir.glob(pattern)):
        events.extend(_read_jsonl(path))
    events.sort(key=lambda item: str(item.get("timestamp") or ""))
    return events[-max(1, int(limit)):]


def _select_current_task(project_state: Any, task_queue: list[dict[str, Any]]) -> dict[str, Any] | None:
    state = project_state if isinstance(project_state, dict) else {}
    current_task_id = state.get("current_task_id")
    if isinstance(current_task_id, str) and current_task_id.strip():
        found = _task_by_id(task_queue, current_task_id)
        if found:
            return found
    for status in ("running", "pending"):
        for task in task_queue:
            if task.get("status") == status:
                return task
    return task_queue[0] if task_queue else None


def _task_by_id(task_queue: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    for task in task_queue:
        if task.get("id") == task_id:
            return task
    return None


def _expected_file_evidence(project_root: Path, expected_files: list[str]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for relative_path in expected_files:
        record = {
            "path": relative_path,
            "exists": False,
            "is_file": False,
            "size": None,
            "absolute_path": None,
        }
        try:
            path = (project_root / relative_path).resolve()
            path.relative_to(project_root)
            record["absolute_path"] = str(path)
            record["exists"] = path.exists()
            record["is_file"] = path.is_file() if path.exists() else False
            record["size"] = path.stat().st_size if path.exists() and path.is_file() else None
        except (OSError, ValueError):
            pass
        records.append(record)
    return {
        "records": records,
        "found": [item["path"] for item in records if item["exists"]],
        "missing": [item["path"] for item in records if not item["exists"]],
    }


def _last_disk_activity_epoch(project_root: Path, runtime_dir: Path, expected_files: list[str]) -> float | None:
    candidates: list[Path] = []
    for relative in ("project_state.json", "task_queue.json", "task_history.jsonl", "failures.jsonl"):
        candidates.append(runtime_dir / relative)
    for dirname in ("checkpoints", "directives", "logs"):
        directory = runtime_dir / dirname
        if directory.exists():
            for path in directory.glob("*"):
                if path.name.endswith("-reviewer.jsonl"):
                    continue
                candidates.append(path)
    for relative_path in expected_files:
        try:
            path = (project_root / relative_path).resolve()
            path.relative_to(project_root)
            candidates.append(path)
        except ValueError:
            continue
    mtimes: list[float] = []
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                mtimes.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(mtimes) if mtimes else None


def _queue_counts(task_queue: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "blocked": 0}
    for task in task_queue:
        status = str(task.get("status") or "pending")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _runtime_warnings(
    project_state: Any,
    task_queue: list[dict[str, Any]],
    history: list[dict[str, Any]],
    worker: dict[str, Any],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    current_task = _select_current_task(project_state, task_queue)
    if current_task and current_task.get("status") == "running" and worker.get("worker_alive") is False:
        warnings.append(
            {
                "code": "worker_not_alive_while_task_running",
                "severity": "warning",
                "message": "La tarea sigue running, pero no hay worker vivo detectado.",
            }
        )

    seen_history: set[tuple[Any, Any, Any]] = set()
    duplicates: list[str] = []
    for event in history:
        result = event.get("result") if isinstance(event, dict) else None
        if not isinstance(result, dict):
            continue
        key = (result.get("task_id"), result.get("completed"), result.get("validation_passed"))
        if key in seen_history:
            duplicates.append(str(result.get("task_id") or "unknown"))
        seen_history.add(key)
    if duplicates:
        warnings.append(
            {
                "code": "duplicate_history_events",
                "severity": "warning",
                "message": "Hay entradas duplicadas o repetidas en task_history.jsonl.",
                "task_ids": sorted(set(duplicates)),
            }
        )
    return warnings


def _message_for_event(event_type: str, snapshot: dict[str, Any], evidence: dict[str, Any]) -> str:
    task_id = snapshot.get("current_task_id") or "sin tarea activa"
    task_status = snapshot.get("current_task_status") or "sin estado"
    total = int(snapshot.get("tasks_total") or 0)
    completed = int(snapshot.get("tasks_completed") or 0)
    found = list(snapshot.get("expected_files_found") or [])
    missing = list(snapshot.get("expected_files_missing") or [])
    worker_alive = snapshot.get("worker_alive")
    checkpoint = snapshot.get("latest_checkpoint")

    if event_type == "reviewer_started":
        return (
            f"Primer corte: la supervision arranco. Veo {total} tarea(s) en cola, "
            f"{task_id} esta {task_status}. Significa que todavia solo puedo narrar evidencia persistida; "
            "espero archivos esperados, historial, validacion y checkpoint antes de declarar cierre."
        )
    if event_type == "reviewer_evidence_found":
        new_files = evidence.get("new_files") or found
        return (
            "Buena senal: aparecieron " + ", ".join(new_files) + ". "
            "Esto es evidencia real en disco, pero no declaro la tarea completa hasta ver validacion, "
            "checkpoint y transicion coherente de cola."
        )
    if event_type == "reviewer_task_transition":
        return (
            f"Confirmado: el control plane cambio de {evidence.get('previous_task_id')} a {evidence.get('next_task_id')}. "
            f"Veo {completed}/{total} tarea(s) completada(s). Ahora espero nueva directiva, worker y evidencia para la tarea activa."
        )
    if event_type == "reviewer_validation_seen":
        passed = "paso" if snapshot.get("latest_history_validation_passed") else "no paso"
        return (
            f"Vi nueva entrada de historial para {task_id}; la validacion {passed}. "
            "Esto significa que hay traza verificable. Ahora espero checkpoint o recovery segun corresponda."
        )
    if event_type == "reviewer_checkpoint_seen":
        return (
            f"Checkpoint detectado: {checkpoint}. La tarea dejo punto de reanudacion real. "
            "Ahora espero que el estado avance a la siguiente tarea lista o cierre la cola si ya termino."
        )
    if event_type == "reviewer_worker_alive":
        return (
            f"El worker sigue vivo para {task_id}. No concluyo progreso por eso solo; "
            "lo uso como senal de que la ejecucion aun puede estar trabajando mientras espero evidencia en disco."
        )
    if event_type == "reviewer_warning":
        warning = evidence.get("warning") if isinstance(evidence.get("warning"), dict) else {}
        warning_message = str(warning.get("message") or "hay una condicion inconsistente").rstrip(".")
        return (
            f"Advertencia: {warning_message}. "
            "No marco fallo automatico; espero nueva evidencia o una decision del runtime."
        )
    if event_type == "reviewer_possible_stall":
        if worker_alive is True:
            return (
                f"Sin nueva evidencia todavia para {task_id}. El worker sigue vivo, asi que no declaro fallo; "
                "espero actividad de disco, historial o checkpoint."
            )
        if worker_alive is False:
            return (
                f"Posible estancamiento: {task_id} sigue {task_status}, pero no detecto worker vivo ni nueva evidencia. "
                "No cambio estado; espero recovery, fallo estructurado o actividad nueva."
            )
        return (
            f"Sin nueva evidencia todavia para {task_id}. No tengo worker observable; "
            "espero archivos, historial, validacion o checkpoint antes de concluir."
        )
    if event_type == "reviewer_completed":
        return (
            f"Revision en vivo cerrada. El ultimo corte vio {completed}/{total} tarea(s) completada(s), "
            f"{len(found)} archivo(s) esperado(s) presentes y {len(missing)} pendiente(s)."
        )
    if found:
        return (
            f"Corte de supervision: {task_id} esta {task_status}. Veo {len(found)} archivo(s) esperado(s) "
            f"y faltan {len(missing)}. Esto indica evidencia parcial; espero validacion y checkpoint."
        )
    return (
        f"Corte de supervision: {task_id} esta {task_status}; {completed}/{total} tarea(s) completada(s). "
        "Aun no veo archivos esperados para esta tarea, asi que no declaro progreso de producto. "
        "Espero evidencia real en disco o una decision estructurada del runtime."
    )


def _read_json(path: Path, *, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
    except OSError:
        return rows
    return rows


def _latest_validation_passed(history_event: Any) -> bool | None:
    if not isinstance(history_event, dict):
        return None
    result = history_event.get("result")
    if isinstance(result, dict):
        value = result.get("validation_passed")
        return bool(value) if isinstance(value, bool) else None
    return None


def _iso_from_epoch(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _pid_alive(pid: Any) -> bool | None:
    try:
        value = int(pid)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    try:
        os.kill(value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
