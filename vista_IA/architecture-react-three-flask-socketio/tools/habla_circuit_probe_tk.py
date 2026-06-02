"""Tkinter client for HABLA CircuitProbe and Prompt Flight Recorder.

The UI is only a client. The backend owns all runtime inspection and writes the
auditable evidence under runtime/continuity_probe/.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.prompt_flight_batch import (  # noqa: E402
    DEFAULT_CASES_RELATIVE_PATH,
    PromptFlightBatchRunner,
    discover_prompt_flight_suites,
    load_prompt_flight_cases,
)


DEFAULT_BASE_URL = "http://127.0.0.1:5001"
DEFAULT_PROMPT_FLIGHT_SUITE = os.environ.get("HABLA_PROMPT_FLIGHT_DEFAULT_SUITE", "").strip()
DEFAULT_PROMPT_FLIGHT_MODE = os.environ.get("HABLA_PROMPT_FLIGHT_DEFAULT_MODE", "ui_session_rest").strip() or "ui_session_rest"
PROMPT_FLIGHT_WORKER_REQUIRED_MODES = {"safe_canary", "real_session_guarded", "ui_session_rest"}


CHECK_ORDER = [
    "prompt_input",
    "policy_loaded",
    "plan_loaded",
    "imports_loaded",
    "backend_health",
    "task_created",
    "queue_persisted",
    "directive_generated",
    "worker_executed",
    "validator_passed",
    "history_written",
    "checkpoint_written",
    "observer_readable",
    "harness_reachable",
    "safety_learning_readable",
    "autopilot_memory",
]


class CircuitProbeClient:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("HABLA CircuitProbe Console")
        self.root.geometry("1280x840")
        self.trace_id = ""
        self.batch_id = ""
        self.batch_running = False
        self.batch_pause_after_current = False
        self.batch_stop_after_current = False
        self.batch_reset_requested = False
        self.batch_runner: PromptFlightBatchRunner | None = None
        self.active_case_id = ""
        self.active_project_slug = ""
        self.active_session_id = ""
        self.available_suites: list[dict[str, object]] = []
        self.suite_labels: dict[str, dict[str, object]] = {}
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self._build_ui()
        self.root.after(200, self._drain_messages)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Backend").grid(row=0, column=0, sticky=tk.W)
        self.base_url = tk.StringVar(value=DEFAULT_BASE_URL)
        ttk.Entry(top, textvariable=self.base_url, width=34).grid(row=0, column=1, sticky=tk.W, padx=(6, 14))

        ttk.Label(top, text="Probe Mode").grid(row=0, column=2, sticky=tk.W)
        self.mode = tk.StringVar(value="active_canary")
        ttk.Combobox(top, textvariable=self.mode, values=("active_canary", "read_only", "harness_canary"), width=16, state="readonly").grid(row=0, column=3, sticky=tk.W, padx=(6, 14))

        ttk.Label(top, text="Project").grid(row=0, column=4, sticky=tk.W)
        self.project = tk.StringVar(value="continuity-probe-canary")
        ttk.Entry(top, textvariable=self.project, width=28).grid(row=0, column=5, sticky=tk.W, padx=(6, 14))

        self.include_harness = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Harness", variable=self.include_harness).grid(row=0, column=6, sticky=tk.W)

        ttk.Button(top, text="Start Probe", command=self.start_probe).grid(row=0, column=7, padx=(12, 0))
        ttk.Button(top, text="Refresh", command=self.refresh_status).grid(row=0, column=8, padx=(8, 0))

        prompt_frame = ttk.LabelFrame(self.root, text="Prompt Flight Recorder", padding=10)
        prompt_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        prompt_controls = ttk.Frame(prompt_frame)
        prompt_controls.pack(fill=tk.X)
        ttk.Label(prompt_controls, text="Flight Mode").pack(side=tk.LEFT)
        self.prompt_mode = tk.StringVar(value=DEFAULT_PROMPT_FLIGHT_MODE if DEFAULT_PROMPT_FLIGHT_MODE in {"ui_session_rest", "real_session_guarded", "trace_only", "safe_canary"} else "ui_session_rest")
        ttk.Combobox(prompt_controls, textvariable=self.prompt_mode, values=("ui_session_rest", "real_session_guarded", "trace_only", "safe_canary"), width=18, state="readonly").pack(side=tk.LEFT, padx=(6, 14))

        ttk.Label(prompt_controls, text="Suite").pack(side=tk.LEFT)
        self.selected_suite = tk.StringVar(value="")
        self.suite_combo = ttk.Combobox(prompt_controls, textvariable=self.selected_suite, values=(), width=34, state="readonly")
        self.suite_combo.pack(side=tk.LEFT, padx=(6, 8))
        self.suite_combo.bind("<<ComboboxSelected>>", self._on_suite_selected)
        ttk.Button(prompt_controls, text="Refresh Suites", command=self.refresh_suites).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(prompt_controls, text="Case JSON").pack(side=tk.LEFT)
        self.prompt_cases_path = tk.StringVar(value=str(DEFAULT_CASES_RELATIVE_PATH))
        ttk.Entry(prompt_controls, textvariable=self.prompt_cases_path, width=42).pack(side=tk.LEFT, padx=(6, 10))

        self.run_batch_button = ttk.Button(prompt_controls, text="Run Prompt Flight", command=self.run_prompt_flight)
        self.run_batch_button.pack(side=tk.LEFT)
        ttk.Button(prompt_controls, text="Run Current Prompt", command=self.run_current_prompt_flight).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(prompt_controls, text="Clear Prompt", command=lambda: self.prompt_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=(8, 0))

        batch_controls = ttk.Frame(prompt_frame)
        batch_controls.pack(fill=tk.X, pady=(8, 0))
        self.pause_button = ttk.Button(batch_controls, text="Pause After Current", command=self.pause_after_current)
        self.pause_button.pack(side=tk.LEFT)
        ttk.Button(batch_controls, text="Resume Batch", command=self.resume_batch).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(batch_controls, text="Stop After Current", command=self.stop_after_current).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(batch_controls, text="Reset Batch", command=self.reset_batch).pack(side=tk.LEFT, padx=(8, 0))
        self.batch_status = tk.StringVar(value="batch idle")
        ttk.Label(batch_controls, textvariable=self.batch_status).pack(side=tk.LEFT, padx=(14, 0))
        self.suite_status = tk.StringVar(value="suite: manual JSON")
        ttk.Label(batch_controls, textvariable=self.suite_status).pack(side=tk.LEFT, padx=(14, 0))

        self.prompt_text = tk.Text(prompt_frame, height=5, wrap=tk.WORD)
        self.prompt_text.pack(fill=tk.X, pady=(8, 0))
        self.prompt_text.insert("1.0", "Crear una tarea real pequena desde la ruta normal de la UI y medir toda la transaccion interna del servidor.")

        status_frame = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        status_frame.pack(fill=tk.X)
        self.status = tk.StringVar(value="idle")
        ttk.Label(status_frame, textvariable=self.status).pack(anchor=tk.W)

        body = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        table_frame = ttk.Frame(body)
        body.add(table_frame, weight=3)
        self.tree = ttk.Treeview(table_frame, columns=("status", "latency", "message", "evidence"), show="headings", height=22)
        self.tree.heading("status", text="Status")
        self.tree.heading("latency", text="Latency")
        self.tree.heading("message", text="Message")
        self.tree.heading("evidence", text="Evidence")
        self.tree.column("status", width=130, anchor=tk.CENTER)
        self.tree.column("latency", width=100, anchor=tk.E)
        self.tree.column("message", width=520)
        self.tree.column("evidence", width=500)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)

        log_frame = ttk.Frame(body)
        body.add(log_frame, weight=1)
        self.log = tk.Text(log_frame, height=8, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
        self._reset_probe_rows()
        self.refresh_suites()

    def refresh_suites(self) -> None:
        self.available_suites = [suite for suite in discover_prompt_flight_suites(REPO_ROOT) if suite.get("status") == "ok"]
        self.suite_labels = {}
        labels = []
        for suite in self.available_suites:
            label = f"{suite.get('title')} ({suite.get('caseCount')} casos)"
            labels.append(label)
            self.suite_labels[label] = suite
        self.suite_combo.configure(values=labels)
        if labels and not self.selected_suite.get():
            selected_label = labels[0]
            if DEFAULT_PROMPT_FLIGHT_SUITE:
                for label, suite in self.suite_labels.items():
                    aliases = {
                        str(suite.get("suiteId") or ""),
                        str(suite.get("title") or ""),
                        str(suite.get("domain") or ""),
                    }
                    if DEFAULT_PROMPT_FLIGHT_SUITE in aliases:
                        selected_label = label
                        break
            self.selected_suite.set(selected_label)
            self._apply_suite(self.suite_labels[selected_label])
        elif not labels:
            self.suite_status.set("suite: no suites found")

    def _on_suite_selected(self, _event: object | None = None) -> None:
        suite = self.suite_labels.get(self.selected_suite.get())
        if suite:
            self._apply_suite(suite)

    def _apply_suite(self, suite: dict[str, object]) -> None:
        case_path = str(suite.get("casePath") or DEFAULT_CASES_RELATIVE_PATH)
        self.prompt_cases_path.set(case_path)
        self.prompt_mode.set(str(suite.get("defaultMode") or "ui_session_rest"))
        self.suite_status.set(f"suite: {suite.get('suiteId')} | {suite.get('caseCount')} casos")

    def _selected_suite_metadata(self) -> dict[str, object] | None:
        return self.suite_labels.get(self.selected_suite.get())

    def _reset_probe_rows(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for check in CHECK_ORDER:
            self.tree.insert("", tk.END, iid=check, values=("pending", "", check, ""))

    def _reset_batch_rows(self, cases: list[dict[str, object]]) -> None:
        self.tree.delete(*self.tree.get_children())
        total = len(cases)
        for index, case in enumerate(cases, start=1):
            case_id = str(case.get("id") or f"case-{index}")
            title = str(case.get("title") or case_id)
            category = str(case.get("category") or "general")
            self.tree.insert("", tk.END, iid=case_id, values=("pending", "", f"{index}/{total} {title}", f"category={category}"))

    def start_probe(self) -> None:
        self._reset_probe_rows()
        payload = {
            "mode": self.mode.get(),
            "project": self.project.get(),
            "baseUrl": self.base_url.get(),
            "includeHarness": bool(self.include_harness.get()),
        }
        self.status.set("starting probe...")
        self._log("Starting continuity probe via backend")
        threading.Thread(target=self._start_worker, args=(payload,), daemon=True).start()

    def _ensure_prompt_flight_worker_ready(self, mode: str) -> bool:
        normalized_mode = str(mode or "").strip().lower()
        if normalized_mode not in PROMPT_FLIGHT_WORKER_REQUIRED_MODES:
            return True
        try:
            response = self._request_json(
                "GET",
                "/api/continuity-probe/prompt-flight/worker-diagnostics",
                None,
                timeout=10,
                base_url=self.base_url.get().strip(),
            )
        except Exception as exc:
            messagebox.showerror("Prompt Flight", f"Cannot verify worker runtime: {exc}")
            self.batch_status.set("worker diagnostics failed")
            return False
        diagnostics = response.get("diagnostics") if isinstance(response.get("diagnostics"), dict) else {}
        if diagnostics.get("promptFlightWorkerReady") is True:
            self._log(
                "Worker runtime verified: "
                + json.dumps(
                    {
                        "effectiveSandboxMode": diagnostics.get("effectiveSandboxMode"),
                        "usesDangerBypass": diagnostics.get("usesDangerBypass"),
                        "safeCommandSummary": diagnostics.get("safeCommandSummary"),
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
            )
            return True
        message = (
            "Worker runtime no verificado. Reinicia con:\n"
            "./start_prompt_flight_tkinter.sh --local-worker-no-bwrap\n\n"
            f"Modo efectivo: {diagnostics.get('effectiveSandboxMode')}\n"
            f"Comando: {diagnostics.get('safeCommandSummary')}\n"
            f"Blockers: {', '.join(str(item) for item in diagnostics.get('blockers') or [])}"
        )
        messagebox.showerror("Prompt Flight bloqueado", message)
        self.batch_status.set("worker runtime blocked")
        self._log("Prompt Flight blocked by worker diagnostics: " + json.dumps(diagnostics, ensure_ascii=True, sort_keys=True))
        return False


    def run_prompt_flight(self) -> None:
        if self.batch_running:
            messagebox.showinfo("Prompt Flight", "A Prompt Flight batch is already running.")
            return
        if not self._ensure_prompt_flight_worker_ready(self.prompt_mode.get()):
            return
        try:
            cases = load_prompt_flight_cases(REPO_ROOT, self.prompt_cases_path.get().strip())
            suite = self._selected_suite_metadata()
            if suite:
                cases = [{**case, "suite": suite, "suiteId": suite.get("suiteId"), "domain": suite.get("domain")} for case in cases]
        except Exception as exc:
            messagebox.showerror("Prompt Flight", f"Cannot load case JSON: {exc}")
            return
        if not cases:
            messagebox.showinfo("Prompt Flight", "The case JSON has no cases.")
            return
        if len(cases) != 50:
            self._log(f"Warning: loaded {len(cases)} cases; default production suite should contain 50 cases.")
        self.batch_running = True
        self.batch_pause_after_current = False
        self.batch_stop_after_current = False
        self.batch_reset_requested = False
        self.active_case_id = ""
        self.active_project_slug = ""
        self.active_session_id = ""
        self._reset_batch_rows(cases)
        self.status.set("running prompt flight batch...")
        self.batch_status.set(f"batch starting: {len(cases)} cases")
        suite = self._selected_suite_metadata()
        suite_id = str(suite.get("suiteId") or "manual") if suite else "manual"
        self._log(f"Running Prompt Flight batch with {len(cases)} sequential cases from suite={suite_id}")
        args = (
            cases,
            self.base_url.get().strip(),
            self.project.get().strip(),
            self.prompt_mode.get().strip(),
            bool(self.include_harness.get()),
        )
        threading.Thread(target=self._prompt_flight_batch_worker, args=args, daemon=True).start()

    def run_current_prompt_flight(self) -> None:
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showinfo("Prompt Flight", "Write a prompt first.")
            return
        if not self._ensure_prompt_flight_worker_ready(self.prompt_mode.get()):
            return
        self.tree.delete(*self.tree.get_children())
        payload = {
            "mode": self.prompt_mode.get(),
            "project": self.project.get(),
            "baseUrl": self.base_url.get(),
            "includeHarness": bool(self.include_harness.get()),
            "prompt": prompt,
            "timeoutSeconds": 120,
        }
        self.status.set("running single prompt flight...")
        self._log("Running one Prompt Flight Recorder case via backend")
        threading.Thread(target=self._prompt_flight_worker, args=(payload, self.base_url.get().strip()), daemon=True).start()

    def pause_after_current(self) -> None:
        if not self.batch_running:
            messagebox.showinfo("Prompt Flight", "No batch is running.")
            return
        self.batch_pause_after_current = True
        self.batch_status.set("pause requested after current case")
        self._log("Pause requested; batch will pause before the next case starts.")

    def resume_batch(self) -> None:
        self.batch_pause_after_current = False
        if self.batch_running:
            self.batch_status.set("batch resume requested")
            self._log("Batch resume requested.")

    def stop_after_current(self) -> None:
        if not self.batch_running:
            messagebox.showinfo("Prompt Flight", "No batch is running.")
            return
        self.batch_stop_after_current = True
        self.batch_pause_after_current = False
        self.batch_status.set("stop requested after current case")
        self._log("Stop requested; batch will stop before starting another case.")

    def reset_batch(self) -> None:
        if not self.batch_running and not self.active_project_slug and not self.active_session_id:
            self.batch_status.set("batch reset")
            self.status.set("batch reset")
            self._log("Reset requested with no active batch; local state cleared.")
            return
        self.batch_reset_requested = True
        self.batch_stop_after_current = True
        self.batch_pause_after_current = False
        evidence = {
            "activeCaseId": self.active_case_id,
            "activeProjectSlug": self.active_project_slug,
            "activeSessionId": self.active_session_id,
        }
        if self.batch_runner is not None:
            self.batch_runner.request_cancel(
                reason="tkinter_reset_requested",
                evidence=evidence,
                event_callback=lambda event: self.messages.put(("batch_event", event)),
            )
        self.batch_status.set("reset requested; stopping backend session if active")
        self.status.set("reset requested")
        self._log("Reset requested; no new cases will start and any active backend session will be stopped if found.")
        threading.Thread(target=self._reset_batch_worker, args=(self.base_url.get().strip(), evidence), daemon=True).start()

    def refresh_status(self) -> None:
        if not self.trace_id:
            messagebox.showinfo("CircuitProbe", "No traceId yet. Start a probe first.")
            return
        threading.Thread(target=self._status_worker, daemon=True).start()

    def _start_worker(self, payload: dict[str, object]) -> None:
        try:
            response = self._request_json("POST", "/api/continuity-probe/start", payload, base_url=str(payload.get("baseUrl") or ""))
            self.messages.put(("started", response))
        except Exception as exc:
            self.messages.put(("error", exc))

    def _prompt_flight_worker(self, payload: dict[str, object], base_url: str) -> None:
        try:
            timeout = max(int(payload.get("timeoutSeconds") or 180) + 180, 1200)
            response = self._request_json("POST", "/api/continuity-probe/prompt-flight", payload, timeout=timeout, base_url=base_url)
            self.messages.put(("prompt_flight", response))
        except Exception as exc:
            self.messages.put(("error", exc))

    def _prompt_flight_batch_worker(
        self,
        cases: list[dict[str, object]],
        base_url: str,
        default_project: str,
        selected_mode: str,
        include_harness: bool,
    ) -> None:
        normalized_cases = []
        for case in cases:
            updated = dict(case)
            updated.setdefault("mode", selected_mode or "ui_session_rest")
            normalized_cases.append(updated)
        runner = PromptFlightBatchRunner(repo_root=REPO_ROOT, cases=normalized_cases)
        self.batch_runner = runner
        self.batch_id = runner.batch_id

        def emit(event: dict[str, object]) -> None:
            self.messages.put(("batch_event", event))

        def request_case(payload: dict[str, object], _case: dict[str, object]) -> dict[str, object]:
            timeout = max(int(payload.get("timeoutSeconds") or 180) + 180, 1200)
            return self._request_json("POST", "/api/continuity-probe/prompt-flight", payload, timeout=timeout, base_url=base_url)

        try:
            summary = runner.run(
                request_case=request_case,
                base_url=base_url,
                default_project=default_project or "continuity-probe-canary",
                include_harness=include_harness,
                default_timeout_seconds=180,
                event_callback=emit,
                should_stop=lambda: self.batch_stop_after_current or self.batch_reset_requested,
                should_pause=lambda: self.batch_pause_after_current and not self.batch_reset_requested,
                pause_sleep_seconds=0.5,
            )
            self.messages.put(("batch_done", summary))
        except Exception as exc:
            self.messages.put(("batch_error", exc))

    def _reset_batch_worker(self, base_url: str, evidence: dict[str, object]) -> None:
        project_slug = str(evidence.get("activeProjectSlug") or "").strip()
        session_id = str(evidence.get("activeSessionId") or "").strip()
        if not session_id and project_slug:
            session_id = self._find_active_agent_session(base_url, project_slug)
        stop_response: dict[str, object] | None = None
        if session_id:
            self.active_session_id = session_id
            stop_response = self._request_json("POST", f"/api/agent/session/{quote(session_id)}/stop", {}, timeout=20, base_url=base_url)
        self.messages.put(("reset_done", {"projectSlug": project_slug, "sessionId": session_id, "stopResponse": stop_response}))

    def _find_active_agent_session(self, base_url: str, project_slug: str) -> str:
        terminal = {"completed", "failed", "stopped", "blocked"}
        for _attempt in range(8):
            response = self._request_json("GET", "/api/agent/sessions", None, timeout=10, base_url=base_url)
            sessions = response.get("sessions") if isinstance(response.get("sessions"), list) else []
            fallback = ""
            for session in sessions:
                if not isinstance(session, dict):
                    continue
                if str(session.get("projectSlug") or "") != project_slug:
                    continue
                session_id = str(session.get("sessionId") or "").strip()
                if not session_id:
                    continue
                status = str(session.get("status") or "").lower()
                if status not in terminal:
                    return session_id
                fallback = fallback or session_id
            if fallback:
                return fallback
            time.sleep(0.5)
        return ""

    def _status_worker(self) -> None:
        try:
            response = self._request_json("GET", f"/api/continuity-probe/status/{self.trace_id}", None)
            self.messages.put(("status", response))
        except Exception as exc:
            self.messages.put(("error", exc))

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None,
        *,
        timeout: int = 160,
        base_url: str | None = None,
    ) -> dict[str, object]:
        body = None
        target_base_url = str(base_url or self.base_url.get()).rstrip("/")
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(target_base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=max(5, int(timeout))) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "non_json_error", "message": raw}
            payload["statusCode"] = exc.code
            return payload
        except (URLError, TimeoutError) as exc:
            return {"ok": False, "error": "connection_failed", "message": str(exc)}

    def _drain_messages(self) -> None:
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "error":
                self.status.set("error")
                self._log(str(payload))
            elif kind == "batch_error":
                self.batch_running = False
                self.batch_runner = None
                self.status.set("batch error")
                self.batch_status.set("batch error")
                self._log(str(payload))
            elif kind == "batch_event":
                data = payload if isinstance(payload, dict) else {}
                self._render_batch_event(data)
            elif kind == "batch_done":
                data = payload if isinstance(payload, dict) else {}
                self.batch_running = False
                self.batch_pause_after_current = False
                self.batch_stop_after_current = False
                self.batch_reset_requested = False
                self.batch_runner = None
                self.active_case_id = ""
                self.active_project_slug = ""
                self.active_session_id = ""
                self._render_batch_done(data)
            elif kind == "reset_done":
                data = payload if isinstance(payload, dict) else {}
                self._render_reset_done(data)
            elif kind == "started":
                data = payload if isinstance(payload, dict) else {}
                self.trace_id = str(data.get("traceId") or "")
                self.status.set(f"traceId={self.trace_id} status=queued")
                self._log(json.dumps(data, ensure_ascii=True, indent=2))
                if self.trace_id:
                    self.root.after(1000, self._poll_until_done)
            elif kind == "status":
                data = payload if isinstance(payload, dict) else {}
                self._render_status(data)
            elif kind == "prompt_flight":
                data = payload if isinstance(payload, dict) else {}
                self.trace_id = str(data.get("traceId") or "")
                self._render_prompt_flight(data)
        self.root.after(200, self._drain_messages)

    def _poll_until_done(self) -> None:
        if not self.trace_id:
            return
        self.refresh_status()
        current = self.status.get()
        if "completed" not in current and "failed" not in current:
            self.root.after(1200, self._poll_until_done)

    def _render_status(self, payload: dict[str, object]) -> None:
        run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
        report = run.get("report") if isinstance(run.get("report"), dict) else {}
        status = str(run.get("status") or report.get("status") or "unknown")
        result = str(run.get("result") or report.get("result") or "")
        self.status.set(f"traceId={self.trace_id} status={status} result={result}")
        checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
        for check in CHECK_ORDER:
            item = checks.get(check) if isinstance(checks.get(check), dict) else {}
            value_status = str(item.get("status") or "pending")
            message = str(item.get("message") or check)
            evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
            evidence_text = self._short_evidence(evidence)
            if self.tree.exists(check):
                self.tree.item(check, values=(value_status, evidence.get("durationMs", ""), message, evidence_text))
        self._log(f"status={status} result={result}")

    def _render_prompt_flight(self, payload: dict[str, object]) -> None:
        report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
        status = str(report.get("status") or "unknown")
        result = str(report.get("result") or "")
        self.status.set(f"traceId={self.trace_id} prompt-flight status={status} result={result}")
        self.tree.delete(*self.tree.get_children())
        stages = report.get("stages") if isinstance(report.get("stages"), list) else []
        for index, stage in enumerate(stages):
            if not isinstance(stage, dict):
                continue
            evidence = stage.get("evidence") if isinstance(stage.get("evidence"), dict) else {}
            name = str(stage.get("name") or f"stage-{index}")
            self.tree.insert(
                "",
                tk.END,
                iid=f"prompt-{index}",
                values=(
                    str(stage.get("status") or ""),
                    str(stage.get("durationMs") or evidence.get("durationMs") or ""),
                    str(stage.get("message") or name),
                    self._short_evidence(evidence),
                ),
            )
        artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
        self._log(json.dumps({"traceId": self.trace_id, "result": result, "summary": report.get("summary"), "reportPath": artifacts.get("reportPath")}, ensure_ascii=True, indent=2))

    def _render_batch_event(self, event: dict[str, object]) -> None:
        event_type = str(event.get("event") or "")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if event_type == "batch_started":
            self.batch_id = str(event.get("batchId") or self.batch_id)
            total = payload.get("totalCases")
            suite = self._selected_suite_metadata() or {}
            self.status.set(f"batchId={self.batch_id} running")
            self.batch_status.set(f"running 0/{total}")
            self._log(json.dumps({"batchId": self.batch_id, "event": event_type, "totalCases": total, "suiteId": suite.get("suiteId")}, ensure_ascii=True))
            return
        if event_type == "case_started":
            case_id = str(payload.get("id") or "")
            self.active_case_id = case_id
            self.active_project_slug = str(payload.get("projectSlug") or "")
            self.active_session_id = ""
            self.trace_id = str(payload.get("traceId") or self.trace_id)
            self._upsert_case_row(payload)
            self.status.set(f"batchId={self.batch_id} case={case_id} running traceId={self.trace_id}")
            self.batch_status.set(f"running case {payload.get('index')}/{self._tree_case_count()}")
            return
        if event_type == "case_finished":
            case_id = str(payload.get("id") or "")
            self.trace_id = str(payload.get("traceId") or self.trace_id)
            if case_id == self.active_case_id:
                self.active_case_id = ""
                self.active_project_slug = ""
                self.active_session_id = ""
            self._upsert_case_row(payload)
            self.status.set(f"batchId={self.batch_id} case={case_id} status={payload.get('status')} result={payload.get('result')}")
            self.batch_status.set(f"finished case {payload.get('index')}/{self._tree_case_count()}: {payload.get('status')}")
            self._log(json.dumps({"caseId": case_id, "status": payload.get("status"), "traceId": payload.get("traceId"), "reportPath": payload.get("reportPath")}, ensure_ascii=True))
            return
        if event_type in {"batch_paused", "batch_resumed", "batch_stopped", "batch_paused_infrastructure", "batch_paused_cleanup_failed", "batch_reset_requested"}:
            self.batch_status.set(event_type)
            self._log(json.dumps({"batchId": self.batch_id, "event": event_type, "payload": payload}, ensure_ascii=True))

    def _render_reset_done(self, payload: dict[str, object]) -> None:
        session_id = str(payload.get("sessionId") or "")
        stop_response = payload.get("stopResponse") if isinstance(payload.get("stopResponse"), dict) else {}
        if session_id:
            self.active_session_id = session_id
            self.batch_status.set(f"reset sent stop for session {session_id}")
            self._log(json.dumps({"reset": "backend_stop_requested", "sessionId": session_id, "ok": stop_response.get("ok"), "error": stop_response.get("error")}, ensure_ascii=True))
        else:
            self.batch_status.set("reset requested; no active backend session found")
            self._log(json.dumps({"reset": "no_active_backend_session_found", "projectSlug": payload.get("projectSlug")}, ensure_ascii=True))

    def _render_batch_done(self, summary: dict[str, object]) -> None:
        status = str(summary.get("status") or "unknown")
        self.status.set(f"batchId={self.batch_id} status={status}")
        self.batch_status.set(
            f"{status}: completed={summary.get('completed')} failed={summary.get('failed')} blocked={summary.get('blocked')} timeout={summary.get('timeout')} infra={summary.get('infrastructureFailed')}"
        )
        artifacts = summary.get("artifacts") if isinstance(summary.get("artifacts"), dict) else {}
        self._log(json.dumps({"batchId": self.batch_id, "status": status, "summaryPath": artifacts.get("summaryPath"), "statePath": artifacts.get("statePath")}, ensure_ascii=True, indent=2))

    def _upsert_case_row(self, case: dict[str, object]) -> None:
        case_id = str(case.get("id") or f"case-{case.get('index')}")
        status = str(case.get("status") or "pending")
        duration = case.get("durationSeconds")
        latency = "" if duration in (None, "") else f"{duration}s"
        message = f"{case.get('index')}/{self._tree_case_count()} {case.get('title') or case_id}"
        evidence = self._short_case_evidence(case)
        values = (status, latency, message, evidence)
        if self.tree.exists(case_id):
            self.tree.item(case_id, values=values)
            self.tree.see(case_id)
        else:
            self.tree.insert("", tk.END, iid=case_id, values=values)

    def _short_case_evidence(self, case: dict[str, object]) -> str:
        keys = []
        for key in ("traceId", "projectSlug", "reportPath", "result", "error"):
            value = case.get(key)
            if value not in (None, ""):
                keys.append(f"{key}={value}")
        return " | ".join(keys)

    def _tree_case_count(self) -> int:
        return len(self.tree.get_children()) or 0

    def _short_evidence(self, evidence: dict[str, object]) -> str:
        keys = []
        for key in ("path", "evidencePath", "statusCode", "taskId", "reportPath", "nestedReportPath", "runtimeAction", "durationMs"):
            if key in evidence and evidence[key] not in (None, ""):
                keys.append(f"{key}={evidence[key]}")
        return " | ".join(keys)

    def _log(self, message: str) -> None:
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)


def main() -> None:
    root = tk.Tk()
    CircuitProbeClient(root)
    root.mainloop()


if __name__ == "__main__":
    main()
