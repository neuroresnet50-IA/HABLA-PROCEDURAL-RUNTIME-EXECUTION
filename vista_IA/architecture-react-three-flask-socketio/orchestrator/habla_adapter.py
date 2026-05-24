"""Adapt directive context into a reusable HABLA BASIC procedure.

This module deliberately returns structured data for the future directive
generator. It does not produce the final worker prompt and does not persist
directives.
"""

from __future__ import annotations

from typing import Any


class HablaAdapterError(RuntimeError):
    """Raised when a HABLA guide cannot be built from context."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def build_habla_guide(context: dict[str, Any]) -> dict[str, Any]:
    """Return a stable procedural guide derived from directive context."""

    if not isinstance(context, dict):
        raise HablaAdapterError("invalid_context", "context must be an object")

    task = context.get("active_task") if isinstance(context.get("active_task"), dict) else {}
    sprint = context.get("sprint") if isinstance(context.get("sprint"), dict) else {}
    rules = context.get("rules") if isinstance(context.get("rules"), dict) else {}
    evidence = context.get("evidence") if isinstance(context.get("evidence"), dict) else {}
    checkpoint = context.get("checkpoint") if isinstance(context.get("checkpoint"), dict) else {}

    task_id = task.get("id")
    expected_files = list(task.get("expected_files", []))
    validation_commands = list(task.get("validation_commands", []))
    risks = _collect_risks(context)

    guide = {
        "schema_version": 1,
        "guide_type": "habla_basic_procedure",
        "task_id": task_id,
        "sprint_number": sprint.get("number"),
        "directive_generator_ready": bool(task_id),
        "objective": {
            "operational_goal": task.get("goal") or sprint.get("objective") or "",
            "task_title": task.get("title") or "",
            "sprint_objective": sprint.get("objective") or "",
        },
        "procedure": {
            "objetivo_operativo_actual": {
                "task_id": task_id,
                "goal": task.get("goal") or "",
                "mode": task.get("mode") or context.get("project_state", {}).get("mode"),
                "timeout_seconds": task.get("timeout_seconds"),
            },
            "alcance_controlado": {
                "sprint_deliverables": list(sprint.get("deliverables", [])),
                "sprint_acceptance": list(sprint.get("acceptance", [])),
                "out_of_scope_deliverables": list(sprint.get("out_of_scope_deliverables", [])),
            },
            "restricciones_activas": _unique(list(rules.get("active_constraints", []))),
            "evidencia_requerida": {
                "expected_files": expected_files,
                "evidence_found": list(evidence.get("found", [])),
                "evidence_missing": list(evidence.get("missing", [])),
                "disk_records": list(evidence.get("expected_files", [])),
            },
            "validacion_esperada": {
                "validation_commands": validation_commands,
                "acceptance_criteria": list(sprint.get("acceptance", [])),
                "validation_ran_must_be_recorded": True,
            },
            "checkpoint_de_partida": {
                "checkpoint_key": checkpoint.get("checkpoint_key"),
                "source": checkpoint.get("source"),
                "path": checkpoint.get("path"),
                "available": checkpoint.get("data") is not None,
            },
            "criterio_de_cierre": _closure_criteria(expected_files, validation_commands),
            "riesgos_o_bloqueos_conocidos": risks,
        },
        "directive_generator_inputs": {
            "repo_root": context.get("repo_root"),
            "runtime_dir": context.get("runtime_dir"),
            "task": task,
            "sprint": sprint,
            "policy_rules": rules,
            "evidence": evidence,
            "checkpoint": checkpoint,
            "runtime_errors": list(context.get("runtime_errors", [])),
        },
    }
    return guide


def habla_from_context(context: dict[str, Any]) -> dict[str, Any]:
    """Alias for callers that treat HABLA as an adapter stage."""

    return build_habla_guide(context)


def _closure_criteria(expected_files: list[str], validation_commands: list[str]) -> list[str]:
    criteria = [
        "TaskResult.completed can be true only with real disk evidence.",
        "TaskResult.blockers must be empty before closing the task.",
    ]
    if expected_files:
        criteria.append("Every expected file must exist under the repository root.")
    if validation_commands:
        criteria.append("Every declared validation command must run and return code 0.")
    criteria.append("Validation results must be represented in the task result history.")
    return criteria


def _collect_risks(context: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    task = context.get("active_task") if isinstance(context.get("active_task"), dict) else {}
    evidence = context.get("evidence") if isinstance(context.get("evidence"), dict) else {}
    task_queue = context.get("task_queue") if isinstance(context.get("task_queue"), dict) else {}
    failures = context.get("failures") if isinstance(context.get("failures"), dict) else {}

    if not task:
        risks.append("No active or ready task is available from persisted queue.")
    for error in context.get("runtime_errors", []):
        if isinstance(error, dict):
            risks.append(f"{error.get('component')}: {error.get('message')}")
    for missing in evidence.get("missing", []):
        risks.append(f"Missing required evidence before execution: {missing}")
    for blocker in evidence.get("blockers", []):
        risks.append(str(blocker))
    for blocked in task_queue.get("blocked_tasks", []):
        if isinstance(blocked, dict):
            risks.append(
                f"Blocked task {blocked.get('task_id')} missing dependencies: "
                f"{', '.join(blocked.get('missing_dependencies', []))}"
            )
    for event in failures.get("active_task_events", []):
        reason = _failure_reason(event)
        risks.append(f"Prior failure for active task: {reason}")
    return _unique(risks)


def _failure_reason(event: dict[str, Any]) -> str:
    failure = event.get("failure") if isinstance(event, dict) else None
    if not isinstance(failure, dict):
        return "unknown"
    nested = failure.get("failure")
    if isinstance(nested, dict):
        task_result = nested.get("task_result")
        if isinstance(task_result, dict) and task_result.get("blockers"):
            return "; ".join(str(item) for item in task_result["blockers"])
        for key in ("reason", "message", "cause"):
            if isinstance(nested.get(key), str):
                return nested[key]
    decision = failure.get("decision")
    if isinstance(decision, dict) and isinstance(decision.get("reason"), str):
        return decision["reason"]
    return "recorded failure without explicit reason"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
