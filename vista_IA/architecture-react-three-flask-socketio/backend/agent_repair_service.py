from __future__ import annotations

import os
import shlex
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List

from orchestrator.planner import create_task
from orchestrator.state_store import StateStore
from orchestrator.task_queue import TaskQueue

NowProvider = Callable[[], str]


def normalize_relative_fragment(value: Any) -> str:
    normalized = str(PurePosixPath(os.path.normpath(str(value or ".")))).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    while normalized.startswith("../"):
        normalized = normalized[3:]
    return normalized.lstrip("/")


def suggested_repair_files(relative_path: str, issue: Dict[str, Any]) -> List[str]:
    files = [normalize_relative_fragment(relative_path)]
    code = str(issue.get("code") or issue.get("issueType") or "").strip()
    evidence = issue.get("evidence") if isinstance(issue.get("evidence"), dict) else {}
    module_name = str(evidence.get("module") or evidence.get("moduleName") or "").strip()
    if code in {"python_relative_import_missing", "unresolved_import"} and module_name:
        base = PurePosixPath(normalize_relative_fragment(relative_path)).parent
        try:
            level = int(evidence.get("level") or 1)
        except (TypeError, ValueError):
            level = 1
        parent_parts = list(base.parts)
        if level > 1:
            parent_parts = parent_parts[: max(0, len(parent_parts) - (level - 1))]
        candidate = PurePosixPath(*parent_parts, *module_name.split("."))
        candidate_path = normalize_relative_fragment(f"{candidate.as_posix()}.py")
        if candidate_path not in files:
            files.append(candidate_path)
    return files


def build_agent_repair_requirement(
    *,
    project_slug: str,
    relative_path: str,
    issue: Dict[str, Any],
    extra_instruction: str,
) -> str:
    try:
        line = max(1, int(issue.get("line") or 1))
    except (TypeError, ValueError):
        line = 1
    code = str(issue.get("code") or "visual_issue")
    severity = str(issue.get("severity") or "warning")
    message = str(issue.get("message") or "Hallazgo visual seleccionado desde el editor.")
    hint = str(issue.get("hint") or "").strip()
    repair_files = suggested_repair_files(relative_path, issue)
    validation_files = " ".join(repair_files)
    file_bullets = "\n".join(f"- {path}" for path in repair_files)

    return (
        "MODO REPARACION AGENTICA EN VIVO.\n"
        "Continua el proyecto existente. No crees un proyecto nuevo y no cambies de workspace.\n\n"
        f"Proyecto existente: {project_slug}\n"
        f"Archivo con punto rojo: {relative_path}\n"
        f"Linea reportada: {line}\n"
        f"Severidad: {severity}\n"
        f"Codigo del hallazgo: {code}\n"
        f"Mensaje: {message}\n"
        + (f"Hint: {hint}\n" if hint else "")
        + "\nEntregables permitidos/esperados para esta reparacion:\n"
        f"{file_bullets}\n\n"
        "Trabajo obligatorio:\n"
        f"- Corregir {relative_path} alrededor de la linea {line} atacando la causa real del punto rojo.\n"
        "- Crear o modificar solo los archivos necesarios listados arriba cuando la reparacion lo requiera.\n"
        "- No hagas refactors esteticos ni cambies partes no relacionadas del proyecto.\n"
        "- Usa el bridge visual: phase antes de trabajar, focus-node sobre el archivo, sync-file despues de cada archivo escrito.\n"
        "- Si creas un archivo nuevo, sincronizalo con sync-file para que el editor lo pueda mostrar en vivo.\n"
        "- Deja evidencia de validacion en el resultado de la tarea.\n\n"
        "Validaciones obligatorias sugeridas:\n"
        f"- python3 -m py_compile {validation_files}\n"
        "- Reauditar el mapa debe eliminar o reducir el punto rojo seleccionado.\n\n"
        f"Instruccion humana adicional: {extra_instruction or 'Repara este error en esta linea y valida que el punto rojo desaparezca.'}\n"
    )


def build_repair_validation_commands(repair_files: List[str], *, smoke_script_path: Path | None = None) -> List[str]:
    commands: List[str] = []
    python_files = [path for path in repair_files if path.endswith(".py")]
    if python_files:
        commands.append("python3 -m py_compile " + " ".join(shlex.quote(path) for path in python_files))
    frontend_files = {
        str(path).replace("\\", "/")
        for path in repair_files
        if str(path).replace("\\", "/").startswith("frontend/")
    }
    if smoke_script_path is not None and frontend_files & {"frontend/index.html", "frontend/app.js", "frontend/styles.css"}:
        commands.append(
            "python3 -B "
            + shlex.quote(str(smoke_script_path))
            + " --workspace . --frontend frontend --mode smoke --light day"
        )
    return commands


def queue_agent_repair_task(
    *,
    project_slug: str,
    project_dir: Path,
    relative_path: str,
    repair_files: List[str],
    requirement: str,
    now_provider: NowProvider,
    smoke_script_path: Path | None = None,
) -> Dict[str, Any]:
    runtime_dir = project_dir / "runtime"
    store = StateStore(runtime_dir)
    now = now_provider()
    try:
        state = store.load_project_state()
    except Exception:
        state = {
            "schema_version": 1,
            "project_id": project_slug,
            "status": "initialized",
            "mode": "build",
            "current_task_id": None,
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "checkpoints": [],
            "created_at": now,
            "updated_at": now,
        }

    state = dict(state)
    state["status"] = "initialized"
    state["current_task_id"] = None
    state["blocked_tasks"] = []
    state["updated_at"] = now
    store.save_project_state(state)

    queue = TaskQueue(store, bootstrap_empty=True)

    existing_ids = {task["id"] for task in queue.list()}
    base_task_id = "REPAIR-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    task_id = base_task_id
    suffix = 2
    while task_id in existing_ids:
        task_id = f"{base_task_id}-{suffix:02d}"
        suffix += 1

    validation_commands = build_repair_validation_commands(repair_files, smoke_script_path=smoke_script_path)
    task = create_task(
        task_id=task_id,
        title=f"Reparar punto rojo en {relative_path}",
        goal=requirement,
        priority=100,
        dependencies=[],
        expected_files=repair_files,
        validation_commands=validation_commands or None,
        timeout_seconds=900,
        max_retries=2,
        mode="build",
        checkpoint_key=f"{task_id.lower()}-checkpoint",
    )
    return queue.enqueue(task)
