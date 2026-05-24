"""Policy-governed workspace cleanup protocol.

This module does not decide UI state. It owns the destructive-action contract:
justify, audit, backup, clean selectively first, and create post-clean recovery
evidence.
"""

from __future__ import annotations

import fnmatch
import json
import shutil
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


GENERATED_DIR_NAMES = {
    ".cache",
    ".mypy_cache",
    ".next",
    ".nuxt",
    ".parcel-cache",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".venv",
    ".vite",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}
TEMP_FILE_PATTERNS = ("*.pyc", "*.pyo", "*.tmp", "*.temp", "*.log")
SOURCE_DIR_NAMES = {"src", "backend", "frontend", "shared", "orchestrator", "workers", "schemas", "tests"}
CONFIG_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "AGENTS.md",
    "PLANS.md",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "requirements.txt",
    "vite.config.js",
}
IMPORTANT_SUFFIXES = {
    ".css",
    ".db",
    ".env",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".sql",
    ".sqlite",
    ".sqlite3",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
DATABASE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
SAFE_TOTAL_CONFIRMATIONS = {"si", "confirmar", "confirmo"}
SAFE_MODES_REQUIRING_HUMAN_TOTAL = {"medium", "long-run"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_for_path(value: str | None = None) -> str:
    source = value or utc_now()
    compact = source.replace("+00:00", "Z").replace(":", "").replace("-", "")
    return compact.replace(".", "_")


def normalize_confirmation(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    return text


def is_total_confirmation(value: Any) -> bool:
    return normalize_confirmation(value) in SAFE_TOTAL_CONFIRMATIONS


def normalize_blanqueo_scope(value: Any) -> str:
    scope = str(value or "selective").strip().lower().replace("_", "-")
    if scope in {"total", "full", "complete", "completo"}:
        return "total"
    return "selective"


def normalize_blanqueo_mode(value: Any) -> str:
    mode = str(value or "build").strip().lower().replace("_", "-")
    if mode in {"smoke", "build", "medium", "long-run"}:
        return mode
    return "build"


def coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def decidir_y_justificar_blanqueo(
    *,
    task_id: str = "POST-BLANQUEO-DECISION",
    mode: str = "build",
    requested_scope: str = "selective",
    source: str = "agent",
    repair_attempts: int = 0,
    compile_failed: bool = False,
    irrecoverable: bool = False,
    selective_attempted: bool = False,
    root_cause: str = "",
    attempted_repairs: Iterable[str] | None = None,
    evidence: Iterable[str] | None = None,
    risk_of_not_cleaning: Iterable[str] | None = None,
    expected_benefits: Iterable[str] | None = None,
    confirmation_phrase: str = "",
    planned_backup_dir: str = "backups/blanqueo/PENDING",
) -> dict[str, Any]:
    """Return a complete, auditable decision before any destructive action."""

    runtime_mode = normalize_blanqueo_mode(mode)
    requested = normalize_blanqueo_scope(requested_scope)
    attempts = max(0, int(repair_attempts or 0))
    critical_compile_failure = bool(compile_failed and attempts >= 3)
    requested_total = requested == "total"
    total_recommended = requested_total or critical_compile_failure or bool(irrecoverable)
    if total_recommended and not requested_total and not selective_attempted and not irrecoverable:
        decision_scope = "selective"
        downgrade_reason = "Regla 4 exige blanqueo selectivo antes del total."
    else:
        decision_scope = "total" if total_recommended else "selective"
        downgrade_reason = ""

    needs_human_gate = decision_scope == "total" and runtime_mode in SAFE_MODES_REQUIRING_HUMAN_TOTAL
    confirmation_ok = is_total_confirmation(confirmation_phrase)
    allowed = not needs_human_gate or confirmation_ok

    repairs = coerce_list(attempted_repairs)
    evidence_items = coerce_list(evidence)
    risks = coerce_list(risk_of_not_cleaning) or [
        "perdida de tiempo por retries sobre un estado degradado",
        "propagacion de errores a nuevas tareas",
    ]
    benefits = coerce_list(expected_benefits) or [
        "restablecer un workspace auditable",
        "forzar recuperacion con evidencia limpia",
    ]

    if not root_cause:
        if critical_compile_failure:
            root_cause = "Fallo critico de compilacion end-to-end tras 3 intentos de reparacion."
        elif irrecoverable:
            root_cause = "Estado marcado como irrecuperable por el agente."
        elif requested_total:
            root_cause = "Solicitud explicita de blanqueo total desde el boton o API autorizada."
        else:
            root_cause = "Limpieza preventiva selectiva por estado no confiable del workspace."

    delete_targets = (
        [
            "workspace/projects/*",
            ".runtime/observer/*",
            ".runtime/email_commands/state.json",
            ".runtime/email_commands/events.jsonl",
            "estado visual y analisis en memoria",
        ]
        if decision_scope == "total"
        else [
            "__pycache__/",
            "node_modules/",
            "build/",
            "dist/",
            ".pytest_cache/",
            ".ruff_cache/",
            "venv/",
            ".venv/",
            "*.pyc",
            "*.log",
        ]
    )
    preserve_targets = [
        "backups/blanqueo/",
        "backups/pre_blanqueo/",
        "AGENTS.md",
        "PLANS.md",
        "runtime/task_history.jsonl",
        "runtime/failures.jsonl",
        "runtime/logs/blanqueo_decision_*.md",
        ".env*",
        "archivos importantes copiados al backup",
    ]

    decision = {
        "type": "BLANQUEO_DECISION",
        "timestamp": utc_now(),
        "task_id": task_id or "POST-BLANQUEO-DECISION",
        "source": source,
        "mode": runtime_mode,
        "decision": "Blanqueo Total" if decision_scope == "total" else "Blanqueo Selectivo",
        "scope": decision_scope,
        "requested_scope": requested,
        "allowed": allowed,
        "requires_confirmation": needs_human_gate and not confirmation_ok,
        "confirmation_prompt": (
            "CONFIRMAR BLANQUEO TOTAL DEL WORKSPACE? (si/confirmar)"
            if needs_human_gate and not confirmation_ok
            else ""
        ),
        "reason": root_cause,
        "root_cause": root_cause,
        "repair_attempts": attempts,
        "attempted_repairs": repairs,
        "evidence": evidence_items,
        "risks_of_not_cleaning": risks,
        "expected_benefits": benefits,
        "delete_targets": delete_targets,
        "preserve_targets": preserve_targets,
        "planned_backup_dir": planned_backup_dir,
        "critical_compile_failure": critical_compile_failure,
        "irrecoverable": bool(irrecoverable),
        "selective_attempted": bool(selective_attempted),
        "downgrade_reason": downgrade_reason,
    }
    decision["summary_markdown"] = build_blanqueo_decision_markdown(decision)
    return decision


def build_blanqueo_decision_markdown(decision: dict[str, Any]) -> str:
    delete_targets = ", ".join(decision.get("delete_targets") or ["sin objetivos"])
    return "\n".join(
        [
            "=== DECISION DE BLANQUEO ===",
            f"Tarea: {decision.get('task_id') or 'sin tarea'}",
            f"Decision: {decision.get('decision')}",
            f"Motivo principal: {decision.get('reason')}",
            f"Intentos fallidos: {decision.get('repair_attempts', 0)}",
            f"Archivos/Carpetas a eliminar: {delete_targets}",
            f"Backups creados en: {decision.get('planned_backup_dir')}",
            "Proceder: "
            + (
                "si"
                if decision.get("allowed")
                else "no, requiere confirmacion humana en modo seguro"
            ),
        ]
    )


def record_blanqueo_decision(decision: dict[str, Any], runtime_dir: str | Path) -> dict[str, str]:
    runtime_path = Path(runtime_dir)
    logs_dir = runtime_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    runtime_path.mkdir(parents=True, exist_ok=True)
    stamp = timestamp_for_path(decision.get("timestamp"))
    decision_path = logs_dir / f"blanqueo_decision_{stamp}.md"
    decision_path.write_text(decision.get("summary_markdown", ""), encoding="utf-8")

    failure_event = {"recorded_at": utc_now(), "failure": decision}
    history_event = {
        "recorded_at": utc_now(),
        "result": {
            "task_id": decision.get("task_id") or "POST-BLANQUEO-DECISION",
            "type": "BLANQUEO_DECISION",
            "completed": False,
            "validation_passed": bool(decision.get("allowed")),
            "summary": decision.get("reason"),
            "decision": decision,
        },
    }
    _append_jsonl(runtime_path / "failures.jsonl", failure_event)
    _append_jsonl(runtime_path / "task_history.jsonl", history_event)
    return {
        "failure_log": str(runtime_path / "failures.jsonl"),
        "task_history": str(runtime_path / "task_history.jsonl"),
        "decision_markdown": str(decision_path),
    }


def create_blanqueo_backup(
    *,
    project_root: str | Path,
    workspace_root: str | Path,
    runtime_dirs: Iterable[str | Path],
    backup_base: str | Path,
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Create a manifest-backed backup before cleanup."""

    project = Path(project_root)
    workspace = Path(workspace_root)
    stamp = timestamp_for_path(decision.get("timestamp"))
    backup_dir = Path(backup_base) / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "created_at": utc_now(),
        "reason": decision.get("reason"),
        "decision": {
            "task_id": decision.get("task_id"),
            "scope": decision.get("scope"),
            "mode": decision.get("mode"),
        },
        "files": [],
        "database_dumps": [],
    }

    if workspace.exists():
        _copy_tree(
            workspace,
            backup_dir / "workspace",
            manifest,
            source_label="workspace",
        )

    for runtime_dir in runtime_dirs:
        runtime = Path(runtime_dir)
        if runtime.exists():
            _copy_tree(
                runtime,
                backup_dir / "runtime" / runtime.name,
                manifest,
                source_label=f"runtime:{runtime.name}",
            )

    for name in CONFIG_FILE_NAMES:
        source = project / name
        if source.exists() and source.is_file():
            _copy_file(source, backup_dir / "config" / name, manifest, source_label="config")

    important_dir = backup_dir / "important_files"
    pre_blanqueo_dir = project / "backups" / "pre_blanqueo" / stamp / "important_files"
    for important in _iter_important_files(workspace):
        relative = _relative_to(important, workspace)
        _copy_file(important, important_dir / relative, manifest, source_label="important")
        if decision.get("scope") == "total":
            _copy_file(important, pre_blanqueo_dir / relative, manifest, source_label="pre_blanqueo")

    for database in _iter_database_files(workspace):
        relative = _relative_to(database, workspace)
        db_target = backup_dir / "database_files" / relative
        _copy_file(database, db_target, manifest, source_label="database")
        dump_target = backup_dir / "database_dumps" / f"{relative.as_posix().replace('/', '__')}.sql"
        dump_target.parent.mkdir(parents=True, exist_ok=True)
        dump_info: dict[str, Any] = {"source": str(database), "dump": str(dump_target)}
        try:
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
                dump_target.write_text("\n".join(connection.iterdump()), encoding="utf-8")
            dump_info["ok"] = True
        except Exception as error:  # pragma: no cover - depends on actual DB format.
            dump_target.write_text(f"-- dump failed: {error}\n", encoding="utf-8")
            dump_info["ok"] = False
            dump_info["error"] = str(error)
        manifest["database_dumps"].append(dump_info)

    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "backup_dir": str(backup_dir),
        "manifest": str(manifest_path),
        "files": len(manifest["files"]),
        "database_dumps": len(manifest["database_dumps"]),
    }


def apply_selective_blanqueo(workspace_root: str | Path, runtime_dirs: Iterable[str | Path] = ()) -> dict[str, Any]:
    removed: list[str] = []
    workspace = Path(workspace_root)
    if workspace.exists():
        for path in sorted(workspace.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if _is_generated_dir(path):
                _remove_path(path, removed)
                continue
            if path.is_file() and _is_temp_file(path):
                _remove_path(path, removed)

    for runtime_dir in runtime_dirs:
        runtime = Path(runtime_dir)
        logs = runtime / "logs"
        if logs.exists():
            for log_file in logs.glob("*.log"):
                if log_file.is_file() and log_file.stat().st_size > 1_000_000:
                    _remove_path(log_file, removed)
        for transient in (
            runtime / "observer" / "memory.json",
            runtime / "observer" / "timeline.jsonl",
            runtime / "email_commands" / "events.jsonl",
        ):
            if transient.exists():
                _remove_path(transient, removed)

    return {"scope": "selective", "removed": removed, "removedCount": len(removed)}


def apply_total_blanqueo(
    workspace_root: str | Path,
    *,
    preserve_names: Iterable[str] = ("runtime", "backups", "lessons_learned"),
) -> dict[str, Any]:
    """Project-scoped total cleanup after backup.

    The control plane must keep runtime/audit directories alive while it is
    executing, so this is intentionally project-scoped rather than process-wide.
    """

    workspace = Path(workspace_root)
    removed: list[str] = []
    preserved = {str(name) for name in preserve_names}
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        return {"scope": "total", "removed": removed, "removedCount": 0, "preserved": sorted(preserved)}

    for child in workspace.iterdir():
        if child.name in preserved:
            continue
        _remove_path(child, removed)

    return {"scope": "total", "removed": removed, "removedCount": len(removed), "preserved": sorted(preserved)}


def create_post_blanqueo_recovery(
    *,
    runtime_dir: str | Path,
    decision: dict[str, Any],
    backup: dict[str, Any],
) -> dict[str, Any]:
    runtime = Path(runtime_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    queue_path = runtime / "task_queue.json"
    lesson_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lesson_relative = f"lessons_learned/blanqueo-{lesson_date}.md"
    task = {
        "id": "POST-BLANQUEO-RECOVERY",
        "title": "POST-BLANQUEO-RECOVERY",
        "goal": "Analizar causa raiz, validar workspace limpio y ajustar politicas preventivas.",
        "status": "pending",
        "priority": 100,
        "dependencies": [],
        "expected_files": [lesson_relative],
        "validation_commands": [
            f"python3 -B -c \"from pathlib import Path; assert Path({lesson_relative!r}).is_file()\""
        ],
        "timeout_seconds": 300,
        "max_retries": 0,
        "mode": normalize_blanqueo_mode(decision.get("mode")),
        "checkpoint_key": "post-blanqueo-recovery-checkpoint",
    }
    queue: list[dict[str, Any]]
    try:
        queue = json.loads(queue_path.read_text(encoding="utf-8")) if queue_path.exists() else []
        if not isinstance(queue, list):
            queue = []
    except Exception:
        queue = []
    queue = [item for item in queue if item.get("id") != task["id"]]
    queue.append(task)
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")

    lessons_dir = runtime.parent / "lessons_learned"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    lesson_path = runtime.parent / lesson_relative
    lesson_path.write_text(
        "\n".join(
            [
                "# Leccion aprendida de blanqueo",
                "",
                f"Fecha: {utc_now()}",
                f"Decision: {decision.get('decision')}",
                f"Causa raiz: {decision.get('root_cause')}",
                f"Que fallo: {', '.join(decision.get('evidence') or ['sin evidencia adicional'])}",
                "Prevencion futura:",
                "- ejecutar validaciones end-to-end antes de cerrar tareas",
                "- no relanzar workers si ya existe evidencia valida en disco",
                "- pedir confirmacion humana para blanqueo total en modo medium o long-run",
                "",
                f"Backup: {backup.get('backup_dir')}",
            ]
        ),
        encoding="utf-8",
    )
    _append_jsonl(
        runtime / "task_history.jsonl",
        {
            "recorded_at": utc_now(),
            "result": {
                "task_id": task["id"],
                "type": "POST_BLANQUEO_RECOVERY_CREATED",
                "completed": True,
                "validation_passed": True,
                "lesson_path": str(lesson_path),
                "backup_dir": backup.get("backup_dir"),
            },
        },
    )
    return {"task": task, "queue_path": str(queue_path), "lesson_path": str(lesson_path)}


def _append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _copy_tree(source: Path, target: Path, manifest: dict[str, Any], *, source_label: str) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for child in source.rglob("*"):
        if _has_generated_part(child):
            continue
        if child.is_file():
            relative = _relative_to(child, source)
            _copy_file(child, target / relative, manifest, source_label=source_label)


def _copy_file(source: Path, target: Path, manifest: dict[str, Any], *, source_label: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    manifest["files"].append(
        {
            "source": str(source),
            "target": str(target),
            "size": target.stat().st_size,
            "label": source_label,
        }
    )


def _iter_important_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (
        path
        for path in root.rglob("*")
        if path.is_file()
        and not _has_generated_part(path)
        and (path.suffix.lower() in IMPORTANT_SUFFIXES or path.name in CONFIG_FILE_NAMES)
    )


def _iter_database_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (
        path
        for path in root.rglob("*")
        if path.is_file() and not _has_generated_part(path) and path.suffix.lower() in DATABASE_SUFFIXES
    )


def _relative_to(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(path.name)


def _has_generated_part(path: Path) -> bool:
    return any(part in GENERATED_DIR_NAMES for part in path.parts)


def _is_generated_dir(path: Path) -> bool:
    return path.is_dir() and path.name in GENERATED_DIR_NAMES


def _is_temp_file(path: Path) -> bool:
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in TEMP_FILE_PATTERNS)


def _remove_path(path: Path, removed: list[str]) -> None:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        removed.append(str(path))
    except OSError:
        return
