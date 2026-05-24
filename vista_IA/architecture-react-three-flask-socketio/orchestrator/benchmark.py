"""Official benchmark harness and deployment gate for Sprint 10.

The harness exercises the task control plane that was built in Sprints 1-9. It
keeps benchmark workspaces under runtime/benchmarks/ and only approves the gate
when every official benchmark passes with persisted evidence.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from backend.agent_runtime import AgentRuntime
except ImportError as exc:  # pragma: no cover - reported as benchmark failure.
    AgentRuntime = None  # type: ignore[assignment]
    _AGENT_RUNTIME_IMPORT_ERROR: Exception | None = exc
else:
    _AGENT_RUNTIME_IMPORT_ERROR = None

try:
    from .contracts import validate_project_state
    from .planner import create_task
    from .state_store import StateStore
    from .task_queue import TaskQueue, save_queue
except ImportError:  # pragma: no cover - supports direct script execution.
    from contracts import validate_project_state  # type: ignore
    from planner import create_task  # type: ignore
    from state_store import StateStore  # type: ignore
    from task_queue import TaskQueue, save_queue  # type: ignore


OFFICIAL_BENCHMARKS = (
    "smoke-01",
    "crud-ui-02",
    "refactor-mid-03",
    "long-project-04",
    "recovery-05",
)

PASSED = "passed"
FAILED = "failed"


class BenchmarkError(RuntimeError):
    """Raised when the benchmark harness itself is misconfigured."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def run_benchmarks(
    names: list[str] | tuple[str, ...] | None = None,
    *,
    repo_root: str | Path | None = None,
    report_dir: str | Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run a benchmark battery and return a structured deployment report."""

    root = _repo_root(repo_root)
    selected = _selected_benchmarks(names)
    run_id = _new_run_id()
    run_dir = _benchmark_root(root, report_dir) / run_id
    started = time.monotonic()
    started_at = _utc_now()

    results = [
        run_benchmark(
            name,
            repo_root=root,
            report_dir=report_dir,
            run_id=run_id,
            persist=persist,
        )
        for name in selected
    ]
    ended_at = _utc_now()

    report: dict[str, Any] = {
        "schema_version": 1,
        "report_type": "official_benchmark_battery",
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": _elapsed(started),
        "repo_root": str(root),
        "report_dir": str(run_dir),
        "official_benchmarks": list(OFFICIAL_BENCHMARKS),
        "requested_benchmarks": list(selected),
        "results": results,
        "summary": _summary(results),
    }
    report["gate"] = benchmark_gate(report)

    if persist:
        report_path = run_dir / "report.json"
        latest_path = _benchmark_root(root, report_dir) / "latest.json"
        report["report_path"] = str(report_path)
        _atomic_write_json(report_path, report)
        _atomic_write_json(latest_path, report)

    return report


def run_benchmark(
    name: str,
    *,
    repo_root: str | Path | None = None,
    report_dir: str | Path | None = None,
    run_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run one official benchmark and return its structured result."""

    root = _repo_root(repo_root)
    if name not in OFFICIAL_BENCHMARKS:
        raise BenchmarkError("unknown_benchmark", f"Unknown benchmark: {name}")

    benchmark_run_id = run_id or _new_run_id()
    bench_dir = _benchmark_root(root, report_dir) / benchmark_run_id / name
    bench_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    started_at = _utc_now()

    try:
        payload = _BENCHMARK_RUNNERS[name](root, bench_dir)
        checks = list(payload.get("checks", []))
        failures = _failed_checks(checks)
        status = PASSED if not failures else FAILED
        evidence = dict(payload.get("evidence", {}))
        recommendations = list(payload.get("recommendations", []))
    except Exception as exc:  # Benchmarks must report failures, not crash the gate.
        checks = []
        failures = [
            {
                "check": "benchmark_execution",
                "message": f"{type(exc).__name__}: {exc}",
            }
        ]
        status = FAILED
        evidence = {"exception": _exception_payload(exc)}
        recommendations = ["Inspect the benchmark exception and rerun this isolated benchmark."]

    result = {
        "schema_version": 1,
        "name": name,
        "status": status,
        "started_at": started_at,
        "ended_at": _utc_now(),
        "duration_seconds": _elapsed(started),
        "evidence": evidence,
        "checks": checks,
        "failures": failures,
        "recommendations": recommendations or _default_recommendations(status),
    }
    if persist:
        result_path = bench_dir / "result.json"
        result["result_path"] = str(result_path)
        _atomic_write_json(result_path, result)
    return result


def benchmark_gate(
    report_or_path: dict[str, Any] | str | Path,
    *,
    require_all: bool = True,
) -> dict[str, Any]:
    """Return the deployment decision for a benchmark report."""

    report = load_benchmark_report(report_or_path) if isinstance(report_or_path, (str, Path)) else report_or_path
    if not isinstance(report, dict):
        raise BenchmarkError("invalid_report", "benchmark report must be an object")

    results = report.get("results")
    if not isinstance(results, list):
        raise BenchmarkError("invalid_report_results", "benchmark report must contain results list")

    by_name = {
        str(result.get("name")): result
        for result in results
        if isinstance(result, dict) and result.get("name")
    }
    required = list(OFFICIAL_BENCHMARKS) if require_all else sorted(by_name)
    missing = [name for name in required if name not in by_name]
    failed = [
        {
            "name": name,
            "status": str(by_name[name].get("status")),
            "failures": list(by_name[name].get("failures", [])),
        }
        for name in required
        if name in by_name and by_name[name].get("status") != PASSED
    ]
    passed = [
        name
        for name in required
        if name in by_name and by_name[name].get("status") == PASSED
    ]
    approved = not missing and not failed and bool(required)

    return {
        "schema_version": 1,
        "gate_type": "deployment_gate",
        "status": PASSED if approved else FAILED,
        "approved": approved,
        "deployment_allowed": approved,
        "required_benchmarks": required,
        "passed": passed,
        "failed": failed,
        "missing": missing,
        "recommendation": (
            "Deployment gate approved: every required benchmark passed."
            if approved
            else "Deployment blocked: every official benchmark must pass before deploy."
        ),
    }


def load_benchmark_report(
    path: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load a persisted benchmark report, defaulting to runtime/benchmarks/latest.json."""

    report_path = Path(path) if path is not None else _repo_root(repo_root) / "runtime" / "benchmarks" / "latest.json"
    try:
        with report_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise BenchmarkError("report_not_found", f"Benchmark report not found: {report_path}") from exc
    except json.JSONDecodeError as exc:
        raise BenchmarkError("invalid_report_json", f"Invalid benchmark report JSON: {report_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BenchmarkError("invalid_report", "Benchmark report must be a JSON object")
    return data


def _benchmark_smoke(root: Path, bench_dir: Path) -> dict[str, Any]:
    env = _prepare_benchmark_env(root, bench_dir, "smoke-01", mode="smoke")
    task = _task(
        "SMOKE-001",
        "Create smoke evidence",
        "Create one expected smoke evidence file through the control plane.",
        expected_files=["smoke-output.txt"],
        validation_commands=[_exists_command("smoke-output.txt")],
        mode="smoke",
        timeout_seconds=10,
    )
    save_queue([task], env["store"])

    result = env["runtime"].run_control_plane_task_once(
        "smoke benchmark",
        mode="smoke",
        runtime_dir=env["runtime_dir"],
        sprint_number=10,
        workspace=env["workspace"],
        command_builder=_static_command_builder(
            _write_files_command({"smoke-output.txt": "smoke benchmark passed\n"})
        ),
    )
    evidence = _execution_evidence(env, result, expected_files=task["expected_files"])
    checks = [
        _check("status completed", result.get("status") == "completed", result.get("status")),
        _check("validation passed", _validation_passed(result), result.get("task_result")),
        _check("expected file exists", _all_files_exist(env["workspace"], task["expected_files"]), task["expected_files"]),
        _check("directive persisted", _path_exists(result.get("directive_json_path")), result.get("directive_json_path")),
        _check("history persisted", len(env["store"].load_task_history()) == 1, env["store"].load_task_history()),
    ]
    return {"checks": checks, "evidence": evidence}


def _benchmark_crud_ui(root: Path, bench_dir: Path) -> dict[str, Any]:
    env = _prepare_benchmark_env(root, bench_dir, "crud-ui-02", mode="build")
    tasks = [
        _task(
            "CRUD-UI-001",
            "Create HTML shell",
            "Create the first UI artifact.",
            expected_files=["frontend/index.html"],
            validation_commands=[_contains_command("frontend/index.html", "<main")],
            priority=30,
        ),
        _task(
            "CRUD-UI-002",
            "Create UI behavior",
            "Create the second UI artifact after the shell exists.",
            dependencies=["CRUD-UI-001"],
            expected_files=["frontend/app.js"],
            validation_commands=[_contains_command("frontend/app.js", "renderItems")],
            priority=20,
        ),
        _task(
            "CRUD-UI-003",
            "Create UI styles",
            "Create the third UI artifact after behavior exists.",
            dependencies=["CRUD-UI-002"],
            expected_files=["frontend/styles.css"],
            validation_commands=[_contains_command("frontend/styles.css", ".item")],
            priority=10,
        ),
    ]
    save_queue(tasks, env["store"])
    commands = {
        "CRUD-UI-001": _write_files_command({"frontend/index.html": "<main id=\"app\"></main>\n"}),
        "CRUD-UI-002": _write_files_command({"frontend/app.js": "export function renderItems(items) { return items.length; }\n"}),
        "CRUD-UI-003": _write_files_command({"frontend/styles.css": ".item { display: grid; gap: 8px; }\n"}),
    }

    results = [
        env["runtime"].run_control_plane_task_once(
            "crud ui benchmark",
            mode="build",
            runtime_dir=env["runtime_dir"],
            sprint_number=10,
            workspace=env["workspace"],
            command_builder=_task_command_builder(commands),
        )
        for _ in tasks
    ]
    queue_after = TaskQueue(env["store"]).list()
    expected_files = [path for task in tasks for path in task["expected_files"]]
    evidence = _sequence_evidence(env, results, expected_files)
    checks = [
        _check("three task sequence completed", [item.get("status") for item in results] == ["completed", "completed", "completed"], results),
        _check("dependency order respected", [item["task"]["id"] for item in results] == ["CRUD-UI-001", "CRUD-UI-002", "CRUD-UI-003"], results),
        _check("queue persisted completed statuses", all(item["status"] == "completed" for item in queue_after), queue_after),
        _check("all UI files exist", _all_files_exist(env["workspace"], expected_files), expected_files),
        _check("history has three entries", len(env["store"].load_task_history()) == 3, env["store"].load_task_history()),
    ]
    return {"checks": checks, "evidence": evidence}


def _benchmark_refactor_mid(root: Path, bench_dir: Path) -> dict[str, Any]:
    env = _prepare_benchmark_env(root, bench_dir, "refactor-mid-03", mode="medium")
    seed_file = env["workspace"] / "src" / "module.py"
    seed_file.parent.mkdir(parents=True, exist_ok=True)
    seed_file.write_text("def transform(value):\n    return value\n", encoding="utf-8")
    task = _task(
        "REFACTOR-001",
        "Refactor existing module",
        "Modify an existing artifact and validate the new behavior marker.",
        expected_files=["src/module.py"],
        validation_commands=[_contains_command("src/module.py", "return value * 2")],
        mode="medium",
        timeout_seconds=10,
    )
    save_queue([task], env["store"])

    result = env["runtime"].run_control_plane_task_once(
        "refactor benchmark",
        mode="medium",
        runtime_dir=env["runtime_dir"],
        sprint_number=10,
        workspace=env["workspace"],
        command_builder=_static_command_builder(
            _write_files_command({"src/module.py": "def transform(value):\n    return value * 2\n"})
        ),
    )
    task_result = result.get("task_result", {})
    evidence = _execution_evidence(env, result, expected_files=task["expected_files"])
    checks = [
        _check("status completed", result.get("status") == "completed", result.get("status")),
        _check("modified file reported", "src/module.py" in task_result.get("files_modified", []), task_result),
        _check("validation passed", _validation_passed(result), task_result),
        _check("refactored content exists", "return value * 2" in seed_file.read_text(encoding="utf-8"), str(seed_file)),
    ]
    return {"checks": checks, "evidence": evidence}


def _benchmark_long_project(root: Path, bench_dir: Path) -> dict[str, Any]:
    env = _prepare_benchmark_env(root, bench_dir, "long-project-04", mode="long-run")
    tasks = []
    previous_id = None
    commands: dict[str, list[str]] = {}
    expected_files: list[str] = []
    for index in range(1, 6):
        task_id = f"LONG-00{index}"
        path = f"docs/phase-{index}.md"
        tasks.append(
            _task(
                task_id,
                f"Complete long project phase {index}",
                f"Advance long project through isolated phase {index}.",
                dependencies=[previous_id] if previous_id else [],
                expected_files=[path],
                validation_commands=[_contains_command(path, f"phase {index}")],
                priority=60 - index,
                mode="long-run",
                timeout_seconds=10,
            )
        )
        commands[task_id] = _write_files_command({path: f"# phase {index}\ncompleted\n"})
        expected_files.append(path)
        previous_id = task_id
    save_queue(tasks, env["store"])

    results = [
        env["runtime"].run_control_plane_task_once(
            "long project benchmark",
            mode="long-run",
            runtime_dir=env["runtime_dir"],
            sprint_number=10,
            workspace=env["workspace"],
            command_builder=_task_command_builder(commands),
        )
        for _ in tasks
    ]
    queue_after = TaskQueue(env["store"]).list()
    evidence = _sequence_evidence(env, results, expected_files)
    checks = [
        _check("five isolated tasks completed", len(results) == 5 and all(item.get("status") == "completed" for item in results), results),
        _check("chained task order respected", [item["task"]["id"] for item in results] == [task["id"] for task in tasks], results),
        _check("long-run mode preserved", all(item["task"]["mode"] == "long-run" for item in results), results),
        _check("all phase files exist", _all_files_exist(env["workspace"], expected_files), expected_files),
        _check("history has five entries", len(env["store"].load_task_history()) == 5, env["store"].load_task_history()),
        _check("queue persisted completed statuses", all(item["status"] == "completed" for item in queue_after), queue_after),
    ]
    return {"checks": checks, "evidence": evidence}


def _benchmark_recovery(root: Path, bench_dir: Path) -> dict[str, Any]:
    env = _prepare_benchmark_env(root, bench_dir, "recovery-05", mode="build")
    task = _task(
        "RECOVERY-001",
        "Recover failed task through retry",
        "Fail once, persist recovery, retry the same task, then complete it.",
        expected_files=["recovery/output.txt"],
        validation_commands=[_contains_command("recovery/output.txt", "recovered")],
        timeout_seconds=10,
        max_retries=2,
    )
    save_queue([task], env["store"])

    attempts: dict[str, int] = {}

    def command_builder(directive: dict[str, Any]) -> list[str]:
        task_id = _directive_task_id(directive)
        attempts[task_id] = attempts.get(task_id, 0) + 1
        if attempts[task_id] == 1:
            return _failing_command("intentional recovery benchmark failure")
        return _write_files_command({"recovery/output.txt": "recovered after retry\n"})

    first = env["runtime"].run_control_plane_task_once(
        "recovery benchmark",
        mode="build",
        runtime_dir=env["runtime_dir"],
        sprint_number=10,
        workspace=env["workspace"],
        command_builder=command_builder,
    )
    second = env["runtime"].run_control_plane_task_once(
        "recovery benchmark",
        mode="build",
        runtime_dir=env["runtime_dir"],
        sprint_number=10,
        workspace=env["workspace"],
        command_builder=command_builder,
    )
    queue_after = TaskQueue(env["store"]).list()
    failures = env["store"].load_failures()
    evidence = _sequence_evidence(env, [first, second], task["expected_files"])
    evidence["failures_path"] = str(env["store"].failures_path)
    evidence["failure_events"] = failures
    evidence["attempts"] = dict(attempts)
    evidence["retry_decision"] = _latest_failure_decision(failures)
    checks = [
        _check("first run requested retry", first.get("status") == "retry", first),
        _check("failure persisted", len(failures) >= 1 and env["store"].failures_path.exists(), failures),
        _check("retry decision persisted next count", _latest_failure_decision(failures).get("next_retry_count") == 1, failures),
        _check("same task executed twice", attempts.get("RECOVERY-001") == 2, attempts),
        _check("second run completed", second.get("status") == "completed" and _validation_passed(second), second),
        _check("task ended completed in queue", queue_after and queue_after[0]["status"] == "completed", queue_after),
        _check("checkpoint exists", bool(second.get("checkpoint", {}).get("path")) and _path_exists(second.get("checkpoint", {}).get("path")), second.get("checkpoint")),
    ]
    return {"checks": checks, "evidence": evidence}


def _prepare_benchmark_env(root: Path, bench_dir: Path, project_id: str, *, mode: str) -> dict[str, Any]:
    if AgentRuntime is None:
        raise BenchmarkError(
            "agent_runtime_import_failed",
            f"Could not import backend.agent_runtime: {_AGENT_RUNTIME_IMPORT_ERROR}",
        )

    runtime_dir = bench_dir / "runtime"
    workspace = bench_dir / "workspace"
    agent_workspace = bench_dir / "agent-runtime-workspace"
    agent_projects = agent_workspace / "agent-projects"
    for path in (
        runtime_dir / "artifacts",
        runtime_dir / "checkpoints",
        runtime_dir / "logs",
        workspace,
        agent_workspace,
        agent_projects,
    ):
        path.mkdir(parents=True, exist_ok=True)

    store = StateStore(runtime_dir)
    store.save_project_state(_project_state(project_id, mode=mode))
    save_queue([], store)

    runtime = AgentRuntime(
        app_root=root,
        workspace_root=agent_workspace,
        projects_root=agent_projects,
        codex_cmd="codex",
        prompt_converter=None,
        graph_provider=lambda: {},
        graph_sync=lambda force=False: {"ok": True, "force": force},
        terminal_emitter=lambda event: None,
        session_emitter=lambda event: None,
        visual_event_handler=lambda event: None,
    )
    runtime.control_plane_enabled = True
    runtime.control_plane_runtime_dir = runtime_dir
    runtime.control_plane_sprint_number = 10

    return {
        "root": root,
        "bench_dir": bench_dir,
        "runtime_dir": runtime_dir,
        "workspace": workspace,
        "store": store,
        "runtime": runtime,
    }


def _task(
    task_id: str,
    title: str,
    goal: str,
    *,
    expected_files: list[str],
    validation_commands: list[str],
    priority: int = 10,
    dependencies: list[str] | None = None,
    timeout_seconds: int = 10,
    max_retries: int = 2,
    mode: str = "build",
) -> dict[str, Any]:
    return create_task(
        task_id=task_id,
        title=title,
        goal=goal,
        priority=priority,
        dependencies=dependencies or [],
        expected_files=expected_files,
        validation_commands=validation_commands,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        mode=mode,
        checkpoint_key=f"{task_id.lower()}-checkpoint",
    )


def _project_state(project_id: str, *, mode: str) -> dict[str, Any]:
    now = _utc_now()
    return validate_project_state(
        {
            "schema_version": 1,
            "project_id": f"benchmark-{project_id}",
            "status": "initialized",
            "mode": mode,
            "current_task_id": None,
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "checkpoints": [],
            "created_at": now,
            "updated_at": now,
        }
    )


def _static_command_builder(command: list[str]) -> Callable[[dict[str, Any]], list[str]]:
    return lambda directive: list(command)


def _task_command_builder(commands_by_task_id: dict[str, list[str]]) -> Callable[[dict[str, Any]], list[str]]:
    def build(directive: dict[str, Any]) -> list[str]:
        task_id = _directive_task_id(directive)
        try:
            return list(commands_by_task_id[task_id])
        except KeyError as exc:
            raise BenchmarkError("missing_benchmark_command", f"No benchmark command for task: {task_id}") from exc

    return build


def _directive_task_id(directive: dict[str, Any]) -> str:
    task = directive.get("task") if isinstance(directive, dict) else None
    task_id = task.get("id") if isinstance(task, dict) else directive.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise BenchmarkError("directive_missing_task_id", "Directive does not include task id")
    return task_id


def _write_files_command(files: dict[str, str]) -> list[str]:
    script_lines = [
        "from pathlib import Path",
        f"files = {files!r}",
        "for name, content in files.items():",
        "    path = Path(name)",
        "    path.parent.mkdir(parents=True, exist_ok=True)",
        "    path.write_text(content, encoding='utf-8')",
    ]
    return [sys.executable, "-B", "-c", "\n".join(script_lines)]


def _failing_command(message: str) -> list[str]:
    script = f"import sys\nsys.stderr.write({message!r} + '\\n')\nsys.exit(7)"
    return [sys.executable, "-B", "-c", script]


def _exists_command(relative_path: str) -> str:
    return "python3 -B -c " + repr(
        "from pathlib import Path; "
        f"assert Path({relative_path!r}).is_file(), {relative_path!r}"
    )


def _contains_command(relative_path: str, marker: str) -> str:
    return "python3 -B -c " + repr(
        "from pathlib import Path; "
        f"text=Path({relative_path!r}).read_text(encoding='utf-8'); "
        f"assert {marker!r} in text, {marker!r}"
    )


def _execution_evidence(env: dict[str, Any], result: dict[str, Any], *, expected_files: list[str]) -> dict[str, Any]:
    return {
        "benchmark_dir": str(env["bench_dir"]),
        "runtime_dir": str(env["runtime_dir"]),
        "workspace": str(env["workspace"]),
        "project_state_path": str(env["store"].project_state_path),
        "task_queue_path": str(env["store"].task_queue_path),
        "task_history_path": str(env["store"].task_history_path),
        "directive_json_path": result.get("directive_json_path"),
        "directive_markdown_path": result.get("directive_markdown_path"),
        "checkpoint": result.get("checkpoint"),
        "expected_files": _file_evidence(env["workspace"], expected_files),
        "task_result": result.get("task_result"),
        "validation": result.get("validation", {}).get("validation"),
    }


def _sequence_evidence(env: dict[str, Any], results: list[dict[str, Any]], expected_files: list[str]) -> dict[str, Any]:
    return {
        "benchmark_dir": str(env["bench_dir"]),
        "runtime_dir": str(env["runtime_dir"]),
        "workspace": str(env["workspace"]),
        "project_state_path": str(env["store"].project_state_path),
        "task_queue_path": str(env["store"].task_queue_path),
        "task_history_path": str(env["store"].task_history_path),
        "checkpoints_dir": str(env["store"].checkpoints_dir),
        "directive_json_paths": [item.get("directive_json_path") for item in results],
        "expected_files": _file_evidence(env["workspace"], expected_files),
        "task_statuses": [
            {"task_id": item.get("task", {}).get("id"), "status": item.get("status")}
            for item in results
        ],
        "history_count": len(env["store"].load_task_history()),
        "queue": TaskQueue(env["store"]).list(),
    }


def _file_evidence(workspace: Path, expected_files: list[str]) -> list[dict[str, Any]]:
    records = []
    for relative_path in expected_files:
        path = (workspace / relative_path).resolve()
        records.append(
            {
                "path": relative_path,
                "absolute_path": str(path),
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() and path.is_file() else None,
            }
        )
    return records


def _validation_passed(result: dict[str, Any]) -> bool:
    task_result = result.get("task_result")
    return bool(
        isinstance(task_result, dict)
        and task_result.get("completed") is True
        and task_result.get("validation_passed") is True
        and not task_result.get("blockers")
    )


def _all_files_exist(workspace: Path, expected_files: list[str]) -> bool:
    return all((workspace / relative_path).is_file() for relative_path in expected_files)


def _path_exists(value: Any) -> bool:
    return isinstance(value, str) and Path(value).exists()


def _latest_failure_decision(failures: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(failures):
        failure = event.get("failure") if isinstance(event, dict) else None
        if isinstance(failure, dict) and isinstance(failure.get("decision"), dict):
            return dict(failure["decision"])
    return {}


def _check(name: str, passed: bool, details: Any = None) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "details": _json_safe(details),
    }


def _failed_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "check": str(check.get("name")),
            "message": "Benchmark check failed.",
            "details": check.get("details"),
        }
        for check in checks
        if not check.get("passed")
    ]


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [result["name"] for result in results if result.get("status") == PASSED]
    failed = [result["name"] for result in results if result.get("status") != PASSED]
    return {
        "total": len(results),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "passed": passed,
        "failed": failed,
    }


def _selected_benchmarks(names: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    selected = tuple(names) if names is not None else OFFICIAL_BENCHMARKS
    if not selected:
        raise BenchmarkError("empty_benchmark_selection", "At least one benchmark must be selected")
    unknown = [name for name in selected if name not in OFFICIAL_BENCHMARKS]
    if unknown:
        raise BenchmarkError("unknown_benchmark", "Unknown benchmark(s): " + ", ".join(unknown))
    return selected


def _default_recommendations(status: str) -> list[str]:
    if status == PASSED:
        return ["Keep this benchmark in the deployment gate."]
    return ["Fix failed checks before allowing deployment."]


def _exception_payload(exc: Exception) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "code": getattr(exc, "code", None),
    }


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return repr(value)
    return value


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
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


def _benchmark_root(root: Path, report_dir: str | Path | None) -> Path:
    if report_dir is None:
        path = root / "runtime" / "benchmarks"
    else:
        candidate = Path(report_dir)
        path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    _assert_under_repo(root, path)
    return path


def _repo_root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]


def _assert_under_repo(root: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise BenchmarkError("path_outside_repo", f"Benchmark path is outside repo: {path}") from exc


def _new_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _elapsed(started: float) -> float:
    return round(time.monotonic() - started, 6)


_BENCHMARK_RUNNERS: dict[str, Callable[[Path, Path], dict[str, Any]]] = {
    "smoke-01": _benchmark_smoke,
    "crud-ui-02": _benchmark_crud_ui,
    "refactor-mid-03": _benchmark_refactor_mid,
    "long-project-04": _benchmark_long_project,
    "recovery-05": _benchmark_recovery,
}


def main(argv: list[str] | None = None) -> int:
    selected = argv if argv is not None else sys.argv[1:]
    report = run_benchmarks(selected or None)
    print(json.dumps({"report_path": report.get("report_path"), "gate": report["gate"]}, ensure_ascii=True, sort_keys=True))
    return 0 if report["gate"]["approved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
