"""Real end-to-end validation runs for the task control plane.

This module is intentionally separate from orchestrator.benchmark. It executes
controlled real runs through the new runtime path, persists evidence under
runtime/real_runs/, and writes an auditable diagnosis under docs/real_validation/.
The worker commands are deterministic local processes so the result validates
the control plane and worker boundary without relying on model availability.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from backend.agent_runtime import AgentRuntime
except ImportError as exc:  # pragma: no cover - reported as blocked validation.
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


REAL_SCENARIOS = ("short-real", "medium-real", "recovery-real")
PASSED = "passed_real"
FAILED = "failed_real"
BLOCKED = "blocked_environment"


class RealValidationError(RuntimeError):
    """Raised when the validation environment cannot run a scenario."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def run_real_validations(
    names: list[str] | tuple[str, ...] | None = None,
    *,
    repo_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    docs_dir: str | Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run all requested real scenarios and return the final diagnosis report."""

    root = _repo_root(repo_root)
    selected = _selected_scenarios(names)
    run_id = _new_run_id()
    run_dir = _output_root(root, output_dir) / run_id
    _assert_allowed_path(root, run_dir)
    started = time.monotonic()

    scenarios = [
        run_real_scenario(
            name,
            repo_root=root,
            output_dir=output_dir,
            run_id=run_id,
            persist=persist,
        )
        for name in selected
    ]
    report: dict[str, Any] = {
        "schema_version": 1,
        "report_type": "real_control_plane_validation",
        "run_id": run_id,
        "started_at": scenarios[0]["started_at"] if scenarios else _utc_now(),
        "ended_at": _utc_now(),
        "duration_seconds": _elapsed(started),
        "repo_root": str(root),
        "run_dir": str(run_dir),
        "requested_scenarios": list(selected),
        "scenario_results": scenarios,
        "summary": _summary(scenarios),
        "validation_scope": {
            "classification": "real_control_plane_local_worker",
            "what_is_real": [
                "persistent task queue and project state",
                "directive context loaded from policy, plan, runtime state, history, failures, and checkpoints",
                "HABLA-derived operational directive generation",
                "worker process execution per task",
                "validator evidence checks and validation commands",
                "failure recording, retry decision, checkpointing, and continuation",
            ],
            "what_is_not_proven": [
                "autonomous quality of an external Codex model on open-ended product work",
                "browser/UI behavior",
                "multi-hour long-project endurance",
                "concurrent workers or distributed execution",
            ],
        },
    }
    report["final_diagnosis"] = _final_diagnosis(report)

    if persist:
        report_path = run_dir / "report.json"
        latest_path = _output_root(root, output_dir) / "latest.json"
        report["report_path"] = str(report_path)
        _atomic_write_json(report_path, report)
        _atomic_write_json(latest_path, report)
        markdown_paths = _persist_markdown_report(root, docs_dir, report)
        report["markdown_report_path"] = markdown_paths["run_markdown_path"]
        report["latest_markdown_path"] = markdown_paths["latest_markdown_path"]
        _atomic_write_json(report_path, report)
        _atomic_write_json(latest_path, report)

    return report


def run_real_scenario(
    name: str,
    *,
    repo_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run one real validation scenario and persist its scenario result."""

    root = _repo_root(repo_root)
    if name not in REAL_SCENARIOS:
        raise RealValidationError("unknown_scenario", f"Unknown real validation scenario: {name}")

    scenario_run_id = run_id or _new_run_id()
    scenario_dir = _output_root(root, output_dir) / scenario_run_id / name
    _assert_allowed_path(root, scenario_dir)
    scenario_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    started_at = _utc_now()

    try:
        payload = _SCENARIO_RUNNERS[name](root, scenario_dir)
        checks = list(payload.get("checks", []))
        failures = _failed_checks(checks)
        status = PASSED if not failures else FAILED
        evidence = dict(payload.get("evidence", {}))
        limitations = list(payload.get("limitations", []))
        recovery_decisions = list(payload.get("recovery_decisions", []))
        task_executions = list(payload.get("task_executions", []))
    except RealValidationError as exc:
        checks = []
        failures = [exc.to_dict()]
        status = BLOCKED
        evidence = {"error": exc.to_dict(), "scenario_dir": str(scenario_dir)}
        limitations = ["Scenario did not execute because the environment was blocked."]
        recovery_decisions = []
        task_executions = []
    except Exception as exc:  # Real validations must report failures instead of hiding them.
        checks = []
        failures = [_exception_payload(exc)]
        status = FAILED
        evidence = {"exception": _exception_payload(exc), "scenario_dir": str(scenario_dir)}
        limitations = ["Scenario crashed; inspect the exception payload before trusting the result."]
        recovery_decisions = []
        task_executions = []

    result = {
        "schema_version": 1,
        "scenario": name,
        "status": status,
        "started_at": started_at,
        "ended_at": _utc_now(),
        "duration_seconds": _elapsed(started),
        "task_executions": task_executions,
        "recovery_decisions": recovery_decisions,
        "evidence": evidence,
        "checks": checks,
        "failures": failures,
        "limitations": limitations,
        "recommendation": _scenario_recommendation(name, status),
    }
    if persist:
        result_path = scenario_dir / "result.json"
        result["result_path"] = str(result_path)
        _atomic_write_json(result_path, result)
    return result


def load_real_validation_report(
    path: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load a persisted real validation report."""

    report_path = Path(path) if path is not None else _repo_root(repo_root) / "runtime" / "real_runs" / "latest.json"
    try:
        with report_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise RealValidationError("report_not_found", f"Real validation report not found: {report_path}") from exc
    except json.JSONDecodeError as exc:
        raise RealValidationError("invalid_report_json", f"Invalid real validation report JSON: {report_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RealValidationError("invalid_report", "Real validation report must be a JSON object")
    return data


def _scenario_short(root: Path, scenario_dir: Path) -> dict[str, Any]:
    env = _prepare_env(root, scenario_dir, "short-real", mode="build")
    task = _task(
        "REAL-SHORT-001",
        "Create short real validation artifact",
        "Create a small auditable artifact through the full control plane.",
        expected_files=["notes/short_real.md"],
        validation_commands=[_contains_command("notes/short_real.md", "real short validation passed")],
        priority=10,
        mode="build",
    )
    _seed_scenario_control_docs(root, env["workspace"], "short-real", [task])
    save_queue([task], env["store"])

    result = env["runtime"].run_control_plane_task_once(
        "real validation short scenario",
        mode="build",
        runtime_dir=env["runtime_dir"],
        workspace=env["workspace"],
        directive_repo_root=env["workspace"],
        directives_dir=env["directives_dir"],
        command_builder=_static_command_builder(
            _write_files_command(
                {
                    "notes/short_real.md": (
                        "# Short real validation\n\n"
                        "real short validation passed\n"
                        "The worker created this file in an isolated process.\n"
                    )
                }
            )
        ),
    )
    task_executions = [_task_execution_summary(result)]
    checks = [
        _check("task completed", result.get("status") == "completed", result),
        _check("validation passed", _validation_passed(result), result.get("task_result")),
        _check("directive persisted", _path_exists(result.get("directive_json_path")), result.get("directive_json_path")),
        _check("HABLA procedure in directive", _directive_has_procedure(result), result.get("directive")),
        _check("expected artifact exists", _all_files_exist(env["workspace"], task["expected_files"]), task["expected_files"]),
        _check("history persisted", len(env["store"].load_task_history()) == 1, env["store"].load_task_history()),
        _check("checkpoint persisted", _path_exists(result.get("checkpoint", {}).get("path")), result.get("checkpoint")),
        *_alignment_checks(env, [result], task["expected_files"]),
    ]
    return {
        "checks": checks,
        "task_executions": task_executions,
        "evidence": _scenario_evidence(env, [result], task["expected_files"]),
        "limitations": _controlled_limitations(),
    }


def _scenario_medium(root: Path, scenario_dir: Path) -> dict[str, Any]:
    env = _prepare_env(root, scenario_dir, "medium-real", mode="medium")
    tasks = [
        _task(
            "REAL-MED-001",
            "Create domain module",
            "Create a small Python domain module as the first medium task.",
            expected_files=["app/__init__.py", "app/domain.py"],
            validation_commands=[_compile_command("app/domain.py"), _contains_command("app/domain.py", "def normalize_name")],
            priority=30,
            mode="medium",
        ),
        _task(
            "REAL-MED-002",
            "Create domain tests",
            "Create executable tests that depend on the domain module.",
            dependencies=["REAL-MED-001"],
            expected_files=["tests/test_domain.py"],
            validation_commands=[_run_python_file_from_workspace_command("tests/test_domain.py")],
            priority=20,
            mode="medium",
        ),
        _task(
            "REAL-MED-003",
            "Document domain usage",
            "Create usage documentation after code and tests exist.",
            dependencies=["REAL-MED-002"],
            expected_files=["docs/usage.md"],
            validation_commands=[_contains_command("docs/usage.md", "normalize_name")],
            priority=10,
            mode="medium",
        ),
    ]
    _seed_scenario_control_docs(root, env["workspace"], "medium-real", tasks)
    save_queue(tasks, env["store"])
    commands = {
        "REAL-MED-001": _write_files_command(
            {
                "app/__init__.py": "",
                "app/domain.py": (
                    "def normalize_name(value):\n"
                    "    return ' '.join(str(value).strip().split()).title()\n"
                ),
            }
        ),
        "REAL-MED-002": _write_files_command(
            {
                "tests/test_domain.py": (
                    "from app.domain import normalize_name\n\n"
                    "assert normalize_name('  ada   lovelace ') == 'Ada Lovelace'\n"
                    "assert normalize_name('grace hopper') == 'Grace Hopper'\n"
                )
            }
        ),
        "REAL-MED-003": _write_files_command(
            {
                "docs/usage.md": (
                    "# Domain usage\n\n"
                    "Use `normalize_name` before presenting user names.\n"
                )
            }
        ),
    }

    results = [
        env["runtime"].run_control_plane_task_once(
            "real validation medium scenario",
            mode="medium",
            runtime_dir=env["runtime_dir"],
            workspace=env["workspace"],
            directive_repo_root=env["workspace"],
            directives_dir=env["directives_dir"],
            command_builder=_task_command_builder(commands),
        )
        for _ in tasks
    ]
    queue_after = TaskQueue(env["store"]).list()
    expected_files = [path for task in tasks for path in task["expected_files"]]
    task_order = [result.get("task", {}).get("id") for result in results]
    task_executions = [_task_execution_summary(result) for result in results]
    checks = [
        _check("three tasks executed", len(results) == 3, results),
        _check("dependency order respected", task_order == [task["id"] for task in tasks], task_order),
        _check("all tasks completed", all(result.get("status") == "completed" for result in results), results),
        _check("all validations passed", all(_validation_passed(result) for result in results), results),
        _check("queue persisted completed statuses", all(task["status"] == "completed" for task in queue_after), queue_after),
        _check("all expected artifacts exist", _all_files_exist(env["workspace"], expected_files), expected_files),
        _check("history has one event per task", len(env["store"].load_task_history()) == 3, env["store"].load_task_history()),
        _check("directives generated per task", len(_directive_paths(results)) == 3, _directive_paths(results)),
        *_alignment_checks(env, results, expected_files),
    ]
    return {
        "checks": checks,
        "task_executions": task_executions,
        "evidence": _scenario_evidence(env, results, expected_files),
        "limitations": _controlled_limitations(),
    }


def _scenario_recovery(root: Path, scenario_dir: Path) -> dict[str, Any]:
    env = _prepare_env(root, scenario_dir, "recovery-real", mode="build")
    tasks = [
        _task(
            "REAL-RECOVERY-001",
            "Recover after a real failing process",
            "Fail once, persist retry recovery, then create the expected artifact.",
            expected_files=["recovery/recovered.txt"],
            validation_commands=[_contains_command("recovery/recovered.txt", "recovered after real retry")],
            priority=20,
            max_retries=2,
            mode="build",
        ),
        _task(
            "REAL-RECOVERY-002",
            "Continue after recovery",
            "Prove that a dependent task can run after the recovered task completes.",
            dependencies=["REAL-RECOVERY-001"],
            expected_files=["recovery/followup.txt"],
            validation_commands=[_contains_command("recovery/followup.txt", "continued after recovery")],
            priority=10,
            max_retries=1,
            mode="build",
        ),
    ]
    _seed_scenario_control_docs(root, env["workspace"], "recovery-real", tasks)
    save_queue(tasks, env["store"])
    attempts: dict[str, int] = {}

    def command_builder(directive: dict[str, Any]) -> list[str]:
        task_id = _directive_task_id(directive)
        attempts[task_id] = attempts.get(task_id, 0) + 1
        if task_id == "REAL-RECOVERY-001" and attempts[task_id] == 1:
            return _failing_command("intentional real validation failure before retry")
        if task_id == "REAL-RECOVERY-001":
            return _write_files_command({"recovery/recovered.txt": "recovered after real retry\n"})
        if task_id == "REAL-RECOVERY-002":
            return _write_files_command({"recovery/followup.txt": "continued after recovery\n"})
        raise RealValidationError("unexpected_task", f"No recovery command for task: {task_id}")

    first = env["runtime"].run_control_plane_task_once(
        "real validation recovery scenario",
        mode="build",
        runtime_dir=env["runtime_dir"],
        workspace=env["workspace"],
        directive_repo_root=env["workspace"],
        directives_dir=env["directives_dir"],
        command_builder=command_builder,
    )
    second = env["runtime"].run_control_plane_task_once(
        "real validation recovery scenario",
        mode="build",
        runtime_dir=env["runtime_dir"],
        workspace=env["workspace"],
        directive_repo_root=env["workspace"],
        directives_dir=env["directives_dir"],
        command_builder=command_builder,
    )
    third = env["runtime"].run_control_plane_task_once(
        "real validation recovery scenario",
        mode="build",
        runtime_dir=env["runtime_dir"],
        workspace=env["workspace"],
        directive_repo_root=env["workspace"],
        directives_dir=env["directives_dir"],
        command_builder=command_builder,
    )
    results = [first, second, third]
    queue_after = TaskQueue(env["store"]).list()
    failures = env["store"].load_failures()
    recovery_decisions = _recovery_decisions(failures)
    expected_files = [path for task in tasks for path in task["expected_files"]]
    task_executions = [_task_execution_summary(result) for result in results]
    checks = [
        _check("first attempt produced retry", first.get("status") == "retry", first),
        _check("failure persisted", env["store"].failures_path.exists() and len(failures) >= 1, failures),
        _check("retry decision persisted", any(decision.get("action") == "retry" for decision in recovery_decisions), recovery_decisions),
        _check("same task retried", attempts.get("REAL-RECOVERY-001") == 2, attempts),
        _check("recovered task completed", second.get("status") == "completed" and _validation_passed(second), second),
        _check("dependent task continued", third.get("task", {}).get("id") == "REAL-RECOVERY-002" and third.get("status") == "completed", third),
        _check("all final queue tasks completed", all(task["status"] == "completed" for task in queue_after), queue_after),
        _check("all recovery artifacts exist", _all_files_exist(env["workspace"], expected_files), expected_files),
        _check("history records failure and continuation attempts", len(env["store"].load_task_history()) == 3, env["store"].load_task_history()),
        *_alignment_checks(env, results, expected_files),
    ]
    evidence = _scenario_evidence(env, results, expected_files)
    evidence["failures_path"] = str(env["store"].failures_path)
    evidence["failure_events"] = failures
    evidence["attempts"] = dict(attempts)
    evidence["recovery_decisions"] = recovery_decisions
    return {
        "checks": checks,
        "task_executions": task_executions,
        "recovery_decisions": recovery_decisions,
        "evidence": evidence,
        "limitations": _controlled_limitations(),
    }


def _prepare_env(root: Path, scenario_dir: Path, scenario_name: str, *, mode: str) -> dict[str, Any]:
    if AgentRuntime is None:
        raise RealValidationError(
            "agent_runtime_import_failed",
            f"Could not import backend.agent_runtime: {_AGENT_RUNTIME_IMPORT_ERROR}",
        )

    runtime_dir = scenario_dir / "runtime"
    workspace = scenario_dir / "workspace"
    directives_dir = workspace / "runtime" / "directives"
    agent_workspace = scenario_dir / "agent-runtime-workspace"
    agent_projects = agent_workspace / "agent-projects"
    for path in (
        runtime_dir / "artifacts",
        runtime_dir / "checkpoints",
        directives_dir,
        runtime_dir / "logs",
        workspace,
        agent_workspace,
        agent_projects,
    ):
        _assert_allowed_path(root, path)
        path.mkdir(parents=True, exist_ok=True)

    store = StateStore(runtime_dir)
    store.save_project_state(_project_state(scenario_name, mode=mode))
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
    runtime.control_plane_sprint_number = None

    return {
        "root": root,
        "scenario_dir": scenario_dir,
        "runtime_dir": runtime_dir,
        "directives_dir": directives_dir,
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
    priority: int,
    dependencies: list[str] | None = None,
    timeout_seconds: int = 15,
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
        checkpoint_key=None,
    )


def _project_state(project_id: str, *, mode: str) -> dict[str, Any]:
    now = _utc_now()
    return validate_project_state(
        {
            "schema_version": 1,
            "project_id": f"real-validation-{project_id}",
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


def _seed_scenario_control_docs(root: Path, workspace: Path, scenario_name: str, tasks: list[dict[str, Any]]) -> None:
    """Create an honest mini control-plane root for the scenario workspace."""

    _assert_allowed_path(root, workspace)
    source_policy = root / "AGENTS.md"
    target_policy = workspace / "AGENTS.md"
    target_plan = workspace / "PLANS.md"
    target_policy.write_text(source_policy.read_text(encoding="utf-8"), encoding="utf-8")
    target_plan.write_text(_scenario_plan_markdown(scenario_name, tasks), encoding="utf-8")


def _scenario_plan_markdown(scenario_name: str, tasks: list[dict[str, Any]]) -> str:
    deliverables = _unique_strings([path for task in tasks for path in task["expected_files"]])
    deliverable_lines = "\n".join(f"- `{path}`" for path in deliverables)
    acceptance_lines = "\n".join(
        [
            "- each queued task runs through directive context, HABLA guide, worker execution, and validation",
            "- every expected file exists in the scenario workspace",
            "- task_history.jsonl records every task result",
            "- no directive may point to Sprint 10 or orchestrator/benchmark.py for this validation phase",
        ]
    )
    return (
        "# PLANS.md\n\n"
        "## Visi\u00f3n del proyecto\n"
        f"Validate the task control plane in the isolated `{scenario_name}` scenario workspace.\n\n"
        "## Problema actual\n"
        "- real validation must not reuse Sprint 10 benchmark scope\n"
        "- directive root and execution workspace must be the same scenario workspace\n\n"
        "## Nueva tesis operativa\n"
        "A real validation scenario is a small standalone project with its own explicit scope.\n\n"
        "## Resultado esperado\n"
        "- context, directive, worker, validator, recovery, and persistence agree on one workspace\n"
        "- scenario evidence is auditable on disk\n\n"
        "# FASE 1 \u2014 Real validation control-plane scenario\n\n"
        "## Objetivo\n"
        f"Execute `{scenario_name}` without borrowing Sprint 10 deliverables.\n\n"
        "## Alcance\n"
        "- use the persisted scenario runtime\n"
        "- use the scenario workspace as the directive root and execution root\n"
        "- persist directives, history, failures, and checkpoints for audit\n\n"
        "## Criterios de aceptaci\u00f3n\n"
        "- context_degraded is false for directive generation\n"
        "- directive mandatory root equals the scenario workspace\n"
        "- validation commands pass against the scenario workspace\n\n"
        "# Arquitectura de modulos\n\n"
        "## orchestrator/real_validation.py\n"
        "Responsabilidad:\n"
        "- prepare scenario control documents\n"
        "- execute real validation runs\n"
        "- report alignment and scope evidence\n\n"
        "## workers/codex_worker.py\n"
        "Responsabilidad:\n"
        "- execute one bounded task process inside the scenario workspace\n\n"
        "# Sprints\n\n"
        "## Sprint 1\n"
        "Objetivo:\n"
        f"Run the `{scenario_name}` real validation scenario with aligned scope.\n\n"
        "Entregables:\n"
        f"{deliverable_lines}\n\n"
        "Aceptaci\u00f3n:\n"
        f"{acceptance_lines}\n\n"
        "# Benchmarks oficiales\n"
        "- not-applicable-real-validation\n\n"
        "## Regla de despliegue\n"
        "This scenario is not a deployment benchmark; it is an end-to-end real validation run.\n"
    )


def _static_command_builder(command: list[str]) -> Callable[[dict[str, Any]], list[str]]:
    return lambda directive: list(command)


def _task_command_builder(commands_by_task_id: dict[str, list[str]]) -> Callable[[dict[str, Any]], list[str]]:
    def build(directive: dict[str, Any]) -> list[str]:
        task_id = _directive_task_id(directive)
        if task_id not in commands_by_task_id:
            raise RealValidationError("missing_command", f"No command registered for task: {task_id}")
        return list(commands_by_task_id[task_id])

    return build


def _directive_task_id(directive: dict[str, Any]) -> str:
    task = directive.get("task") if isinstance(directive, dict) else None
    task_id = task.get("id") if isinstance(task, dict) else directive.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise RealValidationError("directive_missing_task_id", "Directive does not include task id")
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
    script = f"import sys\nsys.stderr.write({message!r} + '\\n')\nsys.exit(9)"
    return [sys.executable, "-B", "-c", script]


def _python_c_command(script: str) -> str:
    return f"{shlex.quote(sys.executable)} -B -c {shlex.quote(script)}"


def _contains_command(relative_path: str, marker: str) -> str:
    return _python_c_command(
        "from pathlib import Path\n"
        f"text = Path({relative_path!r}).read_text(encoding='utf-8')\n"
        f"assert {marker!r} in text, {marker!r}\n"
    )


def _compile_command(relative_path: str) -> str:
    return f"{shlex.quote(sys.executable)} -B -m py_compile {shlex.quote(relative_path)}"


def _run_python_file_from_workspace_command(relative_path: str) -> str:
    return _python_c_command(
        "import runpy\n"
        f"runpy.run_path({relative_path!r}, run_name='__main__')\n"
    )


def _scenario_evidence(env: dict[str, Any], results: list[dict[str, Any]], expected_files: list[str]) -> dict[str, Any]:
    store: StateStore = env["store"]
    return {
        "scenario_dir": str(env["scenario_dir"]),
        "runtime_dir": str(env["runtime_dir"]),
        "workspace": str(env["workspace"]),
        "scenario_policy_path": str(env["workspace"] / "AGENTS.md"),
        "scenario_plan_path": str(env["workspace"] / "PLANS.md"),
        "project_state_path": str(store.project_state_path),
        "task_queue_path": str(store.task_queue_path),
        "task_history_path": str(store.task_history_path),
        "failures_path": str(store.failures_path) if store.failures_path.exists() else None,
        "checkpoints_dir": str(store.checkpoints_dir),
        "checkpoint_files": [str(path) for path in sorted(store.checkpoints_dir.glob("*.json"))],
        "directive_json_paths": _directive_paths(results),
        "directive_markdown_paths": _directive_paths(results, markdown=True),
        "expected_files": _file_evidence(env["workspace"], expected_files),
        "directive_alignment": _directive_alignment_audit(env, results, expected_files),
        "queue": TaskQueue(store).list(),
        "history_count": len(store.load_task_history()),
    }


def _task_execution_summary(result: dict[str, Any]) -> dict[str, Any]:
    task = result.get("task", {}) if isinstance(result.get("task"), dict) else {}
    task_result = result.get("task_result", {}) if isinstance(result.get("task_result"), dict) else {}
    recovery = result.get("recovery", {}) if isinstance(result.get("recovery"), dict) else {}
    decision = recovery.get("decision", {}) if isinstance(recovery.get("decision"), dict) else {}
    return {
        "task_id": task.get("id"),
        "mode": task.get("mode"),
        "status": result.get("status"),
        "completed": task_result.get("completed"),
        "validation_passed": task_result.get("validation_passed"),
        "blockers": list(task_result.get("blockers", [])) if isinstance(task_result.get("blockers"), list) else [],
        "directive_json_path": result.get("directive_json_path"),
        "checkpoint": result.get("checkpoint"),
        "recovery_action": decision.get("action"),
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


def _directive_paths(results: list[dict[str, Any]], *, markdown: bool = False) -> list[str]:
    key = "directive_markdown_path" if markdown else "directive_json_path"
    return [str(result[key]) for result in results if isinstance(result.get(key), str)]


def _recovery_decisions(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decisions = []
    for event in failures:
        failure = event.get("failure") if isinstance(event, dict) else None
        decision = failure.get("decision") if isinstance(failure, dict) else None
        if isinstance(decision, dict):
            decisions.append(dict(decision))
    return decisions


def _directive_has_procedure(result: dict[str, Any]) -> bool:
    directive = result.get("directive")
    operational = directive.get("operational_directive") if isinstance(directive, dict) else None
    return isinstance(operational, dict) and bool(operational.get("current_operational_objective"))


def _alignment_checks(env: dict[str, Any], results: list[dict[str, Any]], expected_files: list[str]) -> list[dict[str, Any]]:
    audit = _directive_alignment_audit(env, results, expected_files)
    return [
        _check("directive context is not degraded", all(not item["context_degraded"] for item in audit), audit),
        _check("directive root equals scenario workspace", all(item["mandatory_root_matches_workspace"] for item in audit), audit),
        _check("execution workspace equals directive root", all(item["execution_workspace_matches_directive_root"] for item in audit), audit),
        _check("directive evidence resolves under scenario workspace", all(item["evidence_paths_under_workspace"] for item in audit), audit),
        _check("scope is not forced to Sprint 10", all(item["sprint_number"] != 10 for item in audit), audit),
        _check("scope does not declare benchmark deliverable", all(not item["declares_benchmark_deliverable"] for item in audit), audit),
        _check("scope deliverables cover scenario files", all(item["scope_covers_expected_files"] for item in audit), audit),
    ]


def _directive_alignment_audit(
    env: dict[str, Any],
    results: list[dict[str, Any]],
    expected_files: list[str],
) -> list[dict[str, Any]]:
    workspace = Path(env["workspace"]).resolve()
    scenario_expected = set(expected_files)
    audit: list[dict[str, Any]] = []
    for result in results:
        directive = result.get("directive") if isinstance(result.get("directive"), dict) else {}
        traceability = directive.get("traceability") if isinstance(directive.get("traceability"), dict) else {}
        repository = directive.get("repository") if isinstance(directive.get("repository"), dict) else {}
        operational = directive.get("operational_directive") if isinstance(directive.get("operational_directive"), dict) else {}
        sprint = directive.get("sprint") if isinstance(directive.get("sprint"), dict) else {}
        required_evidence = operational.get("required_evidence") if isinstance(operational.get("required_evidence"), dict) else {}
        disk_records = required_evidence.get("disk_records") if isinstance(required_evidence.get("disk_records"), list) else []
        mandatory_root = str(repository.get("mandatory_root") or "")
        execution_workspace = _execution_workspace(result)
        sprint_deliverables = [str(item).strip("`") for item in operational.get("sprint_deliverables", [])]
        audit.append(
            {
                "task_id": result.get("task", {}).get("id") if isinstance(result.get("task"), dict) else None,
                "context_degraded": bool(traceability.get("context_degraded")),
                "runtime_errors": list(traceability.get("runtime_errors", [])) if isinstance(traceability.get("runtime_errors"), list) else [],
                "mandatory_root": mandatory_root,
                "workspace": str(workspace),
                "execution_workspace": execution_workspace,
                "mandatory_root_matches_workspace": _same_path(mandatory_root, workspace),
                "execution_workspace_matches_directive_root": bool(execution_workspace) and _same_path(execution_workspace, mandatory_root),
                "evidence_paths_under_workspace": _records_under_workspace(disk_records, workspace),
                "sprint_number": sprint.get("number"),
                "sprint_objective": sprint.get("objective"),
                "sprint_deliverables": sprint_deliverables,
                "declares_benchmark_deliverable": any(item == "orchestrator/benchmark.py" for item in sprint_deliverables),
                "scope_covers_expected_files": scenario_expected.issubset(set(sprint_deliverables)),
            }
        )
    return audit


def _execution_workspace(result: dict[str, Any]) -> str | None:
    execution_wrapper = result.get("execution") if isinstance(result.get("execution"), dict) else {}
    execution = execution_wrapper.get("execution") if isinstance(execution_wrapper.get("execution"), dict) else {}
    workspace = execution.get("workspace")
    return str(workspace) if isinstance(workspace, str) else None


def _same_path(left: str | Path | None, right: str | Path | None) -> bool:
    if left is None or right is None:
        return False
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:
        return False


def _records_under_workspace(records: list[Any], workspace: Path) -> bool:
    for record in records:
        if not isinstance(record, dict):
            return False
        absolute_path = record.get("absolute_path")
        if not isinstance(absolute_path, str):
            return False
        try:
            Path(absolute_path).resolve().relative_to(workspace)
        except ValueError:
            return False
    return True


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


def _check(name: str, passed: bool, details: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "details": _json_safe(details)}


def _failed_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "check": str(check.get("name")),
            "message": "Real validation check failed.",
            "details": check.get("details"),
        }
        for check in checks
        if not check.get("passed")
    ]


def _summary(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [scenario["scenario"] for scenario in scenarios if scenario.get("status") == PASSED]
    failed = [scenario["scenario"] for scenario in scenarios if scenario.get("status") == FAILED]
    blocked = [scenario["scenario"] for scenario in scenarios if scenario.get("status") == BLOCKED]
    return {
        "total": len(scenarios),
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "passed_count": len(passed),
        "failed_count": len(failed),
        "blocked_count": len(blocked),
        "selected_real_validation_passed": len(passed) == len(scenarios) and not failed and not blocked,
        "minimum_real_validation_passed": len(passed) == len(REAL_SCENARIOS) and not failed and not blocked,
    }


def _final_diagnosis(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    minimum_passed = bool(summary["minimum_real_validation_passed"])
    return {
        "status": "passed_real_minimum" if minimum_passed else "not_passed_real_minimum",
        "short_projects": "ready_for_controlled_real_runs" if "short-real" in summary["passed"] else "not_ready",
        "medium_projects": "ready_for_controlled_real_runs" if "medium-real" in summary["passed"] else "not_ready",
        "recovery": "retry_continuity_validated" if "recovery-real" in summary["passed"] else "not_validated",
        "long_projects": "not_yet_proven_by_this_phase",
        "production_controlled_works": [
            "task preparation from persisted queue",
            "directive generation from policy, plan, runtime state, and HABLA procedure",
            "isolated worker process per task",
            "validation commands and disk evidence checks",
            "retry recovery with persisted failure and continuation",
        ]
        if minimum_passed
        else [],
        "remaining_before_trusting_long_projects": [
            "run a real long project with many more tasks and restarts",
            "exercise actual Codex or another replaceable model worker, not only deterministic local worker commands",
            "add retention and cleanup policy for runtime evidence",
            "validate behavior under process crashes and partial filesystem writes",
            "decide how scenario-specific control documents should map to the main product roadmap for non-test projects",
        ],
        "honest_verdict": (
            "The control plane is usable for controlled short and medium real runs, plus retry recovery. "
            "It is not yet proven for open-ended long projects with an autonomous model worker."
            if minimum_passed
            else "The real validation minimum did not pass; inspect failed or blocked scenarios before trusting the runtime."
        ),
    }


def _scenario_recommendation(name: str, status: str) -> str:
    if status == PASSED:
        return f"{name} passed as a controlled real control-plane run."
    if status == BLOCKED:
        return f"{name} was blocked by the environment; inspect evidence.error."
    return f"{name} failed with real evidence; inspect failures before proceeding."


def _controlled_limitations() -> list[str]:
    return [
        "Worker commands were deterministic local processes, not an external Codex model run.",
        "This validates runtime mechanics and evidence handling, not autonomous code quality.",
        "Each real validation scenario uses a generated PLANS.md inside its workspace as an explicit scenario scope.",
    ]


def _selected_scenarios(names: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    selected = tuple(names) if names is not None else REAL_SCENARIOS
    if not selected:
        raise RealValidationError("empty_selection", "At least one real validation scenario must be selected")
    unknown = [name for name in selected if name not in REAL_SCENARIOS]
    if unknown:
        raise RealValidationError("unknown_scenario", "Unknown real validation scenario(s): " + ", ".join(unknown))
    return selected


def _persist_markdown_report(root: Path, docs_dir: str | Path | None, report: dict[str, Any]) -> dict[str, str]:
    target_dir = _docs_root(root, docs_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    run_path = target_dir / f"{report['run_id']}.md"
    latest_path = target_dir / "latest.md"
    markdown = _render_markdown(report)
    _atomic_write_text(run_path, markdown)
    _atomic_write_text(latest_path, markdown)
    return {"run_markdown_path": str(run_path), "latest_markdown_path": str(latest_path)}


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Real Validation Report",
        "",
        f"- Run id: `{report['run_id']}`",
        f"- Status: `{report['final_diagnosis']['status']}`",
        f"- Repo root: `{report['repo_root']}`",
        f"- Report JSON: `{report.get('report_path', '')}`",
        "",
        "## Scenario Results",
    ]
    for scenario in report["scenario_results"]:
        alignment = scenario.get("evidence", {}).get("directive_alignment", [])
        alignment_clean = bool(alignment) and all(
            not item.get("context_degraded")
            and item.get("mandatory_root_matches_workspace")
            and item.get("execution_workspace_matches_directive_root")
            and item.get("sprint_number") != 10
            and not item.get("declares_benchmark_deliverable")
            for item in alignment
            if isinstance(item, dict)
        )
        sprint_numbers = [item.get("sprint_number") for item in alignment if isinstance(item, dict)]
        lines.extend(
            [
                "",
                f"### {scenario['scenario']}",
                f"- Status: `{scenario['status']}`",
                f"- Result JSON: `{scenario.get('result_path', '')}`",
                f"- Tasks executed: `{len(scenario.get('task_executions', []))}`",
                f"- Recovery decisions: `{[item.get('action') for item in scenario.get('recovery_decisions', [])]}`",
                f"- Failures: `{len(scenario.get('failures', []))}`",
                f"- Directive alignment clean: `{alignment_clean}`",
                f"- Scope sprint numbers: `{sprint_numbers}`",
            ]
        )
    diagnosis = report["final_diagnosis"]
    lines.extend(
        [
            "",
            "## Honest Verdict",
            "",
            diagnosis["honest_verdict"],
            "",
            "## Remaining Risks",
        ]
    )
    lines.extend(f"- {item}" for item in diagnosis["remaining_before_trusting_long_projects"])
    lines.append("")
    return "\n".join(lines)


def _exception_payload(exc: Exception) -> dict[str, Any]:
    return {"type": type(exc).__name__, "message": str(exc), "code": getattr(exc, "code", None)}


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return repr(value)
    return value


def _unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(_json_safe(payload), handle, ensure_ascii=True, indent=2, sort_keys=True)
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


def _atomic_write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _output_root(root: Path, output_dir: str | Path | None) -> Path:
    if output_dir is None:
        path = root / "runtime" / "real_runs"
    else:
        candidate = Path(output_dir)
        path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    _assert_allowed_path(root, path)
    return path


def _docs_root(root: Path, docs_dir: str | Path | None) -> Path:
    if docs_dir is None:
        path = root / "docs" / "real_validation"
    else:
        candidate = Path(docs_dir)
        path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    _assert_allowed_path(root, path)
    return path


def _repo_root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]


def _assert_allowed_path(root: Path, path: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RealValidationError("path_outside_repo", f"Path is outside repo root: {resolved}") from exc
    forbidden = [
        root / "runtime_orquestador_codex_pack",
        root / "workspace" / "projects",
    ]
    for forbidden_path in forbidden:
        try:
            resolved.relative_to(forbidden_path.resolve())
        except ValueError:
            continue
        raise RealValidationError("forbidden_path", f"Refusing to write inside forbidden path: {resolved}")


def _new_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _elapsed(started: float) -> float:
    return round(time.monotonic() - started, 6)


_SCENARIO_RUNNERS: dict[str, Callable[[Path, Path], dict[str, Any]]] = {
    "short-real": _scenario_short,
    "medium-real": _scenario_medium,
    "recovery-real": _scenario_recovery,
}


def main(argv: list[str] | None = None) -> int:
    selected = argv if argv is not None else sys.argv[1:]
    report = run_real_validations(selected or None)
    print(
        json.dumps(
            {
                "report_path": report.get("report_path"),
                "markdown_report_path": report.get("markdown_report_path"),
                "status": report["final_diagnosis"]["status"],
                "summary": report["summary"],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0 if report["summary"]["selected_real_validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
