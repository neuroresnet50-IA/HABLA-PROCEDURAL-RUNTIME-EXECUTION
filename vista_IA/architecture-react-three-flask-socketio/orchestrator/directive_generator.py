"""Generate and persist per-task operational directives.

Sprint 8 builds directives from the Sprint 7 context and HABLA guide. It does
not integrate with the legacy runtime and does not run benchmarks.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .directive_context import build_directive_context
    from .habla_adapter import build_habla_guide
except ImportError:  # pragma: no cover - supports direct script execution.
    from directive_context import build_directive_context  # type: ignore
    from habla_adapter import build_habla_guide  # type: ignore


class DirectiveGenerationError(RuntimeError):
    """Raised when a worker directive cannot be generated or loaded."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        task_id: str | None = None,
        path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.task_id = task_id
        self.path = path

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "task_id": self.task_id,
            "path": self.path,
        }


def generate_directive(
    context: dict[str, Any],
    habla_guide: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured, auditable directive for the active task."""

    if not isinstance(context, dict):
        raise DirectiveGenerationError("invalid_context", "context must be an object")

    task = context.get("active_task")
    if not isinstance(task, dict) or not task.get("id"):
        raise DirectiveGenerationError(
            "missing_active_task",
            "Cannot generate a directive without an active or ready task.",
        )

    guide = habla_guide if habla_guide is not None else build_habla_guide(context)
    if not isinstance(guide, dict):
        raise DirectiveGenerationError("invalid_habla_guide", "habla_guide must be an object")
    if guide.get("task_id") != task["id"]:
        raise DirectiveGenerationError(
            "task_mismatch",
            "HABLA guide task_id must match context active_task.id.",
            task_id=task["id"],
        )
    if not guide.get("directive_generator_ready"):
        raise DirectiveGenerationError(
            "habla_not_ready",
            "HABLA guide is not ready for directive generation.",
            task_id=task["id"],
        )

    repo_root = _repo_root_from_context(context)
    task_workspace_root = _task_workspace_root_from_context(context, repo_root)
    sprint = _mapping(context.get("sprint"))
    procedure = _mapping(guide.get("procedure"))
    directive_body = _directive_body(context, guide, repo_root, task_workspace_root)
    generated_at = _utc_now()
    source_hash = _source_hash(directive_body)

    directive = {
        "schema_version": 1,
        "directive_type": "worker_operational_directive",
        "generated_at": generated_at,
        "task_id": task["id"],
        "sprint": {
            "number": sprint.get("number"),
            "objective": sprint.get("objective", ""),
        },
        "traceability": {
            "source_hash": source_hash,
            "context_type": context.get("context_type"),
            "runtime_dir": context.get("runtime_dir"),
            "context_degraded": bool(context.get("degraded")),
            "runtime_errors": list(context.get("runtime_errors", [])),
            "checkpoint_key": _mapping(context.get("checkpoint")).get("checkpoint_key"),
            "checkpoint_source": _mapping(context.get("checkpoint")).get("source"),
            "checkpoint_path": _mapping(context.get("checkpoint")).get("path"),
            "policy_file": _mapping(_mapping(context.get("audit")).get("inputs")).get("policy_file"),
            "plan_file": _mapping(_mapping(context.get("audit")).get("inputs")).get("plan_file"),
        },
        "repository": {
            "system_root": str(repo_root),
            "task_workspace_root": str(task_workspace_root),
            "mandatory_root": str(task_workspace_root),
            "forbidden_paths": _forbidden_paths(repo_root, task_workspace_root),
        },
        "task": {
            "id": task["id"],
            "title": task.get("title", ""),
            "goal": task.get("goal", ""),
            "mode": task.get("mode"),
            "timeout_seconds": task.get("timeout_seconds"),
            "max_retries": task.get("max_retries"),
            "checkpoint_key": task.get("checkpoint_key"),
        },
        "operational_directive": directive_body,
        "rendered_instruction": "",
    }
    directive["rendered_instruction"] = render_worker_instruction(directive)
    return directive


def generate_current_directive(
    *,
    repo_root: str | Path | None = None,
    runtime_dir: str | Path | None = None,
    task_id: str | None = None,
    sprint_number: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Build context, adapt HABLA, generate a directive, and optionally persist."""

    if runtime_dir is None:
        raise DirectiveGenerationError(
            "runtime_dir_required",
            "generate_current_directive requires an explicit project runtime_dir.",
        )
    context = build_directive_context(
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        task_id=task_id,
        sprint_number=sprint_number,
    )
    guide = build_habla_guide(context)
    directive = generate_directive(context, guide)
    if persist:
        return persist_directive(directive, directives_dir=Path(runtime_dir).resolve() / "directives")["directive"]
    return directive


def persist_directive(
    directive: dict[str, Any],
    *,
    directives_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Persist JSON and Markdown artifacts under runtime/directives/."""

    _validate_directive(directive)
    root = Path(directive["repository"]["mandatory_root"]).resolve()
    runtime_dir = _runtime_dir_from_directive(directive)
    target_dir = _directives_dir(root, directives_dir, runtime_dir=runtime_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    task_id = directive["task_id"]
    stem = f"{_safe_filename(task_id)}-{_timestamp_for_filename(directive['generated_at'])}-{directive['traceability']['source_hash'][:12]}"
    json_path = target_dir / f"{stem}.json"
    md_path = target_dir / f"{stem}.md"

    persisted = dict(directive)
    persisted["persistence"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _atomic_write_json(json_path, persisted)
    _atomic_write_text(md_path, _render_markdown(persisted))
    return {
        "directive": persisted,
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }


def load_latest_directive(
    task_id: str,
    *,
    repo_root: str | Path | None = None,
    directives_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load the newest persisted JSON directive for task_id."""

    if not isinstance(task_id, str) or not task_id.strip():
        raise DirectiveGenerationError("invalid_task_id", "task_id must be a non-empty string")

    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]
    if directives_dir is None:
        raise DirectiveGenerationError(
            "directives_dir_required",
            "load_latest_directive requires an explicit directives_dir.",
            task_id=task_id,
        )
    target_dir = _directives_dir(root, directives_dir, runtime_dir=Path(directives_dir).resolve().parent)
    pattern = f"{_safe_filename(task_id)}-*.json"
    candidates = sorted(path for path in target_dir.glob(pattern) if path.is_file())
    if not candidates:
        raise DirectiveGenerationError(
            "directive_not_found",
            f"No persisted directive found for task_id: {task_id}",
            task_id=task_id,
            path=str(target_dir),
        )
    path = candidates[-1]
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise DirectiveGenerationError(
            "invalid_directive_json",
            f"Invalid directive JSON: {path}: {exc}",
            task_id=task_id,
            path=str(path),
        ) from exc
    _validate_directive(data)
    return data


def render_worker_instruction(directive: dict[str, Any]) -> str:
    """Render a concise human-auditable worker instruction from structured data."""

    _validate_directive_shape(directive)
    operational = _mapping(directive.get("operational_directive"))
    repository = _mapping(directive.get("repository"))
    task = _mapping(directive.get("task"))
    sprint = _mapping(directive.get("sprint"))

    lines = [
        f"Task: {task.get('id')} - {task.get('title')}",
        f"System root: {repository.get('system_root') or repository.get('mandatory_root')}",
        f"Task workspace root: {repository.get('task_workspace_root') or repository.get('mandatory_root')}",
        f"Mandatory write root: {repository.get('mandatory_root')}",
        "Forbidden paths:",
        *_bullet_lines(repository.get("forbidden_paths", [])),
        "Control-plane ownership:",
        *_bullet_lines(operational.get("control_plane_guardrails", [])),
        f"Sprint: {sprint.get('number')} - {sprint.get('objective')}",
        f"Goal: {task.get('goal')}",
        *_complexity_lines(operational),
        "Exact deliverables:",
        *_bullet_lines(operational.get("sprint_deliverables", [])),
        "Active restrictions:",
        *_bullet_lines(operational.get("active_restrictions", [])),
        "Required evidence:",
        *_bullet_lines(_mapping(operational.get("required_evidence")).get("expected_files", [])),
        "Expected validation:",
        *_bullet_lines(_mapping(operational.get("expected_validation")).get("validation_commands", [])),
        *_visual_bridge_lines(operational),
        *_lace_habla_lines(operational),
        "Starting checkpoint:",
        f"- {_mapping(operational.get('starting_checkpoint')).get('checkpoint_key') or 'none'}",
        "Known risks or blockers:",
        *_bullet_lines(operational.get("known_risks_or_blockers", [])),
        "Closure criteria:",
        *_bullet_lines(operational.get("closure_criteria", [])),
    ]
    return "\n".join(lines).strip() + "\n"


def _visual_bridge_lines(operational: dict[str, Any]) -> list[str]:
    bridge = _mapping(operational.get("visual_bridge"))
    command = str(bridge.get("command") or "").strip()
    examples = list(bridge.get("required_commands", []))
    lines = [
        "Bridge visual obligatorio:",
        f"- Comando base: `{command}`",
        "- Si existe `VISTA_AGENT_BRIDGE`, usalo como comando base preferente.",
        "- Antes de editar, emite `phase` describiendo que vas a observar o construir.",
        "- Declara nodos del mapa conceptual con `upsert-node` para archivos importantes.",
        "- Conecta nodos relacionados con `connect-nodes`.",
        "- Enfoca el archivo activo con `focus-node`.",
        "- Declara pasos de flujo con `upsert-step` y enlazalos con `connect-steps`.",
        "- Despues de escribir o modificar cada archivo real, ejecuta `sync-file` inmediatamente.",
        "- No declares progreso visual si no hay evento real del bridge o evidencia real en disco.",
        "- Ejemplos obligatorios:",
    ]
    lines.extend(f"  - `{item}`" for item in examples)
    return lines


def _lace_habla_lines(operational: dict[str, Any]) -> list[str]:
    lace = _mapping(operational.get("lace"))
    habla = _mapping(operational.get("habla"))
    lines = [
        "HABLA BASIC y LACE:",
        f"- HABLA guide: {habla.get('guide_type') or 'available through structured directive context'}",
    ]
    if lace.get("available"):
        lines.extend(
            [
                f"- LACE policy: {lace.get('policy_path')}",
                f"- LACE log: {lace.get('log_path')}",
                f"- Ciclos LACE requeridos: {lace.get('required_cycles') or 'desconocido'}",
                "- LACE es disciplina de sesion/control-plane, no una tarea monolitica.",
                "- No ejecutes todos los ciclos LACE dentro de una sola tarea de worker.",
                "- Este worker solo puede actualizar el ciclo LACE correspondiente a la tarea acotada que esta ejecutando.",
                "- Mantén LACE_LOG.md alineado con evidencia real y sincronizalo con `sync-file` cuando cambie.",
                "- No marques progreso LACE sin cambios reales en LACE_LOG.md o archivos de producto.",
                "- Si faltan ciclos al cierre, no extiendas silenciosamente esta tarea: el control plane debe bloquear cierre o encolar tareas LACE pendientes.",
                "- No cierres una sesion long-run si la politica LACE aplicable exige ciclos pendientes.",
            ]
        )
    else:
        lines.append("- LACE no detectado en el workspace de tarea para esta directiva.")
    return lines


def _complexity_lines(operational: dict[str, Any]) -> list[str]:
    estimate = _mapping(operational.get("complexity_estimate"))
    if not estimate:
        return ["Complejidad operativa:", "- Sin estimacion persistida; usar presupuesto de la tarea."]
    required_tools = ", ".join(map(str, estimate.get("required_tools") or [])) or "n/a"
    return [
        "Complejidad operativa:",
        f"- Dificultad: {estimate.get('difficulty_label') or estimate.get('difficulty') or 'desconocida'}",
        f"- Score: {estimate.get('score', 'n/a')} | confianza: {estimate.get('confidence', 'n/a')}",
        f"- Agentes recomendados: {estimate.get('recommended_agents', 'n/a')} de max {estimate.get('max_agents', 'n/a')}",
        f"- Ciclos LACE recomendados: {estimate.get('recommended_lace_cycles', 'n/a')} (min {estimate.get('min_lace_cycles', 'n/a')} / max {estimate.get('max_lace_cycles', 'n/a')})",
        f"- Presupuesto: {estimate.get('max_tasks', 'n/a')} tareas, {estimate.get('timeout_seconds', 'n/a')}s timeout, {estimate.get('max_retries', 'n/a')} retries",
        f"- Herramientas requeridas: {required_tools}",
    ]


def _directive_body(
    context: dict[str, Any],
    guide: dict[str, Any],
    repo_root: Path,
    task_workspace_root: Path,
) -> dict[str, Any]:
    procedure = _mapping(guide.get("procedure"))
    sprint = _mapping(context.get("sprint"))
    task = _mapping(context.get("active_task"))
    sprint_deliverables = list(sprint.get("deliverables", [])) or list(task.get("expected_files", []))
    visual_bridge = _visual_bridge_contract(repo_root, task_workspace_root)
    lace_snapshot = _lace_snapshot(task_workspace_root)
    controlled_scope = dict(procedure.get("alcance_controlado", {}))
    if not controlled_scope.get("sprint_deliverables"):
        controlled_scope["sprint_deliverables"] = sprint_deliverables
    if not controlled_scope.get("sprint_acceptance"):
        controlled_scope["sprint_acceptance"] = [
            "Every expected task file must exist under the task workspace root.",
            "Every validation command must run in the task workspace root and return code 0.",
        ]
    return {
        "current_operational_objective": procedure.get("objetivo_operativo_actual", {}),
        "active_restrictions": list(procedure.get("restricciones_activas", [])),
        "controlled_sprint_scope": controlled_scope,
        "required_evidence": procedure.get("evidencia_requerida", {}),
        "expected_validation": procedure.get("validacion_esperada", {}),
        "starting_checkpoint": procedure.get("checkpoint_de_partida", {}),
        "known_risks_or_blockers": list(procedure.get("riesgos_o_bloqueos_conocidos", [])),
        "closure_criteria": list(procedure.get("criterio_de_cierre", [])),
        "system_root": str(repo_root),
        "task_workspace_root": str(task_workspace_root),
        "mandatory_repo_root": str(task_workspace_root),
        "forbidden_paths": _forbidden_paths(repo_root, task_workspace_root),
        "visual_bridge": visual_bridge,
        "complexity_estimate": _mapping(context.get("complexity_estimate")),
        "control_plane_guardrails": [
            "No edites runtime/project_state.json, runtime/task_queue.json, runtime/task_history.jsonl ni runtime/failures.jsonl.",
            "No edites runtime/checkpoints/, runtime/directives/ ni runtime/logs/.",
            "El worker solo entrega archivos de producto o artefactos declarados; el control plane persiste estado, cola, historial, retries y checkpoints.",
            "No marques una tarea como completada escribiendo archivos internos del runtime; devuelve TaskResult y deja que el control plane valide.",
        ],
        "lace": lace_snapshot,
        "habla": {
            "guide_type": guide.get("guide_type"),
            "task_id": guide.get("task_id"),
            "objective": _mapping(guide.get("objective")),
            "directive_generator_ready": bool(guide.get("directive_generator_ready")),
        },
        "sprint_deliverables": sprint_deliverables,
        "out_of_scope": list(sprint.get("out_of_scope_deliverables", [])),
        "task_expected_files": list(task.get("expected_files", [])),
        "task_validation_commands": list(task.get("validation_commands", [])),
    }


def _visual_bridge_contract(repo_root: Path, task_workspace_root: Path) -> dict[str, Any]:
    bridge_path = (repo_root / "backend" / "vista_agent_bridge.py").resolve()
    command = f"python3 {shlex.quote(str(bridge_path))}"
    expected_files = [
        "frontend/index.html",
        "frontend/app.js",
        "frontend/styles.css",
    ]
    return {
        "bridge_path": str(bridge_path),
        "command": command,
        "system_root": str(repo_root),
        "task_workspace_root": str(task_workspace_root),
        "environment_variables": [
            "VISTA_AGENT_SESSION_ID",
            "VISTA_AGENT_PROJECT_SLUG",
            "VISTA_AGENT_PROJECT_DIR",
            "VISTA_AGENT_EVENT_FILE",
            "VISTA_AGENT_BRIDGE",
        ],
        "required_commands": [
            f"{command} phase --label plan --message \"Preparando la tarea con evidencia visual\"",
            f"{command} upsert-node --path frontend/index.html --layer frontend --layer-label Frontend --language html --description \"Pantalla principal\" --x 220 --y 180",
            f"{command} connect-nodes --from-path frontend/app.js --to-path shared/crm_schema.json --type uses --label \"usa esquema\"",
            f"{command} focus-node --path frontend/app.js",
            f"{command} upsert-step --node-path frontend/app.js --step-id start --type start --label Inicio --x 260 --y 80",
            f"{command} upsert-step --node-path frontend/app.js --step-id render --type process --label \"Renderizar estado\" --x 260 --y 220",
            f"{command} connect-steps --node-path frontend/app.js --from-step start --to-step render",
            f"{command} sync-file --path frontend/app.js --language javascript --description \"Logica sincronizada desde evidencia real\"",
        ],
        "expected_live_artifacts": expected_files,
    }


def _lace_snapshot(task_workspace_root: Path) -> dict[str, Any]:
    policy_path = task_workspace_root / "LACE.md"
    log_path = task_workspace_root / "LACE_LOG.md"
    required_cycles: int | None = None
    log_preview = ""
    if log_path.exists():
        try:
            text = log_path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        match = re.search(r"Regla activa:\s*(\d+)\s+ciclos", text, flags=re.I)
        if match:
            required_cycles = int(match.group(1))
        log_preview = "\n".join(text.splitlines()[:24])
    return {
        "available": policy_path.exists() or log_path.exists(),
        "policy_path": str(policy_path) if policy_path.exists() else None,
        "log_path": str(log_path) if log_path.exists() else None,
        "required_cycles": required_cycles,
        "execution_model": "session_level_control_plane_cycles",
        "worker_guardrails": [
            "do_not_run_all_lace_cycles_inside_one_worker_task",
            "update_only_the_cycle_supported_by_current_task_evidence",
            "do_not_extend_task_timeout_for_missing_lace_cycles",
            "control_plane_blocks_closure_or_enqueues_pending_lace_work",
            "lace_progress_requires_lace_log_or_product_file_evidence",
        ],
        "log_preview": log_preview,
    }


def _render_markdown(directive: dict[str, Any]) -> str:
    return (
        f"# Directive {directive['task_id']}\n\n"
        f"- Generated at: `{directive['generated_at']}`\n"
        f"- Sprint: `{directive['sprint']['number']}`\n"
        f"- Source hash: `{directive['traceability']['source_hash']}`\n"
        f"- Checkpoint: `{directive['traceability'].get('checkpoint_key') or 'none'}`\n\n"
        "## Worker Instruction\n\n"
        "```text\n"
        f"{directive['rendered_instruction']}"
        "```\n"
    )


def _validate_directive(directive: dict[str, Any]) -> None:
    _validate_directive_shape(directive)
    try:
        json.dumps(directive, ensure_ascii=True, sort_keys=True)
    except TypeError as exc:
        raise DirectiveGenerationError("directive_not_json_serializable", str(exc)) from exc


def _validate_directive_shape(directive: dict[str, Any]) -> None:
    if not isinstance(directive, dict):
        raise DirectiveGenerationError("invalid_directive", "directive must be an object")
    for key in ("task_id", "sprint", "traceability", "repository", "task", "operational_directive"):
        if key not in directive:
            raise DirectiveGenerationError("invalid_directive", f"directive missing required key: {key}")
    if not directive.get("task_id"):
        raise DirectiveGenerationError("invalid_directive", "directive.task_id must not be empty")
    repository = _mapping(directive.get("repository"))
    mandatory_root = repository.get("mandatory_root")
    forbidden_paths = repository.get("forbidden_paths")
    if not mandatory_root or not isinstance(forbidden_paths, list):
        raise DirectiveGenerationError("invalid_directive", "directive.repository is incomplete")


def _repo_root_from_context(context: dict[str, Any]) -> Path:
    value = context.get("repo_root")
    if not isinstance(value, str) or not value.strip():
        raise DirectiveGenerationError("missing_repo_root", "context.repo_root is required")
    return Path(value).resolve()


def _task_workspace_root_from_context(context: dict[str, Any], fallback: Path) -> Path:
    value = context.get("task_workspace_root")
    if isinstance(value, str) and value.strip():
        return Path(value).resolve()
    return fallback


def _runtime_dir_from_directive(directive: dict[str, Any]) -> Path:
    value = _mapping(directive.get("traceability")).get("runtime_dir")
    if not isinstance(value, str) or not value.strip():
        raise DirectiveGenerationError(
            "runtime_dir_required",
            "Directive persistence requires traceability.runtime_dir.",
        )
    return Path(value).resolve()


def _directives_dir(root: Path, directives_dir: str | Path | None, *, runtime_dir: Path) -> Path:
    base = (runtime_dir / "directives").resolve()
    target = Path(directives_dir).resolve() if directives_dir is not None else base
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise DirectiveGenerationError(
            "invalid_directives_dir",
            "Directives may only be written under the active runtime/directives/.",
            path=str(target),
        ) from exc
    return target


def _forbidden_paths(repo_root: Path, task_workspace_root: Path | None = None) -> list[str]:
    workspace_projects = repo_root / "workspace" / "projects"
    forbidden = [str(repo_root / "runtime_orquestador_codex_pack")]
    if task_workspace_root is not None:
        try:
            task_workspace_root.resolve().relative_to(workspace_projects.resolve())
        except ValueError:
            forbidden.append(str(workspace_projects))
        else:
            forbidden.append(f"{workspace_projects}/* except {task_workspace_root.resolve()}")
    else:
        forbidden.append(str(workspace_projects))
    return forbidden


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
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


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _source_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_for_filename(value: str) -> str:
    return value.replace("-", "").replace(":", "").replace("Z", "Z")


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    if not safe or safe in {".", ".."}:
        raise DirectiveGenerationError("invalid_filename", f"Unsafe task id for filename: {value}")
    return safe


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bullet_lines(values: Any) -> list[str]:
    if not values:
        return ["- none"]
    return [f"- {item}" for item in values]
