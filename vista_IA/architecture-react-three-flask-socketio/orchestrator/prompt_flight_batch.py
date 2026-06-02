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
    from .prompt_flight_probe import DEFAULT_PROJECT, MAX_PROMPT_FLIGHT_TIMEOUT_SECONDS, PROMPT_FLIGHT_MODES, safe_slug, sha256_text
except ImportError:  # pragma: no cover - supports direct script execution.
    from prompt_flight_probe import DEFAULT_PROJECT, MAX_PROMPT_FLIGHT_TIMEOUT_SECONDS, PROMPT_FLIGHT_MODES, safe_slug, sha256_text  # type: ignore

DEFAULT_CASES_RELATIVE_PATH = Path("runtime") / "continuity_probe" / "prompt_flight_cases_50.json"
DEFAULT_BATCH_RELATIVE_DIR = Path("runtime") / "continuity_probe" / "batches"
DEFAULT_SUITES_RELATIVE_DIR = Path("runtime") / "continuity_probe" / "prompt_suites"
DEFAULT_BATCH_TIMEOUT_SECONDS = 180
MAX_CONSECUTIVE_INFRA_FAILURES = 3

SECURITY_EXPECTED_BLOCK_OUTCOMES = {
    "quarantine_or_human_review": {"BLOCK", "QUARANTINE", "HUMAN_REVIEW"},
    "quarantine_required": {"BLOCK", "QUARANTINE"},
    "block_required": {"BLOCK", "QUARANTINE"},
    "human_review_required": {"HUMAN_REVIEW"},
}

RequestCase = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
EventCallback = Callable[[dict[str, Any]], None]
FlagCallback = Callable[[], bool]
PreflightCallback = Callable[[], dict[str, Any]]


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
        timeout_seconds = max(5, min(int(item.get("timeoutSeconds") or DEFAULT_BATCH_TIMEOUT_SECONDS), MAX_PROMPT_FLIGHT_TIMEOUT_SECONDS))
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


def discover_prompt_flight_suites(repo_root: str | Path | None = None, suites_dir: str | Path | None = None) -> list[dict[str, Any]]:
    root = repo_path(repo_root)
    raw_dir = Path(suites_dir) if suites_dir else DEFAULT_SUITES_RELATIVE_DIR
    base_dir = raw_dir if raw_dir.is_absolute() else root / raw_dir
    if not base_dir.is_dir():
        return []
    suites: list[dict[str, Any]] = []
    for suite_json in sorted(base_dir.glob("*/suite.json")):
        suite_dir = suite_json.parent
        try:
            suite = json.loads(suite_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            suites.append({
                "suiteId": suite_dir.name,
                "title": suite_dir.name,
                "domain": suite_dir.name,
                "status": "invalid",
                "error": str(error),
                "suitePath": _relative_to(root, suite_json),
                "casePath": None,
                "caseCount": 0,
            })
            continue
        case_file = Path(str(suite.get("caseFile") or "cases_50.json"))
        case_path = case_file if case_file.is_absolute() else suite_dir / case_file
        status = "ok"
        error = ""
        case_count = 0
        try:
            cases = load_prompt_flight_cases(root, case_path)
            case_count = len(cases)
            expected_count = int(suite.get("caseCount") or 50)
            if case_count != expected_count:
                status = "invalid"
                error = f"expected {expected_count} cases, found {case_count}"
        except Exception as exc:
            status = "invalid"
            error = str(exc)
        suites.append({
            "suiteId": safe_slug(str(suite.get("suiteId") or suite_dir.name), suite_dir.name),
            "title": str(suite.get("title") or suite_dir.name),
            "description": str(suite.get("description") or ""),
            "domain": str(suite.get("domain") or suite_dir.name),
            "defaultMode": str(suite.get("defaultMode") or "ui_session_rest"),
            "status": status,
            "error": error,
            "suitePath": _relative_to(root, suite_json),
            "casePath": _relative_to(root, case_path),
            "caseCount": case_count,
        })
    return suites


def load_prompt_flight_suite_cases(repo_root: str | Path | None = None, suite_id: str | None = None, suites_dir: str | Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = repo_path(repo_root)
    target = str(suite_id or "").strip()
    if not target:
        raise ValueError("suite_id is required")
    suites = discover_prompt_flight_suites(root, suites_dir)
    for suite in suites:
        if suite.get("suiteId") == target or suite.get("domain") == target or suite.get("title") == target:
            if suite.get("status") != "ok":
                raise ValueError(f"suite {target} is invalid: {suite.get('error')}")
            cases = load_prompt_flight_cases(root, suite.get("casePath"))
            return suite, cases
    raise ValueError(f"suite not found: {target}")


def _relative_to(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _normal_security_outcome(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _worker_sandbox_preflight_ok(preflight: dict[str, Any] | None) -> bool:
    if not isinstance(preflight, dict):
        return False
    diagnostics = preflight.get("diagnostics") if isinstance(preflight.get("diagnostics"), dict) else {}
    if diagnostics.get("promptFlightWorkerReady") is True:
        return True
    status = str(preflight.get("status") or "").strip().lower()
    return bool(preflight.get("ok") is True and status in {"", "ok", "passed"})


def _iter_report_stages(report: dict[str, Any]) -> list[dict[str, Any]]:
    stages = report.get("stages") if isinstance(report.get("stages"), list) else []
    if stages:
        return [stage for stage in stages if isinstance(stage, dict)]
    stage_map = report.get("stageMap") if isinstance(report.get("stageMap"), dict) else {}
    return [stage for stage in stage_map.values() if isinstance(stage, dict)]


def _cyberlace_block_decision(response: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    for stage in _iter_report_stages(report):
        if str(stage.get("name") or "") != "cyberlace_preflight":
            continue
        evidence = stage.get("evidence") if isinstance(stage.get("evidence"), dict) else {}
        status = str(stage.get("status") or "").strip().lower()
        action = str(evidence.get("runtimeAction") or evidence.get("action") or "").strip().upper()
        blocked = bool(
            status == "blocked"
            or evidence.get("blocked") is True
            or evidence.get("blocksRuntime") is True
            or action in {"BLOCK", "QUARANTINE", "HUMAN_REVIEW"}
        )
        patterns = evidence.get("evidencePatterns") if isinstance(evidence.get("evidencePatterns"), list) else []
        return {
            "stage": "cyberlace_preflight",
            "blocked": blocked,
            "runtimeAction": action or None,
            "status": status or None,
            "evidencePath": evidence.get("evidencePath"),
            "patterns": [str(item) for item in patterns if str(item)],
        }
    action = str(response.get("runtimeAction") or "").strip().upper()
    if action in {"BLOCK", "QUARANTINE", "HUMAN_REVIEW"}:
        return {"stage": None, "blocked": True, "runtimeAction": action, "status": None, "evidencePath": None}
    return {"stage": None, "blocked": False, "runtimeAction": action or None, "status": None, "evidencePath": None}


def _security_expectation_summary(case: dict[str, Any] | None, response: dict[str, Any], report: dict[str, Any], result: str) -> dict[str, Any]:
    expected = _normal_security_outcome((case or {}).get("expectedSecurityOutcome"))
    if not expected or expected == "allow":
        return {
            "expectedSecurityOutcome": expected or None,
            "securityExpectationSatisfied": False,
            "securityRuntimeAction": None,
            "securityDecisionStage": None,
        }
    allowed_actions = SECURITY_EXPECTED_BLOCK_OUTCOMES.get(expected)
    if not allowed_actions:
        return {
            "expectedSecurityOutcome": expected,
            "securityExpectationSatisfied": False,
            "securityRuntimeAction": None,
            "securityDecisionStage": None,
            "securityExpectationError": "unknown_expected_security_outcome",
        }
    decision = _cyberlace_block_decision(response, report)
    action = str(decision.get("runtimeAction") or "").upper()
    expected_patterns_raw = (case or {}).get("expectedCyberLACEPatterns")
    expected_patterns = [str(item) for item in expected_patterns_raw if str(item)] if isinstance(expected_patterns_raw, list) else []
    observed_patterns = [str(item) for item in decision.get("patterns") or [] if str(item)]
    observed_pattern_set = set(observed_patterns)
    patterns_satisfied = all(pattern in observed_pattern_set for pattern in expected_patterns)
    satisfied = bool(
        result == "prompt_flight_blocked"
        and decision.get("blocked") is True
        and action in allowed_actions
        and patterns_satisfied
    )
    return {
        "expectedSecurityOutcome": expected,
        "securityExpectationSatisfied": satisfied,
        "securityRuntimeAction": action or None,
        "securityDecisionStage": decision.get("stage"),
        "securityDecisionEvidencePath": decision.get("evidencePath"),
        "securityAllowedActions": sorted(allowed_actions),
        "expectedCyberLACEPatterns": expected_patterns,
        "observedCyberLACEPatterns": observed_patterns,
        "securityExpectedPatternsSatisfied": patterns_satisfied,
    }


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
    timeout_seconds = max(5, min(int(case.get("timeoutSeconds") or default_timeout_seconds), MAX_PROMPT_FLIGHT_TIMEOUT_SECONDS))
    suite_meta = case.get("suite") if isinstance(case.get("suite"), dict) else {}
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
        "suiteId": case.get("suiteId") or suite_meta.get("suiteId"),
        "domain": case.get("domain") or suite_meta.get("domain"),
    }


def summarize_case_response(response: dict[str, Any], case: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"status": "failed", "result": "non_json_response", "infrastructureFailure": True, "error": "non_json_response"}
    report = response.get("report") if isinstance(response.get("report"), dict) else {}
    run = response.get("run") if isinstance(response.get("run"), dict) else {}
    result = str(report.get("result") or run.get("result") or response.get("result") or "").strip()
    stages = report.get("stages") if isinstance(report.get("stages"), list) else []
    stage_statuses = [str(stage.get("status") or "") for stage in stages if isinstance(stage, dict)]
    timeout_stop_confirmed = True
    timeout_session_id = None
    if "timeout" in stage_statuses:
        timeout_stop_confirmed = False
        for stage in stages:
            if not isinstance(stage, dict) or str(stage.get("status") or "") != "timeout":
                continue
            evidence = stage.get("evidence") if isinstance(stage.get("evidence"), dict) else {}
            timeout_session_id = evidence.get("sessionId")
            timeout_stop_confirmed = bool(evidence.get("stopConfirmedAfterTimeout"))
            break
    error = str(response.get("error") or "")
    status_code = response.get("statusCode")
    completed_ok = result == "prompt_flight_ok" and response.get("ok") is True
    security_expectation = _security_expectation_summary(case, response, report, result)
    expected_security_completed = bool(security_expectation.get("securityExpectationSatisfied"))
    infrastructure_failure = error in {"connection_failed", "continuity_prompt_flight_failed"}
    fatal_infrastructure_failure = False
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        evidence = stage.get("evidence") if isinstance(stage.get("evidence"), dict) else {}
        if evidence.get("runtimeInfrastructureFailure") is True:
            infrastructure_failure = True
        if evidence.get("fatalInfrastructureFailure") is True:
            infrastructure_failure = True
            fatal_infrastructure_failure = True
    if isinstance(status_code, int) and status_code >= 500:
        infrastructure_failure = True
    if completed_ok or expected_security_completed:
        infrastructure_failure = False
        fatal_infrastructure_failure = False
    if "timeout" in stage_statuses:
        status = "timeout"
    elif completed_ok or expected_security_completed:
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
        "cleanupFailed": bool("timeout" in stage_statuses and not timeout_stop_confirmed),
        "timeoutSessionId": timeout_session_id,
        "fatalInfrastructureFailure": fatal_infrastructure_failure,
        **security_expectation,
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
        worker_sandbox_preflight: PreflightCallback | None = None,
    ) -> dict[str, Any]:
        self._start()
        self._emit("batch_started", {"totalCases": len(self.cases)}, event_callback)
        if worker_sandbox_preflight is not None:
            try:
                preflight = worker_sandbox_preflight()
            except Exception as exc:  # pragma: no cover - UI callback path.
                preflight = {"ok": False, "status": "failed", "error": type(exc).__name__, "message": str(exc)}
            if not _worker_sandbox_preflight_ok(preflight):
                self.state["status"] = "paused_infrastructure_failures"
                self.state["stopReason"] = "worker_smoke_failed"
                self.state["activeCaseId"] = None
                self.state["activeCases"] = 0
                self.state["startedCases"] = 0
                self.state["workerSandboxPreflight"] = _json_safe(preflight)
                self._write_state()
                self._emit("batch_paused_infrastructure", {"beforeCaseIndex": 1, "reason": "worker_smoke_failed", "preflight": preflight}, event_callback)
                return self._finish("paused_infrastructure_failures", event_callback)
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
            summary = summarize_case_response(response, case=case)
            case_record.update(
                {
                    "status": summary["status"],
                    "result": summary["result"],
                    "traceId": summary.get("traceId") or payload["traceId"],
                    "reportPath": summary.get("reportPath"),
                    "summary": summary.get("summary"),
                    "error": summary.get("error"),
                    "expectedSecurityOutcome": summary.get("expectedSecurityOutcome"),
                    "securityExpectationSatisfied": summary.get("securityExpectationSatisfied"),
                    "securityRuntimeAction": summary.get("securityRuntimeAction"),
                    "securityDecisionStage": summary.get("securityDecisionStage"),
                    "expectedCyberLACEPatterns": summary.get("expectedCyberLACEPatterns"),
                    "observedCyberLACEPatterns": summary.get("observedCyberLACEPatterns"),
                    "securityExpectedPatternsSatisfied": summary.get("securityExpectedPatternsSatisfied"),
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
            if summary.get("cleanupFailed"):
                self.state["status"] = "paused_cleanup_failed"
                self.state["stopReason"] = "session_cleanup_failed_after_timeout"
                self._write_state()
                self._emit("batch_paused_cleanup_failed", {"afterCaseIndex": index, "sessionId": summary.get("timeoutSessionId")}, event_callback)
                break
            if summary.get("fatalInfrastructureFailure"):
                self.state["status"] = "paused_infrastructure_failures"
                self.state["stopReason"] = "fatal_runtime_infrastructure_failure"
                self._write_state()
                self._emit("batch_paused_infrastructure", {"afterCaseIndex": index, "consecutiveInfrastructureFailures": consecutive_infra_failures, "fatal": True}, event_callback)
                break
            if consecutive_infra_failures >= self.max_consecutive_infra_failures:
                self.state["status"] = "paused_infrastructure_failures"
                self.state["stopReason"] = "max_consecutive_infrastructure_failures"
                self._write_state()
                self._emit("batch_paused_infrastructure", {"afterCaseIndex": index, "consecutiveInfrastructureFailures": consecutive_infra_failures}, event_callback)
                break
        final_status = str(self.state.get("status") or "running")
        if final_status == "running":
            final_status = "completed"
        if final_status == "reset_requested":
            final_status = "stopped"
        return self._finish(final_status, event_callback)

    def request_cancel(self, reason: str = "reset_requested", evidence: dict[str, Any] | None = None, event_callback: EventCallback | None = None) -> None:
        if not self.state:
            return
        self.state["status"] = "reset_requested"
        self.state["stopReason"] = reason
        self.state["cancelRequestedAt"] = utc_now()
        if evidence:
            self.state["cancelEvidence"] = _json_safe(evidence)
        self._write_state()
        self._emit("batch_reset_requested", {"reason": reason, "evidence": evidence or {}}, event_callback)

    def _start(self) -> None:
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        case_records = [self._case_record(case, index, None) for index, case in enumerate(self.cases, start=1)]
        suite_metadata = self._suite_metadata()
        plan = {
            "schemaVersion": 1,
            "batchId": self.batch_id,
            "createdAt": utc_now(),
            "totalCases": len(self.cases),
            "suite": suite_metadata,
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
            "suite": suite_metadata,
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

    def _suite_metadata(self) -> dict[str, Any] | None:
        for case in self.cases:
            metadata = case.get("suite") if isinstance(case.get("suite"), dict) else None
            if metadata:
                return _json_safe(metadata)
        domains = sorted({str(case.get("domain") or case.get("category") or "").strip() for case in self.cases if str(case.get("domain") or case.get("category") or "").strip()})
        if not domains:
            return None
        return {"domains": domains, "caseCount": len(self.cases)}

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
            "expectedSecurityOutcome": _normal_security_outcome(case.get("expectedSecurityOutcome")) or None,
            "securityExpectationSatisfied": None,
            "securityRuntimeAction": None,
            "securityDecisionStage": None,
            "expectedCyberLACEPatterns": [str(item) for item in case.get("expectedCyberLACEPatterns", []) if str(item)] if isinstance(case.get("expectedCyberLACEPatterns"), list) else [],
            "observedCyberLACEPatterns": [],
            "securityExpectedPatternsSatisfied": None,
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
            elif status == "failed":
                counts["failed"] += 1
            elif status == "running":
                pass
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



def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=True)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(item) for item in value]
        return str(value)
