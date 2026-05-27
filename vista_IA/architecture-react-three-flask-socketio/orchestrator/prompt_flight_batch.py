"""Sequential batch runner for Prompt Flight cases.

The Tkinter console uses this module to send many Prompt Flight cases as
transactional work: one request starts, reaches a terminal response, writes
ledger evidence, and only then can the next case start.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from .prompt_flight_probe import DEFAULT_PROJECT, PROMPT_FLIGHT_MODES, safe_slug, sha256_text
except ImportError:  # pragma: no cover - supports direct script execution.
    from prompt_flight_probe import DEFAULT_PROJECT, PROMPT_FLIGHT_MODES, safe_slug, sha256_text  # type: ignore

DEFAULT_CASES_RELATIVE_PATH = Path("runtime") / "continuity_probe" / "prompt_flight_cases_50.json"
DEFAULT_BATCH_RELATIVE_DIR = Path("runtime") / "continuity_probe" / "batches"
DEFAULT_BATCH_TIMEOUT_SECONDS = 180
MAX_CONSECUTIVE_INFRA_FAILURES = 3

RequestCase = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
EventCallback = Callable[[dict[str, Any]], None]
FlagCallback = Callable[[], bool]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_batch_id() -> str:
    return "prompt-flight-batch-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repo_path(repo_root: str | Path | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]


def resolve_cases_path(repo_root: str | Path | None = None, cases_path: str | Path | None = None) -> Path:
    root = repo_path(repo_root)
    raw = Path(cases_path) if cases_path else DEFAULT_CASES_RELATIVE_PATH
    return raw if raw.is_absolute() else root / raw


def load_prompt_flight_cases(repo_root: str | Path | None = None, cases_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = resolve_cases_path(repo_root, cases_path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    cases_raw = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(cases_raw, list):
        raise ValueError("Prompt Flight cases JSON must contain a cases list.")
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(cases_raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"case {index} must be an object")
        case_id = safe_slug(str(item.get("id") or f"PF-{index:03d}"), f"PF-{index:03d}")
        if case_id in seen:
            raise ValueError(f"duplicate case id: {case_id}")
        prompt = str(item.get("prompt") or "").strip()
        if not prompt:
            raise ValueError(f"case {case_id} is missing prompt")
        mode = str(item.get("mode") or "ui_session_rest").strip().lower()
        if mode not in PROMPT_FLIGHT_MODES:
            raise ValueError(f"case {case_id} has invalid mode: {mode}")
        timeout_seconds = max(5, min(int(item.get("timeoutSeconds") or DEFAULT_BATCH_TIMEOUT_SECONDS), 300))
        normalized = dict(item)
        normalized.update(
            {
                "id": case_id,
                "title": str(item.get("title") or case_id).strip(),
                "category": str(item.get("category") or "general").strip(),
                "prompt": prompt,
                "mode": mode,
                "timeoutSeconds": timeout_seconds,
            }
        )
        seen.add(case_id)
        cases.append(normalized)
    return cases


def build_case_payload(
    case: dict[str, Any],
    *,
    batch_id: str,
    case_index: int,
    base_url: str,
    default_project: str = DEFAULT_PROJECT,
    include_harness: bool = True,
    default_timeout_seconds: int = DEFAULT_BATCH_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    case_id = safe_slug(str(case.get("id") or f"PF-{case_index:03d}"), f"PF-{case_index:03d}")
    project_slug = safe_slug(str(case.get("projectSlug") or f"{default_project}-{case_id.lower()}"), DEFAULT_PROJECT)
    trace_id = safe_slug(str(case.get("traceId") or f"{batch_id}-{case_id.lower()}"), f"{batch_id}-{case_index:03d}")
    timeout_seconds = max(5, min(int(case.get("timeoutSeconds") or default_timeout_seconds), 300))
    return {
        "prompt": str(case.get("prompt") or "").strip(),
        "mode": str(case.get("mode") or "ui_session_rest").strip().lower(),
        "project": project_slug,
        "baseUrl": str(base_url or "").rstrip("/"),
        "includeHarness": bool(case.get("includeHarness", include_harness)),
        "timeoutSeconds": timeout_seconds,
        "traceId": trace_id,
        "batchId": batch_id,
        "caseId": case_id,
        "caseIndex": case_index,
    }


def summarize_case_response(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"status": "failed", "result": "non_json_response", "infrastructureFailure": True, "error": "non_json_response"}
    report = response.get("report") if isinstance(response.get("report"), dict) else {}
    run = response.get("run") if isinstance(response.get("run"), dict) else {}
    result = str(report.get("result") or run.get("result") or response.get("result") or "").strip()
    stages = report.get("stages") if isinstance(report.get("stages"), list) else []
    stage_statuses = [str(stage.get("status") or "") for stage in stages if isinstance(stage, dict)]
    error = str(response.get("error") or "")
    status_code = response.get("statusCode")
    infrastructure_failure = error in {"connection_failed", "continuity_prompt_flight_failed"}
    if isinstance(status_code, int) and status_code >= 500:
        infrastructure_failure = True
    if "timeout" in stage_statuses:
        status = "timeout"
    elif result == "prompt_flight_ok" and response.get("ok") is True:
        status = "completed"
    elif result == "prompt_flight_blocked":
        status = "blocked"
    elif infrastructure_failure:
        status = "infrastructure_failed"
    else:
        status = "failed"
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    return {
        "status": status,
        "result": result or error or status,
        "infrastructureFailure": infrastructure_failure,
        "traceId": response.get("traceId") or run.get("traceId") or report.get("traceId"),
        "reportPath": artifacts.get("reportPath") or report.get("reportPath") or run.get("reportPath"),
        "summary": report.get("summary") or run.get("summary"),
        "error": error or None,
    }


class PromptFlightBatchRunner:
    def __init__(
        self,
        *,
        repo_root: str | Path | None = None,
        cases: list[dict[str, Any]],
        batch_id: str | None = None,
        batch_root: str | Path | None = None,
        max_consecutive_infra_failures: int = MAX_CONSECUTIVE_INFRA_FAILURES,
    ) -> None:
        self.repo_root = repo_path(repo_root)
        self.cases = cases
        self.batch_id = safe_slug(batch_id or new_batch_id(), "prompt-flight-batch")
        root = Path(batch_root) if batch_root else self.repo_root / DEFAULT_BATCH_RELATIVE_DIR
        self.batch_dir = root if root.is_absolute() else self.repo_root / root
        self.batch_dir = self.batch_dir / self.batch_id
        self.events_path = self.batch_dir / "batch_events.jsonl"
        self.plan_path = self.batch_dir / "batch_plan.json"
        self.state_path = self.batch_dir / "batch_state.json"
        self.summary_path = self.batch_dir / "batch_summary.json"
        self.max_consecutive_infra_failures = max(1, int(max_consecutive_infra_failures or MAX_CONSECUTIVE_INFRA_FAILURES))
        self.state: dict[str, Any] = {}

    def run(
        self,
        *,
        request_case: RequestCase,
        base_url: str,
        default_project: str = DEFAULT_PROJECT,
        include_harness: bool = True,
        default_timeout_seconds: int = DEFAULT_BATCH_TIMEOUT_SECONDS,
        event_callback: EventCallback | None = None,
        should_stop: FlagCallback | None = None,
        should_pause: FlagCallback | None = None,
        pause_sleep_seconds: float = 1.0,
    ) -> dict[str, Any]:
        self._start()
        self._emit("batch_started", {"totalCases": len(self.cases)}, event_callback)
        consecutive_infra_failures = 0
        for index, case in enumerate(self.cases, start=1):
            if should_stop and should_stop():
                self.state["status"] = "stopped"
                self.state["stopReason"] = "stop_requested_before_case"
                self._write_state()
                self._emit("batch_stopped", {"nextCaseIndex": index}, event_callback)
                break
            paused_once = False
            while should_pause and should_pause():
                if not paused_once:
                    self.state["status"] = "paused"
                    self.state["pauseReason"] = "pause_requested_after_current"
                    self._write_state()
                    self._emit("batch_paused", {"nextCaseIndex": index}, event_callback)
                    paused_once = True
                if should_stop and should_stop():
                    self.state["status"] = "stopped"
                    self.state["stopReason"] = "stop_requested_while_paused"
                    self._write_state()
                    self._emit("batch_stopped", {"nextCaseIndex": index}, event_callback)
                    return self._finish("stopped", event_callback)
                time.sleep(max(0.05, pause_sleep_seconds))
            if paused_once:
                self.state["status"] = "running"
                self.state.pop("pauseReason", None)
                self._write_state()
                self._emit("batch_resumed", {"nextCaseIndex": index}, event_callback)

            payload = build_case_payload(
                case,
                batch_id=self.batch_id,
                case_index=index,
                base_url=base_url,
                default_project=default_project,
                include_harness=include_harness,
                default_timeout_seconds=default_timeout_seconds,
            )
            case_record = self._case_record(case, index, payload)
            self.state["activeCaseId"] = case_record["id"]
            self.state["currentIndex"] = index
            self._set_case(case_record)
            self._write_state()
            self._emit("case_started", case_record, event_callback)
            started = time.monotonic()
            try:
                response = request_case(payload, case)
            except Exception as exc:  # pragma: no cover - Tk path; tests use response payloads.
                response = {"ok": False, "error": "request_exception", "message": str(exc)}
            duration_seconds = round(time.monotonic() - started, 3)
            summary = summarize_case_response(response)
            case_record.update(
                {
                    "status": summary["status"],
                    "result": summary["result"],
                    "traceId": summary.get("traceId") or payload["traceId"],
                    "reportPath": summary.get("reportPath"),
                    "summary": summary.get("summary"),
                    "error": summary.get("error"),
                    "durationSeconds": duration_seconds,
                    "finishedAt": utc_now(),
                    "responseHash": sha256_text(response),
                }
            )
            self.state["activeCaseId"] = None
            self._set_case(case_record)
            self._recount()
            if summary.get("infrastructureFailure"):
                consecutive_infra_failures += 1
            else:
                consecutive_infra_failures = 0
            self.state["consecutiveInfrastructureFailures"] = consecutive_infra_failures
            self._write_state()
            self._emit("case_finished", case_record, event_callback)
            if consecutive_infra_failures >= self.max_consecutive_infra_failures:
                self.state["status"] = "paused_infrastructure_failures"
                self.state["stopReason"] = "max_consecutive_infrastructure_failures"
                self._write_state()
                self._emit("batch_paused_infrastructure", {"afterCaseIndex": index, "consecutiveInfrastructureFailures": consecutive_infra_failures}, event_callback)
                break
        final_status = str(self.state.get("status") or "running")
        if final_status == "running":
            final_status = "completed"
        return self._finish(final_status, event_callback)

    def _start(self) -> None:
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        case_records = [self._case_record(case, index, None) for index, case in enumerate(self.cases, start=1)]
        plan = {
            "schemaVersion": 1,
            "batchId": self.batch_id,
            "createdAt": utc_now(),
            "totalCases": len(self.cases),
            "cases": self.cases,
        }
        self._write_json(self.plan_path, plan)
        self.state = {
            "schemaVersion": 1,
            "batchId": self.batch_id,
            "status": "running",
            "startedAt": utc_now(),
            "updatedAt": utc_now(),
            "finishedAt": None,
            "totalCases": len(self.cases),
            "currentIndex": 0,
            "activeCaseId": None,
            "completed": 0,
            "failed": 0,
            "blocked": 0,
            "timeout": 0,
            "infrastructureFailed": 0,
            "pending": len(self.cases),
            "consecutiveInfrastructureFailures": 0,
            "cases": case_records,
            "artifacts": {
                "batchDir": self._relative(self.batch_dir),
                "planPath": self._relative(self.plan_path),
                "statePath": self._relative(self.state_path),
                "eventsPath": self._relative(self.events_path),
                "summaryPath": self._relative(self.summary_path),
            },
        }
        self._write_state()

    def _finish(self, status: str, event_callback: EventCallback | None) -> dict[str, Any]:
        self.state["status"] = status
        self.state["finishedAt"] = utc_now()
        self.state["updatedAt"] = utc_now()
        self._recount()
        self._write_state()
        summary = {
            "schemaVersion": 1,
            "batchId": self.batch_id,
            "status": status,
            "totalCases": self.state.get("totalCases"),
            "completed": self.state.get("completed"),
            "failed": self.state.get("failed"),
            "blocked": self.state.get("blocked"),
            "timeout": self.state.get("timeout"),
            "infrastructureFailed": self.state.get("infrastructureFailed"),
            "pending": self.state.get("pending"),
            "startedAt": self.state.get("startedAt"),
            "finishedAt": self.state.get("finishedAt"),
            "artifacts": self.state.get("artifacts"),
            "cases": self.state.get("cases"),
            "stopReason": self.state.get("stopReason"),
        }
        self._write_json(self.summary_path, summary)
        self._emit("batch_finished", summary, event_callback)
        return summary

    def _case_record(self, case: dict[str, Any], index: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        case_id = safe_slug(str(case.get("id") or f"PF-{index:03d}"), f"PF-{index:03d}")
        record = {
            "id": case_id,
            "index": index,
            "title": str(case.get("title") or case_id),
            "category": str(case.get("category") or "general"),
            "status": "pending",
            "mode": str(case.get("mode") or "ui_session_rest"),
            "projectSlug": str(case.get("projectSlug") or ""),
            "traceId": None,
            "reportPath": None,
            "result": None,
            "durationSeconds": None,
            "startedAt": None,
            "finishedAt": None,
            "error": None,
        }
        if payload:
            record.update({"status": "running", "traceId": payload.get("traceId"), "projectSlug": payload.get("project"), "startedAt": utc_now()})
        return record

    def _set_case(self, case_record: dict[str, Any]) -> None:
        cases = self.state.setdefault("cases", [])
        for offset, existing in enumerate(cases):
            if isinstance(existing, dict) and existing.get("id") == case_record.get("id"):
                cases[offset] = case_record
                return
        cases.append(case_record)

    def _recount(self) -> None:
        cases = [case for case in self.state.get("cases", []) if isinstance(case, dict)]
        counts = {"completed": 0, "failed": 0, "blocked": 0, "timeout": 0, "infrastructureFailed": 0, "pending": 0}
        for case in cases:
            status = str(case.get("status") or "pending")
            if status == "completed":
                counts["completed"] += 1
            elif status == "blocked":
                counts["blocked"] += 1
            elif status == "timeout":
                counts["timeout"] += 1
            elif status == "infrastructure_failed":
                counts["infrastructureFailed"] += 1
            elif status in {"failed", "running"}:
                counts["failed"] += 1 if status == "failed" else 0
            else:
                counts["pending"] += 1
        self.state.update(counts)
        self.state["updatedAt"] = utc_now()

    def _emit(self, event_type: str, payload: dict[str, Any], event_callback: EventCallback | None) -> None:
        event = {"at": utc_now(), "batchId": self.batch_id, "event": event_type, "payload": payload}
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")
        if event_callback:
            event_callback(event)

    def _write_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state["updatedAt"] = utc_now()
        self._write_json(self.state_path, self.state)

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _relative(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.repo_root))
        except ValueError:
            return str(path)
