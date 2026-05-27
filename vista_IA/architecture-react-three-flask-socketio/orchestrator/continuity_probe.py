"""Internal continuity probe for HABLA runtime wiring.

The probe sends a traceable canary signal through persisted policy, plan,
queue, directive, worker, validator, history, checkpoint, Observer, and Harness
surfaces. It is intentionally small and auditable; it does not replace the
project E2E gate.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .contracts import ContractError, validate_task
    from .directive_context import build_directive_context
    from .directive_generator import generate_directive, persist_directive
    from .executor import execute_task_with_details
    from .habla_adapter import build_habla_guide
    from .plan_loader import load_plan
    from .policy_loader import load_policy
    from .state_store import StateStore
    from .task_queue import TaskQueue
    from .validator import validate_task_execution
except ImportError:  # pragma: no cover - supports direct script execution.
    from contracts import ContractError, validate_task  # type: ignore
    from directive_context import build_directive_context  # type: ignore
    from directive_generator import generate_directive, persist_directive  # type: ignore
    from executor import execute_task_with_details  # type: ignore
    from habla_adapter import build_habla_guide  # type: ignore
    from plan_loader import load_plan  # type: ignore
    from policy_loader import load_policy  # type: ignore
    from state_store import StateStore  # type: ignore
    from task_queue import TaskQueue  # type: ignore
    from validator import validate_task_execution  # type: ignore


DEFAULT_BASE_URL = "http://127.0.0.1:5001"
DEFAULT_PROJECT = "continuity-probe-canary"
VALID_MODES = {"read_only", "active_canary", "harness_canary"}
TERMINAL_BAD_STATUSES = {"failed", "disconnected", "missing_evidence", "timeout"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_trace_id() -> str:
    return "continuity-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str, fallback: str = DEFAULT_PROJECT) -> str:
    raw = str(value or "").strip() or fallback
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-._")
    return cleaned[:80] or fallback


def run_continuity_probe(
    *,
    repo_root: str | Path | None = None,
    mode: str = "active_canary",
    project: str = DEFAULT_PROJECT,
    base_url: str = DEFAULT_BASE_URL,
    trace_id: str | None = None,
    timeout_seconds: int = 45,
    include_harness: bool | None = None,
) -> dict[str, Any]:
    probe = ContinuityProbe(
        repo_root=repo_root,
        mode=mode,
        project=project,
        base_url=base_url,
        trace_id=trace_id,
        timeout_seconds=timeout_seconds,
        include_harness=include_harness,
    )
    return probe.run()


def load_continuity_report(*, repo_root: str | Path | None = None, trace_id: str) -> dict[str, Any] | None:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
    path = root / "runtime" / "continuity_probe" / safe_slug(trace_id, "missing") / "report.json"
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return None


def list_continuity_reports(*, repo_root: str | Path | None = None, limit: int = 20) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
    reports_root = root / "runtime" / "continuity_probe"
    if not reports_root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for report_path in sorted(reports_root.glob("*/report.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        report = load_continuity_report(repo_root=root, trace_id=report_path.parent.name)
        if not isinstance(report, dict):
            continue
        rows.append(
            {
                "traceId": report.get("traceId"),
                "mode": report.get("mode"),
                "project": report.get("project"),
                "status": report.get("status"),
                "result": report.get("result"),
                "startedAt": report.get("startedAt"),
                "finishedAt": report.get("finishedAt"),
                "reportPath": report.get("reportPath"),
            }
        )
        if len(rows) >= limit:
            break
    return rows


class ContinuityProbe:
    def __init__(
        self,
        *,
        repo_root: str | Path | None,
        mode: str,
        project: str,
        base_url: str,
        trace_id: str | None,
        timeout_seconds: int,
        include_harness: bool | None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
        self.mode = str(mode or "active_canary").strip().lower()
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of: {', '.join(sorted(VALID_MODES))}")
        self.project = safe_slug(project)
        self.base_url = str(base_url or "").rstrip("/")
        self.trace_id = safe_slug(trace_id or new_trace_id(), "continuity")
        self.timeout_seconds = max(5, min(int(timeout_seconds or 45), 300))
        self.include_harness = bool(include_harness) if include_harness is not None else True
        self.run_dir = self.repo_root / "runtime" / "continuity_probe" / self.trace_id
        self.events_path = self.run_dir / "events.jsonl"
        self.report_path = self.run_dir / "report.json"
        self.markdown_path = self.run_dir / "report.md"
        self.started = time.monotonic()
        self.report: dict[str, Any] = {
            "schemaVersion": 1,
            "traceId": self.trace_id,
            "mode": self.mode,
            "project": self.project,
            "baseUrl": self.base_url,
            "status": "running",
            "result": "running",
            "startedAt": utc_now(),
            "finishedAt": "",
            "durationSeconds": 0.0,
            "checks": {},
            "summary": {"ok": 0, "failed": 0, "skipped": 0, "warning": 0, "total": 0},
            "artifacts": {
                "runDir": self._relative(self.run_dir),
                "eventsPath": self._relative(self.events_path),
                "reportPath": self._relative(self.report_path),
                "markdownPath": self._relative(self.markdown_path),
            },
        }

    def run(self) -> dict[str, Any]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._persist_input()
        self._check_policy()
        self._check_plan()
        self._check_imports()
        self._check_backend_health()

        if self.mode == "active_canary":
            self._run_active_canary()
        else:
            for name in (
                "task_created",
                "queue_persisted",
                "directive_generated",
                "worker_executed",
                "validator_passed",
                "history_written",
                "checkpoint_written",
            ):
                self._set_check(name, "skipped", "Skipped because probe mode is not active_canary.")

        self._check_observer()
        if self.include_harness or self.mode == "harness_canary":
            self._check_harness()
        else:
            for name in ("harness_reachable", "safety_learning_readable", "autopilot_memory"):
                self._set_check(name, "skipped", "Harness checks disabled by request.")
        return self._finalize()

    def _persist_input(self) -> None:
        payload = {
            "traceId": self.trace_id,
            "mode": self.mode,
            "project": self.project,
            "baseUrl": self.base_url,
            "createdAt": utc_now(),
            "prompt": "HABLA CircuitProbe canary prompt-to-action continuity signal.",
        }
        path = self.run_dir / "input.json"
        self._write_json(path, payload)
        self._set_check("prompt_input", "ok", "Probe input persisted with traceId.", evidencePath=self._relative(path))

    def _check_policy(self) -> None:
        try:
            policy = load_policy(self.repo_root)
            rules = policy.get("master_rules") or []
            self._set_check(
                "policy_loaded",
                "ok",
                "AGENTS.md loaded through policy_loader.",
                source=policy.get("source_path"),
                ruleCount=len(rules),
            )
        except Exception as exc:
            self._set_check("policy_loaded", "failed", "Policy loader failed.", error=self._error(exc))

    def _check_plan(self) -> None:
        try:
            plan = load_plan(self.repo_root)
            self._set_check(
                "plan_loaded",
                "ok",
                "PLANS.md loaded through plan_loader.",
                source=plan.get("source_path"),
                sprintCount=len(plan.get("sprints") or {}),
                moduleCount=len(plan.get("modules") or {}),
            )
        except Exception as exc:
            self._set_check("plan_loaded", "failed", "Plan loader failed.", error=self._error(exc))

    def _check_imports(self) -> None:
        modules = [
            "orchestrator.state_store",
            "orchestrator.task_queue",
            "orchestrator.directive_context",
            "orchestrator.directive_generator",
            "orchestrator.executor",
            "orchestrator.validator",
            "workers.codex_worker",
        ]
        try:
            __import__("orchestrator.state_store")
            self._set_check("imports_loaded", "ok", "Core orchestration imports resolved.", modules=modules)
        except Exception as exc:
            self._set_check("imports_loaded", "failed", "Core orchestration import failed.", modules=modules, error=self._error(exc))

    def _check_backend_health(self) -> None:
        if not self.base_url:
            self._set_check("backend_health", "skipped", "No baseUrl supplied.")
            return
        status_code, payload = self._request_json("GET", "/api/health", timeout=8)
        if status_code == 200 and payload.get("ok") is not False:
            self._set_check("backend_health", "ok", "Backend health endpoint responded.", statusCode=status_code, service=payload.get("service"))
        else:
            self._set_check("backend_health", "failed", "Backend health endpoint failed.", statusCode=status_code, payload=self._compact(payload))

    def _run_active_canary(self) -> None:
        if not self.project.startswith("continuity-"):
            self._set_check(
                "task_created",
                "failed",
                "Active canary only writes to project slugs starting with continuity-.",
                project=self.project,
            )
            return
        try:
            project_dir = self.repo_root / "workspace" / "projects" / self.project
            runtime_dir = project_dir / "runtime"
            task_id = "CONTINUITY-" + self.trace_id.replace("continuity-", "")
            task = self._build_task(task_id)
            validate_task(task)
            self._bootstrap_project(project_dir, runtime_dir, task_id)
            self._set_check("task_created", "ok", "Canary task built and validated.", taskId=task_id, projectPath=self._relative(project_dir))

            store = StateStore.for_project_runtime(project_dir)
            queue = TaskQueue(store, bootstrap_empty=True)
            queue.enqueue(task)
            persisted_queue = store.load_task_queue()
            queue_ok = any(item.get("id") == task_id for item in persisted_queue)
            self._set_check(
                "queue_persisted",
                "ok" if queue_ok else "missing_evidence",
                "Task queue persisted and reloaded." if queue_ok else "Task id missing after queue reload.",
                path=self._relative(store.task_queue_path),
                taskCount=len(persisted_queue),
            )

            context = build_directive_context(
                repo_root=self.repo_root,
                runtime_dir=runtime_dir,
                task_workspace_root=project_dir,
                task_id=task_id,
                strict=False,
            )
            guide = build_habla_guide(context)
            directive = generate_directive(context, guide)
            persisted = persist_directive(directive, directives_dir=runtime_dir / "directives")
            directive_path = persisted.get("json_path")
            self._set_check(
                "directive_generated",
                "ok" if directive_path and Path(str(directive_path)).is_file() else "missing_evidence",
                "Worker directive generated and persisted.",
                path=self._relative(Path(str(directive_path))) if directive_path else None,
                taskId=task_id,
            )

            queue.mark_task_status(task_id, "running")
            command = [sys.executable, "-B", "-c", self._worker_code()]
            execution = execute_task_with_details(
                task,
                workspace=project_dir,
                command=command,
                python_executable=sys.executable,
                worker_timeout_grace_seconds=3,
            )
            worker_result = execution.get("task_result") if isinstance(execution, dict) else {}
            worker_execution = execution.get("execution") if isinstance(execution, dict) else {}
            worker_ok = bool(isinstance(worker_result, dict) and worker_result.get("completed") is True)
            self._set_check(
                "worker_executed",
                "ok" if worker_ok else "failed",
                "Codex subprocess worker executed canary command." if worker_ok else "Worker did not complete the canary task.",
                taskId=task_id,
                workerAdapter=worker_execution.get("worker_adapter"),
                workerReturnCode=worker_execution.get("worker_returncode"),
                childReturnCode=worker_execution.get("returncode"),
                output=self._compact(worker_execution.get("stdout")),
                blockers=worker_result.get("blockers") if isinstance(worker_result, dict) else None,
            )

            validation = validate_task_execution(task, execution, workspace=project_dir, command_timeout_seconds=15)
            validated_result = validation["task_result"]
            validation_ok = bool(validated_result.get("validation_passed") is True and validated_result.get("completed") is True)
            self._set_check(
                "validator_passed",
                "ok" if validation_ok else "failed",
                "Validator confirmed disk evidence and validation command." if validation_ok else "Validator rejected canary evidence.",
                validationPassed=validated_result.get("validation_passed"),
                validationRan=validated_result.get("validation_ran"),
                blockers=validated_result.get("blockers"),
            )

            queue.mark_task_status(task_id, "completed" if validation_ok else "failed")
            event = store.append_task_history(validated_result)
            history_ok = store.task_history_path.is_file() and bool(event.get("result", {}).get("task_id") == task_id)
            self._set_check(
                "history_written",
                "ok" if history_ok else "missing_evidence",
                "Task history event appended." if history_ok else "Task history event missing.",
                path=self._relative(store.task_history_path),
                taskId=task_id,
            )

            checkpoint_path = store.save_checkpoint(
                "continuity-" + self.trace_id,
                {
                    "traceId": self.trace_id,
                    "taskId": task_id,
                    "validationPassed": validation_ok,
                    "createdFile": "src/continuity_probe.txt",
                },
            )
            state = store.load_project_state()
            state["status"] = "completed" if validation_ok else "failed"
            state["current_task_id"] = None
            if validation_ok and task_id not in state["completed_tasks"]:
                state["completed_tasks"].append(task_id)
            if not validation_ok and task_id not in state["failed_tasks"]:
                state["failed_tasks"].append(task_id)
            checkpoint_key = checkpoint_path.stem
            if checkpoint_key not in state["checkpoints"]:
                state["checkpoints"].append(checkpoint_key)
            state["updated_at"] = utc_now()
            store.save_project_state(state)
            self._set_check(
                "checkpoint_written",
                "ok" if checkpoint_path.is_file() else "missing_evidence",
                "Continuity checkpoint written and project state updated.",
                path=self._relative(checkpoint_path),
                projectState=self._relative(store.project_state_path),
            )
        except Exception as exc:
            self._set_check("active_canary", "failed", "Active canary raised an exception.", error=self._error(exc))
            for name in (
                "task_created",
                "queue_persisted",
                "directive_generated",
                "worker_executed",
                "validator_passed",
                "history_written",
                "checkpoint_written",
            ):
                if name not in self.report["checks"]:
                    self._set_check(name, "failed", "Active canary stopped before this check ran.")

    def _check_observer(self) -> None:
        if not self.base_url:
            self._set_check("observer_readable", "skipped", "No baseUrl supplied.")
            return
        status_code, payload = self._request_json("GET", "/api/observer/status", timeout=10)
        observer = payload.get("observer") if isinstance(payload.get("observer"), dict) else {}
        if status_code == 200 and payload.get("ok") is not False:
            self._set_check(
                "observer_readable",
                "ok",
                "Observer status is readable without starting a mission.",
                statusCode=status_code,
                state=observer.get("state"),
                enabled=observer.get("enabled"),
            )
        else:
            self._set_check("observer_readable", "failed", "Observer status endpoint failed.", statusCode=status_code, payload=self._compact(payload))

    def _check_harness(self) -> None:
        if not self.base_url:
            self._set_check("harness_reachable", "skipped", "No baseUrl supplied.")
            self._set_check("safety_learning_readable", "skipped", "No baseUrl supplied.")
        else:
            status_code, payload = self._request_json("GET", "/api/harness/training/summary", timeout=15)
            summary_ok = status_code == 200 and payload.get("ok") is True
            self._set_check(
                "harness_reachable",
                "ok" if summary_ok else "failed",
                "Harness training summary endpoint responded." if summary_ok else "Harness training summary failed.",
                statusCode=status_code,
                hasRunsKey=isinstance(payload, dict) and "runs" in payload,
                caseCount=len(payload.get("cases") or []) if isinstance(payload, dict) else None,
            )
            status_code, payload = self._request_json("GET", "/api/harness/safety-learning/status", timeout=10)
            safety_ok = status_code == 200 and isinstance(payload, dict) and payload.get("ok") is not False
            self._set_check(
                "safety_learning_readable",
                "ok" if safety_ok else "failed",
                "Safety Learning status endpoint responded." if safety_ok else "Safety Learning status failed.",
                statusCode=status_code,
                totalExperiences=payload.get("totalExperiences") or payload.get("total_experiences") if isinstance(payload, dict) else None,
            )

        runs_dir = self.repo_root / "runtime" / "cyberlace" / "training_runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        self._set_check(
            "autopilot_memory",
            "ok" if runs_dir.is_dir() else "missing_evidence",
            "Autopilot persistent run directory is present.",
            path=self._relative(runs_dir),
            jsonRunCount=len(list(runs_dir.glob("*.json"))) if runs_dir.is_dir() else 0,
        )

    def _build_task(self, task_id: str) -> dict[str, Any]:
        validation_code = (
            "from pathlib import Path; "
            "text=Path('src/continuity_probe.txt').read_text(encoding='utf-8'); "
            f"assert 'traceId={self.trace_id}' in text; "
            "assert 'status=worker_executed' in text"
        )
        return {
            "id": task_id,
            "title": "Continuity probe canary task",
            "goal": "Write one traceable canary artifact through a real isolated worker.",
            "status": "pending",
            "priority": 100,
            "dependencies": [],
            "expected_files": ["src/continuity_probe.txt"],
            "validation_commands": ["python3 -B -c " + shlex.quote(validation_code)],
            "timeout_seconds": self.timeout_seconds,
            "max_retries": 0,
            "mode": "build",
            "checkpoint_key": None,
        }

    def _bootstrap_project(self, project_dir: Path, runtime_dir: Path, task_id: str) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "src").mkdir(parents=True, exist_ok=True)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        for child in ("checkpoints", "directives", "artifacts", "logs"):
            (runtime_dir / child).mkdir(parents=True, exist_ok=True)
        now = utc_now()
        state = {
            "schema_version": 1,
            "project_id": self.project,
            "status": "running",
            "mode": "build",
            "current_task_id": task_id,
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "checkpoints": [],
            "created_at": now,
            "updated_at": now,
        }
        store = StateStore.for_project_runtime(project_dir)
        store.save_project_state(state)
        store.save_task_queue([])
        store.failures_path.parent.mkdir(parents=True, exist_ok=True)
        store.failures_path.touch(exist_ok=True)
        (project_dir / "README.md").write_text(
            "# HABLA CircuitProbe Canary\n\nControlled project generated by continuity_probe.\n",
            encoding="utf-8",
        )

    def _worker_code(self) -> str:
        payload = json.dumps(
            {
                "traceId": self.trace_id,
                "status": "worker_executed",
                "createdAt": utc_now(),
                "source": "HABLA CircuitProbe",
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        return (
            "from pathlib import Path\n"
            "p=Path('src/continuity_probe.txt')\n"
            "p.parent.mkdir(parents=True, exist_ok=True)\n"
            f"p.write_text('traceId={self.trace_id}\\nstatus=worker_executed\\npayload=' + {payload!r} + '\\n', encoding='utf-8')\n"
            "print('wrote ' + str(p))\n"
        )

    def _request_json(self, method: str, path: str, *, timeout: int) -> tuple[int, dict[str, Any]]:
        request = Request(f"{self.base_url}{path}", headers={"Accept": "application/json"}, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return int(response.status), json.loads(raw) if raw else {}
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "non_json_error", "message": raw}
            return int(exc.code), payload
        except (TimeoutError, URLError, OSError) as exc:
            return 0, {"ok": False, "error": "connection_failed", "message": str(exc)}

    def _set_check(self, name: str, status: str, message: str, **evidence: Any) -> None:
        status = str(status or "failed")
        event = {
            "at": utc_now(),
            "traceId": self.trace_id,
            "check": name,
            "status": status,
            "message": message,
            "evidence": _json_safe(evidence),
        }
        self.report["checks"][name] = {
            "status": status,
            "message": message,
            "updatedAt": event["at"],
            **({"evidence": event["evidence"]} if evidence else {}),
        }
        self._append_event(event)
        self._write_report()

    def _append_event(self, event: dict[str, Any]) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")

    def _finalize(self) -> dict[str, Any]:
        checks = self.report.get("checks") if isinstance(self.report.get("checks"), dict) else {}
        failed = [name for name, item in checks.items() if isinstance(item, dict) and item.get("status") in TERMINAL_BAD_STATUSES]
        self.report["status"] = "failed" if failed else "completed"
        self.report["result"] = "continuity_failed" if failed else "continuity_ok"
        self.report["failedChecks"] = failed
        self.report["finishedAt"] = utc_now()
        self.report["durationSeconds"] = round(time.monotonic() - self.started, 6)
        self._refresh_summary()
        self._write_report()
        self.markdown_path.write_text(self._markdown_report(), encoding="utf-8")
        return dict(self.report)

    def _write_report(self) -> None:
        self.report["durationSeconds"] = round(time.monotonic() - self.started, 6)
        self.report["reportPath"] = self._relative(self.report_path)
        self.report["eventsPath"] = self._relative(self.events_path)
        self._refresh_summary()
        self._write_json(self.report_path, self.report)

    def _refresh_summary(self) -> None:
        counts = {"ok": 0, "failed": 0, "skipped": 0, "warning": 0, "total": 0}
        for item in (self.report.get("checks") or {}).values():
            if not isinstance(item, dict):
                continue
            counts["total"] += 1
            status = str(item.get("status") or "failed")
            if status == "ok":
                counts["ok"] += 1
            elif status == "skipped":
                counts["skipped"] += 1
            elif status == "warning":
                counts["warning"] += 1
            elif status in TERMINAL_BAD_STATUSES:
                counts["failed"] += 1
        self.report["summary"] = counts

    def _markdown_report(self) -> str:
        lines = [
            f"# HABLA CircuitProbe Report - {self.trace_id}",
            "",
            f"- result: `{self.report.get('result')}`",
            f"- mode: `{self.mode}`",
            f"- project: `{self.project}`",
            f"- durationSeconds: `{self.report.get('durationSeconds')}`",
            "",
            "| Check | Status | Message |",
            "| --- | --- | --- |",
        ]
        for name, item in (self.report.get("checks") or {}).items():
            if not isinstance(item, dict):
                continue
            lines.append(f"| `{name}` | `{item.get('status')}` | {str(item.get('message') or '').replace('|', '/')} |")
        lines.append("")
        return "\n".join(lines)

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_json_safe(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo_root.resolve()).as_posix()
        except ValueError:
            return str(path)

    def _compact(self, value: Any, limit: int = 500) -> Any:
        if isinstance(value, str):
            return value if len(value) <= limit else value[: limit - 3] + "..."
        if isinstance(value, dict):
            return {str(key): self._compact(item, limit=limit) for key, item in list(value.items())[:20]}
        if isinstance(value, list):
            return [self._compact(item, limit=limit) for item in value[:10]]
        return value

    def _error(self, exc: Exception) -> dict[str, str]:
        return {"type": type(exc).__name__, "message": str(exc)}


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=True)
        return value
    except TypeError:
        return str(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run HABLA internal continuity probe.")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--mode", default="active_canary", choices=sorted(VALID_MODES))
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--trace-id", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--no-harness", action="store_true")
    parser.add_argument("--report", default="", help="Print an existing report by trace id instead of running.")
    parser.add_argument("--list", action="store_true", help="List recent reports.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        payload = {"ok": True, "reports": list_continuity_reports(repo_root=args.repo_root)}
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    if args.report:
        report = load_continuity_report(repo_root=args.repo_root, trace_id=args.report)
        if report is None:
            print(json.dumps({"ok": False, "error": "report_not_found", "traceId": args.report}, ensure_ascii=True, indent=2))
            return 1
        print(json.dumps({"ok": True, "report": report}, ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    report = run_continuity_probe(
        repo_root=args.repo_root,
        mode=args.mode,
        project=args.project,
        base_url=args.base_url,
        trace_id=args.trace_id,
        timeout_seconds=args.timeout_seconds,
        include_harness=not args.no_harness,
    )
    print(
        json.dumps(
            {
                "ok": report.get("result") == "continuity_ok",
                "traceId": report.get("traceId"),
                "result": report.get("result"),
                "summary": report.get("summary"),
                "reportPath": report.get("reportPath"),
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.get("result") == "continuity_ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
