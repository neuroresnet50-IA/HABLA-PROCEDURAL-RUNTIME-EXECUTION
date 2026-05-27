"""Tkinter client for HABLA CircuitProbe and Prompt Flight Recorder.

The UI is only a client. The backend owns all runtime inspection and writes the
auditable evidence under runtime/continuity_probe/.
"""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:5001"
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
        self.root.geometry("1120x780")
        self.trace_id = ""
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
        self.prompt_mode = tk.StringVar(value="ui_session_rest")
        ttk.Combobox(prompt_controls, textvariable=self.prompt_mode, values=("ui_session_rest", "real_session_guarded", "trace_only", "safe_canary"), width=16, state="readonly").pack(side=tk.LEFT, padx=(6, 14))
        ttk.Button(prompt_controls, text="Run Prompt Flight", command=self.run_prompt_flight).pack(side=tk.LEFT)
        ttk.Button(prompt_controls, text="Clear Prompt", command=lambda: self.prompt_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=(8, 0))
        self.prompt_text = tk.Text(prompt_frame, height=5, wrap=tk.WORD)
        self.prompt_text.pack(fill=tk.X, pady=(8, 0))
        self.prompt_text.insert("1.0", "Crear una tarea real pequeña desde la ruta normal de la UI y medir toda la transaccion interna del servidor.")

        status_frame = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        status_frame.pack(fill=tk.X)
        self.status = tk.StringVar(value="idle")
        ttk.Label(status_frame, textvariable=self.status).pack(anchor=tk.W)

        body = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        table_frame = ttk.Frame(body)
        body.add(table_frame, weight=3)
        self.tree = ttk.Treeview(table_frame, columns=("status", "latency", "message", "evidence"), show="headings", height=18)
        self.tree.heading("status", text="Status")
        self.tree.heading("latency", text="Latency ms")
        self.tree.heading("message", text="Message")
        self.tree.heading("evidence", text="Evidence")
        self.tree.column("status", width=110, anchor=tk.CENTER)
        self.tree.column("latency", width=90, anchor=tk.E)
        self.tree.column("message", width=430)
        self.tree.column("evidence", width=420)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)

        log_frame = ttk.Frame(body)
        body.add(log_frame, weight=1)
        self.log = tk.Text(log_frame, height=8, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
        self._reset_probe_rows()

    def _reset_probe_rows(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for check in CHECK_ORDER:
            self.tree.insert("", tk.END, iid=check, values=("pending", "", check, ""))

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

    def run_prompt_flight(self) -> None:
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showinfo("Prompt Flight", "Write a prompt first.")
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
        self.status.set("running prompt flight...")
        self._log("Running Prompt Flight Recorder via backend")
        threading.Thread(target=self._prompt_flight_worker, args=(payload,), daemon=True).start()

    def refresh_status(self) -> None:
        if not self.trace_id:
            messagebox.showinfo("CircuitProbe", "No traceId yet. Start a probe first.")
            return
        threading.Thread(target=self._status_worker, daemon=True).start()

    def _start_worker(self, payload: dict[str, object]) -> None:
        try:
            response = self._request_json("POST", "/api/continuity-probe/start", payload)
            self.messages.put(("started", response))
        except Exception as exc:
            self.messages.put(("error", exc))

    def _prompt_flight_worker(self, payload: dict[str, object]) -> None:
        try:
            response = self._request_json("POST", "/api/continuity-probe/prompt-flight", payload)
            self.messages.put(("prompt_flight", response))
        except Exception as exc:
            self.messages.put(("error", exc))

    def _status_worker(self) -> None:
        try:
            response = self._request_json("GET", f"/api/continuity-probe/status/{self.trace_id}", None)
            self.messages.put(("status", response))
        except Exception as exc:
            self.messages.put(("error", exc))

    def _request_json(self, method: str, path: str, payload: dict[str, object] | None) -> dict[str, object]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url.get().rstrip("/") + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=160) as response:
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
        self._log(json.dumps({"traceId": self.trace_id, "result": result, "summary": report.get("summary"), "reportPath": report.get("reportPath")}, ensure_ascii=True, indent=2))

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
