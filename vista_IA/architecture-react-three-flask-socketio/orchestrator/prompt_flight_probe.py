"""Prompt Flight Recorder for HABLA runtime continuity.

This module traces a prompt through diagnostic layers and, in
real_session_guarded mode, through the actual task queue/directive/executor/
worker/validator/history/checkpoint path inside an isolated canary project.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    from .directive_context import build_directive_context
    from .directive_generator import generate_directive, persist_directive
    from .executor import execute_task_with_details
    from .habla_adapter import build_habla_guide
    from .plan_loader import load_plan
    from .policy_loader import load_policy
    from .runtime_failure_classifier import classify_runtime_failure
    from .state_store import StateStore
    from .task_queue import TaskQueue
    from .validator import validate_task_execution
except ImportError:  # pragma: no cover - supports direct script execution.
    from directive_context import build_directive_context  # type: ignore
    from directive_generator import generate_directive, persist_directive  # type: ignore
    from executor import execute_task_with_details  # type: ignore
    from habla_adapter import build_habla_guide  # type: ignore
    from plan_loader import load_plan  # type: ignore
    from policy_loader import load_policy  # type: ignore
    from runtime_failure_classifier import classify_runtime_failure  # type: ignore
    from state_store import StateStore  # type: ignore
    from task_queue import TaskQueue  # type: ignore
    from validator import validate_task_execution  # type: ignore


DEFAULT_BASE_URL = "http://127.0.0.1:5001"
DEFAULT_PROJECT = "continuity-probe-canary"
PROMPT_FLIGHT_MODES = {"trace_only", "safe_canary", "real_session_guarded", "ui_session_rest"}
PROMPT_FLIGHT_WORKER_REQUIRED_MODES = {"safe_canary", "real_session_guarded", "ui_session_rest"}
TERMINAL_BAD_STATUSES = {"failed", "disconnected", "missing_evidence", "timeout"}
MAX_PROMPT_FLIGHT_TIMEOUT_SECONDS = 1200
UI_SESSION_POSTFLIGHT_GRACE_SECONDS = 120
MAX_UI_SESSION_MONITOR_SECONDS = 3600


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_prompt_trace_id() -> str:
    return "prompt-flight-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str, fallback: str = DEFAULT_PROJECT) -> str:
    raw = str(value or "").strip() or fallback
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-._")
    return cleaned[:80] or fallback


def sha256_text(value: Any) -> str:
    payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()


def run_prompt_flight_probe(
    *,
    repo_root: str | Path | None = None,
    prompt: str,
    mode: str = "trace_only",
    project: str = DEFAULT_PROJECT,
    base_url: str = DEFAULT_BASE_URL,
    trace_id: str | None = None,
    timeout_seconds: int = 90,
    include_harness: bool = True,
) -> dict[str, Any]:
    probe = PromptFlightProbe(
        repo_root=repo_root,
        prompt=prompt,
        mode=mode,
        project=project,
        base_url=base_url,
        trace_id=trace_id,
        timeout_seconds=timeout_seconds,
        include_harness=include_harness,
    )
    return probe.run()


def load_prompt_flight_report(*, repo_root: str | Path | None = None, trace_id: str) -> dict[str, Any] | None:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
    path = root / "runtime" / "continuity_probe" / safe_slug(trace_id, "missing") / "prompt_flight_report.json"
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return None


class PromptFlightProbe:
    def __init__(
        self,
        *,
        repo_root: str | Path | None,
        prompt: str,
        mode: str,
        project: str,
        base_url: str,
        trace_id: str | None,
        timeout_seconds: int,
        include_harness: bool,
    ) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
        self.prompt = str(prompt or "").strip()
        if not self.prompt:
            raise ValueError("prompt is required for prompt flight probe")
        self.mode = str(mode or "trace_only").strip().lower()
        if self.mode not in PROMPT_FLIGHT_MODES:
            raise ValueError(f"mode must be one of: {', '.join(sorted(PROMPT_FLIGHT_MODES))}")
        self.project = safe_slug(project)
        self.base_url = str(base_url or "").rstrip("/")
        self.trace_id = safe_slug(trace_id or new_prompt_trace_id(), "prompt-flight")
        self.timeout_seconds = max(5, min(int(timeout_seconds or 90), MAX_PROMPT_FLIGHT_TIMEOUT_SECONDS))
        self.include_harness = bool(include_harness)
        self.project_dir = self.repo_root / "workspace" / "projects" / self.project
        self.runtime_dir = self.project_dir / "runtime"
        self.run_dir = self.repo_root / "runtime" / "continuity_probe" / self.trace_id
        self.events_path = self.run_dir / "prompt_flight_events.jsonl"
        self.report_path = self.run_dir / "prompt_flight_report.json"
        self.markdown_path = self.run_dir / "prompt_flight_report.md"
        self.started = time.monotonic()
        self.blocked = False
        self.real_task: dict[str, Any] | None = None
        self.real_execution: dict[str, Any] = {}
        self.real_validation: dict[str, Any] = {}
        self.real_directive: dict[str, Any] = {}
        self.real_history_event: dict[str, Any] = {}
        self.real_checkpoint_path: Path | None = None
        self.ui_session: dict[str, Any] = {}
        self.ui_session_polls: list[dict[str, Any]] = []
        self.ui_runtime_truth: dict[str, Any] = {}
        self.ui_session_payload: dict[str, Any] = {}
        self.stage_map: dict[str, dict[str, Any]] = {}
        self.report: dict[str, Any] = {
            "schemaVersion": 2,
            "reportType": "prompt_flight_probe",
            "traceId": self.trace_id,
            "mode": self.mode,
            "project": self.project,
            "baseUrl": self.base_url,
            "status": "running",
            "result": "running",
            "startedAt": utc_now(),
            "finishedAt": "",
            "durationSeconds": 0.0,
            "promptHash": sha256_text(self.prompt),
            "stages": [],
            "stageMap": {},
            "summary": {"ok": 0, "failed": 0, "skipped": 0, "blocked": 0, "total": 0},
            "artifacts": {
                "runDir": self._relative(self.run_dir),
                "eventsPath": self._relative(self.events_path),
                "reportPath": self._relative(self.report_path),
                "markdownPath": self._relative(self.markdown_path),
            },
        }

    def run(self) -> dict[str, Any]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._stage("prompt_received", self._stage_prompt_received)
        self._stage("habla_basic_envelope", self._stage_habla_basic_envelope)
        self._stage("cyberlace_preflight", self._stage_cyberlace_preflight)
        self._stage("policy_loaded", self._stage_policy_loaded)
        self._stage("plan_loaded", self._stage_plan_loaded)
        self._stage("prompt_classified", self._stage_prompt_classified)
        self._stage("task_planned", self._stage_task_planned)
        self._stage("backend_health", self._stage_backend_health)
        self._stage("worker_sandbox_preflight", self._stage_worker_sandbox_preflight)
        self._stage("observer_status", self._stage_observer_status)
        if self.include_harness:
            self._stage("harness_summary", self._stage_harness_summary)
        else:
            self._record_stage("harness_summary", "skipped", "Harness checks disabled.")

        if self.mode == "safe_canary" and not self.blocked:
            self._stage("safe_canary_continuity", self._stage_safe_canary)
        elif self.mode == "safe_canary" and self.blocked:
            self._record_stage("safe_canary_continuity", "skipped", "Skipped because CyberLACE preflight blocked the prompt.")
        elif self.mode in {"real_session_guarded", "ui_session_rest"}:
            self._record_stage("safe_canary_continuity", "skipped", f"Skipped because mode is {self.mode}; runtime session follows.")
        else:
            self._record_stage("safe_canary_continuity", "skipped", "Skipped because mode is trace_only.")

        if self.mode == "real_session_guarded" and not self.blocked:
            self._stage("real_session_bootstrap", self._stage_real_session_bootstrap)
            self._stage("task_queue_persisted", self._stage_real_task_queue_persisted)
            self._stage("directive_generated", self._stage_real_directive_generated)
            self._stage("worker_executed", self._stage_real_worker_executed)
            self._stage("validator_passed", self._stage_real_validator_passed)
            self._stage("history_written", self._stage_real_history_written)
            self._stage("checkpoint_written", self._stage_real_checkpoint_written)
        elif self.mode == "real_session_guarded" and self.blocked:
            for stage_name in (
                "real_session_bootstrap",
                "task_queue_persisted",
                "directive_generated",
                "worker_executed",
                "validator_passed",
                "history_written",
                "checkpoint_written",
            ):
                self._record_stage(stage_name, "skipped", "Skipped because CyberLACE preflight blocked the prompt.")

        if self.mode == "ui_session_rest" and not self.blocked:
            self._stage("ui_rest_payload_built", self._stage_ui_rest_payload_built)
            self._stage("ui_agent_session_posted", self._stage_ui_agent_session_posted)
            self._stage("ui_agent_session_polled", self._stage_ui_agent_session_polled)
            self._stage("ui_runtime_truth_read", self._stage_ui_runtime_truth_read)
            self._stage("ui_runtime_artifacts_read", self._stage_ui_runtime_artifacts_read)
        elif self.mode == "ui_session_rest" and self.blocked:
            for stage_name in (
                "ui_rest_payload_built",
                "ui_agent_session_posted",
                "ui_agent_session_polled",
                "ui_runtime_truth_read",
                "ui_runtime_artifacts_read",
            ):
                self._record_stage(stage_name, "skipped", "Skipped because CyberLACE preflight blocked the prompt.")

        self._stage("response_synthesized", self._stage_response_synthesized)
        return self._finalize()

    def _stage(self, name: str, func: Any) -> None:
        started_at = utc_now()
        started = time.monotonic()
        try:
            payload = func()
            status = str(payload.pop("status", "ok")) if isinstance(payload, dict) else "ok"
            message = str(payload.pop("message", f"{name} completed.")) if isinstance(payload, dict) else f"{name} completed."
            evidence = payload if isinstance(payload, dict) else {}
        except Exception as exc:
            status = "failed"
            message = f"{name} failed."
            evidence = {"error": {"type": type(exc).__name__, "message": str(exc)}}
        finished_at = utc_now()
        duration_ms = round((time.monotonic() - started) * 1000, 3)
        self._record_stage(name, status, message, startedAt=started_at, finishedAt=finished_at, durationMs=duration_ms, **evidence)
        if status == "blocked":
            self.blocked = True

    def _record_stage(self, name: str, status: str, message: str, **evidence: Any) -> None:
        stage = {
            "name": name,
            "status": str(status or "failed"),
            "message": message,
            "updatedAt": utc_now(),
            "evidence": _json_safe(evidence),
        }
        if "durationMs" not in stage["evidence"]:
            stage["evidence"]["durationMs"] = 0.0
        stage["durationMs"] = stage["evidence"].get("durationMs", 0.0)
        self.stage_map[name] = stage
        self.report["stageMap"] = self.stage_map
        self.report["stages"] = [self.stage_map[key] for key in self.stage_map]
        event = {"at": utc_now(), "traceId": self.trace_id, "stage": name, "status": stage["status"], "message": message, "evidence": stage["evidence"]}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")
        self._write_report()

    def _stage_prompt_received(self) -> dict[str, Any]:
        path = self.run_dir / "input_prompt.json"
        payload = {
            "traceId": self.trace_id,
            "mode": self.mode,
            "project": self.project,
            "prompt": self.prompt,
            "promptHash": sha256_text(self.prompt),
            "receivedAt": utc_now(),
        }
        self._write_json(path, payload)
        return {"message": "Prompt persisted with trace hash.", "evidencePath": self._relative(path), "promptChars": len(self.prompt), "promptHash": payload["promptHash"]}

    def _stage_habla_basic_envelope(self) -> dict[str, Any]:
        expected_actions = {
            "trace_only": "trace_prompt_to_internal_response_without_worker",
            "safe_canary": "trace_prompt_and_execute_safe_canary",
            "real_session_guarded": "process_prompt_through_guarded_runtime_task",
            "ui_session_rest": "post_prompt_to_real_ui_agent_session_endpoint_and_monitor",
        }
        allowed_actions = ["policy", "plan", "classify", "task_plan", "backend", "observer", "harness"]
        if self.mode in {"safe_canary", "real_session_guarded", "ui_session_rest"}:
            allowed_actions.extend(["worker", "validator"])
        if self.mode == "real_session_guarded":
            allowed_actions.extend(["project_state", "task_queue", "directive_generator", "executor", "history", "checkpoint"])
        if self.mode == "ui_session_rest":
            allowed_actions.extend(["POST /api/agent/session", "GET /api/agent/session/<sessionId>", "GET /api/projects/<projectSlug>/runtime-truth", "runtime_artifact_read"])
        envelope = {
            "schemaVersion": 1,
            "traceId": self.trace_id,
            "mode": self.mode,
            "createdAt": utc_now(),
            "hablaBasic": {
                "inputPrompt": self.prompt,
                "inputHash": sha256_text(self.prompt),
                "intent": self._classify_prompt()["intent"],
                "expectedAction": expected_actions[self.mode],
                "allowedActions": allowed_actions,
                "project": self.project,
                "runtimeMode": "build",
                "budgetSeconds": self.timeout_seconds,
            },
        }
        path = self.run_dir / "habla_basic_envelope.json"
        self._write_json(path, envelope)
        return {"message": "HABLA BASIC envelope persisted.", "evidencePath": self._relative(path), "outputHash": sha256_text(envelope)}

    def _stage_cyberlace_preflight(self) -> dict[str, Any]:
        try:
            from backend.cyberlace_document_guard import inspect_runtime_document_inputs
        except Exception as exc:
            return {"status": "failed", "message": "CyberLACE document guard import failed.", "error": {"type": type(exc).__name__, "message": str(exc)}}
        decision = inspect_runtime_document_inputs(
            requirement=self.prompt,
            project_dir=self.run_dir,
            repo_root=self.repo_root,
            task={"id": self.trace_id, "goal": "Prompt flight diagnostic"},
            directive={"rendered_instruction": self.prompt},
            session_id=self.trace_id,
            project_slug=self.project,
            scan_workspace=False,
        )
        path = self.run_dir / "cyberlace_preflight.json"
        self._write_json(path, decision)
        findings = decision.get("evidence") if isinstance(decision.get("evidence"), list) else []
        evidence_patterns = sorted({str(item.get("pattern") or "") for item in findings if isinstance(item, dict) and str(item.get("pattern") or "")})
        evidence_types = sorted({str(item.get("type") or "") for item in findings if isinstance(item, dict) and str(item.get("type") or "")})
        blocked = bool(decision.get("blocked") is True or decision.get("blocksRuntime") is True or str(decision.get("runtimeAction") or "").upper() in {"BLOCK", "QUARANTINE", "HUMAN_REVIEW"})
        return {
            "status": "blocked" if blocked else "ok",
            "message": "CyberLACE blocked the prompt before execution." if blocked else "CyberLACE preflight allowed diagnostic processing.",
            "evidencePath": self._relative(path),
            "runtimeAction": decision.get("runtimeAction"),
            "riskScore": decision.get("riskScore"),
            "blocked": blocked,
            "safeAlternative": decision.get("safeAlternative"),
            "evidencePatterns": evidence_patterns,
            "evidenceTypes": evidence_types,
            "findingCount": len(findings),
        }

    def _stage_policy_loaded(self) -> dict[str, Any]:
        policy = load_policy(self.repo_root)
        return {"message": "AGENTS.md policy loaded.", "source": policy.get("source_path"), "ruleCount": len(policy.get("master_rules") or [])}

    def _stage_plan_loaded(self) -> dict[str, Any]:
        plan = load_plan(self.repo_root)
        return {"message": "PLANS.md roadmap loaded.", "source": plan.get("source_path"), "sprintCount": len(plan.get("sprints") or {}), "moduleCount": len(plan.get("modules") or {})}

    def _stage_prompt_classified(self) -> dict[str, Any]:
        classification = self._classify_prompt()
        path = self.run_dir / "prompt_classification.json"
        self._write_json(path, classification)
        return {"message": "Prompt classified for diagnostic routing.", "evidencePath": self._relative(path), **classification}

    def _stage_task_planned(self) -> dict[str, Any]:
        task = self._build_prompt_task()
        self.real_task = task
        path = self.run_dir / "planned_task.json"
        self._write_json(path, task)
        if self.mode == "real_session_guarded":
            message = "Real guarded Task model planned for runtime execution."
        elif self.mode == "ui_session_rest":
            message = "UI REST session payload planned; execution goes through /api/agent/session."
        else:
            message = "Diagnostic task model planned without hidden execution."
        return {"message": message, "evidencePath": self._relative(path), "taskId": task["id"], "taskHash": sha256_text(task), "expectedFiles": task["expected_files"]}

    def _stage_backend_health(self) -> dict[str, Any]:
        if not self.base_url:
            return {"status": "skipped", "message": "No baseUrl supplied for backend health."}
        status_code, payload = self._request_json("GET", "/api/health", timeout=8)
        return {"status": "ok" if status_code == 200 and payload.get("ok") is not False else "failed", "message": "Backend health checked.", "statusCode": status_code, "service": payload.get("service")}

    def _stage_worker_sandbox_preflight(self) -> dict[str, Any]:
        if self.mode not in PROMPT_FLIGHT_WORKER_REQUIRED_MODES:
            return {"status": "skipped", "message": "Worker sandbox preflight is not required for trace-only mode.", "mode": self.mode}
        if not self.base_url:
            if self.mode == "real_session_guarded":
                return {"status": "ok", "message": "Worker sandbox preflight passed for local direct worker execution.", "mode": self.mode, "preflightMode": "local_direct_worker"}
            return {"status": "blocked", "message": "Worker sandbox preflight requires a backend baseUrl.", "mode": self.mode}
        status_code, payload = self._request_json("GET", "/api/continuity-probe/prompt-flight/worker-diagnostics", timeout=10)
        diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
        ready = bool(status_code == 200 and payload.get("ok") is not False and diagnostics.get("promptFlightWorkerReady") is True)
        return {
            "status": "ok" if ready else "blocked",
            "message": "Worker sandbox preflight passed before Prompt Flight execution." if ready else "Worker sandbox preflight blocked Prompt Flight before launching a case.",
            "statusCode": status_code,
            "mode": self.mode,
            "effectiveSandboxMode": diagnostics.get("effectiveSandboxMode"),
            "effectiveApprovalPolicy": diagnostics.get("effectiveApprovalPolicy"),
            "usesDangerBypass": diagnostics.get("usesDangerBypass"),
            "usesWorkspaceWrite": diagnostics.get("usesWorkspaceWrite"),
            "safeCommandSummary": diagnostics.get("safeCommandSummary"),
            "blockers": diagnostics.get("blockers") or [],
            "requiredAction": diagnostics.get("requiredAction") or "./start_prompt_flight_tkinter.sh --local-worker-no-bwrap",
        }

    def _stage_observer_status(self) -> dict[str, Any]:
        if not self.base_url:
            return {"status": "skipped", "message": "No baseUrl supplied for Observer status."}
        status_code, payload = self._request_json("GET", "/api/observer/status", timeout=10)
        observer = payload.get("observer") if isinstance(payload.get("observer"), dict) else {}
        return {"status": "ok" if status_code == 200 and payload.get("ok") is not False else "failed", "message": "Observer status checked without starting a mission.", "statusCode": status_code, "observerState": observer.get("state"), "observerEnabled": observer.get("enabled")}

    def _stage_harness_summary(self) -> dict[str, Any]:
        if not self.base_url:
            return {"status": "skipped", "message": "No baseUrl supplied for Harness summary."}
        status_code, summary = self._request_json("GET", "/api/harness/training/summary", timeout=15)
        safety_code, safety = self._request_json("GET", "/api/harness/safety-learning/status", timeout=10)
        ok = status_code == 200 and summary.get("ok") is True and safety_code == 200 and safety.get("ok") is not False
        return {"status": "ok" if ok else "failed", "message": "Harness and Safety Learning checked.", "harnessStatusCode": status_code, "safetyStatusCode": safety_code, "hasRunsKey": "runs" in summary, "totalExperiences": safety.get("totalExperiences") or safety.get("total_experiences")}

    def _stage_safe_canary(self) -> dict[str, Any]:
        try:
            from .continuity_probe import run_continuity_probe
        except ImportError:  # pragma: no cover - direct script fallback.
            from continuity_probe import run_continuity_probe  # type: ignore
        nested_trace = self.trace_id + "-canary"
        report = run_continuity_probe(
            repo_root=self.repo_root,
            mode="active_canary",
            project=self.project,
            base_url=self.base_url,
            trace_id=nested_trace,
            timeout_seconds=self.timeout_seconds,
            include_harness=self.include_harness,
        )
        ok = report.get("result") == "continuity_ok"
        return {"status": "ok" if ok else "failed", "message": "Safe canary continuity run completed." if ok else "Safe canary continuity run failed.", "nestedTraceId": nested_trace, "nestedResult": report.get("result"), "nestedSummary": report.get("summary"), "nestedReportPath": report.get("reportPath")}

    def _stage_real_session_bootstrap(self) -> dict[str, Any]:
        if not (self.project.startswith("continuity-") or self.project.startswith("prompt-flight-")):
            return {"status": "failed", "message": "real_session_guarded only writes to continuity-* or prompt-flight-* project slugs.", "project": self.project}
        task = self._require_real_task()
        self.project_dir.mkdir(parents=True, exist_ok=True)
        (self.project_dir / "src").mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        for child in ("checkpoints", "directives", "artifacts", "logs"):
            (self.runtime_dir / child).mkdir(parents=True, exist_ok=True)
        now = utc_now()
        state = {
            "schema_version": 1,
            "project_id": self.project,
            "status": "running",
            "mode": "build",
            "current_task_id": task["id"],
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "checkpoints": [],
            "created_at": now,
            "updated_at": now,
        }
        store = StateStore.for_project_runtime(self.project_dir)
        store.save_project_state(state)
        store.save_task_queue([])
        store.failures_path.parent.mkdir(parents=True, exist_ok=True)
        store.failures_path.touch(exist_ok=True)
        input_copy = self.runtime_dir / "artifacts" / f"{self.trace_id}-input_prompt.json"
        self._write_json(
            input_copy,
            {
                "traceId": self.trace_id,
                "promptHash": sha256_text(self.prompt),
                "prompt": self.prompt,
                "mode": self.mode,
                "sourceRunDir": self._relative(self.run_dir),
                "createdAt": utc_now(),
            },
        )
        readme = self.project_dir / "README.md"
        if not readme.exists():
            readme.write_text(
                "# Prompt Flight Guarded Runtime\n\nControlled workspace for prompt flight real_session_guarded probes.\n",
                encoding="utf-8",
            )
        return {"message": "Project runtime bootstrapped for guarded prompt execution.", "projectPath": self._relative(self.project_dir), "runtimeDir": self._relative(self.runtime_dir), "taskId": task["id"], "inputArtifact": self._relative(input_copy)}

    def _stage_real_task_queue_persisted(self) -> dict[str, Any]:
        task = self._require_real_task()
        store = StateStore.for_project_runtime(self.project_dir)
        queue = TaskQueue(store)
        queue.enqueue(task)
        persisted_queue = store.load_task_queue()
        queue_ok = any(item.get("id") == task["id"] for item in persisted_queue)
        return {"status": "ok" if queue_ok else "missing_evidence", "message": "Prompt task persisted and reloaded from task_queue.json." if queue_ok else "Prompt task missing after queue reload.", "path": self._relative(store.task_queue_path), "taskId": task["id"], "taskCount": len(persisted_queue)}

    def _stage_real_directive_generated(self) -> dict[str, Any]:
        task = self._require_real_task()
        context = build_directive_context(
            repo_root=self.repo_root,
            runtime_dir=self.runtime_dir,
            task_workspace_root=self.project_dir,
            task_id=task["id"],
            strict=False,
        )
        context_artifact = self.run_dir / "directive_context.json"
        self._write_json(context_artifact, context)
        guide = build_habla_guide(context)
        guide_artifact = self.run_dir / "habla_guide.json"
        self._write_json(guide_artifact, guide)
        directive = generate_directive(context, guide)
        persisted = persist_directive(directive, directives_dir=self.runtime_dir / "directives")
        directive_path = Path(str(persisted.get("json_path") or ""))
        self.real_directive = persisted.get("directive") if isinstance(persisted.get("directive"), dict) else directive
        ok = directive_path.is_file()
        return {"status": "ok" if ok else "missing_evidence", "message": "Directive generated from policy, plan, state, task queue and HABLA guide." if ok else "Directive artifact missing.", "path": self._relative(directive_path) if directive_path else None, "contextPath": self._relative(context_artifact), "hablaGuidePath": self._relative(guide_artifact), "taskId": task["id"], "sourceHash": self.real_directive.get("traceability", {}).get("source_hash") if isinstance(self.real_directive, dict) else None}

    def _stage_real_worker_executed(self) -> dict[str, Any]:
        task = self._require_real_task()
        store = StateStore.for_project_runtime(self.project_dir)
        queue = TaskQueue(store)
        queue.mark_task_status(task["id"], "running")
        command = ["python3", "-B", "-c", self._prompt_worker_code()]
        execution = execute_task_with_details(
            task,
            workspace=self.project_dir,
            command=command,
            python_executable=sys.executable,
            worker_timeout_grace_seconds=3,
            extra_env={
                "VISTA_AGENT_SESSION_ID": self.trace_id,
                "VISTA_AGENT_PROJECT_SLUG": self.project,
                "PROMPT_FLIGHT_TRACE_ID": self.trace_id,
            },
        )
        self.real_execution = execution if isinstance(execution, dict) else {}
        worker_result = self.real_execution.get("task_result") if isinstance(self.real_execution.get("task_result"), dict) else {}
        worker_execution = self.real_execution.get("execution") if isinstance(self.real_execution.get("execution"), dict) else {}
        worker_ok = bool(worker_result.get("completed") is True)
        return {
            "status": "ok" if worker_ok else "failed",
            "message": "Worker processed the real prompt into response evidence." if worker_ok else "Worker failed while processing the guarded prompt task.",
            "taskId": task["id"],
            "workerAdapter": worker_execution.get("worker_adapter"),
            "workerReturnCode": worker_execution.get("worker_returncode"),
            "childReturnCode": worker_execution.get("returncode"),
            "childDurationSeconds": worker_execution.get("duration_seconds"),
            "workerDurationSeconds": worker_execution.get("worker_duration_seconds"),
            "stdout": self._compact(worker_execution.get("stdout"), limit=1200),
            "workerProcessStdout": self._compact(worker_execution.get("worker_process_stdout"), limit=1200),
            "workerProcessStderr": self._compact(worker_execution.get("worker_process_stderr"), limit=1200),
            "cyberlaceDocumentDecision": self._compact(worker_execution.get("cyberlace_document_decision"), limit=1200),
            "blockers": worker_result.get("blockers"),
            "responsePath": "src/prompt_flight_response.json",
        }

    def _stage_real_validator_passed(self) -> dict[str, Any]:
        task = self._require_real_task()
        if not self.real_execution:
            return {"status": "failed", "message": "Worker execution result is missing before validation."}
        validation = validate_task_execution(task, self.real_execution, workspace=self.project_dir, command_timeout_seconds=15)
        self.real_validation = validation
        validated_result = validation.get("task_result") if isinstance(validation.get("task_result"), dict) else {}
        validation_payload = validation.get("validation") if isinstance(validation.get("validation"), dict) else {}
        validation_ok = bool(validated_result.get("validation_passed") is True and validated_result.get("completed") is True)
        validation_artifact = self.run_dir / "real_session_validation.json"
        self._write_json(validation_artifact, validation)
        return {"status": "ok" if validation_ok else "failed", "message": "Validator confirmed prompt response evidence and validation command." if validation_ok else "Validator rejected prompt response evidence.", "evidencePath": self._relative(validation_artifact), "validationPassed": validated_result.get("validation_passed"), "validationRan": validated_result.get("validation_ran"), "commands": self._compact(validation_payload.get("commands"), limit=1200), "blockers": validated_result.get("blockers")}

    def _stage_real_history_written(self) -> dict[str, Any]:
        task = self._require_real_task()
        if not self.real_validation:
            return {"status": "failed", "message": "Validation result is missing before history write."}
        store = StateStore.for_project_runtime(self.project_dir)
        validated_result = self.real_validation.get("task_result") if isinstance(self.real_validation.get("task_result"), dict) else {}
        event = store.append_task_history(validated_result)
        self.real_history_event = event
        history_ok = store.task_history_path.is_file() and bool(event.get("result", {}).get("task_id") == task["id"])
        return {"status": "ok" if history_ok else "missing_evidence", "message": "Task history event appended for guarded prompt task." if history_ok else "Task history event missing after append.", "path": self._relative(store.task_history_path), "taskId": task["id"]}

    def _stage_real_checkpoint_written(self) -> dict[str, Any]:
        task = self._require_real_task()
        if not self.real_validation:
            return {"status": "failed", "message": "Validation result is missing before checkpoint write."}
        store = StateStore.for_project_runtime(self.project_dir)
        validated_result = self.real_validation.get("task_result") if isinstance(self.real_validation.get("task_result"), dict) else {}
        validation_ok = bool(validated_result.get("validation_passed") is True and validated_result.get("completed") is True)
        checkpoint_path = store.save_checkpoint(
            "prompt-flight-" + self.trace_id,
            {
                "traceId": self.trace_id,
                "taskId": task["id"],
                "mode": self.mode,
                "promptHash": sha256_text(self.prompt),
                "validationPassed": validation_ok,
                "responseFile": "src/prompt_flight_response.json",
                "reportPath": self._relative(self.report_path),
                "stageLatenciesMs": {name: stage.get("durationMs") for name, stage in self.stage_map.items()},
            },
        )
        self.real_checkpoint_path = checkpoint_path
        state = store.load_project_state()
        state["status"] = "completed" if validation_ok else "failed"
        state["current_task_id"] = None
        if validation_ok and task["id"] not in state["completed_tasks"]:
            state["completed_tasks"].append(task["id"])
        if not validation_ok and task["id"] not in state["failed_tasks"]:
            state["failed_tasks"].append(task["id"])
        checkpoint_key = checkpoint_path.stem
        if checkpoint_key not in state["checkpoints"]:
            state["checkpoints"].append(checkpoint_key)
        state["updated_at"] = utc_now()
        store.save_project_state(state)
        queue = TaskQueue(store)
        queue.mark_task_status(task["id"], "completed" if validation_ok else "failed")
        return {"status": "ok" if checkpoint_path.is_file() else "missing_evidence", "message": "Checkpoint written and project state closed for guarded prompt task.", "path": self._relative(checkpoint_path), "projectState": self._relative(store.project_state_path), "validationPassed": validation_ok}

    def _stage_ui_rest_payload_built(self) -> dict[str, Any]:
        payload = {
            "projectName": self.project,
            "projectSlug": self.project,
            "requirement": self.prompt,
            "ensureNewProject": True,
            "bootstrapProject": False,
            "runtimeMode": "build",
            "subagentPlan": None,
        }
        self.ui_session_payload = payload
        path = self.run_dir / "ui_agent_session_request.json"
        self._write_json(path, payload)
        return {
            "message": "Exact AgentStudio REST payload persisted for /api/agent/session.",
            "evidencePath": self._relative(path),
            "method": "POST",
            "endpoint": "/api/agent/session",
            "payloadHash": sha256_text(payload),
            "projectSlug": self.project,
            "runtimeMode": payload["runtimeMode"],
        }

    def _stage_ui_agent_session_posted(self) -> dict[str, Any]:
        if not self.base_url:
            return {"status": "failed", "message": "baseUrl is required for ui_session_rest."}
        if not self.ui_session_payload:
            self.ui_session_payload = self._ui_session_payload()
        status_code, payload, elapsed_ms = self._request_json_payload(
            "POST",
            "/api/agent/session",
            self.ui_session_payload,
            timeout=min(max(self.timeout_seconds, 10), 60),
        )
        path = self.run_dir / "ui_agent_session_response.json"
        self._write_json(path, {"statusCode": status_code, "response": payload, "elapsedMs": elapsed_ms})
        session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
        self.ui_session = dict(session)
        if session.get("projectSlug"):
            self.project = safe_slug(str(session.get("projectSlug") or self.project), self.project)
            self.project_dir = self.repo_root / "workspace" / "projects" / self.project
            self.runtime_dir = self.project_dir / "runtime"
            self.report["project"] = self.project
        ok = status_code == 200 and payload.get("ok") is True and bool(session.get("sessionId"))
        return {
            "status": "ok" if ok else "failed",
            "message": "Real UI session accepted by /api/agent/session." if ok else "Real UI session POST failed.",
            "evidencePath": self._relative(path),
            "statusCode": status_code,
            "elapsedMs": elapsed_ms,
            "sessionId": session.get("sessionId"),
            "sessionStatus": session.get("status"),
            "projectSlug": session.get("projectSlug"),
            "progressLabel": session.get("progressLabel"),
            "errorCode": session.get("errorCode"),
        }

    def _ui_session_active_task_timeout_seconds(self, session: dict[str, Any]) -> int | None:
        control_plane = session.get("controlPlane") if isinstance(session.get("controlPlane"), dict) else {}
        active_task = control_plane.get("activeTask") if isinstance(control_plane.get("activeTask"), dict) else {}
        for key in ("timeout_seconds", "timeoutSeconds"):
            try:
                value = int(active_task.get(key) or 0)
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                return value
        return None

    def _ui_session_monitor_budget_seconds(self, session: dict[str, Any]) -> int:
        budget = int(self.timeout_seconds)
        active_task_timeout = self._ui_session_active_task_timeout_seconds(session)
        if active_task_timeout:
            budget = max(budget, active_task_timeout + UI_SESSION_POSTFLIGHT_GRACE_SECONDS)
        return max(5, min(budget, MAX_UI_SESSION_MONITOR_SECONDS))

    def _stage_ui_agent_session_polled(self) -> dict[str, Any]:
        session_id = str(self.ui_session.get("sessionId") or "").strip()
        if not session_id:
            return {"status": "failed", "message": "No sessionId returned by /api/agent/session."}
        terminal_statuses = {"completed", "failed", "stopped", "blocked"}
        polls: list[dict[str, Any]] = []
        poll_started = time.monotonic()
        monitor_budget_seconds = self._ui_session_monitor_budget_seconds(self.ui_session)
        active_task_timeout_seconds = self._ui_session_active_task_timeout_seconds(self.ui_session)
        deadline = poll_started + monitor_budget_seconds
        final_session = dict(self.ui_session)
        poll_index = 0
        while True:
            poll_index += 1
            status_code, payload, elapsed_ms = self._request_json_payload(
                "GET",
                f"/api/agent/session/{quote(session_id)}",
                None,
                timeout=10,
            )
            session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
            if session:
                final_session = dict(session)
                next_budget = self._ui_session_monitor_budget_seconds(final_session)
                if next_budget > monitor_budget_seconds:
                    monitor_budget_seconds = next_budget
                    active_task_timeout_seconds = self._ui_session_active_task_timeout_seconds(final_session)
                    deadline = max(deadline, poll_started + monitor_budget_seconds)
            snapshot = {
                "poll": poll_index,
                "at": utc_now(),
                "statusCode": status_code,
                "elapsedMs": elapsed_ms,
                "sessionStatus": final_session.get("status"),
                "progressPercent": final_session.get("progressPercent"),
                "progressLabel": final_session.get("progressLabel"),
                "pid": final_session.get("pid"),
                "currentTaskId": (final_session.get("controlPlane") or {}).get("activeTaskId") if isinstance(final_session.get("controlPlane"), dict) else None,
                "visualEventCount": final_session.get("visualEventCount"),
                "outputChars": len(str(final_session.get("output") or "")),
                "errorCode": final_session.get("errorCode"),
            }
            polls.append(snapshot)
            self._append_ui_poll_event(snapshot)
            if str(final_session.get("status") or "").lower() in terminal_statuses:
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(1.0)
        final_status = str(final_session.get("status") or "unknown").lower()
        stop_after_timeout: dict[str, Any] = {}
        if final_status not in terminal_statuses:
            stop_after_timeout = self._stop_ui_session_after_timeout(session_id, terminal_statuses)
            stopped_session = stop_after_timeout.get("finalSession") if isinstance(stop_after_timeout.get("finalSession"), dict) else {}
            if stopped_session:
                final_session = dict(stopped_session)
                final_status = str(final_session.get("status") or final_status).lower()

        self.ui_session = final_session
        self.ui_session_polls = polls
        path = self.run_dir / "ui_agent_session_polls.json"
        self._write_json(path, {
            "sessionId": session_id,
            "polls": polls,
            "finalSession": self._compact(final_session, limit=4000),
            "stopAfterTimeout": self._compact(stop_after_timeout, limit=4000),
            "monitorBudgetSeconds": monitor_budget_seconds,
            "activeTaskTimeoutSeconds": active_task_timeout_seconds,
        })
        if final_status in terminal_statuses and not stop_after_timeout:
            status = "ok" if final_status == "completed" else "failed"
            message = f"Real UI session reached terminal status: {final_status}."
        elif stop_after_timeout:
            status = "timeout"
            message = "Real UI session timed out; stop was requested before continuing."
        else:
            status = "timeout"
            message = "Real UI session did not reach a terminal status before monitor timeout."
        return {
            "status": status,
            "message": message,
            "evidencePath": self._relative(path),
            "sessionId": session_id,
            "finalStatus": final_status,
            "pollCount": len(polls),
            "lastProgressPercent": final_session.get("progressPercent"),
            "lastProgressLabel": final_session.get("progressLabel"),
            "pid": final_session.get("pid"),
            "returncode": final_session.get("returncode"),
            "errorCode": final_session.get("errorCode"),
            "terminalLogPath": final_session.get("terminalLogPath"),
            "monitorBudgetSeconds": monitor_budget_seconds,
            "activeTaskTimeoutSeconds": active_task_timeout_seconds,
            "stopRequestedAfterTimeout": bool(stop_after_timeout),
            "stopConfirmedAfterTimeout": bool(stop_after_timeout.get("stopConfirmed")) if stop_after_timeout else False,
            "stopEvidencePath": stop_after_timeout.get("evidencePath") if stop_after_timeout else None,
            "stopStatusCode": stop_after_timeout.get("stopStatusCode") if stop_after_timeout else None,
            "stopError": stop_after_timeout.get("stopError") if stop_after_timeout else None,
        }

    def _stop_ui_session_after_timeout(self, session_id: str, terminal_statuses: set[str]) -> dict[str, Any]:
        evidence_path = self.run_dir / "ui_agent_session_stop_after_timeout.json"
        result: dict[str, Any] = {
            "sessionId": session_id,
            "requestedAt": utc_now(),
            "reason": "prompt_flight_poll_timeout",
            "stopRequest": None,
            "confirmPolls": [],
            "stopConfirmed": False,
            "finalStatus": "unknown",
            "finalSession": {},
            "evidencePath": self._relative(evidence_path),
        }
        confirm_timeout_seconds = min(max(20.0, self.timeout_seconds * 0.2), 60.0)
        confirm_poll_limit = max(8, int(confirm_timeout_seconds / 2))
        confirm_deadline = time.monotonic() + confirm_timeout_seconds
        result["confirmTimeoutSeconds"] = round(confirm_timeout_seconds, 3)
        result["confirmPollLimit"] = confirm_poll_limit
        status_code, payload, elapsed_ms = self._request_json_payload(
            "POST",
            f"/api/agent/session/{quote(session_id)}/stop",
            {},
            timeout=15,
        )
        stop_session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
        result["stopRequest"] = {
            "statusCode": status_code,
            "elapsedMs": elapsed_ms,
            "ok": payload.get("ok"),
            "error": payload.get("error"),
            "sessionStatus": stop_session.get("status"),
        }
        if stop_session:
            result["finalSession"] = stop_session
            result["finalStatus"] = str(stop_session.get("status") or "unknown").lower()
        for attempt in range(1, confirm_poll_limit + 1):
            current_status = str(result.get("finalStatus") or "unknown").lower()
            if current_status in terminal_statuses:
                break
            poll_code, poll_payload, poll_elapsed_ms = self._request_json_payload(
                "GET",
                f"/api/agent/session/{quote(session_id)}",
                None,
                timeout=5,
            )
            session = poll_payload.get("session") if isinstance(poll_payload.get("session"), dict) else {}
            poll_snapshot = {
                "attempt": attempt,
                "at": utc_now(),
                "statusCode": poll_code,
                "elapsedMs": poll_elapsed_ms,
                "sessionStatus": session.get("status"),
                "progressPercent": session.get("progressPercent"),
                "progressLabel": session.get("progressLabel"),
                "errorCode": session.get("errorCode"),
            }
            result["confirmPolls"].append(poll_snapshot)
            if session:
                result["finalSession"] = session
                result["finalStatus"] = str(session.get("status") or "unknown").lower()
            if str(result.get("finalStatus") or "unknown").lower() in terminal_statuses:
                break
            remaining = confirm_deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(2.0, max(0.1, remaining)))
        result["stopConfirmed"] = str(result.get("finalStatus") or "unknown").lower() in terminal_statuses
        result["stopStatusCode"] = status_code
        result["stopError"] = payload.get("error")
        self._write_json(evidence_path, _json_safe(result))
        return result

    def _stage_ui_runtime_truth_read(self) -> dict[str, Any]:
        project_slug = str(self.ui_session.get("projectSlug") or self.project).strip()
        if not project_slug:
            return {"status": "failed", "message": "Cannot query runtime-truth without projectSlug."}
        status_code, payload, elapsed_ms = self._request_json_payload(
            "GET",
            f"/api/projects/{quote(project_slug)}/runtime-truth",
            None,
            timeout=15,
        )
        self.ui_runtime_truth = payload if isinstance(payload, dict) else {}
        path = self.run_dir / "ui_runtime_truth.json"
        self._write_json(path, {"statusCode": status_code, "elapsedMs": elapsed_ms, "runtimeTruth": payload})
        ok = status_code == 200 and payload.get("ok") is True
        control = payload.get("controlPlane") if isinstance(payload.get("controlPlane"), dict) else {}
        sessions = payload.get("sessions") if isinstance(payload.get("sessions"), dict) else {}
        return {
            "status": "ok" if ok else "failed",
            "message": "runtime-truth read after real UI session." if ok else "runtime-truth request failed.",
            "evidencePath": self._relative(path),
            "statusCode": status_code,
            "elapsedMs": elapsed_ms,
            "verdict": payload.get("verdict"),
            "projectStatus": control.get("projectStatus"),
            "currentTaskId": control.get("currentTaskId"),
            "queueCounts": control.get("queueCounts"),
            "activeSessionCount": sessions.get("activeCount"),
        }

    def _stage_ui_runtime_artifacts_read(self) -> dict[str, Any]:
        project_slug = str(self.ui_session.get("projectSlug") or self.project).strip()
        project_dir = self.repo_root / "workspace" / "projects" / safe_slug(project_slug, self.project)
        runtime_dir = project_dir / "runtime"
        artifacts: dict[str, Any] = {
            "projectDir": self._relative(project_dir),
            "runtimeDir": self._relative(runtime_dir),
            "files": {},
            "latestDirective": None,
            "latestCheckpoint": None,
            "terminalLog": None,
        }
        for name in ("project_state.json", "task_queue.json", "task_history.jsonl", "failures.jsonl", "complexity_estimate.json"):
            path = runtime_dir / name
            artifacts["files"][name] = self._file_summary(path)
        directive = self._latest_file(runtime_dir / "directives", "*.json")
        checkpoint = self._latest_file(runtime_dir / "checkpoints", "*.json")
        artifacts["latestDirective"] = self._file_summary(directive) if directive else None
        artifacts["latestCheckpoint"] = self._file_summary(checkpoint) if checkpoint else None
        terminal_log = self.ui_session.get("terminalLogPath")
        terminal_path = Path(str(terminal_log)) if terminal_log else None
        artifacts["terminalLog"] = self._file_summary(terminal_path) if terminal_path else None
        latest_history = self._latest_jsonl_entry(runtime_dir / "task_history.jsonl")
        latest_failure = self._latest_jsonl_entry(runtime_dir / "failures.jsonl")
        artifacts["latestHistory"] = self._compact(latest_history, limit=1000)
        artifacts["latestFailure"] = self._compact(latest_failure, limit=1000)
        latest_failure_for_classification, ignored_failure_reason = self._latest_failure_for_classification(latest_history, latest_failure)
        artifacts["latestFailureIncludedInClassification"] = latest_failure_for_classification is not None
        if ignored_failure_reason:
            artifacts["latestFailureIgnoredReason"] = ignored_failure_reason
        classification = classify_runtime_failure(
            latest_history,
            latest_failure_for_classification,
            artifacts.get("terminalLog", {}).get("tail") if isinstance(artifacts.get("terminalLog"), dict) else None,
        )
        artifacts["runtimeFailureClassification"] = classification
        path = self.run_dir / "ui_runtime_artifacts.json"
        self._write_json(path, artifacts)
        state_exists = bool(artifacts["files"].get("project_state.json", {}).get("exists"))
        queue_exists = bool(artifacts["files"].get("task_queue.json", {}).get("exists"))
        return {
            "status": "ok" if state_exists and queue_exists else "missing_evidence",
            "message": "Runtime artifacts sampled from the real UI session project." if state_exists and queue_exists else "Runtime artifacts missing after UI session.",
            "evidencePath": self._relative(path),
            "projectDir": self._relative(project_dir),
            "projectState": artifacts["files"].get("project_state.json"),
            "taskQueue": artifacts["files"].get("task_queue.json"),
            "latestDirective": artifacts.get("latestDirective"),
            "latestCheckpoint": artifacts.get("latestCheckpoint"),
            "terminalLog": artifacts.get("terminalLog"),
            "runtimeInfrastructureFailure": bool(classification.get("infrastructureFailure")),
            "fatalInfrastructureFailure": bool(classification.get("fatalInfrastructureFailure")),
            "infrastructureFailureMarkers": classification.get("markers"),
            "latestTaskResultBlockers": self._latest_task_result_blockers(latest_history),
        }

    def _stage_response_synthesized(self) -> dict[str, Any]:
        failed = [stage["name"] for stage in self.report.get("stages", []) if stage.get("status") in TERMINAL_BAD_STATUSES]
        blocked = [stage["name"] for stage in self.report.get("stages", []) if stage.get("status") == "blocked"]
        validated_result = self.real_validation.get("task_result") if isinstance(self.real_validation.get("task_result"), dict) else {}
        response_file = self.project_dir / "src" / "prompt_flight_response.json"
        runtime_response = None
        if response_file.is_file():
            try:
                runtime_response = json.loads(response_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                runtime_response = {"error": "invalid_runtime_response_json"}
        recommendation = "Prompt flight is connected."
        if self.mode == "real_session_guarded" and not failed and not blocked:
            recommendation = "Prompt processed through real guarded runtime loop."
        elif failed or blocked:
            recommendation = "Inspect blocked/failed stages before executing a real session."
        response = {
            "traceId": self.trace_id,
            "promptHash": sha256_text(self.prompt),
            "mode": self.mode,
            "blockedStages": blocked,
            "failedStages": failed,
            "taskId": self._require_real_task()["id"] if self.real_task else None,
            "validationPassed": validated_result.get("validation_passed"),
            "runtimeResponsePath": self._relative(response_file) if response_file.is_file() else None,
            "runtimeResponseHash": sha256_text(runtime_response) if isinstance(runtime_response, dict) else None,
            "recommendation": recommendation,
        }
        path = self.run_dir / "response_summary.json"
        self._write_json(path, response)
        return {"message": "Response synthesized from stage evidence and runtime output.", "evidencePath": self._relative(path), "responseHash": sha256_text(response), **response}

    def _build_prompt_task(self) -> dict[str, Any]:
        task_id = "PROMPT-FLIGHT-" + self.trace_id.replace("prompt-flight-", "")
        if self.mode == "real_session_guarded":
            task_id = "PROMPT-REAL-" + self.trace_id.replace("prompt-flight-", "")
            validation_code = (
                "from pathlib import Path; import json; "
                "d=json.loads(Path('src/prompt_flight_response.json').read_text(encoding='utf-8')); "
                f"assert d.get('traceId') == {self.trace_id!r}; "
                f"assert d.get('promptHash') == {sha256_text(self.prompt)!r}; "
                "assert d.get('processedBy') == 'guarded_runtime_worker'; "
                "assert d.get('hablaBasic', {}).get('inputHash') == d.get('promptHash')"
            )
            return {
                "id": task_id,
                "title": "Process guarded HABLA BASIC prompt",
                "goal": "Process one persisted prompt through task queue, directive generation, worker, validator, history and checkpoint.",
                "status": "pending",
                "priority": 80,
                "dependencies": [],
                "expected_files": ["src/prompt_flight_response.json"],
                "validation_commands": ["python3 -B -c " + shlex.quote(validation_code)],
                "timeout_seconds": self.timeout_seconds,
                "max_retries": 0,
                "mode": "build",
                "checkpoint_key": None,
            }
        return {
            "id": task_id,
            "title": "Prompt flight diagnostic task",
            "goal": "Trace how one HABLA BASIC prompt would move through internal runtime layers.",
            "status": "pending",
            "priority": 50,
            "dependencies": [],
            "expected_files": ["runtime/continuity_probe/" + self.trace_id + "/prompt_flight_report.json"],
            "validation_commands": ["python3 -B -m py_compile orchestrator/continuity_probe.py"],
            "timeout_seconds": self.timeout_seconds,
            "max_retries": 0,
            "mode": "build",
            "checkpoint_key": None,
        }

    def _require_real_task(self) -> dict[str, Any]:
        if self.real_task is None:
            self.real_task = self._build_prompt_task()
        return self.real_task

    def _prompt_worker_code(self) -> str:
        classification = self._classify_prompt()
        habla_basic = {
            "inputHash": sha256_text(self.prompt),
            "intent": classification["intent"],
            "runtimeMode": "build",
            "guarded": True,
        }
        payload = {
            "traceId": self.trace_id,
            "project": self.project,
            "prompt": self.prompt,
            "promptHash": sha256_text(self.prompt),
            "classification": classification,
            "hablaBasic": habla_basic,
            "processedBy": "guarded_runtime_worker",
            "processedAt": utc_now(),
            "response": {
                "type": "guarded_prompt_response",
                "summary": "Prompt received, classified and processed through the real guarded runtime path.",
                "intent": classification["intent"],
                "safety": "Prompt was not executed as arbitrary code; it was processed into auditable response evidence inside the worker sandbox.",
            },
        }
        payload_literal = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        return (
            "from pathlib import Path\n"
            "import json\n"
            f"payload=json.loads({payload_literal!r})\n"
            "path=Path('src/prompt_flight_response.json')\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
            "print(json.dumps({'processed': True, 'responsePath': str(path), 'traceId': payload['traceId']}, ensure_ascii=True, sort_keys=True))\n"
        )

    def _classify_prompt(self) -> dict[str, Any]:
        text = self.prompt.lower()
        if any(token in text for token in ("crear", "build", "constru", "implement", "hacer")):
            intent = "build_or_modify"
        elif any(token in text for token in ("revis", "analiz", "debug", "error", "fall")):
            intent = "inspect_or_debug"
        elif any(token in text for token in ("test", "prueba", "valid", "verific")):
            intent = "validate_or_test"
        else:
            intent = "general_runtime_request"
        complexity = "medium" if len(self.prompt) > 500 else "small"
        return {"intent": intent, "complexity": complexity, "promptChars": len(self.prompt), "promptHash": sha256_text(self.prompt)}

    def _request_json(self, method: str, path: str, *, timeout: int) -> tuple[int, dict[str, Any]]:
        if not self.base_url:
            return 0, {"ok": False, "error": "missing_base_url"}
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

    def _ui_session_payload(self) -> dict[str, Any]:
        return {
            "projectName": self.project,
            "projectSlug": self.project,
            "requirement": self.prompt,
            "ensureNewProject": True,
            "bootstrapProject": False,
            "runtimeMode": "build",
            "subagentPlan": None,
        }

    def _request_json_payload(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        *,
        timeout: int,
    ) -> tuple[int, dict[str, Any], float]:
        if not self.base_url:
            return 0, {"ok": False, "error": "missing_base_url"}, 0.0
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        started = time.monotonic()
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return int(response.status), json.loads(raw) if raw else {}, round((time.monotonic() - started) * 1000, 3)
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                error_payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                error_payload = {"ok": False, "error": "non_json_error", "message": raw}
            return int(exc.code), error_payload, round((time.monotonic() - started) * 1000, 3)
        except (TimeoutError, URLError, OSError) as exc:
            return 0, {"ok": False, "error": "connection_failed", "message": str(exc)}, round((time.monotonic() - started) * 1000, 3)

    def _append_ui_poll_event(self, snapshot: dict[str, Any]) -> None:
        event = {
            "at": utc_now(),
            "traceId": self.trace_id,
            "stage": "ui_agent_session_poll",
            "status": str(snapshot.get("sessionStatus") or "unknown"),
            "message": str(snapshot.get("progressLabel") or "poll"),
            "evidence": _json_safe(snapshot),
        }
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")

    def _latest_file(self, directory: Path, pattern: str) -> Path | None:
        if not directory.exists() or not directory.is_dir():
            return None
        files = [path for path in directory.glob(pattern) if path.is_file()]
        if not files:
            return None
        return sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)[0]

    def _file_summary(self, path: Path | None) -> dict[str, Any]:
        if path is None:
            return {"exists": False}
        payload: dict[str, Any] = {"path": self._relative(path), "exists": path.exists(), "isFile": path.is_file() if path.exists() else False}
        if not path.exists() or not path.is_file():
            return payload
        stat = path.stat()
        payload["size"] = stat.st_size
        payload["mtime"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            payload["readError"] = str(exc)
            return payload
        payload["sha256"] = sha256_text(text)
        payload["lineCount"] = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        payload["tail"] = text[-1200:]
        if path.suffix == ".json":
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    payload["jsonKeys"] = sorted(str(key) for key in parsed.keys())[:40]
            except json.JSONDecodeError:
                payload["jsonError"] = "invalid_json"
        return payload

    def _latest_jsonl_entry(self, path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                return {"raw": line[-1200:]}
            return payload if isinstance(payload, dict) else {"value": payload}
        return None

    def _latest_task_result_blockers(self, history_entry: dict[str, Any] | None) -> list[str]:
        if not isinstance(history_entry, dict):
            return []
        result = history_entry.get("result") if isinstance(history_entry.get("result"), dict) else {}
        blockers = result.get("blockers") if isinstance(result.get("blockers"), list) else []
        return [str(item) for item in blockers if str(item).strip()][:8]

    def _latest_failure_for_classification(self, latest_history: dict[str, Any] | None, latest_failure: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str]:
        if not isinstance(latest_failure, dict):
            return None, ""
        history_task_id = self._task_id_from_runtime_record(latest_history)
        failure_task_id = self._task_id_from_runtime_record(latest_failure)
        if history_task_id and failure_task_id and history_task_id != failure_task_id:
            return None, f"stale_failure_for_different_task:{failure_task_id}"
        if not self._history_entry_is_validated_completion(latest_history):
            return latest_failure, ""
        history_recorded_at = self._recorded_at_key(latest_history)
        failure_recorded_at = self._recorded_at_key(latest_failure)
        if history_recorded_at and failure_recorded_at and history_recorded_at >= failure_recorded_at:
            return None, "superseded_by_validated_history"
        return latest_failure, ""

    def _history_entry_is_validated_completion(self, history_entry: dict[str, Any] | None) -> bool:
        if not isinstance(history_entry, dict):
            return False
        result = history_entry.get("result") if isinstance(history_entry.get("result"), dict) else {}
        blockers = result.get("blockers") if isinstance(result.get("blockers"), list) else []
        return result.get("completed") is True and result.get("validation_passed") is True and not blockers

    def _task_id_from_runtime_record(self, value: Any) -> str:
        if isinstance(value, dict):
            for key in ("task_id", "taskId", "currentTaskId"):
                raw = value.get(key)
                if isinstance(raw, str) and raw.strip():
                    return raw.strip()
            for item in value.values():
                found = self._task_id_from_runtime_record(item)
                if found:
                    return found
        if isinstance(value, list):
            for item in value:
                found = self._task_id_from_runtime_record(item)
                if found:
                    return found
        return ""

    def _recorded_at_key(self, record: dict[str, Any] | None) -> str:
        if not isinstance(record, dict):
            return ""
        raw = record.get("recorded_at") or record.get("timestamp") or record.get("at") or ""
        return str(raw).strip()

    def _finalize(self) -> dict[str, Any]:
        stages = self.report.get("stages") if isinstance(self.report.get("stages"), list) else []
        failed = [stage.get("name") for stage in stages if isinstance(stage, dict) and stage.get("status") in TERMINAL_BAD_STATUSES]
        blocked = [stage.get("name") for stage in stages if isinstance(stage, dict) and stage.get("status") == "blocked"]
        if blocked:
            result = "prompt_flight_blocked"
            status = "blocked"
        elif failed:
            result = "prompt_flight_failed"
            status = "failed"
        else:
            result = "prompt_flight_ok"
            status = "completed"
        self.report["status"] = status
        self.report["result"] = result
        self.report["failedStages"] = failed
        self.report["blockedStages"] = blocked
        self.report["finishedAt"] = utc_now()
        self.report["durationSeconds"] = round(time.monotonic() - self.started, 6)
        self._refresh_summary()
        self._write_report()
        self.markdown_path.write_text(self._markdown_report(), encoding="utf-8")
        return dict(self.report)

    def _refresh_summary(self) -> None:
        counts = {"ok": 0, "failed": 0, "skipped": 0, "blocked": 0, "total": 0}
        for stage in self.report.get("stages", []):
            if not isinstance(stage, dict):
                continue
            counts["total"] += 1
            status = str(stage.get("status") or "failed")
            if status == "ok":
                counts["ok"] += 1
            elif status == "skipped":
                counts["skipped"] += 1
            elif status == "blocked":
                counts["blocked"] += 1
            elif status in TERMINAL_BAD_STATUSES:
                counts["failed"] += 1
        self.report["summary"] = counts

    def _write_report(self) -> None:
        self.report["project"] = self.project
        self.report["durationSeconds"] = round(time.monotonic() - self.started, 6)
        self.report["reportPath"] = self._relative(self.report_path)
        self.report["eventsPath"] = self._relative(self.events_path)
        self._refresh_summary()
        self._write_json(self.report_path, self.report)

    def _markdown_report(self) -> str:
        lines = [
            f"# Prompt Flight Report - {self.trace_id}",
            "",
            f"- result: `{self.report.get('result')}`",
            f"- mode: `{self.mode}`",
            f"- project: `{self.project}`",
            f"- durationSeconds: `{self.report.get('durationSeconds')}`",
            "",
            "| Stage | Status | Latency ms | Message |",
            "| --- | --- | ---: | --- |",
        ]
        for stage in self.report.get("stages", []):
            if not isinstance(stage, dict):
                continue
            lines.append(f"| `{stage.get('name')}` | `{stage.get('status')}` | `{stage.get('durationMs')}` | {str(stage.get('message') or '').replace('|', '/')} |")
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


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=True)
        return value
    except TypeError:
        return str(value)
