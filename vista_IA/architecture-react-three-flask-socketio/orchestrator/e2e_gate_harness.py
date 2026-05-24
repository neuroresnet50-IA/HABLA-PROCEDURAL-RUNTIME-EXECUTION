"""End-to-end gate sentinel for one existing workspace project.

The harness treats each project gate as a node with explicit entry, timeout,
exit, and persisted evidence. It does not create projects. Mutating gates are
opt-in through --apply-lace-gate.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PROJECT = "sesion-20260518014728-jeego-en-3d"
DEFAULT_BASE_URL = "http://127.0.0.1:5001"
REPORT_ROOT = Path("runtime") / "e2e_gate_harness"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def truncate(value: str, limit: int = 4000) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 40] + "\n...<truncated>...\n" + value[-20:]


@dataclass
class NodeResult:
    name: str
    command: list[str]
    entered_at: str
    exited_at: str
    duration_seconds: float
    timeout_seconds: int
    exit_code: int | None
    ok: bool
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "enteredAt": self.entered_at,
            "exitedAt": self.exited_at,
            "durationSeconds": self.duration_seconds,
            "timeoutSeconds": self.timeout_seconds,
            "exitCode": self.exit_code,
            "ok": self.ok,
            "timedOut": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "evidence": self.evidence,
        }


def run_binary_node(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    ok_exit_codes: set[int] | None = None,
    evidence_from_stdout: bool = False,
) -> NodeResult:
    allowed_codes = ok_exit_codes or {0}
    entered = utc_now()
    started = time.monotonic()
    process: subprocess.Popen[str] | None = None
    stdout = ""
    stderr = ""
    exit_code: int | None = None
    timed_out = False
    error = ""
    evidence: dict[str, Any] = {}
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            error = "timeout_killed_process_group"
    except FileNotFoundError as exc:
        exit_code = 127
        error = str(exc)
    except Exception as exc:  # pragma: no cover - defensive CLI reporting.
        exit_code = 1
        error = f"{type(exc).__name__}: {exc}"

    if evidence_from_stdout and stdout.strip():
        try:
            evidence = json.loads(stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            evidence = {"rawLastLine": stdout.strip().splitlines()[-1]}

    ok = (exit_code in allowed_codes) and not timed_out and not error
    return NodeResult(
        name=name,
        command=command,
        entered_at=entered,
        exited_at=utc_now(),
        duration_seconds=round(time.monotonic() - started, 6),
        timeout_seconds=timeout_seconds,
        exit_code=exit_code,
        ok=ok,
        timed_out=timed_out,
        stdout=truncate(stdout),
        stderr=truncate(stderr),
        error=error,
        evidence=evidence,
    )


def python_lace_status_command(project: str, required_cycles: int) -> list[str]:
    code = f"""
from pathlib import Path
import json
import sys
sys.path.insert(0, 'backend')
import agent_runtime as ar
p = Path('workspace/projects/{project}/LACE_LOG.md')
validated = ar.validate_lace_log(p, {required_cycles})
status = ar.lace_closure_status(p, {required_cycles})
print(json.dumps({{'validate_lace_log': validated, 'lace_closure_status': status}}, ensure_ascii=True))
raise SystemExit(0 if validated[0] == {required_cycles} and status[0] else 1)
"""
    return [sys.executable, "-B", "-c", code]


def python_lace_gate_command(project: str) -> list[str]:
    code = f"""
from pathlib import Path
import json
import sys
sys.path.insert(0, 'backend')
from agent_runtime import AgentRuntime
root = Path.cwd()
project = root / 'workspace' / 'projects' / '{project}'
visual_events = []
runtime = AgentRuntime(
    app_root=root,
    workspace_root=root / 'workspace',
    projects_root=root / 'workspace' / 'projects',
    codex_cmd=sys.executable,
    prompt_converter=lambda _requirement: {{'available': True, 'prompt': 'E2E_GATE_HARNESS', 'state': {{'safeToAnswer': True, 'blocked': False}}}},
    graph_provider=lambda: {{'nodes': [], 'edges': []}},
    graph_sync=lambda _force: {{'nodes': [], 'edges': []}},
    terminal_emitter=lambda _payload: None,
    session_emitter=lambda _payload: None,
    visual_event_handler=visual_events.append,
    reviewer_event_handler=lambda _payload: None,
    lace_policy_source=root / 'LACE.md',
)
result = runtime._apply_lace_closure_gate(
    runtime_dir=project / 'runtime',
    workspace=project,
    runtime_mode='long-run',
    session_id=None,
    allow_enqueue=True,
)
summary = {{
    'status': result.get('status'),
    'completed_cycles': result.get('completed_cycles'),
    'missing_cycles': result.get('missing_cycles'),
    'completed_cycle_numbers': result.get('completed_cycle_numbers'),
    'log_valid_cycle_numbers': result.get('log_valid_cycle_numbers'),
    'doc_valid_cycle_numbers': result.get('doc_valid_cycle_numbers'),
    'checkpoint': result.get('checkpoint'),
}}
print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
raise SystemExit(0 if summary['status'] == 'clear' and summary['completed_cycles'] == 10 and summary['missing_cycles'] == [] else 1)
"""
    return [sys.executable, "-B", "-c", code]


def python_state_command(project: str) -> list[str]:
    code = f"""
from pathlib import Path
import json
project = Path('workspace/projects/{project}')
state = json.loads((project / 'runtime' / 'project_state.json').read_text(encoding='utf-8'))
queue_payload = json.loads((project / 'runtime' / 'task_queue.json').read_text(encoding='utf-8'))
tasks = queue_payload.get('tasks') if isinstance(queue_payload, dict) else queue_payload
counts = {{}}
for task in tasks or []:
    status = str(task.get('status'))
    counts[status] = counts.get(status, 0) + 1
blocked_file = project / 'runtime' / 'checkpoints' / 'lace-closure-gate-blocked.json'
completed_file = project / 'runtime' / 'checkpoints' / 'lace-closure-gate-completed.json'
summary = {{
    'status': state.get('status'),
    'current_task_id': state.get('current_task_id'),
    'blocked_tasks': state.get('blocked_tasks'),
    'failed_tasks': state.get('failed_tasks'),
    'task_status_counts': counts,
    'blocked_checkpoint_exists': blocked_file.exists(),
    'completed_checkpoint_exists': completed_file.exists(),
}}
print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
raise SystemExit(0 if summary['status'] == 'completed' and summary['blocked_tasks'] == [] and summary['failed_tasks'] == [] and not summary['blocked_checkpoint_exists'] and summary['completed_checkpoint_exists'] else 1)
"""
    return [sys.executable, "-B", "-c", code]


def python_scanner_artifact_command(project: str) -> list[str]:
    code = f"""
from pathlib import Path
import json
project = Path('workspace/projects/{project}')
report = json.loads((project / 'runtime' / 'artifacts' / 'final_code_scanner_report.json').read_text(encoding='utf-8'))
validation = report.get('validation') or {{}}
scanner = report.get('scanner') or {{}}
summary = {{
    'validation_passed': validation.get('passed'),
    'blockers': validation.get('blockers'),
    'visual_playback': scanner.get('visual_playback'),
    'scrolls_to_last_line': scanner.get('scrolls_to_last_line'),
    'summary': report.get('summary'),
}}
print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
raise SystemExit(0 if summary['validation_passed'] is True and summary['blockers'] == [] and summary['visual_playback'] == 'magnifier_line_by_line_to_last_line' and summary['scrolls_to_last_line'] is True else 1)
"""
    return [sys.executable, "-B", "-c", code]


def python_integrity_artifact_command(project: str) -> list[str]:
    code = f"""
from pathlib import Path
import json
project = Path('workspace/projects/{project}')
report = json.loads((project / 'runtime' / 'artifacts' / 'file_integrity_report.json').read_text(encoding='utf-8'))
validation = report.get('validation') or {{}}
summary = report.get('summary') or {{}}
payload = {{
    'validation_passed': validation.get('passed'),
    'blockers': validation.get('blockers'),
    'totalFindings': summary.get('totalFindings'),
    'modifiedFiles': summary.get('modifiedFiles'),
    'deletedFiles': summary.get('deletedFiles'),
    'untrackedFiles': summary.get('untrackedFiles'),
}}
print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
raise SystemExit(0 if payload['validation_passed'] is True and payload['blockers'] == [] and payload['totalFindings'] == 0 else 1)
"""
    return [sys.executable, "-B", "-c", code]


def python_findings_artifact_command(project: str) -> list[str]:
    code = f"""
from pathlib import Path
import json
project = Path('workspace/projects/{project}')
report = json.loads((project / 'runtime' / 'artifacts' / 'observer_findings.json').read_text(encoding='utf-8'))
summary = report.get('summary') or {{}}
payload = {{
    'activeFindings': summary.get('activeFindings'),
    'totalFindings': summary.get('totalFindings'),
    'resolvedFindings': summary.get('resolvedFindings'),
    'observationScore': summary.get('observationScore'),
}}
print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
raise SystemExit(0 if payload['activeFindings'] == 0 else 1)
"""
    return [sys.executable, "-B", "-c", code]


def python_sandbox_command(project: str) -> list[str]:
    code = f"""
from pathlib import Path
from urllib.request import Request, urlopen
import json
project = Path('workspace/projects/{project}')
sandbox = json.loads((project / 'runtime' / 'sandbox.json').read_text(encoding='utf-8'))
url = sandbox.get('embedUrl') or sandbox.get('url')
status_code = None
if url:
    request = Request(url, method='HEAD')
    with urlopen(request, timeout=5) as response:
        status_code = int(response.status)
summary = {{
    'running': sandbox.get('running'),
    'ready': sandbox.get('ready'),
    'url': sandbox.get('url'),
    'embedUrl': sandbox.get('embedUrl'),
    'pid': sandbox.get('pid'),
    'statusCode': status_code,
    'healthcheck': sandbox.get('healthcheck'),
}}
print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
raise SystemExit(0 if summary['running'] is True and summary['ready'] is True and url and status_code and 200 <= status_code < 400 else 1)
"""
    return [sys.executable, "-B", "-c", code]


def agent_tools_command(base_url: str, timeout: int, command: str, project: str | None = None) -> list[str]:
    args = [sys.executable, "-B", "orchestrator/agent_tools.py", "--base-url", base_url, "--timeout-seconds", str(timeout), command]
    if project:
        args.append(project)
    return args


def python_cleanup_command() -> list[str]:
    code = """
from pathlib import Path
import json
import shutil
cache = Path('.pytest_cache')
existed = cache.exists()
shutil.rmtree(cache, ignore_errors=True)
print(json.dumps({'pytest_cache_existed': existed, 'pytest_cache_exists_after': cache.exists()}, sort_keys=True))
raise SystemExit(0 if not cache.exists() else 1)
"""
    return [sys.executable, "-B", "-c", code]


def build_cycle_nodes(args: argparse.Namespace) -> list[tuple[str, list[str], int, set[int], bool]]:
    project = args.project
    nodes: list[tuple[str, list[str], int, set[int], bool]] = [
        ("pytest_available", [sys.executable, "-m", "pytest", "--version"], 20, {0}, False),
        ("pytest_lace_unit", [sys.executable, "-B", "-m", "pytest", "backend/test_agent_runtime_lace.py", "-q"], args.pytest_timeout, {0}, False),
        (
            "pytest_lace_control_gate",
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "backend/test_control_plane_visual_bridge.py::ControlPlaneVisualBridgeTest::test_lace_closure_gate_allows_completion_only_with_all_cycles_valid",
                "-q",
            ],
            args.pytest_timeout,
            {0},
            False,
        ),
        ("lace_log_readonly", python_lace_status_command(project, args.required_cycles), 30, {0}, True),
    ]
    if args.apply_lace_gate:
        nodes.append(("lace_gate_apply", python_lace_gate_command(project), 45, {0}, True))
    nodes.extend(
        [
            ("runtime_state_after_gate", python_state_command(project), 20, {0}, True),
            ("backend_health", agent_tools_command(args.base_url, args.http_timeout, "health"), args.http_timeout + 5, {0}, True),
            ("scanner_gate", agent_tools_command(args.base_url, args.scanner_timeout, "scanner", project), args.scanner_timeout + 10, {0}, True),
            ("scanner_artifact_gate", python_scanner_artifact_command(project), 20, {0}, True),
            ("integrity_gate", agent_tools_command(args.base_url, args.scanner_timeout, "integrity", project), args.scanner_timeout + 10, {0}, True),
            ("integrity_artifact_gate", python_integrity_artifact_command(project), 20, {0}, True),
            ("findings_gate", agent_tools_command(args.base_url, args.http_timeout, "findings", project), args.http_timeout + 5, {0}, True),
            ("findings_artifact_gate", python_findings_artifact_command(project), 20, {0}, True),
            ("sandbox_http_gate", python_sandbox_command(project), 20, {0}, True),
            ("no_pytest_process_left", ["pgrep", "-af", "[p]ytest"], 10, {1}, False),
        ]
    )
    return nodes


def run_harness(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.workspace).resolve()
    project_dir = root / "workspace" / "projects" / args.project
    if not project_dir.exists():
        raise SystemExit(f"project_not_found: {project_dir}")
    if not (root / "backend" / "agent_runtime.py").exists():
        raise SystemExit(f"workspace_not_valid: {root}")

    all_nodes: list[dict[str, Any]] = []
    passed = True
    for cycle_number in range(1, args.cycles + 1):
        for name, command, timeout_seconds, ok_codes, parse_json in build_cycle_nodes(args):
            node_name = f"cycle-{cycle_number:03d}:{name}"
            result = run_binary_node(
                node_name,
                command,
                cwd=root,
                timeout_seconds=int(timeout_seconds),
                ok_exit_codes=set(ok_codes),
                evidence_from_stdout=parse_json,
            )
            all_nodes.append(result.as_dict())
            if args.verbose or not result.ok:
                status = "OK" if result.ok else "FAIL"
                print(f"{status} {node_name} {result.duration_seconds}s exit={result.exit_code}")
            if not result.ok:
                passed = False
                if args.fail_fast:
                    break
        if args.fail_fast and not passed:
            break

    if not args.keep_pytest_cache:
        cleanup = run_binary_node(
            "final:pytest_cache_cleanup",
            python_cleanup_command(),
            cwd=root,
            timeout_seconds=10,
            ok_exit_codes={0},
            evidence_from_stdout=True,
        )
        all_nodes.append(cleanup.as_dict())
        if args.verbose or not cleanup.ok:
            status = "OK" if cleanup.ok else "FAIL"
            print(f"{status} final:pytest_cache_cleanup {cleanup.duration_seconds}s exit={cleanup.exit_code}")
        if not cleanup.ok:
            passed = False

    report = {
        "report_type": "e2e_gate_harness",
        "generatedAt": utc_now(),
        "workspace": str(root),
        "project": args.project,
        "baseUrl": args.base_url,
        "cyclesRequested": args.cycles,
        "cyclesCompleted": max(0, len({item["name"].split(":", 1)[0] for item in all_nodes if str(item.get("name") or "").startswith("cycle-")})),
        "applyLaceGate": bool(args.apply_lace_gate),
        "summary": {
            "passed": passed,
            "nodesTotal": len(all_nodes),
            "nodesPassed": sum(1 for item in all_nodes if item.get("ok") is True),
            "nodesFailed": sum(1 for item in all_nodes if item.get("ok") is not True),
            "timedOut": sum(1 for item in all_nodes if item.get("timedOut") is True),
        },
        "nodes": all_nodes,
    }
    if not args.no_report:
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = REPORT_ROOT / f"e2e-gate-harness-{args.project}-{run_id}.json"
        latest_path = REPORT_ROOT / "latest.json"
        report["reportPath"] = str(report_path)
        report["latestPath"] = str(latest_path)
        report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        latest_path.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run fast end-to-end gate pulses for one existing project.")
    parser.add_argument("--workspace", default=".", help="Repo workspace root.")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Existing project slug under workspace/projects.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend base URL for agent_tools gates.")
    parser.add_argument("--cycles", type=int, default=1, help="How many full gate pulses to run.")
    parser.add_argument("--required-cycles", type=int, default=10, help="Required LACE cycle count.")
    parser.add_argument("--pytest-timeout", type=int, default=60, help="Timeout for pytest nodes.")
    parser.add_argument("--http-timeout", type=int, default=45, help="Timeout for lightweight HTTP/backend nodes.")
    parser.add_argument("--scanner-timeout", type=int, default=180, help="Timeout for scanner/integrity nodes.")
    parser.add_argument("--apply-lace-gate", action="store_true", help="Run the mutating LACE closure gate through AgentRuntime.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop at first failed node.")
    parser.add_argument("--no-report", action="store_true", help="Do not persist runtime/e2e_gate_harness JSON report.")
    parser.add_argument("--keep-pytest-cache", action="store_true", help="Leave .pytest_cache in place after the harness run.")
    parser.add_argument("--verbose", action="store_true", help="Print every node entry/exit status.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_harness(args)
    print(
        json.dumps(
            {
                "ok": report["summary"]["passed"],
                "summary": report["summary"],
                "reportPath": report.get("reportPath"),
                "latestPath": report.get("latestPath"),
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
