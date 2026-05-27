from __future__ import annotations

import json
import os
import pwd
import pty
import re
import select
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid
import hashlib
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from orchestrator.complexity_estimator import estimate_complexity
    from orchestrator.contracts import ContractError as RuntimeContractError
    from orchestrator.directive_context import build_directive_context
    from orchestrator.directive_generator import generate_directive, persist_directive
    from orchestrator.executor import execute_task_with_details
    from orchestrator.habla_adapter import build_habla_guide
    from orchestrator.live_reviewer import LiveReviewer
    from orchestrator.planner import DEFAULT_TIMEOUT_SECONDS, plan_project
    from orchestrator.recovery import recover_task
    from orchestrator.state_store import StateStore
    from orchestrator.task_queue import TaskQueue
    from orchestrator.tool_invocation_policy import ToolInvocationPolicy
    from orchestrator.safe_process_env import safe_child_process_env
    from orchestrator.validator import validate_task_execution
    from backend.agent_worker_adapters import SessionWorkerAdapter, select_session_worker_adapter
    from backend.human_alignment_review import create_human_alignment_review
    from backend.workspace_blanqueo import (
        apply_selective_blanqueo,
        apply_total_blanqueo,
        create_blanqueo_backup,
        create_post_blanqueo_recovery,
        decidir_y_justificar_blanqueo,
        record_blanqueo_decision,
    )
except Exception as error:  # pragma: no cover - surfaced clearly when control plane is used.
    estimate_complexity = None  # type: ignore[assignment]
    RuntimeContractError = ValueError  # type: ignore[assignment]
    build_directive_context = None  # type: ignore[assignment]
    generate_directive = None  # type: ignore[assignment]
    persist_directive = None  # type: ignore[assignment]
    execute_task_with_details = None  # type: ignore[assignment]
    build_habla_guide = None  # type: ignore[assignment]
    LiveReviewer = None  # type: ignore[assignment]
    DEFAULT_TIMEOUT_SECONDS = {"smoke": 300, "build": 900, "medium": 1800, "long-run": 3600}
    plan_project = None  # type: ignore[assignment]
    recover_task = None  # type: ignore[assignment]
    StateStore = None  # type: ignore[assignment]
    TaskQueue = None  # type: ignore[assignment]
    ToolInvocationPolicy = None  # type: ignore[assignment]
    safe_child_process_env = None  # type: ignore[assignment]
    validate_task_execution = None  # type: ignore[assignment]
    SessionWorkerAdapter = Any  # type: ignore[assignment]
    select_session_worker_adapter = None  # type: ignore[assignment]
    create_human_alignment_review = None  # type: ignore[assignment]
    apply_selective_blanqueo = None  # type: ignore[assignment]
    apply_total_blanqueo = None  # type: ignore[assignment]
    create_blanqueo_backup = None  # type: ignore[assignment]
    create_post_blanqueo_recovery = None  # type: ignore[assignment]
    decidir_y_justificar_blanqueo = None  # type: ignore[assignment]
    record_blanqueo_decision = None  # type: ignore[assignment]
    CONTROL_PLANE_IMPORT_ERROR: Exception | None = error
else:
    CONTROL_PLANE_IMPORT_ERROR = None

try:
    from backend.cyberlace_integration import (
        cyberlace_after_model_output,
        cyberlace_before_external_action,
        cyberlace_before_memory_read,
        cyberlace_before_prompt,
        cyberlace_before_tool_call,
    )
    from backend.cyberlace_policy_bridge import should_block_action, should_redact_payload
except Exception:  # pragma: no cover - CyberLACE must remain lateral if unavailable.
    cyberlace_after_model_output = None  # type: ignore[assignment]
    cyberlace_before_external_action = None  # type: ignore[assignment]
    cyberlace_before_memory_read = None  # type: ignore[assignment]
    cyberlace_before_prompt = None  # type: ignore[assignment]
    cyberlace_before_tool_call = None  # type: ignore[assignment]
    should_block_action = None  # type: ignore[assignment]
    should_redact_payload = None  # type: ignore[assignment]

try:
    from backend.cyberlace_document_guard import inspect_runtime_document_inputs
except Exception:  # pragma: no cover - document guard must fail closed only when explicitly invoked.
    inspect_runtime_document_inputs = None  # type: ignore[assignment]

ANSI_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
SOURCE_FILE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".json",
    ".txt",
    ".md",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
}
PROJECT_FOLDERS = ("src", "backend", "frontend", "shared", "tests", "docs", "algorithms", "assets")
MAX_OUTPUT_CHARS = 240_000
READ_CHUNK_SIZE = 4096
VISUAL_DIR_NAME = ".vista"
FIRST_VISUAL_TIMEOUT_SECONDS = float(os.environ.get("AGENT_FIRST_VISUAL_TIMEOUT_SECONDS", "300"))
HEARTBEAT_INTERVAL_SECONDS = float(os.environ.get("AGENT_HEARTBEAT_INTERVAL_SECONDS", "5"))
SESSION_IDLE_TIMEOUT_SECONDS = float(os.environ.get("AGENT_SESSION_IDLE_TIMEOUT_SECONDS", "120"))
FIRST_AGENT_SIGNAL_TIMEOUT_SECONDS = float(os.environ.get("AGENT_FIRST_AGENT_SIGNAL_TIMEOUT_SECONDS", "90"))
SESSION_IDLE_RETRY_LIMIT = int(os.environ.get("AGENT_SESSION_IDLE_RETRY_LIMIT", "5"))
VISUAL_EVENT_OPS = {"upsert_node", "upsert_edge", "upsert_flow_step", "upsert_flow_edge", "sync_file"}
HABLA_DEBUG_LINES_LIMIT = 12
HABLA_TEXT_LIMIT = 2_400
LACE_VISUAL_DIR = Path("docs") / "lace_cycles"
LACE_MIN_REQUIRED_CYCLES = 2
LACE_MAX_REQUIRED_CYCLES = 10
LACE_COMPLETION_MARKER = "¿El proyecto mejoró objetivamente? SI"
LACE_SECTION_YES_PATTERN = re.compile(r"\bS[IÍ]\b", flags=re.IGNORECASE)
LACE_CYCLE_SECTION_PATTERN = re.compile(
    r"^\[CICLO-(?P<cycle>\d+)(?:\s+RECALCE\s+\d{8})?\s+(?P<section>PROBLEMAS|MEJORA|COMPLETADO)\]\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
LACE_REQUIRED_LAYERS = (
    "CAPA 1 — INTERPRETACIÓN",
    "CAPA 2 — CLASIFICACIÓN SEMÁNTICA",
    "CAPA 3 — PLANIFICACIÓN DEL RAZONAMIENTO",
    "CAPA 4 — REACT",
    "CAPA 5 — RECUPERACIÓN Y EVIDENCIA",
    "CAPA 6 — TRIANGULACIÓN",
    "CAPA 7 — CONFIANZA POR COMPONENTE",
    "CAPA 8 — AUTO-CRÍTICA",
    "CAPA 9 — MEMORIA EPISÓDICA",
    "CAPA 10 — RESPUESTA",
)
LACE_AREAS = (
    "bugs críticos",
    "limpieza y organización",
    "interfaz de usuario",
    "documentación",
    "rendimiento",
    "errores y casos extremos",
    "seguridad básica",
    "funcionalidad adicional de valor real",
    "experiencia de usuario punta a punta",
    "revisión integral final",
)
LACE_PLACEHOLDER_TEXTS = {
    "técnico / funcional / humano.",
    "lógica, ui, rendimiento, errores, seguridad.",
    "buscaré cierre prematuro, parches débiles u omisiones.",
    "implementar cambio verificable.",
    "pendiente de ejecución.",
    "se definirá tras validación.",
}
LACE_LABEL_PREFIXES = (
    "thought:",
    "triangulacion:",
    "confianza:",
    "auto-critica:",
    "problemas priorizados:",
    "action:",
    "observation esperada:",
    "observation real:",
    "coincide con observation esperada?",
    "problemas resueltos:",
    "estado ahora vs antes:",
    "el proyecto mejoro objetivamente?",
    "memoria episodica:",
    "proximo ciclo - que atacare:",
)
SMOKE_REQUIREMENT_PATTERN = re.compile(
    r"\b(smoke|sanity|probe|verificaci[oó]n|prueba|check|validaci[oó]n)\b",
    flags=re.IGNORECASE,
)
SMOKE_MINIMALITY_PATTERN = re.compile(
    r"\b(m[ií]nim(?:o|a|os|as)|breve|b[aá]sic(?:o|a)|corto|puntual|intern[oa]|r[aá]pid[oa]|conectad[oa])\b",
    flags=re.IGNORECASE,
)
SMOKE_ARTIFACT_PATTERN = re.compile(
    r"(?:^|[\s/`\"'])("
    r"internal[-_\s]?smoke(?:\.md)?"
    r"|smokecheck"
    r"|smoke-ui-\d+"
    r"|runprojectservice"
    r")(?=$|[\s`\"'.,:;!?)])",
    flags=re.IGNORECASE,
)
CODE_ACTION_PATTERN = re.compile(
    r"\b(crea|crear|construye|construir|implementa|implementar|desarrolla|desarrollar|genera|generar|haz|hacer|arma|monta)\b",
    flags=re.IGNORECASE,
)
CODE_TARGET_PATTERN = re.compile(
    r"\b(app|aplicacion|aplicacion web|proyecto|frontend|backend|api|html|css|javascript|typescript|react|vue|python|flask|fastapi|ui|interfaz|pagina|sitio|modulo|componente|test|tests|pruebas|localstorage|responsive|web)\b",
    flags=re.IGNORECASE,
)
SNAP_CODEX_PATH_MARKERS = ("/snap/codex/",)
DEFAULT_INNER_CODEX_SANDBOX_MODE = "workspace-write"
DEFAULT_INNER_CODEX_APPROVAL_POLICY = "never"
ALLOWED_AGENT_RUNTIME_MODES = frozenset({"smoke", "build", "medium", "long-run"})
ACTIVE_AGENT_SESSION_STATUSES = {"queued", "preparing", "starting", "running"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def real_user_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def common_codex_bin_dirs() -> List[Path]:
    user_home = real_user_home()
    return [
        Path("/usr/local/bin"),
        Path("/usr/bin"),
        user_home / ".local" / "bin",
        user_home / ".npm-global" / "bin",
        user_home / ".volta" / "bin",
        user_home / "bin",
    ]


def is_snap_codex_path(path_value: str | None) -> bool:
    normalized = os.path.realpath(os.path.expanduser(str(path_value or "")))
    return any(marker in normalized for marker in SNAP_CODEX_PATH_MARKERS)


def build_preferred_shell_path(path_value: str | None) -> str:
    entries: List[str] = []
    seen: set[str] = set()

    for candidate_dir in common_codex_bin_dirs():
        candidate = str(candidate_dir)
        if candidate in seen:
            continue
        seen.add(candidate)
        entries.append(candidate)

    for raw_entry in str(path_value or "").split(os.pathsep):
        entry = str(raw_entry or "").strip()
        if not entry:
            continue
        normalized = os.path.realpath(os.path.expanduser(entry))
        if any(marker in normalized for marker in SNAP_CODEX_PATH_MARKERS):
            continue
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)

    return os.pathsep.join(entries)


def resolve_codex_command_tokens(codex_cmd: str, path_value: str | None = None) -> List[str]:
    raw_value = str(codex_cmd or "").strip() or "codex"
    tokens = shlex.split(raw_value)
    if not tokens:
        tokens = ["codex"]

    command_name = tokens[0]
    if "/" in command_name or "\\" in command_name:
        return tokens
    if Path(command_name).name != "codex":
        return tokens

    preferred_path = build_preferred_shell_path(path_value)
    resolved = shutil.which(command_name, path=preferred_path)
    if resolved:
        tokens[0] = resolved
        return tokens

    fallback = shutil.which(command_name)
    if fallback:
        tokens[0] = fallback
    return tokens


def env_flag_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def normalize_agent_runtime_mode(value: str | None = None, *, default: str = "build") -> str:
    """Return one explicit runtime mode; never infer mode from prompt text."""

    raw_value = (
        str(value or "").strip()
        or str(os.environ.get("VISTA_AGENT_RUNTIME_MODE") or "").strip()
        or str(os.environ.get("AGENT_RUNTIME_MODE") or "").strip()
        or default
    )
    normalized = raw_value.lower()
    if normalized not in ALLOWED_AGENT_RUNTIME_MODES:
        allowed = ", ".join(sorted(ALLOWED_AGENT_RUNTIME_MODES))
        raise ValueError(f"runtime mode must be explicit and one of: {allowed}")
    return normalized


def mode_timeout_seconds(mode: str) -> int:
    normalized = normalize_agent_runtime_mode(mode)
    return int(DEFAULT_TIMEOUT_SECONDS.get(normalized, DEFAULT_TIMEOUT_SECONDS["build"]))


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-") or f"project-{uuid.uuid4().hex[:6]}"


def titleize(value: str) -> str:
    return " ".join(part.capitalize() for part in str(value or "").replace("-", " ").split()) or "Nuevo Proyecto"


def strip_ansi(value: str) -> str:
    return ANSI_PATTERN.sub("", value or "").replace("\r\n", "\n").replace("\r", "\n")


def ensure_file(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def remove_file_if_exists(path: Path) -> None:
    try:
        if path.exists() and path.is_file():
            path.unlink()
    except OSError:
        return


def _append_unique(values: List[str], value: str) -> List[str]:
    result = [str(item) for item in values if str(item)]
    if value not in result:
        result.append(value)
    return result


def count_source_files(project_dir: Path) -> int:
    file_count = 0
    for file_path in project_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in SOURCE_FILE_SUFFIXES:
            file_count += 1
    return file_count


def normalize_project_relative_path(value: str | Path) -> str:
    normalized = str(Path(str(value or ".")).as_posix())
    return "" if normalized == "." else normalized


RUNTIME_CONTROL_EXACT_PATHS = frozenset(
    {
        ".agent-project.json",
        "agent-project.json",
        "LACE.md",
        "LACE_LOG.md",
        "docs/habla-session.md",
    }
)


def is_runtime_control_path(relative_path: str | Path) -> bool:
    normalized = normalize_project_relative_path(relative_path)
    if not normalized:
        return True
    if normalized.startswith(".vista/"):
        return True
    if normalized in RUNTIME_CONTROL_EXACT_PATHS:
        return True
    if normalized.startswith("docs/lace_cycles/"):
        return True
    return False


def is_control_plane_state_path(relative_path: str | Path) -> bool:
    normalized = normalize_project_relative_path(relative_path)
    if normalized in {
        "runtime/project_state.json",
        "runtime/task_queue.json",
        "runtime/task_history.jsonl",
        "runtime/failures.jsonl",
        "runtime/tool_invocation_policy.jsonl",
        "runtime/artifacts/tool_invocation_policy_latest.json",
    }:
        return True
    return normalized.startswith(
        (
            "runtime/checkpoints/",
            "runtime/directives/",
            "runtime/logs/",
            "runtime/artifacts/tool_invocations/",
        )
    )


def is_material_project_path(relative_path: str | Path) -> bool:
    normalized = normalize_project_relative_path(relative_path)
    if is_runtime_control_path(normalized) or is_control_plane_state_path(normalized):
        return False
    suffix = Path(normalized).suffix.lower()
    if suffix == ".svg":
        return True
    return suffix in SOURCE_FILE_SUFFIXES


def list_material_project_files(project_dir: Path, *, limit: int = 16) -> List[str]:
    files: List[str] = []
    for file_path in sorted(project_dir.rglob("*")):
        if not file_path.is_file():
            continue
        try:
            relative_path = file_path.relative_to(project_dir).as_posix()
        except ValueError:
            continue
        if not is_material_project_path(relative_path):
            continue
        files.append(relative_path)
        if len(files) >= limit:
            break
    return files


def collect_recent_declared_paths(project_dir: Path, *, limit: int = 16) -> List[str]:
    vista_dir = project_dir / VISUAL_DIR_NAME
    if not vista_dir.exists():
        return []

    discovered: List[str] = []
    seen: set[str] = set()
    event_logs = sorted(vista_dir.glob("*-events.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    for event_log in event_logs:
        try:
            lines = event_log.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw_line in reversed(lines):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            candidate = str(payload.get("relativePath") or payload.get("nodePath") or "").strip()
            if not candidate:
                continue
            normalized = normalize_project_relative_path(candidate)
            if normalized in seen or not is_material_project_path(normalized):
                continue
            seen.add(normalized)
            discovered.append(normalized)
            if len(discovered) >= limit:
                return discovered
    return discovered


def collect_recent_visual_payloads(project_dir: Path, *, limit: int = 24) -> List[Dict[str, Any]]:
    vista_dir = project_dir / VISUAL_DIR_NAME
    if not vista_dir.exists():
        return []

    discovered: List[Dict[str, Any]] = []
    event_logs = sorted(vista_dir.glob("*-events.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    for event_log in event_logs:
        try:
            lines = event_log.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw_line in reversed(lines):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            op = str(payload.get("op") or "").strip().lower()
            if op in {"session_start", "session_complete", "session_failed", "session_stopped", "heartbeat"}:
                continue
            discovered.append(payload)
            if len(discovered) >= limit:
                return discovered
    return discovered


def inspect_project_resume_context(project_dir: Path) -> Dict[str, Any]:
    lace_log_path = project_dir / "LACE_LOG.md"
    lace_text = ""
    if lace_log_path.exists():
        try:
            lace_text = lace_log_path.read_text(encoding="utf-8")
        except OSError:
            lace_text = ""

    material_files = list_material_project_files(project_dir)
    declared_paths = collect_recent_declared_paths(project_dir)
    pending_declared = [path for path in declared_paths if path not in material_files][:10]
    completed_cycles = count_completed_lace_cycles(lace_log_path if lace_log_path.exists() else None)
    has_habla_initial = "[HABLA INICIAL]" in lace_text
    has_pre_base = "[PRE-BASE]" in lace_text
    has_base = "[BASE]" in lace_text

    return {
        "materialFiles": material_files,
        "declaredPaths": declared_paths,
        "pendingDeclaredPaths": pending_declared,
        "completedCycles": completed_cycles,
        "hasHablaInitial": has_habla_initial,
        "hasPreBase": has_pre_base,
        "hasBase": has_base,
        "shouldResume": bool(material_files or declared_paths or has_habla_initial or has_pre_base or has_base),
    }


def summarize_graph(graph: Dict[str, Any]) -> str:
    nodes = graph.get("nodes") or []
    if not nodes:
        return "No hay nodos cargados en el editor visual."

    layers = {}
    for node in nodes:
        layers.setdefault(node.get("layerLabel") or node.get("layer") or "Script", []).append(node)

    lines = []
    for layer_name, layer_nodes in list(layers.items())[:8]:
        lines.append(f"- {layer_name}: {len(layer_nodes)} bloque(s)")
        for node in layer_nodes[:4]:
            lines.append(f"  - {node.get('path')}")
    return "\n".join(lines)


def scope_graph_to_project(graph: Dict[str, Any], project_slug: str) -> Dict[str, Any]:
    slug = str(project_slug or "").strip()
    if not slug:
        return graph

    nodes = graph.get("nodes") or []
    scoped_nodes = []
    for node in nodes:
        scene_key = str(node.get("workspaceScene") or "").strip()
        path = str(node.get("path") or "")
        if scene_key == slug or scene_key.startswith(f"{slug}/") or f"workspace/projects/{slug}/" in path:
            scoped_nodes.append(node)

    scoped_scenes = [
        scene for scene in (graph.get("scenes") or [])
        if str(scene.get("key") or "") == slug or str(scene.get("key") or "").startswith(f"{slug}/")
    ]
    node_ids = {str(node.get("id") or "") for node in scoped_nodes}
    scoped_edges = [
        edge for edge in (graph.get("edges") or [])
        if str(edge.get("from") or "") in node_ids and str(edge.get("to") or "") in node_ids
    ]
    scoped_issues = []
    for issue in (graph.get("issues") or []):
        issue_scene = str(issue.get("workspaceScene") or "").strip()
        if issue_scene == slug or issue_scene.startswith(f"{slug}/"):
            scoped_issues.append(issue)

    project_label = scoped_nodes[0].get("workspaceSceneLabel") if scoped_nodes else titleize(slug)
    return {
        **graph,
        "nodes": scoped_nodes,
        "edges": scoped_edges,
        "issues": scoped_issues,
        "scenes": scoped_scenes,
        "metadata": {
            **(graph.get("metadata") or {}),
            "projectName": project_label,
            "note": f"Vista acotada al proyecto {project_label}.",
        },
    }


def build_workspace_readme(projects_root: Path) -> str:
    return (
        "# Agent Workspace\n\n"
        "Este arbol es el espacio de trabajo de Codex dentro del editor visual.\n\n"
        "## Convencion\n"
        "- Cada proyecto vive dentro de `projects/<slug>/`\n"
        "- Cada proyecto debe mantener su propio `AGENTS.md`\n"
        "- El editor detecta archivos reales y genera el mapa conceptual y los diagramas a partir de ellos\n"
        f"- Ruta base de proyectos: `{projects_root}`\n"
    )


def build_project_readme(project_name: str, project_slug: str) -> str:
    return (
        f"# {project_name}\n\n"
        "Proyecto creado desde el editor agentico.\n\n"
        "## Estructura sugerida\n"
        "- `src/`: logica principal\n"
        "- `backend/`: servicios o API\n"
        "- `frontend/`: interfaces\n"
        "- `shared/`: contratos compartidos\n"
        "- `tests/`: pruebas\n"
        "- `docs/`: notas de arquitectura\n"
        "- `algorithms/`: flujos o pseudocodigo de apoyo\n"
        "- `assets/`: recursos estaticos\n\n"
        f"Slug del proyecto: `{project_slug}`\n"
    )


def build_project_agents(project_name: str) -> str:
    return (
        f"# AGENTS.md for {project_name}\n\n"
        "## Objetivo\n"
        "Trabaja como ingeniero de software full stack dentro de este proyecto.\n\n"
        "## Reglas\n"
        "- Edita archivos dentro de este proyecto salvo que el requerimiento pida integracion externa.\n"
        "- Mantiene una estructura clara en `src/`, `backend/`, `frontend/`, `shared/`, `tests/`, `docs/`, `algorithms/` y `assets/`.\n"
        "- Si creas nuevos modulos o microservicios, agrega puntos de entrada claros y README breves.\n"
        "- Prefiere conexiones reales por import, HTTP o sockets para que el mapa conceptual pueda detectarlas.\n"
        "- Documenta decisiones clave en `docs/architecture-notes.md`.\n"
        "- Al terminar una tarea, resume archivos creados o modificados.\n"
    )


def build_architecture_notes(project_name: str) -> str:
    return (
        f"# Architecture Notes: {project_name}\n\n"
        "- Proposito:\n"
        "- Programas conectados:\n"
        "- Flujos internos clave:\n"
        "- Integraciones externas:\n"
    )


def build_project_main(project_name: str) -> str:
    return (
        'import { runProjectService } from "./service.js";\n\n'
        f'console.log("bootstrap {slugify(project_name)}");\n'
        "runProjectService();\n"
    )


def build_project_service(project_name: str) -> str:
    return (
        "export function runProjectService() {\n"
        f'  return {{ project: "{slugify(project_name)}", status: "ready" }};\n'
        "}\n"
    )


def build_project_runtime(project_name: str) -> str:
    return json.dumps(
        {
            "project": slugify(project_name),
            "status": "bootstrapped",
            "createdBy": "agent-studio",
        },
        ensure_ascii=True,
        indent=2,
    )


def shorten_text(value: Any, limit: int = HABLA_TEXT_LIMIT) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def build_habla_preflight_markdown(
    *,
    requirement: str,
    habla_prompt: str,
    habla_available: bool,
    habla_state: Dict[str, Any],
    lace_context: "LaceContext | None",
) -> str:
    confidence = habla_state.get("confidence") if isinstance(habla_state.get("confidence"), dict) else {}
    debug_lines = [str(item).strip() for item in habla_state.get("debug") or [] if str(item).strip()]
    sources = [item for item in habla_state.get("sources") or [] if isinstance(item, dict)]
    lines = [
        "# HABLA Session Prelude",
        "",
        "## Requerimiento humano",
        requirement.strip() or "(sin requerimiento)",
        "",
        "## Estado del motor HABLA",
        f"- disponible: {'si' if habla_available else 'no'}",
        f"- knowledgeType: {habla_state.get('knowledgeType') or 'desconocido'}",
        f"- toolRequired: {habla_state.get('toolRequired') or 'desconocido'}",
        f"- strategy: {habla_state.get('strategy') or 'desconocida'}",
        f"- safeToAnswer: {habla_state.get('safeToAnswer') if 'safeToAnswer' in habla_state else 'desconocido'}",
        f"- blocked: {habla_state.get('blocked') if 'blocked' in habla_state else 'desconocido'}",
    ]
    if habla_state.get("blockReason"):
        lines.append(f"- blockReason: {habla_state['blockReason']}")
    if confidence:
        lines.extend(
            [
                f"- confidence.dato: {confidence.get('dato', 0)}",
                f"- confidence.fecha: {confidence.get('fecha', 0)}",
                f"- confidence.fuente: {confidence.get('fuente', 0)}",
                f"- confidence.calculo: {confidence.get('calculo', 0)}",
                f"- confidence.inferencia: {confidence.get('inferencia', 0)}",
                f"- confidence.global: {confidence.get('global', 0)}",
            ]
        )
    if lace_context is not None:
        lines.extend(
            [
                "",
                "## LACE",
                f"- ciclos minimos: {LACE_MIN_REQUIRED_CYCLES}",
                f"- ciclos maximos: {lace_context.required_cycles}",
                "- salida temprana: scanner, sandbox, integrity, findings y cola sin pendientes",
                f"- policyPath: {lace_context.policy_path}",
                f"- logPath: {lace_context.log_path}",
            ]
        )
    if habla_state.get("triangulatedText"):
        lines.extend(
            [
                "",
                "## Triangulacion",
                shorten_text(habla_state.get("triangulatedText")),
            ]
        )
    if habla_state.get("answerPreview"):
        lines.extend(
            [
                "",
                "## Respuesta tentativa del motor",
                shorten_text(habla_state.get("answerPreview")),
            ]
        )
    if habla_state.get("directive"):
        lines.extend(
            [
                "",
                "## Directiva HABLA para Codex",
                "```text",
                str(habla_state["directive"]).strip(),
                "```",
            ]
        )
    lines.extend(
        [
            "",
            "## Prompt HABLA BASIC",
            "```text",
            str(habla_prompt or "").strip(),
            "```",
        ]
    )
    if sources:
        lines.extend(["", "## Evidencia recuperada"])
        for source in sources[:8]:
            lines.append(
                f"- {source.get('source') or 'fuente'}: {shorten_text(source.get('text') or '')}"
                + (f" (valor={source.get('value')})" if source.get("value") is not None else "")
            )
    if debug_lines:
        lines.extend(["", "## Traza resumida"])
        for item in debug_lines[:HABLA_DEBUG_LINES_LIMIT]:
            lines.append(f"- {item}")
    if habla_state.get("error"):
        lines.extend(["", "## Error de preflight", shorten_text(habla_state.get("error"))])
    return "\n".join(lines).strip() + "\n"


def lace_focus_for_cycle(cycle_number: int) -> str:
    return LACE_AREAS[(max(1, cycle_number) - 1) % len(LACE_AREAS)]


def lace_cycle_visual_relative_path(cycle_number: int) -> str:
    return (LACE_VISUAL_DIR / f"ciclo-{cycle_number:02d}.md").as_posix()


def first_meaningful_line(value: str) -> str:
    for raw_line in str(value or "").splitlines():
        candidate = raw_line.strip()
        if candidate:
            return candidate
    return ""


def summarize_lace_cycle_visual(cycle_number: int, cycle_sections: Dict[str, List[str]]) -> Dict[str, Any]:
    problems = cycle_sections.get("PROBLEMAS", [])
    improvements = effective_lace_improvement_sections(cycle_sections)
    completed = cycle_sections.get("COMPLETADO", [])
    has_problems = bool(problems)
    has_improvements = bool(improvements)
    has_completed = bool(completed)
    valid_problems = any(is_valid_lace_problems_section(section) for section in problems)
    valid_improvements = any(is_valid_lace_improvement_section(section) for section in improvements)
    valid_completed = any(is_valid_lace_completed_section(section) for section in completed)
    valid = valid_problems and valid_improvements and valid_completed

    if valid:
        stage = "validated"
    elif has_completed:
        stage = "completed"
    elif has_improvements:
        stage = "improving"
    elif has_problems:
        stage = "analyzing"
    else:
        stage = "pending"

    focus = lace_focus_for_cycle(cycle_number)
    problem_summary = first_meaningful_line(problems[-1]) if problems else ""
    improvement_summary = first_meaningful_line(improvements[-1]) if improvements else ""
    completed_summary = first_meaningful_line(completed[-1]) if completed else ""
    description = {
        "pending": f"Ciclo {cycle_number:02d} en espera. Foco sugerido: {focus}.",
        "analyzing": f"Ciclo {cycle_number:02d} analizando el proyecto. {problem_summary or 'Registrando problemas y triangulación.'}",
        "improving": f"Ciclo {cycle_number:02d} aplicando mejora. {improvement_summary or 'Registrando action/observation esperada.'}",
        "completed": f"Ciclo {cycle_number:02d} cerró observaciones pero todavía no supera toda la validación LACE.",
        "validated": f"Ciclo {cycle_number:02d} validado por LACE. {completed_summary or 'La mejora quedó documentada con evidencia.'}",
    }[stage]
    return {
        "cycle": cycle_number,
        "focus": focus,
        "stage": stage,
        "valid": valid,
        "description": description,
        "problemSummary": problem_summary,
        "improvementSummary": improvement_summary,
        "completedSummary": completed_summary,
        "hasProblems": has_problems,
        "hasImprovements": has_improvements,
        "hasCompleted": has_completed,
        "validProblems": valid_problems,
        "validImprovements": valid_improvements,
        "validCompleted": valid_completed,
    }


def build_lace_cycle_visual_markdown(cycle_number: int, cycle_summary: Dict[str, Any], cycle_sections: Dict[str, List[str]]) -> str:
    effective_sections = {
        "PROBLEMAS": cycle_sections.get("PROBLEMAS", []),
        "MEJORA": effective_lace_improvement_sections(cycle_sections),
        "COMPLETADO": cycle_sections.get("COMPLETADO", []),
    }
    lines = [
        f"# Ciclo {cycle_number:02d}",
        "",
        f"- Estado: {cycle_summary.get('stage')}",
        f"- Foco: {cycle_summary.get('focus')}",
        f"- Valido para cierre LACE: {'si' if cycle_summary.get('valid') else 'no'}",
        f"- Problemas registrados: {'si' if cycle_summary.get('hasProblems') else 'no'}",
        f"- Mejora registrada: {'si' if cycle_summary.get('hasImprovements') else 'no'}",
        f"- Validacion registrada: {'si' if cycle_summary.get('hasCompleted') else 'no'}",
        "",
        "## Resumen",
        cycle_summary.get("description") or "",
    ]
    for section_name in ("PROBLEMAS", "MEJORA", "COMPLETADO"):
        bodies = effective_sections.get(section_name, [])
        lines.extend(["", f"## {section_name}"])
        if bodies:
            lines.append("```text")
            lines.append(str(bodies[-1]).strip())
            lines.append("```")
        else:
            lines.append("Pendiente.")
    return "\n".join(lines).strip() + "\n"


def build_lace_cycle_placeholder_markdown(cycle_number: int) -> str:
    focus = lace_focus_for_cycle(cycle_number)
    return (
        f"# Ciclo {cycle_number:02d}\n\n"
        "- Estado: pending\n"
        f"- Foco: {focus}\n"
        "- Valido para cierre LACE: no\n\n"
        "## Resumen\n"
        "Este ciclo todavía no tiene evidencia real en LACE_LOG.md.\n"
    )


def clamp_lace_required_cycles(value: int) -> int:
    try:
        cycles = int(value)
    except (TypeError, ValueError):
        return 0
    if cycles <= 0:
        return 0
    return min(LACE_MAX_REQUIRED_CYCLES, max(LACE_MIN_REQUIRED_CYCLES, cycles))


def detect_lace_required_cycles(text: str) -> int:
    patterns = (
        r"completado\s+(\d+)\s+ciclos",
        r"completar\s+(\d+)\s+ciclos",
        r"mínimo\s+de\s+(\d+)\s+ciclos",
        r"mínimo\s+(\d+)\s+ciclos",
        r"(\d+)\s+ciclos\s+obligatorios",
        r"CICLOS\s+1\s+AL\s+(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clamp_lace_required_cycles(int(match.group(1)))
    return LACE_MAX_REQUIRED_CYCLES


def is_observational_smoke_requirement(requirement: str) -> bool:
    """Legacy compatibility shim: smoke only comes from explicit config now."""

    return normalize_agent_runtime_mode() == "smoke"


def is_code_generation_requirement(requirement: str) -> bool:
    text = str(requirement or "").strip()
    if not text:
        return False
    return bool(CODE_ACTION_PATTERN.search(text)) and bool(CODE_TARGET_PATTERN.search(text))


def build_habla_code_execution_prompt(requirement: str) -> str:
    normalized_requirement = str(requirement or "").strip()
    return (
        "PROTOCOLO HABLA PARA EJECUCION DE PROYECTO DE CODIGO\n\n"
        "OBJETIVO:\n"
        "Construir y validar en disco el proyecto solicitado por el usuario, sin tratar la tarea como una pregunta teórica.\n\n"
        "INSTRUCCIONES OPERATIVAS:\n"
        "1. Interpreta el requerimiento como trabajo de implementacion real sobre archivos.\n"
        "2. Usa el filesystem del proyecto como fuente primaria de evidencia.\n"
        "3. Si falta contexto, crea una base minima coherente y luego iterala con validacion tecnica.\n"
        "4. No bloquees la ejecucion por ausencia de evidencia externa; la evidencia debe surgir del codigo, pruebas y archivos creados.\n"
        "5. Reporta limites reales del entorno solo despues de intentar validar.\n\n"
        "REQUERIMIENTO HUMANO:\n"
        f"{normalized_requirement}\n"
    )


def validate_lace_policy_text(text: str) -> None:
    missing = [layer for layer in LACE_REQUIRED_LAYERS if layer not in text]
    if missing:
        raise ValueError("LACE.md no contiene todas las capas requeridas: " + ", ".join(missing))


def build_lace_compact_directive(policy_path: Path, log_path: Path, required_cycles: int) -> str:
    return (
        "LACE v2.0 ESTA ACTIVO Y FUE LEIDO ANTES DE ARRANCAR EL AGENTE.\n"
        f"REGLA ADAPTATIVA: completa minimo {LACE_MIN_REQUIRED_CYCLES} ciclos y maximo {required_cycles}; "
        "puedes cerrar temprano solo si no hay tareas pendientes, scanner OK, sandbox OK, integrity OK y findings sin activos.\n"
        "Cada ciclo debe usar HABLA por capas: interpretación, clasificación, planificación, ReAct, evidencia, triangulación, confianza, autocrítica, memoria y acción final.\n"
        "Cada ciclo debe abrir secciones literales `[CICLO-n PROBLEMAS]`, `[CICLO-n MEJORA]` y `[CICLO-n COMPLETADO]`.\n"
        f"ANTES DE CUALQUIER ACCIÓN: lee `{policy_path.name}` completo y escribe tu comprensión inicial en `{log_path.name}`.\n"
        "Antes de modificar código, escribe THOUGHT/ACTION/OBSERVATION dentro de `[CICLO-n MEJORA]` en LACE_LOG.md.\n"
        "Antes de cerrar, verifica la puerta de cierre LACE y las compuertas de calidad persistidas.\n"
        "Si una validación falla por entorno o herramienta, corrige la estrategia y continúa el siguiente ciclo en vez de cerrar."
    )


def build_lace_cycle_plan(required_cycles: int) -> str:
    lines = []
    for cycle_number in range(1, required_cycles + 1):
        focus = LACE_AREAS[(cycle_number - 1) % len(LACE_AREAS)]
        lines.append(f"{cycle_number}. {focus.capitalize()}.")
    return "\n".join(lines)


def initialize_lace_log(log_path: Path, *, project_prompt: str, policy_path: Path, required_cycles: int) -> None:
    if log_path.exists():
        try:
            if log_path.read_text(encoding="utf-8").strip():
                return
        except OSError:
            return

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        (
            "# LACE_LOG.md\n\n"
            "[INIT]\n"
            f"Fecha UTC: {datetime.now(timezone.utc).isoformat()}\n"
            f"LACE leído desde: {policy_path}\n"
            f"Regla activa: {required_cycles} ciclos maximos; minimo {LACE_MIN_REQUIRED_CYCLES}; salida temprana con compuertas limpias.\n\n"
            "[COMPRENSIÓN DEL PROYECTO]\n"
            f"{project_prompt.strip()}\n\n"
            f"[PLAN PARA {required_cycles} CICLOS]\n"
            f"{build_lace_cycle_plan(required_cycles)}\n\n"
        ),
        encoding="utf-8",
    )


def scaffold_lace_cycles(log_path: Path, required_cycles: int) -> None:
    try:
        current = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    except OSError:
        return
    if "[CICLO-1 PROBLEMAS]" in current:
        return

    with log_path.open("a", encoding="utf-8") as handle:
        for cycle_number in range(1, required_cycles + 1):
            focus = LACE_AREAS[(cycle_number - 1) % len(LACE_AREAS)]
            handle.write(
                (
                    f"[CICLO-{cycle_number} PROBLEMAS]\n"
                    f"THOUGHT: analizaré el estado actual enfocado en {focus}.\n"
                    "TRIANGULACIÓN: técnico / funcional / humano.\n"
                    "CONFIANZA: lógica, UI, rendimiento, errores, seguridad.\n"
                    "AUTO-CRÍTICA: buscaré cierre prematuro, parches débiles u omisiones.\n\n"
                    "Problemas priorizados:\n"
                    "1. Pendiente de análisis real — severidad: media\n\n"
                    f"[CICLO-{cycle_number} MEJORA]\n"
                    f"THOUGHT: aplicar mejora concreta sobre {focus}.\n"
                    "ACTION: implementar cambio verificable.\n"
                    f"OBSERVATION esperada: el proyecto debe mejorar objetivamente en {focus}.\n\n"
                    f"[CICLO-{cycle_number} COMPLETADO]\n"
                    "OBSERVATION real: pendiente de ejecución.\n"
                    "¿Coincide con OBSERVATION esperada? PENDIENTE\n"
                    "Problemas resueltos: pendiente\n"
                    "Estado ahora vs antes: pendiente\n"
                    "¿El proyecto mejoró objetivamente? PENDIENTE\n\n"
                    "MEMORIA EPISÓDICA:\n"
                    "- Qué funcionó: pendiente\n"
                    "- Qué no funcionó: pendiente\n"
                    "- Qué evitar en el próximo ciclo: pendiente\n\n"
                    "Próximo ciclo — qué atacaré: se definirá tras validación.\n\n"
                )
            )


def count_completed_lace_cycles(log_path: Path | None) -> int:
    if log_path is None or not log_path.exists():
        return 0
    try:
        return validate_lace_log(log_path, 0)[0]
    except OSError:
        return 0


def normalize_lace_document(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    cleaned = (
        without_accents
        .replace("¿", "")
        .replace("¡", "")
        .replace("—", "-")
        .replace("–", "-")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    return re.sub(r"[ \t]+", " ", cleaned).strip().lower()


def normalize_lace_text(value: str) -> str:
    cleaned = normalize_lace_document(value)
    return re.sub(r"\s+", " ", cleaned.strip()).strip().lower()


def _has_canonical_lace_closure_marker(text: str) -> bool:
    header_lines: List[str] = []
    for raw_line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines():
        normalized_line = normalize_lace_text(raw_line)
        if normalized_line.startswith("## ") or re.match(r"^\[ciclo-\d+", normalized_line):
            break
        header_lines.append(raw_line)
    header_text = "\n".join(header_lines)
    return bool(
        re.search(
            r"^\s*-\s*v[aá]lido para cierre lace:\s*s[ií]\s*$",
            header_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )


def extract_lace_block(text: str, *, headings: List[str], stops: List[str]) -> str | None:
    normalized_text = normalize_lace_document(str(text or ""))
    heading_pattern = "|".join(headings)
    stop_pattern = "|".join(stops)
    match = re.search(
        rf"\[(?:{heading_pattern})\]\s*(?P<body>.*?)(?=\[(?:{stop_pattern})\]|\Z)",
        normalized_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match is None:
        return None
    body = match.group("body").strip()
    return body or None


def is_lace_placeholder(value: str) -> bool:
    normalized = normalize_lace_text(value)
    if not normalized:
        return True
    if re.fullmatch(r"pendiente(?: de ejecucion)?\.?", normalized, flags=re.IGNORECASE):
        return True
    if normalized in {normalize_lace_text(item) for item in LACE_PLACEHOLDER_TEXTS}:
        return True
    if normalized.startswith("el proyecto debe mejorar objetivamente en "):
        return True
    return False


def extract_lace_cycle_sections(text: str) -> Dict[int, Dict[str, List[str]]]:
    sections: Dict[int, Dict[str, List[str]]] = {}
    matches = list(LACE_CYCLE_SECTION_PATTERN.finditer(text or ""))
    for index, match in enumerate(matches):
        cycle_number = int(match.group("cycle"))
        section_name = str(match.group("section")).upper()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.setdefault(cycle_number, {}).setdefault(section_name, []).append(body)
    return sections


def extract_embedded_lace_improvement_section(section_text: str) -> str | None:
    raw_lines = str(section_text or "").splitlines()
    for index, raw_line in enumerate(raw_lines):
        line = normalize_lace_text(raw_line)
        if not line.startswith("thought:"):
            continue
        labels_after_thought: List[str] = []
        for next_line in raw_lines[index + 1:]:
            normalized_next = normalize_lace_text(next_line)
            if not normalized_next:
                continue
            if not is_lace_label_line(next_line):
                continue
            labels_after_thought.append(normalized_next)
            if len(labels_after_thought) >= 2:
                break
        if (
            len(labels_after_thought) >= 2
            and labels_after_thought[0].startswith("action:")
            and labels_after_thought[1].startswith("observation esperada:")
        ):
            body = "\n".join(raw_lines[index:]).strip()
            return body or None
    return None


def effective_lace_improvement_sections(cycle_sections: Dict[str, List[str]]) -> List[str]:
    explicit_sections = [str(section).strip() for section in cycle_sections.get("MEJORA", []) if str(section).strip()]
    if explicit_sections:
        return explicit_sections

    inferred_sections = []
    for section in cycle_sections.get("PROBLEMAS", []):
        inferred = extract_embedded_lace_improvement_section(section)
        if inferred:
            inferred_sections.append(inferred)
    return inferred_sections


def _normalized_lace_labels(labels: str | List[str] | tuple[str, ...]) -> List[str]:
    if isinstance(labels, str):
        items = [labels]
    else:
        items = list(labels)
    return [normalize_lace_text(label) for label in items if normalize_lace_text(label)]


def is_lace_label_line(value: str) -> bool:
    line = normalize_lace_text(value)
    if not line or line.startswith(("- ", "* ")):
        return False
    if line.startswith("["):
        return True
    return any(line.startswith(prefix) for prefix in LACE_LABEL_PREFIXES)


def extract_lace_line_value(section_text: str, labels: str | List[str] | tuple[str, ...]) -> str | None:
    normalized_labels = _normalized_lace_labels(labels)
    raw_lines = str(section_text or "").splitlines()
    for index, raw_line in enumerate(raw_lines):
        line = normalize_lace_text(raw_line)
        if not line:
            continue
        for label in normalized_labels:
            if line.startswith(label):
                value = line[len(label):].strip()
                if value:
                    return value
                collected = []
                for next_line in raw_lines[index + 1:]:
                    normalized_next = normalize_lace_text(next_line)
                    if not normalized_next:
                        if collected:
                            break
                        continue
                    if is_lace_label_line(next_line):
                        break
                    collected.append(normalized_next)
                return " ".join(collected).strip() or None
    return None


def extract_lace_bullet_value(section_text: str, labels: str | List[str] | tuple[str, ...]) -> str | None:
    normalized_labels = _normalized_lace_labels(labels)
    for raw_line in str(section_text or "").splitlines():
        line = normalize_lace_text(raw_line)
        if not line:
            continue
        for label in normalized_labels:
            for prefix in ("- ", "* "):
                candidate = f"{prefix}{label}"
                if line.startswith(candidate):
                    value = line[len(candidate):].strip()
                    return value or None
    return None


def lace_line_has_yes(section_text: str, labels: str | List[str] | tuple[str, ...]) -> bool:
    value = extract_lace_line_value(section_text, labels)
    return value is not None and value.startswith("si")


def has_real_lace_line(section_text: str, labels: str | List[str] | tuple[str, ...]) -> bool:
    value = extract_lace_line_value(section_text, labels)
    return value is not None and not is_lace_placeholder(value)


def has_real_lace_bullet(section_text: str, labels: str | List[str] | tuple[str, ...]) -> bool:
    value = extract_lace_bullet_value(section_text, labels)
    return value is not None and not is_lace_placeholder(value)


def is_valid_lace_problems_section(section_text: str) -> bool:
    if not has_real_lace_line(section_text, "THOUGHT:"):
        return False
    triangulation = extract_lace_line_value(section_text, ("TRIANGULACION:", "TRIANGULACIÓN:"))
    if triangulation is None or is_lace_placeholder(triangulation):
        return False
    normalized_triangulation = normalize_lace_text(triangulation)
    if not all(token in normalized_triangulation for token in ("tecnico", "funcional", "humano")):
        return False
    confidence = extract_lace_line_value(section_text, "CONFIANZA:")
    if confidence is None or is_lace_placeholder(confidence):
        return False
    normalized_confidence = normalize_lace_text(confidence)
    if not any(level in normalized_confidence for level in ("alta", "media", "baja")):
        return False
    if not has_real_lace_line(section_text, ("AUTO-CRITICA:", "AUTO-CRÍTICA:")):
        return False
    prioritized_items = [match.group(1).strip() for match in re.finditer(r"^\d+\.\s+(.+)$", section_text, flags=re.MULTILINE)]
    return any(not is_lace_placeholder(item) for item in prioritized_items)


def is_valid_lace_improvement_section(section_text: str) -> bool:
    return (
        has_real_lace_line(section_text, "THOUGHT:")
        and has_real_lace_line(section_text, "ACTION:")
        and has_real_lace_line(section_text, "OBSERVATION esperada:")
    )


def is_valid_lace_completed_section(section_text: str) -> bool:
    return (
        has_real_lace_line(section_text, "OBSERVATION real:")
        and lace_line_has_yes(section_text, ("¿Coincide con OBSERVATION esperada?", "Coincide con OBSERVATION esperada?"))
        and has_real_lace_line(section_text, "Problemas resueltos:")
        and has_real_lace_line(section_text, "Estado ahora vs antes:")
        and lace_line_has_yes(section_text, ("¿El proyecto mejoró objetivamente?", "¿El proyecto mejoro objetivamente?", "El proyecto mejoro objetivamente?"))
        and has_real_lace_bullet(section_text, ("Qué funcionó:", "Que funciono:"))
        and has_real_lace_bullet(section_text, ("Qué no funcionó:", "Que no funciono:"))
        and has_real_lace_bullet(
            section_text,
            (
                "Qué evitar en el próximo ciclo:",
                "Que evitar en el proximo ciclo:",
                "Qué evitar en el próximo cierre:",
                "Que evitar en el proximo cierre:",
            ),
        )
        and has_real_lace_line(
            section_text,
            (
                "Próximo ciclo — qué atacaré:",
                "Proximo ciclo - que atacare:",
                "Proximo ciclo — que atacare:",
                "Próximo ciclo:",
                "Proximo ciclo:",
            ),
        )
    )


def has_valid_lace_base(text: str) -> bool:
    normalized = normalize_lace_document(text)
    match = re.search(r"^\[base\]\s*(.+)\nestado actual:\s*(.+)$", normalized, flags=re.MULTILINE)
    if match is None:
        return False
    return not is_lace_placeholder(match.group(1)) and not is_lace_placeholder(match.group(2))


def has_valid_lace_comprehension(text: str) -> bool:
    body = extract_lace_block(
        text,
        headings=[r"comprension del proyecto", r"comprension inicial", r"comprension"],
        stops=[r"plan para \d+ ciclos", r"plan de construccion", r"plan inicial(?: de ciclos)?", r"plan de ciclos"],
    )
    if body is None:
        return False
    return not is_lace_placeholder(body)


def has_valid_lace_plan(text: str) -> bool:
    body = extract_lace_block(
        text,
        headings=[r"plan para \d+ ciclos", r"plan de construccion", r"plan inicial(?: de ciclos)?", r"plan de ciclos"],
        stops=[r"base(?: analisis| mejora)?", r"ciclo-\d+ [a-z]+", r"ciclo-\d+", r"puerta de cierre"],
    )
    if body is None:
        return False
    plan_lines = []
    for line in body.splitlines():
        normalized_line = normalize_lace_text(line)
        if re.match(r"^\d+\.\s+", normalized_line):
            plan_lines.append(normalized_line)
            continue
        if re.match(r"^-+\s*(?:base|ciclo\s+\d+)\b", normalized_line):
            plan_lines.append(normalized_line)
    return len(plan_lines) > 0


def inspect_lace_cycle_reports(text: str, required_cycles: int) -> List[Dict[str, Any]]:
    sections_by_cycle = extract_lace_cycle_sections(text)
    cycle_limit = required_cycles if required_cycles > 0 else max(sections_by_cycle.keys(), default=0)
    cycle_reports: List[Dict[str, Any]] = []
    for cycle_number in range(1, cycle_limit + 1):
        cycle_sections = sections_by_cycle.get(cycle_number, {})
        problems = cycle_sections.get("PROBLEMAS", [])
        improvements = effective_lace_improvement_sections(cycle_sections)
        completed = cycle_sections.get("COMPLETADO", [])
        valid_problems = any(is_valid_lace_problems_section(section) for section in problems)
        valid_improvements = any(is_valid_lace_improvement_section(section) for section in improvements)
        valid_completed = any(is_valid_lace_completed_section(section) for section in completed)
        missing_parts = []
        if not valid_problems:
            missing_parts.append("analizar/criticar")
        if not valid_improvements:
            missing_parts.append("mejorar")
        if not valid_completed:
            missing_parts.append("validar")
        cycle_reports.append(
            {
                "cycle": cycle_number,
                "sections": cycle_sections,
                "hasProblems": bool(problems),
                "hasImprovements": bool(improvements),
                "hasCompleted": bool(completed),
                "validProblems": valid_problems,
                "validImprovements": valid_improvements,
                "validCompleted": valid_completed,
                "valid": valid_problems and valid_improvements and valid_completed,
                "missingParts": missing_parts,
            }
        )
    return cycle_reports


def validate_lace_log(log_path: Path | None, required_cycles: int) -> tuple[int, List[str]]:
    if log_path is None or not log_path.exists():
        return 0, ["No existe LACE_LOG.md."]
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return 0, ["No fue posible leer LACE_LOG.md."]

    completed_cycles = 0
    invalid_cycles = []
    for cycle_report in inspect_lace_cycle_reports(text, required_cycles):
        cycle_number = int(cycle_report["cycle"])
        if cycle_report["valid"]:
            completed_cycles += 1
            continue

        invalid_cycles.append(f"{cycle_number} ({', '.join(cycle_report['missingParts'])})")

    issues = []
    if not has_valid_lace_comprehension(text):
        issues.append("falta comprensión inicial real")
    if not has_valid_lace_plan(text):
        issues.append("falta plan inicial de ciclos")
    if not has_valid_lace_base(text):
        issues.append("falta sección [BASE] con estado actual")
    if invalid_cycles:
        issues.append("ciclos incompletos: " + ", ".join(invalid_cycles[:5]))
    return completed_cycles, issues


def lace_closure_status(log_path: Path | None, required_cycles: int) -> tuple[bool, str]:
    completed_cycles, issues = validate_lace_log(log_path, required_cycles)
    if completed_cycles < required_cycles:
        suffix = f" {'; '.join(issues)}." if issues else ""
        return False, f"Cierre bloqueado por LACE: {completed_cycles}/{required_cycles} ciclos válidos.{suffix}"
    if issues:
        return False, "Cierre bloqueado por LACE: " + "; ".join(issues) + "."
    return True, "Puerta LACE superada."


def lace_cycle_stage_color(stage: str, *, is_current: bool = False) -> str:
    normalized = str(stage or "").lower()
    if normalized == "failed":
        return "#ef4444"
    if is_current or normalized in {"analyzing", "improving", "pending"}:
        return "#ef4444"
    if normalized in {"validated", "completed"}:
        return "#a3e635"
    return "#94a3b8"


@dataclass(frozen=True)
class LaceContext:
    policy_text: str
    directive: str
    policy_path: Path
    log_path: Path
    required_cycles: int


class AgentRuntimeControlPlaneError(RuntimeError):
    """Raised when the task control plane cannot prepare or run a task."""

    def __init__(self, code: str, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass
class AgentSession:
    session_id: str
    project_name: str
    project_slug: str
    project_dir: Path
    requirement: str
    prompt: str
    command: List[str]
    habla_prompt: str = ""
    habla_available: bool = False
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    ended_at: str | None = None
    first_output_at: str | None = None
    status: str = "queued"
    output: str = ""
    returncode: int | None = None
    pid: int | None = None
    first_visual_event_at: str | None = None
    last_visual_event_at: str | None = None
    last_heartbeat_at: str | None = None
    visual_event_count: int = 0
    progress_percent: int = 0
    progress_label: str = "En cola"
    error_code: str | None = None
    error_message: str | None = None
    stop_requested: bool = False
    failure_event_emitted: bool = field(default=False, repr=False)
    start_monotonic: float | None = field(default=None, repr=False)
    last_agent_activity_monotonic: float | None = field(default=None, repr=False)
    first_visual_monotonic: float | None = field(default=None, repr=False)
    last_visual_monotonic: float | None = field(default=None, repr=False)
    last_heartbeat_monotonic: float | None = field(default=None, repr=False)
    process: subprocess.Popen[bytes] | None = field(default=None, repr=False)
    master_fd: int | None = field(default=None, repr=False)
    event_file: Path | None = field(default=None, repr=False)
    terminal_file: Path | None = field(default=None, repr=False)
    lace_policy_path: Path | None = field(default=None, repr=False)
    lace_log_path: Path | None = field(default=None, repr=False)
    habla_preflight_path: Path | None = field(default=None, repr=False)
    lace_required_cycles: int = 0
    complexity_estimate: Dict[str, Any] = field(default_factory=dict, repr=False)
    smoke_mode: bool = False
    runtime_mode: str = "build"
    control_plane_enabled: bool = False
    control_plane_runtime_dir: str | None = None
    active_task_id: str | None = None
    active_task: Dict[str, Any] = field(default_factory=dict, repr=False)
    directive: Dict[str, Any] = field(default_factory=dict, repr=False)
    directive_json_path: str | None = None
    directive_markdown_path: str | None = None
    directive_source_hash: str | None = None
    reviewer_log_path: str | None = None
    task_result: Dict[str, Any] = field(default_factory=dict, repr=False)
    validation_result: Dict[str, Any] = field(default_factory=dict, repr=False)
    recovery_result: Dict[str, Any] = field(default_factory=dict, repr=False)
    checkpoint_result: Dict[str, Any] = field(default_factory=dict, repr=False)
    cyberlace_decisions: List[Dict[str, Any]] = field(default_factory=list, repr=False)
    event_offset: int = field(default=0, repr=False)
    habla_state: Dict[str, Any] = field(default_factory=dict, repr=False)
    lace_cycle_states: List[Dict[str, Any]] = field(default_factory=list, repr=False)
    lace_cycle_signatures: Dict[int, str] = field(default_factory=dict, repr=False)
    lace_log_digest: str = field(default="", repr=False)
    retry_count: int = 0
    retry_limit: int = SESSION_IDLE_RETRY_LIMIT
    retry_pending: bool = False
    last_retry_reason: str | None = None
    last_retry_checkpoint: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        lace_completed_cycles = count_completed_lace_cycles(self.lace_log_path) if self.lace_required_cycles else 0
        effective_status = self.status
        if effective_status == "running" and self.pid is None and self.process is None:
            effective_status = "preparing"
        return {
            "sessionId": self.session_id,
            "projectName": self.project_name,
            "projectSlug": self.project_slug,
            "projectDir": str(self.project_dir),
            "requirement": self.requirement,
            "status": effective_status,
            "output": self.output,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
            "firstOutputAt": self.first_output_at,
            "returncode": self.returncode,
            "pid": self.pid,
            "firstVisualEventAt": self.first_visual_event_at,
            "lastVisualEventAt": self.last_visual_event_at,
            "lastHeartbeatAt": self.last_heartbeat_at,
            "visualEventCount": self.visual_event_count,
            "progressPercent": self.progress_percent,
            "progressLabel": self.progress_label,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "stopRequested": self.stop_requested,
            "command": self.command,
            "terminalLogPath": str(self.terminal_file) if self.terminal_file is not None else None,
            "lacePolicyPath": str(self.lace_policy_path) if self.lace_policy_path is not None else None,
            "laceLogPath": str(self.lace_log_path) if self.lace_log_path is not None else None,
            "hablaPreflightPath": str(self.habla_preflight_path) if self.habla_preflight_path is not None else None,
            "laceRequiredCycles": self.lace_required_cycles or None,
            "complexityEstimate": self.complexity_estimate or None,
            "laceCompletedCycles": lace_completed_cycles,
            "smokeMode": self.smoke_mode,
            "runtimeMode": self.runtime_mode,
            "laceCycles": self.lace_cycle_states,
            "retryCount": self.retry_count,
            "retryLimit": self.retry_limit,
            "retryPending": self.retry_pending,
            "lastRetryReason": self.last_retry_reason,
            "lastRetryCheckpoint": self.last_retry_checkpoint,
            "habla": {
                "available": self.habla_available,
                "prompt": self.habla_prompt,
                "state": self.habla_state,
            },
            "controlPlane": {
                "enabled": self.control_plane_enabled,
                "runtimeDir": self.control_plane_runtime_dir,
                "activeTaskId": self.active_task_id,
                "activeTask": self.active_task or None,
                "directiveJsonPath": self.directive_json_path,
                "directiveMarkdownPath": self.directive_markdown_path,
                "directiveSourceHash": self.directive_source_hash,
                "reviewerLogPath": self.reviewer_log_path,
                "taskResult": self.task_result or None,
                "validation": self.validation_result or None,
                "recovery": self.recovery_result or None,
                "checkpoint": self.checkpoint_result or None,
            },
            "cyberlace": {
                "decisions": self.cyberlace_decisions[-12:],
            },
        }


class AgentRuntime:
    def __init__(
        self,
        *,
        app_root: Path,
        workspace_root: Path,
        projects_root: Path,
        codex_cmd: str,
        prompt_converter: Callable[[str], Any] | None,
        graph_provider: Callable[[], Dict[str, Any]],
        graph_sync: Callable[[bool], Dict[str, Any]],
        terminal_emitter: Callable[[Dict[str, Any]], None],
        session_emitter: Callable[[Dict[str, Any]], None],
        visual_event_handler: Callable[[Dict[str, Any]], None],
        reviewer_event_handler: Callable[[Dict[str, Any]], None] | None = None,
        lace_policy_source: Path | None = None,
    ) -> None:
        self.app_root = app_root
        self.repo_root = REPO_ROOT
        self.workspace_root = workspace_root
        self.projects_root = projects_root
        self.codex_cmd = codex_cmd
        self.codex_launch_path = build_preferred_shell_path(os.environ.get("PATH"))
        self.codex_command_tokens = resolve_codex_command_tokens(codex_cmd, path_value=self.codex_launch_path)
        self.codex_exec_sandbox_mode = str(
            os.environ.get("VISTA_CODEX_EXEC_SANDBOX_MODE") or DEFAULT_INNER_CODEX_SANDBOX_MODE
        ).strip() or DEFAULT_INNER_CODEX_SANDBOX_MODE
        self.codex_exec_approval_policy = str(
            os.environ.get("VISTA_CODEX_EXEC_APPROVAL_POLICY") or DEFAULT_INNER_CODEX_APPROVAL_POLICY
        ).strip() or DEFAULT_INNER_CODEX_APPROVAL_POLICY
        if self.codex_exec_sandbox_mode == "danger-full-access" and not env_flag_enabled(
            os.environ.get("VISTA_ALLOW_DANGER_FULL_ACCESS_CODEX"),
            default=False,
        ):
            self.codex_exec_sandbox_mode = DEFAULT_INNER_CODEX_SANDBOX_MODE
        self.codex_exec_extra_args = shlex.split(str(os.environ.get("VISTA_CODEX_EXEC_EXTRA_ARGS") or "").strip())
        self.codex_exec_use_full_auto = env_flag_enabled(os.environ.get("VISTA_CODEX_EXEC_USE_FULL_AUTO"), default=False)
        if self.codex_exec_use_full_auto and not env_flag_enabled(
            os.environ.get("VISTA_ALLOW_FULL_AUTO_CODEX"),
            default=False,
        ):
            self.codex_exec_use_full_auto = False
        self.prompt_converter = prompt_converter
        self.graph_provider = graph_provider
        self.graph_sync = graph_sync
        self.terminal_emitter = terminal_emitter
        self.session_emitter = session_emitter
        self.visual_event_handler = visual_event_handler
        self.reviewer_event_handler = reviewer_event_handler
        self.bridge_python = sys.executable or "python3"
        self.bridge_script = self.app_root / "backend" / "vista_agent_bridge.py"
        self.lace_policy_source = (lace_policy_source or (self.app_root.parent.parent / "habla_agentic_engine_v5_1_lace_visual" / "LACE.md")).expanduser()
        self.control_plane_enabled = env_flag_enabled(os.environ.get("VISTA_CONTROL_PLANE_ENABLED"), default=True)
        configured_runtime_dir = str(os.environ.get("VISTA_CONTROL_PLANE_RUNTIME_DIR") or "").strip()
        self.control_plane_runtime_dir = Path(configured_runtime_dir).expanduser().resolve() if configured_runtime_dir else None
        sprint_value = str(os.environ.get("VISTA_CONTROL_PLANE_SPRINT") or "").strip()
        self.control_plane_sprint_number = int(sprint_value) if sprint_value.isdigit() else None
        self.sessions: Dict[str, AgentSession] = {}
        self.lock = threading.Lock()
        self.ensure_workspace()

    def ensure_workspace(self) -> None:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.projects_root.mkdir(parents=True, exist_ok=True)
        ensure_file(self.workspace_root / "README.md", build_workspace_readme(self.projects_root))

    def list_projects(self) -> List[Dict[str, Any]]:
        self.ensure_workspace()
        projects = []
        for project_dir in sorted(self.projects_root.iterdir(), key=lambda item: item.name):
            if not project_dir.is_dir():
                continue

            metadata = self._load_project_metadata(project_dir)
            projects.append(
                {
                    "name": metadata.get("name") or titleize(project_dir.name),
                    "slug": project_dir.name,
                    "path": str(project_dir),
                    "relativePath": self._relative_path(project_dir),
                    "updatedAt": metadata.get("updatedAt") or utc_now(),
                    "createdAt": metadata.get("createdAt") or utc_now(),
                    "fileCount": count_source_files(project_dir),
                    "demoLabel": metadata.get("demoLabel") or "",
                    "description": metadata.get("description") or "",
                    "demoRole": metadata.get("demoRole") or "",
                    "systemDemo": bool(metadata.get("systemDemo")),
                    "nativeExample": bool(metadata.get("nativeExample")),
                    "evaluatedProject": bool(metadata.get("evaluatedProject")),
                    "learningMode": bool(metadata.get("learningMode")),
                    "protected": bool(metadata.get("protected")),
                    "protectedReason": metadata.get("protectedReason") or "",
                }
            )
        return projects

    def create_project(
        self,
        project_name: str,
        *,
        bootstrap: bool = True,
        ensure_unique: bool = False,
        preferred_slug: str | None = None,
    ) -> Dict[str, Any]:
        self.ensure_workspace()
        base_name = str(project_name or "").strip() or "nuevo-proyecto"
        normalized_preferred_slug = str(preferred_slug or "").strip()
        base_slug = slugify(normalized_preferred_slug) if normalized_preferred_slug else slugify(base_name)
        project_slug = base_slug
        display_name = base_name
        if ensure_unique:
            suffix = 2
            while (self.projects_root / project_slug).exists():
                project_slug = f"{base_slug}-{suffix}"
                display_name = f"{base_name}-{suffix}"
                suffix += 1
        project_dir = self.projects_root / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)

        for folder_name in PROJECT_FOLDERS:
            (project_dir / folder_name).mkdir(parents=True, exist_ok=True)

        if bootstrap:
            ensure_file(project_dir / "README.md", build_project_readme(display_name or titleize(project_slug), project_slug))
            ensure_file(project_dir / "AGENTS.md", build_project_agents(display_name or titleize(project_slug)))
            ensure_file(project_dir / "docs" / "architecture-notes.md", build_architecture_notes(display_name or titleize(project_slug)))
            ensure_file(project_dir / "src" / "main.js", build_project_main(display_name or titleize(project_slug)))
            ensure_file(project_dir / "src" / "service.js", build_project_service(display_name or titleize(project_slug)))
            ensure_file(project_dir / "shared" / "runtime.json", build_project_runtime(display_name or titleize(project_slug)))

        metadata_path = project_dir / ".agent-project.json"
        metadata = self._load_project_metadata(project_dir)
        if metadata.get("name") and not ensure_unique:
            display_name = str(metadata.get("name") or display_name)
        metadata.update(
            {
                "name": display_name or metadata.get("name") or titleize(project_slug),
                "slug": project_slug,
                "projectDir": str(project_dir),
                "createdAt": metadata.get("createdAt") or utc_now(),
                "updatedAt": utc_now(),
            }
        )
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
        return {
            "name": metadata["name"],
            "slug": project_slug,
            "path": str(project_dir),
            "relativePath": self._relative_path(project_dir),
            "updatedAt": metadata["updatedAt"],
            "createdAt": metadata["createdAt"],
            "fileCount": count_source_files(project_dir),
        }

    def get_session(self, session_id: str) -> Dict[str, Any] | None:
        with self.lock:
            session = self.sessions.get(session_id)
            return session.to_dict() if session else None

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [session.to_dict() for session in sorted(self.sessions.values(), key=lambda item: item.created_at)]

    def _find_active_session_for_project(self, project_slug: str) -> AgentSession | None:
        normalized_slug = str(project_slug or "").strip()
        if not normalized_slug:
            return None
        with self.lock:
            for session in sorted(self.sessions.values(), key=lambda item: item.created_at, reverse=True):
                if session.project_slug != normalized_slug:
                    continue
                if session.status not in {"queued", "preparing", "starting", "running"}:
                    continue
                if self._mark_orphaned_control_plane_session_locked(session):
                    continue
                return session
        return None

    def _mark_orphaned_control_plane_session_locked(self, session: AgentSession) -> bool:
        if not session.control_plane_enabled or session.status not in {"queued", "preparing", "starting", "running"}:
            return False
        if session.process is not None or session.pid is not None:
            return False
        last_activity = session.last_agent_activity_monotonic or session.start_monotonic
        if last_activity is None or time.monotonic() - last_activity < SESSION_IDLE_TIMEOUT_SECONDS:
            return False
        runtime_dir = Path(session.control_plane_runtime_dir or session.project_dir / "runtime")
        try:
            queue = TaskQueue(StateStore(runtime_dir), bootstrap_empty=True)  # type: ignore[operator]
            tasks = queue.list()
        except Exception:
            return False
        has_running = any(str(task.get("status") or "") == "running" for task in tasks)
        has_pending = any(str(task.get("status") or "") == "pending" for task in tasks)
        if has_running or not has_pending:
            return False
        now_value = utc_now()
        session.status = "stopped"
        session.returncode = -15
        session.error_code = "stale_control_plane_without_worker"
        session.error_message = "Sesion anterior sin worker vivo; se libera para reanudar tareas pendientes."
        session.progress_label = session.error_message
        session.updated_at = now_value
        session.ended_at = now_value
        session.process = None
        session.pid = None
        return True

    def _cyberlace_record_decision(self, session_id: str | None, decision: Dict[str, Any] | None) -> None:
        if not session_id or not isinstance(decision, dict):
            return
        compact = {
            "timestamp": decision.get("timestamp") or utc_now(),
            "stage": decision.get("stage"),
            "mode": decision.get("mode"),
            "action": decision.get("action"),
            "runtimeAction": decision.get("runtimeAction"),
            "riskScore": decision.get("riskScore"),
            "severity": decision.get("severity"),
            "reason": decision.get("reason"),
            "eventId": decision.get("eventId"),
            "ok": decision.get("ok"),
        }
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            session.cyberlace_decisions = [*session.cyberlace_decisions[-31:], compact]
            session.updated_at = utc_now()

    def _cyberlace_guard(
        self,
        stage: str,
        *,
        agent_id: str,
        user_id: str = "local",
        content: Any = "",
        context: Dict[str, Any] | None = None,
        session_id: str | None = None,
        tool_name: str | None = None,
        tool_args: Dict[str, Any] | None = None,
        action_type: str | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        resolved_session_id = session_id or "agent-runtime"
        context = context or {}
        try:
            if stage == "prompt" and cyberlace_before_prompt is not None:
                decision = cyberlace_before_prompt(agent_id, user_id, str(content or ""), context, resolved_session_id)
            elif stage == "memory" and cyberlace_before_memory_read is not None:
                decision = cyberlace_before_memory_read(agent_id, user_id, str(content or ""), context, resolved_session_id)
            elif stage == "tool" and cyberlace_before_tool_call is not None:
                decision = cyberlace_before_tool_call(
                    agent_id,
                    user_id,
                    tool_name or "unknown_tool",
                    tool_args or {},
                    context,
                    resolved_session_id,
                )
            elif stage == "output" and cyberlace_after_model_output is not None:
                decision = cyberlace_after_model_output(agent_id, user_id, str(content or ""), context, resolved_session_id)
            elif stage == "external-action" and cyberlace_before_external_action is not None:
                decision = cyberlace_before_external_action(
                    agent_id,
                    user_id,
                    action_type or "external_action",
                    payload or {},
                    context,
                    resolved_session_id,
                )
            else:
                decision = {"ok": True, "mode": "off", "stage": stage, "runtimeAction": "ALLOW", "allowed": True}
        except Exception as error:  # pragma: no cover - adapter normally converts failures to decisions.
            decision = {
                "ok": False,
                "mode": "monitor",
                "stage": stage,
                "runtimeAction": "ALLOW",
                "allowed": True,
                "reason": f"CyberLACE hook failure ignored by runtime: {error}",
                "riskScore": 0,
            }
        self._cyberlace_record_decision(session_id, decision if isinstance(decision, dict) else None)
        return decision if isinstance(decision, dict) else {"ok": False, "runtimeAction": "ALLOW", "allowed": True}

    def _cyberlace_should_block(self, decision: Dict[str, Any] | None) -> bool:
        if not isinstance(decision, dict):
            return False
        runtime_action = str(decision.get("runtimeAction") or decision.get("action") or "").upper()
        if decision.get("blocked") is True or decision.get("blocksRuntime") is True:
            return True
        if runtime_action in {"BLOCK", "QUARANTINE", "HUMAN_REVIEW"}:
            return True
        if should_block_action is not None:
            return bool(should_block_action(decision))
        return False

    def _cyberlace_should_redact(self, decision: Dict[str, Any] | None) -> bool:
        if not isinstance(decision, dict):
            return False
        if should_redact_payload is not None:
            return bool(should_redact_payload(decision))
        return str(decision.get("runtimeAction") or "").upper() == "REDACT" and decision.get("modified_payload") is not None

    def _cyberlace_block_message(self, decision: Dict[str, Any] | None, *, stage: str) -> str:
        if not isinstance(decision, dict):
            return f"CyberLACE blocked {stage}."
        action = decision.get("runtimeAction") or decision.get("action") or "BLOCK"
        reason = decision.get("reason") or "decision without reason"
        return f"CyberLACE {action} en {stage}: {reason}"

    def _cyberlace_document_decision(
        self,
        *,
        requirement: str,
        project_dir: Path,
        project_slug: str,
        session_id: str | None,
        task: Dict[str, Any] | None = None,
        directive: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if inspect_runtime_document_inputs is None:
            return {
                "ok": False,
                "mode": "hard-gate",
                "stage": "document-preflight",
                "action": "QUARANTINE",
                "runtimeAction": "QUARANTINE",
                "allowed": False,
                "blocked": True,
                "blocksRuntime": True,
                "severity": "CRITICAL",
                "riskScore": 100.0,
                "message": "PELIGRO: CyberLACE document guard no esta disponible; runtime negado por seguridad.",
                "reason": "CyberLACE document guard unavailable; fail closed before Codex can read local files.",
                "evidence": [{"type": "document_guard_unavailable", "sample": "[REDACTED]"}],
                "blockedPaths": [],
            }
        return inspect_runtime_document_inputs(
            requirement=requirement,
            project_dir=project_dir,
            repo_root=self.repo_root,
            task=task,
            directive=directive,
            session_id=session_id,
            project_slug=project_slug,
        )

    def _persist_cyberlace_document_block(
        self,
        runtime_dir: Path,
        project_slug: str,
        decision: Dict[str, Any],
        *,
        task: Dict[str, Any] | None = None,
    ) -> Dict[str, Any] | None:
        if StateStore is None:
            return None
        try:
            store = StateStore(runtime_dir)  # type: ignore[operator]
            runtime_dir.mkdir(parents=True, exist_ok=True)
            failure_event = store.append_failure(
                {
                    "kind": "cyberlace_sensitive_document_blocked",
                    "project_id": project_slug,
                    "task_id": task.get("id") if isinstance(task, dict) else None,
                    "reason": decision.get("reason"),
                    "severity": decision.get("severity"),
                    "riskScore": decision.get("riskScore"),
                    "blockedPaths": decision.get("blockedPaths") or [],
                    "deniedAction": decision.get("deniedAction"),
                    "safeAlternative": decision.get("safeAlternative"),
                    "safeNextSteps": decision.get("safeNextSteps") or [],
                    "evidence": decision.get("evidence") or [],
                }
            )
            task_id = str(task.get("id") or "session") if isinstance(task, dict) else "session"
            checkpoint_key = f"{task_id.lower()}-cyberlace-document-blocked-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            checkpoint_path = store.save_checkpoint(
                checkpoint_key,
                {
                    "reason": "cyberlace_sensitive_document_blocked",
                    "project_id": project_slug,
                    "task_id": task.get("id") if isinstance(task, dict) else None,
                    "decision": decision,
                    "failure_event": failure_event,
                },
            )
            try:
                state = store.load_project_state()
            except Exception:
                now_value = utc_now()
                state = {
                    "schema_version": 1,
                    "project_id": project_slug,
                    "status": "initialized",
                    "mode": task.get("mode", "build") if isinstance(task, dict) else "build",
                    "current_task_id": None,
                    "completed_tasks": [],
                    "failed_tasks": [],
                    "blocked_tasks": [],
                    "checkpoints": [],
                    "created_at": now_value,
                    "updated_at": now_value,
                }
            state["status"] = "blocked"
            state["current_task_id"] = None
            if isinstance(task, dict) and task.get("id"):
                state["blocked_tasks"] = _append_unique(state.get("blocked_tasks", []), str(task.get("id")))
            state["last_cyberlace_block_at"] = utc_now()
            state["last_cyberlace_block_reason"] = decision.get("reason")
            state["last_cyberlace_block_paths"] = list(decision.get("blockedPaths") or [])
            state["last_cyberlace_denied_action"] = decision.get("deniedAction")
            state["last_cyberlace_safe_alternative"] = decision.get("safeAlternative")
            state["checkpoints"] = _append_unique(state.get("checkpoints", []), checkpoint_key)
            state["updated_at"] = utc_now()
            store.save_project_state(state)
            return {"checkpoint_key": checkpoint_key, "path": str(checkpoint_path), "failure": failure_event}
        except Exception:
            return None

    def _persist_cyberlace_document_block_later(
        self,
        runtime_dir: Path,
        project_slug: str,
        decision: Dict[str, Any],
        *,
        session_id: str,
        task: Dict[str, Any] | None = None,
    ) -> None:
        def persist_block() -> None:
            checkpoint = self._persist_cyberlace_document_block(runtime_dir, project_slug, decision, task=task)
            if checkpoint is None:
                return
            snapshot: Dict[str, Any] | None = None
            with self.lock:
                live_session = self.sessions.get(session_id)
                if live_session is not None:
                    live_session.checkpoint_result = checkpoint
                    live_session.updated_at = utc_now()
                    snapshot = live_session.to_dict()
            if snapshot is not None:
                try:
                    self.session_emitter(snapshot)
                except Exception:
                    pass

        threading.Thread(target=persist_block, daemon=True).start()


    def _block_session_for_cyberlace_document(
        self,
        session: AgentSession,
        decision: Dict[str, Any],
        *,
        checkpoint: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        message = str(decision.get("message") or "PELIGRO: potencial informacion insegura. Accion negada por CyberLACE.")
        with self.lock:
            live_session = self.sessions.get(session.session_id, session)
            live_session.status = "blocked"
            live_session.returncode = 126
            live_session.pid = None
            live_session.process = None
            live_session.error_code = "cyberlace_sensitive_document_blocked"
            live_session.error_message = message
            live_session.progress_label = message
            live_session.progress_percent = max(live_session.progress_percent, 96)
            live_session.updated_at = utc_now()
            live_session.ended_at = live_session.updated_at
            live_session.cyberlace_decisions = [*live_session.cyberlace_decisions[-31:], decision]
            if checkpoint is not None:
                live_session.checkpoint_result = checkpoint
            snapshot = live_session.to_dict()
            blocked_ref = live_session
        def emit_block_events() -> None:
            self._append_output(session.session_id, f"[cyberlace] {message}\n")
            self.session_emitter(snapshot)
            self._emit_visual_runtime_event(
                blocked_ref,
                op="cyberlace_document_blocked",
                status="blocked",
                phase="cyberlace",
                error_code="cyberlace_sensitive_document_blocked",
                message=message,
                securityBlock=decision,
                checkpoint=checkpoint,
            )
            self._emit_visual_runtime_event(
                blocked_ref,
                op="session_blocked",
                status="blocked",
                phase="cyberlace",
                error_code="cyberlace_sensitive_document_blocked",
                message=message,
                securityBlock=decision,
                checkpoint=checkpoint,
            )

        threading.Thread(target=emit_block_events, daemon=True).start()
        return snapshot

    def _cyberlace_guard_text(
        self,
        stage: str,
        text: str,
        *,
        agent_id: str,
        session_id: str | None,
        context: Dict[str, Any] | None = None,
    ) -> tuple[str, Dict[str, Any]]:
        decision = self._cyberlace_guard(
            stage,
            agent_id=agent_id,
            content=text,
            context=context or {},
            session_id=session_id,
        )
        if self._cyberlace_should_redact(decision):
            modified = decision.get("modified_payload")
            if modified is not None:
                return str(modified), decision
        return text, decision

    def _cyberlace_finalize_session_output(self, session_id: str) -> None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or not session.output:
                return
            output = session.output[-16000:]
            context = {
                "project_slug": session.project_slug,
                "project_dir": str(session.project_dir),
                "runtime_mode": session.runtime_mode,
                "control_plane_enabled": session.control_plane_enabled,
            }
        decision = self._cyberlace_guard(
            "output",
            agent_id="agent-runtime",
            content=output,
            context=context,
            session_id=session_id,
        )
        if self._cyberlace_should_redact(decision):
            modified = str(decision.get("modified_payload") or "")
            with self.lock:
                session = self.sessions.get(session_id)
                if session is not None:
                    prefix = session.output[:-len(output)] if len(session.output) > len(output) else ""
                    session.output = f"{prefix}{modified}"[-MAX_OUTPUT_CHARS:]
                    session.updated_at = utc_now()
        if self._cyberlace_should_block(decision):
            with self.lock:
                session = self.sessions.get(session_id)
                if session is not None and session.status == "completed":
                    session.status = "failed"
                    session.returncode = 126
                    session.error_code = "cyberlace_output_blocked"
                    session.error_message = self._cyberlace_block_message(decision, stage="output")
                    session.progress_label = session.error_message
                    session.updated_at = utc_now()

    def _start_control_plane_session(
        self,
        requirement: str,
        project_name: str,
        *,
        project_slug: str | None,
        runtime_mode: str,
        bootstrap: bool,
        ensure_new_project: bool,
    ) -> Dict[str, Any]:
        requested_slug = slugify(str(project_slug or "").strip()) if str(project_slug or "").strip() else slugify(project_name)
        if not ensure_new_project:
            active_session = self._find_active_session_for_project(requested_slug)
            if active_session is not None:
                return active_session.to_dict()

        project = self.create_project(
            project_name,
            bootstrap=bootstrap,
            ensure_unique=ensure_new_project,
            preferred_slug=requested_slug,
        )
        project_dir = Path(project["path"]).resolve()
        project_slug = project["slug"]
        display_name = project["name"]
        session_runtime_dir = project_dir / "runtime"
        session_id = f"agent-{uuid.uuid4().hex[:10]}"
        event_file, terminal_file = self._new_control_plane_log_paths(session_runtime_dir, session_id=session_id)
        try:
            self._persist_control_plane_preparing_state(
                session_runtime_dir,
                project_slug,
                runtime_mode,
                session_id,
                reason="session_accepted_background_prepare",
            )
        except Exception:
            pass
        session = AgentSession(
            session_id=session_id,
            project_name=display_name,
            project_slug=project_slug,
            project_dir=project_dir,
            requirement=requirement,
            prompt="",
            command=[],
            event_file=event_file,
            terminal_file=terminal_file,
            status="preparing",
            progress_percent=1,
            progress_label="Preparando runtime y directiva en segundo plano",
            smoke_mode=runtime_mode == "smoke",
            runtime_mode=runtime_mode,
            control_plane_enabled=True,
            control_plane_runtime_dir=str(session_runtime_dir),
            reviewer_log_path=str(session_runtime_dir / "logs" / f"{session_id}-reviewer.jsonl"),
        )
        with self.lock:
            self.sessions[session.session_id] = session

        document_decision = self._cyberlace_document_decision(
            requirement=requirement,
            project_dir=project_dir,
            project_slug=project_slug,
            session_id=session_id,
        )
        if self._cyberlace_should_block(document_decision):
            self._persist_cyberlace_document_block_later(
                session_runtime_dir,
                project_slug,
                document_decision,
                session_id=session.session_id,
            )
            return self._block_session_for_cyberlace_document(session, document_decision)

        self._emit_session(session)
        self._append_output(
            session.session_id,
            "[control-plane] Sesion registrada; la preparacion pesada continua en background.\n",
        )
        worker = threading.Thread(target=self._run_session, args=(session.session_id,), daemon=True)
        worker.start()
        return session.to_dict()

    def start_session(
        self,
        requirement: str,
        project_name: str,
        *,
        project_slug: str | None = None,
        bootstrap: bool = True,
        ensure_new_project: bool = False,
        mode: str | None = None,
    ) -> Dict[str, Any]:
        runtime_mode = normalize_agent_runtime_mode(mode)
        if self.control_plane_enabled:
            return self._start_control_plane_session(
                requirement,
                project_name,
                project_slug=project_slug,
                runtime_mode=runtime_mode,
                bootstrap=bootstrap,
                ensure_new_project=ensure_new_project,
            )

        normalized_requested_slug = str(project_slug or "").strip()
        requested_slug = slugify(normalized_requested_slug) if normalized_requested_slug else slugify(project_name)
        if not ensure_new_project:
            active_session = self._find_active_session_for_project(requested_slug)
            if active_session is not None:
                return active_session.to_dict()

        project_preexisting = (self.projects_root / requested_slug).exists() if not ensure_new_project else False
        project = self.create_project(
            project_name,
            bootstrap=bootstrap,
            ensure_unique=ensure_new_project,
            preferred_slug=requested_slug,
        )
        project_dir = Path(project["path"])
        project_slug = project["slug"]
        display_name = project["name"]
        smoke_mode = runtime_mode == "smoke"
        complexity_estimate = self._build_complexity_estimate(project_dir, requirement, runtime_mode)
        lace_context = None if smoke_mode else self._prepare_lace_context(
            project_dir,
            requirement,
            complexity_estimate=complexity_estimate,
        )
        habla_prompt, habla_available, habla_state = self._resolve_habla_payload(requirement)
        habla_preflight_path = self._write_habla_preflight(
            project_dir=project_dir,
            requirement=requirement,
            habla_prompt=habla_prompt,
            habla_available=habla_available,
            habla_state=habla_state,
            lace_context=lace_context,
        )
        prompt = self._build_codex_prompt(
            requirement=requirement,
            project_name=display_name,
            project_slug=project_slug,
            project_dir=project_dir,
            habla_prompt=habla_prompt,
            habla_available=habla_available,
            habla_state=habla_state,
            lace_context=lace_context,
            smoke_mode=smoke_mode,
            continuing_existing_project=project_preexisting,
        )
        session_id = f"agent-{uuid.uuid4().hex[:10]}"
        prompt, prompt_decision = self._cyberlace_guard_text(
            "prompt",
            prompt,
            agent_id="legacy-pty-worker",
            session_id=session_id,
            context={
                "kind": "legacy_worker_prompt",
                "project_slug": project_slug,
                "project_dir": str(project_dir),
                "runtime_mode": runtime_mode,
            },
        )
        command = [] if self._cyberlace_should_block(prompt_decision) else self._build_codex_command(project_dir, prompt)
        event_file = project_dir / VISUAL_DIR_NAME / f"{uuid.uuid4().hex}-events.jsonl"
        event_file.parent.mkdir(parents=True, exist_ok=True)
        if event_file.exists():
            event_file.unlink()
        terminal_file = project_dir / VISUAL_DIR_NAME / f"{uuid.uuid4().hex}-terminal.log"
        remove_file_if_exists(terminal_file)

        session = AgentSession(
            session_id=session_id,
            project_name=display_name,
            project_slug=project_slug,
            project_dir=project_dir,
            requirement=requirement,
            prompt=prompt,
            command=command,
            habla_prompt=habla_prompt,
            habla_available=habla_available,
            event_file=event_file,
            terminal_file=terminal_file,
            lace_policy_path=lace_context.policy_path if lace_context is not None else None,
            lace_log_path=lace_context.log_path if lace_context is not None else None,
            habla_preflight_path=habla_preflight_path,
            lace_required_cycles=lace_context.required_cycles if lace_context is not None else 0,
            complexity_estimate=complexity_estimate,
            smoke_mode=smoke_mode,
            runtime_mode=runtime_mode,
            habla_state=habla_state,
            cyberlace_decisions=[prompt_decision] if isinstance(prompt_decision, dict) else [],
        )
        document_decision = self._cyberlace_document_decision(
            requirement=requirement,
            project_dir=project_dir,
            project_slug=project_slug,
            session_id=session_id,
        )
        if self._cyberlace_should_block(document_decision):
            session.command = []
            session.cyberlace_decisions = [*session.cyberlace_decisions, document_decision]

        if self._cyberlace_should_block(prompt_decision):
            session.status = "failed"
            session.returncode = 126
            session.ended_at = utc_now()
            session.error_code = "cyberlace_prompt_blocked"
            session.error_message = self._cyberlace_block_message(prompt_decision, stage="prompt")
            session.progress_label = session.error_message
        with self.lock:
            self.sessions[session.session_id] = session

        if self._cyberlace_should_block(document_decision):
            checkpoint = self._persist_cyberlace_document_block(
                project_dir / "runtime",
                project_slug,
                document_decision,
            )
            return self._block_session_for_cyberlace_document(session, document_decision, checkpoint=checkpoint)

        self._emit_session(session)
        if self._cyberlace_should_block(prompt_decision):
            self._emit_visual_runtime_event(
                session,
                op="session_failed",
                status="failed",
                phase="cyberlace",
                error_code="cyberlace_prompt_blocked",
                message=session.error_message or "CyberLACE blocked prompt.",
            )
            return session.to_dict()
        worker = threading.Thread(target=self._run_session, args=(session.session_id,), daemon=True)
        worker.start()
        return session.to_dict()

    def _build_codex_command(self, project_dir: Path, prompt: str) -> List[str]:
        command = [*self.codex_command_tokens]
        if self.codex_exec_use_full_auto:
            command.append("--full-auto")
        elif (
            self.codex_exec_approval_policy == "never"
            and self.codex_exec_sandbox_mode == "danger-full-access"
        ):
            command.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            command.extend(["-a", self.codex_exec_approval_policy, "-s", self.codex_exec_sandbox_mode])
        command.extend(["-C", str(project_dir), "exec", "--skip-git-repo-check"])
        command.extend(self.codex_exec_extra_args)
        command.append(prompt)
        return command

    def _new_control_plane_log_paths(
        self,
        runtime_dir: str | Path | None = None,
        *,
        session_id: str | None = None,
    ) -> tuple[Path, Path]:
        logs_dir = self._resolve_control_plane_runtime_dir(runtime_dir) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        token = session_id or uuid.uuid4().hex
        event_file = logs_dir / f"{token}-events.jsonl"
        terminal_file = logs_dir / f"{token}-terminal.log"
        remove_file_if_exists(event_file)
        remove_file_if_exists(terminal_file)
        return event_file, terminal_file

    def _resolve_control_plane_runtime_dir(
        self,
        runtime_dir: str | Path | None = None,
        *,
        session: AgentSession | None = None,
    ) -> Path:
        candidate = runtime_dir or (session.control_plane_runtime_dir if session is not None else None) or self.control_plane_runtime_dir
        if candidate is None:
            raise AgentRuntimeControlPlaneError(
                "control_plane_runtime_dir_required",
                "Control plane runtime_dir must be explicit; project sessions must use workspace/projects/<slug>/runtime.",
            )
        return Path(candidate).expanduser().resolve()

    def _require_control_plane_imports(self) -> None:
        if CONTROL_PLANE_IMPORT_ERROR is not None:
            raise AgentRuntimeControlPlaneError(
                "control_plane_import_error",
                f"No fue posible importar el control plane: {CONTROL_PLANE_IMPORT_ERROR}",
            )
        required = {
            "estimate_complexity": estimate_complexity,
            "StateStore": StateStore,
            "TaskQueue": TaskQueue,
            "ToolInvocationPolicy": ToolInvocationPolicy,
            "plan_project": plan_project,
            "build_directive_context": build_directive_context,
            "build_habla_guide": build_habla_guide,
            "generate_directive": generate_directive,
            "persist_directive": persist_directive,
            "execute_task_with_details": execute_task_with_details,
            "validate_task_execution": validate_task_execution,
            "recover_task": recover_task,
            "LiveReviewer": LiveReviewer,
            "create_human_alignment_review": create_human_alignment_review,
            "decidir_y_justificar_blanqueo": decidir_y_justificar_blanqueo,
            "record_blanqueo_decision": record_blanqueo_decision,
            "create_blanqueo_backup": create_blanqueo_backup,
            "create_post_blanqueo_recovery": create_post_blanqueo_recovery,
            "apply_selective_blanqueo": apply_selective_blanqueo,
            "apply_total_blanqueo": apply_total_blanqueo,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise AgentRuntimeControlPlaneError(
                "control_plane_incomplete",
                "Faltan componentes del control plane: " + ", ".join(sorted(missing)),
            )

    def _ensure_control_plane_runtime(self, runtime_dir: Path, project_id: str, runtime_mode: str) -> None:
        self._require_control_plane_imports()
        store = StateStore(runtime_dir)  # type: ignore[operator]
        now = utc_now()
        if not store.project_state_path.exists():
            store.save_project_state(
                {
                    "schema_version": 1,
                    "project_id": project_id,
                    "status": "initialized",
                    "mode": runtime_mode,
                    "current_task_id": None,
                    "completed_tasks": [],
                    "failed_tasks": [],
                    "blocked_tasks": [],
                    "checkpoints": [],
                    "created_at": now,
                    "updated_at": now,
                }
            )
        if not store.task_queue_path.exists():
            store.save_task_queue([])

    def _persist_control_plane_preparing_state(
        self,
        runtime_dir: Path,
        project_id: str,
        runtime_mode: str,
        session_id: str,
        *,
        reason: str,
    ) -> None:
        self._require_control_plane_imports()
        runtime_dir.mkdir(parents=True, exist_ok=True)
        store = StateStore(runtime_dir)  # type: ignore[operator]
        now = utc_now()
        if store.project_state_path.exists():
            state = store.load_project_state()
        else:
            state = {
                "schema_version": 1,
                "project_id": project_id,
                "status": "initialized",
                "mode": runtime_mode,
                "current_task_id": None,
                "completed_tasks": [],
                "failed_tasks": [],
                "blocked_tasks": [],
                "checkpoints": [],
                "created_at": now,
                "updated_at": now,
            }
        if not store.task_queue_path.exists():
            store.save_task_queue([])
        checkpoint_key = f"session-preparing-{session_id}"
        checkpoint_path = store.save_checkpoint(
            checkpoint_key,
            {
                "reason": reason,
                "session_id": session_id,
                "project_id": project_id,
                "runtime_mode": runtime_mode,
                "status": "preparing",
            },
        )
        state["status"] = "preparing"
        state["mode"] = runtime_mode
        state["current_task_id"] = None
        state["preparing_session_id"] = session_id
        state["last_preparing_at"] = now
        state["checkpoints"] = _append_unique(state.get("checkpoints", []), checkpoint_key)
        state["updated_at"] = now
        store.save_project_state(state)

    def _count_material_project_files(self, project_dir: Path, *, limit: int = 500) -> int:
        if not project_dir.exists() or not project_dir.is_dir():
            return 0
        count = 0
        for file_path in project_dir.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                relative_path = file_path.relative_to(project_dir).as_posix()
            except ValueError:
                continue
            if not is_material_project_path(relative_path):
                continue
            count += 1
            if count >= limit:
                return count
        return count

    def _build_complexity_estimate(self, project_dir: Path, requirement: str, runtime_mode: str) -> Dict[str, Any]:
        if estimate_complexity is None:
            return {}
        return estimate_complexity(  # type: ignore[misc]
            requirement,
            runtime_mode=runtime_mode,
            project_file_count=self._count_material_project_files(project_dir),
            launch_mode="existing" if project_dir.exists() else "new",
            project_slug=project_dir.name,
        )

    def _load_complexity_estimate(self, runtime_dir: str | Path | None) -> Dict[str, Any]:
        if runtime_dir is None:
            return {}
        path = Path(runtime_dir) / "complexity_estimate.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _persist_complexity_estimate(self, runtime_dir: str | Path, estimate: Dict[str, Any]) -> None:
        if not estimate:
            return
        runtime_path = Path(runtime_dir)
        runtime_path.mkdir(parents=True, exist_ok=True)
        estimate_path = runtime_path / "complexity_estimate.json"
        estimate_path.write_text(json.dumps(estimate, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        try:
            store = StateStore(runtime_path)  # type: ignore[operator]
            checkpoint_key = "complexity-estimate"
            store.save_checkpoint(checkpoint_key, {"reason": "complexity_estimate_created", "estimate": estimate})
            state = store.load_project_state()
            state["checkpoints"] = _append_unique(state.get("checkpoints", []), checkpoint_key)
            state["updated_at"] = utc_now()
            store.save_project_state(state)
        except Exception:
            return

    def _complexity_budget_value(
        self,
        estimate: Dict[str, Any],
        key: str,
        fallback: int,
        *,
        minimum: int = 0,
    ) -> int:
        try:
            value = int(estimate.get(key) or fallback)
        except (TypeError, ValueError):
            value = fallback
        return max(minimum, value)

    def _control_plane_bootstrap_task_count(self, runtime_mode: str) -> int:
        configured = str(os.environ.get("VISTA_CONTROL_PLANE_MAX_BOOTSTRAP_TASKS") or "").strip()
        if configured.isdigit():
            return max(1, int(configured))
        defaults = {"smoke": 1, "build": 4, "medium": 6, "long-run": 6}
        return defaults.get(runtime_mode, 4)

    def _control_plane_max_tasks_per_session(self, runtime_mode: str) -> int:
        configured = str(os.environ.get("VISTA_CONTROL_PLANE_MAX_TASKS_PER_SESSION") or "").strip()
        if configured.isdigit():
            return max(1, int(configured))
        defaults = {"smoke": 1, "build": 6, "medium": 12, "long-run": 30}
        return defaults.get(runtime_mode, 6)

    def _control_plane_recovery_task_budget(self, runtime_mode: str) -> int:
        configured = str(os.environ.get("VISTA_CONTROL_PLANE_RECOVERY_TASK_BUDGET") or "").strip()
        if configured.isdigit():
            return max(0, int(configured))
        defaults = {"smoke": 4, "build": 6, "medium": 8, "long-run": 12}
        return defaults.get(runtime_mode, 6)

    def _normalize_control_plane_planned_tasks(
        self,
        tasks: List[Dict[str, Any]],
        workspace: str | Path,
    ) -> List[Dict[str, Any]]:
        workspace_path = Path(workspace).resolve()
        material_files = list_material_project_files(workspace_path, limit=8) if workspace_path.exists() else []
        normalized_tasks: List[Dict[str, Any]] = []
        for task in tasks:
            updated = dict(task)
            original_validation_commands = [
                str(command)
                for command in updated.get("validation_commands", [])
                if str(command).strip()
            ] if isinstance(updated.get("validation_commands"), list) else []
            expected_files = self._sanitize_control_plane_expected_files(updated.get("expected_files", []))
            if material_files and (
                not expected_files
                or all(str(path).startswith("runtime/artifacts/") for path in expected_files)
            ):
                expected_files = list(material_files)
            if not expected_files:
                expected_files = [f"runtime/artifacts/{str(updated.get('id') or 'task').lower()}.json"]
            updated["expected_files"] = expected_files
            updated["validation_commands"] = self._merge_control_plane_validation_commands(
                expected_files,
                original_validation_commands,
                workspace_path=workspace_path,
            )
            normalized_tasks.append(updated)
        return normalized_tasks

    def _merge_control_plane_validation_commands(
        self,
        expected_files: List[str],
        original_validation_commands: List[str],
        *,
        workspace_path: Path | None = None,
    ) -> List[str]:
        expected_command = self._expected_files_are_files_command(expected_files)
        merged = [expected_command]
        browser_command = self._browser_render_smoke_command(expected_files, workspace_path=workspace_path)
        for command in original_validation_commands:
            if not command or command == expected_command:
                continue
            if "missing=[p for p in" in command:
                continue
            if command not in merged:
                merged.append(command)
        if browser_command and browser_command not in merged:
            merged.append(browser_command)
        return merged

    def _browser_render_smoke_command(
        self,
        expected_files: List[str],
        *,
        workspace_path: Path | None = None,
    ) -> str | None:
        if not self._requires_browser_render_validation(expected_files, workspace_path=workspace_path):
            return None
        script_path = (self.app_root / "backend" / "browser_render_smoke.py").resolve()
        return (
            "python3 -B "
            + shlex.quote(str(script_path))
            + " --workspace . --frontend frontend --mode smoke --light day"
        )

    def _requires_browser_render_validation(
        self,
        expected_files: List[str],
        *,
        workspace_path: Path | None = None,
    ) -> bool:
        normalized = {str(path).replace("\\", "/") for path in expected_files}
        frontend_targets = {
            path
            for path in normalized
            if path.startswith("frontend/") and Path(path).suffix.lower() in {".html", ".js", ".css"}
        }
        if not frontend_targets:
            return False
        if {"frontend/index.html", "frontend/app.js"}.issubset(normalized):
            return True
        if workspace_path is None:
            return False
        index_path = workspace_path / "frontend" / "index.html"
        app_path = workspace_path / "frontend" / "app.js"
        if not (index_path.is_file() and app_path.is_file()):
            return False
        try:
            index_text = index_path.read_text(encoding="utf-8", errors="ignore").lower()
            app_text = app_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            return False
        return "<canvas" in index_text or "webglrenderer" in app_text or "three" in app_text

    def _has_browser_render_validation(self, task: Dict[str, Any]) -> bool:
        commands = task.get("validation_commands") if isinstance(task, dict) else []
        return any("browser_render_smoke.py" in str(command) for command in commands if str(command).strip())

    def _sanitize_control_plane_expected_files(self, paths: Any) -> List[str]:
        sanitized: List[str] = []
        for raw_path in paths if isinstance(paths, list) else []:
            relative = normalize_project_relative_path(raw_path)
            if (
                not relative
                or relative.endswith("/")
                or relative == "workspace/projects"
                or relative.startswith("workspace/projects/")
                or Path(relative).is_absolute()
                or is_runtime_control_path(relative)
                or is_control_plane_state_path(relative)
                or ".." in Path(relative).parts
                or not Path(relative).suffix
            ):
                continue
            if relative not in sanitized:
                sanitized.append(relative)
        return sanitized

    def _repair_control_plane_task_evidence(self, store: Any, queue: Any, workspace: str | Path) -> bool:
        tasks = queue.list()
        if not tasks:
            return False
        repaired_tasks = self._normalize_control_plane_planned_tasks(tasks, workspace)
        changed = any(
            task.get("expected_files") != repaired.get("expected_files")
            or task.get("validation_commands") != repaired.get("validation_commands")
            for task, repaired in zip(tasks, repaired_tasks)
        )
        if changed:
            store.save_task_queue(repaired_tasks)
        return changed

    def _expected_files_are_files_command(self, expected_files: List[str]) -> str:
        return (
            "python3 -B -c "
            + repr(
                "from pathlib import Path; "
                f"missing=[p for p in {expected_files!r} if not Path(p).is_file()]; "
                "assert not missing, missing"
            )
        )

    def _prepare_control_plane_directive(
        self,
        requirement: str,
        *,
        runtime_mode: str,
        runtime_dir: str | Path | None = None,
        sprint_number: int | None = None,
        directive_repo_root: str | Path | None = None,
        task_workspace_root: str | Path | None = None,
        directives_dir: str | Path | None = None,
        complexity_estimate: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._require_control_plane_imports()
        store = StateStore(self._resolve_control_plane_runtime_dir(runtime_dir))  # type: ignore[operator]
        try:
            store.load_project_state()
        except Exception as error:
            raise AgentRuntimeControlPlaneError(
                "control_plane_state_missing",
                f"No se pudo cargar project_state.json: {error}",
            ) from error

        try:
            queue = TaskQueue(store, bootstrap_empty=True)  # type: ignore[operator]
        except Exception as error:
            raise AgentRuntimeControlPlaneError(
                "control_plane_queue_invalid",
                f"No se pudo cargar task_queue.json: {error}",
            ) from error

        workspace_for_reconciliation = (
            Path(task_workspace_root).resolve()
            if task_workspace_root is not None
            else Path(directive_repo_root).resolve()
            if directive_repo_root is not None
            else self.repo_root
        )
        if self._reconcile_recovered_split_tasks(store, queue, workspace_for_reconciliation):
            queue = TaskQueue(store, bootstrap_empty=True)  # type: ignore[operator]
        if self._recover_stale_running_tasks(store, queue):
            queue = TaskQueue(store, bootstrap_empty=True)  # type: ignore[operator]
        if self._repair_control_plane_task_evidence(store, queue, workspace_for_reconciliation):
            queue = TaskQueue(store, bootstrap_empty=True)  # type: ignore[operator]

        complexity_budget = complexity_estimate if isinstance(complexity_estimate, dict) else {}
        if not complexity_budget:
            complexity_budget = self._load_complexity_estimate(store.runtime_dir)
        bootstrap_task_count = self._complexity_budget_value(
            complexity_budget,
            "bootstrap_tasks",
            self._control_plane_bootstrap_task_count(runtime_mode),
            minimum=1,
        )
        task_timeout_seconds = self._complexity_budget_value(
            complexity_budget,
            "timeout_seconds",
            mode_timeout_seconds(runtime_mode),
            minimum=1,
        )
        task_max_retries = self._complexity_budget_value(complexity_budget, "max_retries", 3, minimum=0)

        task = queue.next_ready_task()
        existing_tasks = queue.list()
        if task is None:
            if existing_tasks and all(item.get("status") == "completed" for item in existing_tasks):
                task_prefix = "RUNTIME-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                planned_tasks = plan_project(  # type: ignore[misc]
                    requirement,
                    mode=runtime_mode,
                    max_tasks=bootstrap_task_count,
                    sequential=True,
                    task_id_prefix=task_prefix,
                    timeout_seconds=task_timeout_seconds,
                    max_retries=task_max_retries,
                )
                planned_tasks = self._normalize_control_plane_planned_tasks(planned_tasks, workspace_for_reconciliation)
                queue.enqueue_many(planned_tasks)
                state = store.load_project_state()
                state["status"] = "preparing"
                state["current_task_id"] = None
                state["blocked_tasks"] = []
                state["failed_tasks"] = []
                state["updated_at"] = utc_now()
                store.save_project_state(state)
                task = queue.next_ready_task()
                existing_tasks = queue.list()
            elif existing_tasks:
                blocked_tasks = queue.blocked_tasks()
                raise AgentRuntimeControlPlaneError(
                    "control_plane_no_ready_task",
                    "La cola persistida existe, pero no hay tarea ejecutable. "
                    f"Tareas bloqueadas: {blocked_tasks}",
                )
            if task is None and not existing_tasks:
                task_prefix = "RUNTIME-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                planned_tasks = plan_project(  # type: ignore[misc]
                    requirement,
                    mode=runtime_mode,
                    max_tasks=bootstrap_task_count,
                    sequential=True,
                    task_id_prefix=task_prefix,
                    timeout_seconds=task_timeout_seconds,
                    max_retries=task_max_retries,
                )
                planned_tasks = self._normalize_control_plane_planned_tasks(planned_tasks, workspace_for_reconciliation)
                queue.enqueue_many(planned_tasks)
                task = queue.next_ready_task()

        if task is None:
            raise AgentRuntimeControlPlaneError(
                "control_plane_no_active_task",
                "No se pudo obtener una tarea activa desde la cola persistida.",
            )

        task_document_decision = self._cyberlace_document_decision(
            requirement=requirement,
            project_dir=workspace_for_reconciliation,
            project_slug=workspace_for_reconciliation.name,
            session_id=None,
            task=task,
        )
        if self._cyberlace_should_block(task_document_decision):
            try:
                queue.mark_task_status(task["id"], "blocked")
            except Exception:
                pass
            checkpoint = self._persist_cyberlace_document_block(
                store.runtime_dir,
                workspace_for_reconciliation.name,
                task_document_decision,
                task=task,
            )
            raise AgentRuntimeControlPlaneError(
                "cyberlace_sensitive_document_blocked",
                str(task_document_decision.get("message") or "CyberLACE bloqueo documentos sensibles antes del worker."),
                {"decision": task_document_decision, "checkpoint": checkpoint},
            )

        self._save_project_state_transition(store, task, "preparing")
        context_root = Path(directive_repo_root).resolve() if directive_repo_root is not None else self.repo_root
        workspace_root = (
            Path(task_workspace_root).resolve()
            if task_workspace_root is not None
            else Path(directive_repo_root).resolve()
            if directive_repo_root is not None
            else self.repo_root
        )
        context = build_directive_context(  # type: ignore[misc]
            repo_root=context_root,
            runtime_dir=store.runtime_dir,
            task_workspace_root=workspace_root,
            task_id=task["id"],
            sprint_number=sprint_number,
        )
        if complexity_budget:
            context["complexity_estimate"] = complexity_budget
        if not isinstance(context.get("active_task"), dict):
            raise AgentRuntimeControlPlaneError(
                "control_plane_context_missing_task",
                "El contexto no contiene tarea activa; no se generara directiva falsa.",
            )
        guide = build_habla_guide(context)  # type: ignore[misc]
        directive = generate_directive(context, guide)  # type: ignore[misc]
        directive_document_decision = self._cyberlace_document_decision(
            requirement=requirement,
            project_dir=workspace_root,
            project_slug=workspace_root.name,
            session_id=None,
            task=task,
            directive=directive,
        )
        if self._cyberlace_should_block(directive_document_decision):
            try:
                queue.mark_task_status(task["id"], "blocked")
            except Exception:
                pass
            checkpoint = self._persist_cyberlace_document_block(
                store.runtime_dir,
                workspace_root.name,
                directive_document_decision,
                task=task,
            )
            raise AgentRuntimeControlPlaneError(
                "cyberlace_sensitive_document_blocked",
                str(directive_document_decision.get("message") or "CyberLACE bloqueo documentos sensibles antes del worker."),
                {"decision": directive_document_decision, "checkpoint": checkpoint},
            )
        persisted = persist_directive(directive, directives_dir=directives_dir)  # type: ignore[misc]
        return {
            "runtime_dir": store.runtime_dir,
            "store": store,
            "task": task,
            "context": context,
            "habla_guide": guide,
            "directive": persisted["directive"],
            "directive_json_path": persisted["json_path"],
            "directive_markdown_path": persisted["markdown_path"],
        }

    def _build_control_plane_worker_command(
        self,
        directive: Dict[str, Any],
        *,
        workspace: str | Path | None = None,
        session_id: str | None = None,
        task: Dict[str, Any] | None = None,
    ) -> List[str]:
        instruction = str(directive.get("rendered_instruction") or "").strip()
        if not instruction:
            raise AgentRuntimeControlPlaneError(
                "control_plane_empty_directive",
                "La directiva generada no tiene instruccion para el worker.",
            )
        instruction, decision = self._cyberlace_guard_text(
            "prompt",
            instruction,
            agent_id="control-plane-worker",
            session_id=session_id,
            context={
                "kind": "control_plane_directive",
                "workspace": str(Path(workspace).resolve()) if workspace is not None else str(self.repo_root),
                "task": task or {},
                "directiveTraceability": directive.get("traceability") if isinstance(directive.get("traceability"), dict) else {},
            },
        )
        if self._cyberlace_should_block(decision):
            raise AgentRuntimeControlPlaneError(
                "cyberlace_directive_blocked",
                self._cyberlace_block_message(decision, stage="directive"),
            )
        return self._build_codex_command(Path(workspace).resolve() if workspace is not None else self.repo_root, instruction)

    def _control_plane_worker_env(
        self,
        *,
        session_id: str | None,
        workspace: str | Path,
        runtime_dir: str | Path,
    ) -> Dict[str, str]:
        workspace_path = Path(workspace).resolve()
        runtime_path = Path(runtime_dir).resolve()
        with self.lock:
            session = self.sessions.get(session_id or "") if session_id else None
            event_file = session.event_file if session is not None else runtime_path / "logs" / f"{session_id or 'control-plane'}-events.jsonl"
            project_slug = session.project_slug if session is not None else workspace_path.name
            resolved_session_id = session.session_id if session is not None else (session_id or "control-plane")
        return {
            "VISTA_AGENT_SESSION_ID": resolved_session_id,
            "VISTA_AGENT_PROJECT_SLUG": project_slug,
            "VISTA_AGENT_PROJECT_DIR": str(workspace_path),
            "VISTA_AGENT_EVENT_FILE": str(event_file),
            "VISTA_AGENT_BRIDGE": f"{self.bridge_python} {self.bridge_script}",
        }

    def _control_plane_session_stop_requested(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        with self.lock:
            session = self.sessions.get(session_id)
            return bool(session is not None and session.stop_requested)

    def _attach_control_plane_process(self, session_id: str | None, process: subprocess.Popen[Any]) -> None:
        if not session_id:
            return
        snapshot = None
        session_ref = None
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            now = utc_now()
            session.process = process
            session.pid = process.pid
            session.status = "running"
            session.started_at = session.started_at or now
            session.updated_at = now
            session.start_monotonic = session.start_monotonic or time.monotonic()
            session.last_agent_activity_monotonic = session.start_monotonic
            session.last_heartbeat_monotonic = session.start_monotonic
            session.last_heartbeat_at = now
            session.progress_percent = max(session.progress_percent, 14)
            session.progress_label = "Worker Codex lanzado con PID real"
            snapshot = session.to_dict()
            session_ref = session
        self.session_emitter(snapshot)
        self._emit_visual_runtime_event(
            session_ref,
            op="worker_started",
            status="running",
            phase="worker",
            message=f"Worker Codex activo con PID {process.pid}.",
        )

    def _clear_control_plane_process(self, session_id: str | None, process: subprocess.Popen[Any] | None) -> None:
        if not session_id:
            return
        snapshot = None
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            if process is None or session.process is process:
                session.process = None
                session.pid = None
                if session.status == "running":
                    session.status = "preparing"
                    session.progress_label = "Worker termino; validando salida"
                session.updated_at = utc_now()
                snapshot = session.to_dict()
        if snapshot is not None:
            self.session_emitter(snapshot)

    def run_control_plane_task_once(
        self,
        requirement: str,
        *,
        mode: str | None = None,
        runtime_dir: str | Path | None = None,
        sprint_number: int | None = None,
        command_builder: Callable[[Dict[str, Any]], List[str] | str] | None = None,
        workspace: str | Path | None = None,
        directive_repo_root: str | Path | None = None,
        task_workspace_root: str | Path | None = None,
        directives_dir: str | Path | None = None,
    ) -> Dict[str, Any]:
        """Prepare, generate, execute, validate, and persist one control-plane task."""

        runtime_mode = normalize_agent_runtime_mode(mode)
        prepared = self._prepare_control_plane_directive(
            requirement,
            runtime_mode=runtime_mode,
            runtime_dir=runtime_dir,
            sprint_number=sprint_number,
            directive_repo_root=directive_repo_root,
            task_workspace_root=task_workspace_root,
            directives_dir=directives_dir,
        )
        directive = prepared["directive"]
        workspace_path = Path(workspace).resolve() if workspace is not None else self.repo_root
        command = (
            command_builder(directive)
            if command_builder is not None
            else self._build_control_plane_worker_command(directive, workspace=workspace_path, task=prepared.get("task") if isinstance(prepared, dict) else None)
        )
        return self._execute_prepared_control_plane_task(
            prepared,
            command=command,
            workspace=workspace_path,
        )

    def run_control_plane_until_idle(
        self,
        requirement: str,
        *,
        mode: str | None = None,
        runtime_dir: str | Path | None = None,
        sprint_number: int | None = None,
        command_builder: Callable[[Dict[str, Any]], List[str] | str] | None = None,
        workspace: str | Path | None = None,
        directive_repo_root: str | Path | None = None,
        task_workspace_root: str | Path | None = None,
        directives_dir: str | Path | None = None,
        max_tasks: int | None = None,
        session_id: str | None = None,
        initial_prepared: Dict[str, Any] | None = None,
        initial_command: List[str] | str | None = None,
    ) -> Dict[str, Any]:
        """Run ready control-plane tasks sequentially until the queue is idle."""

        runtime_mode = normalize_agent_runtime_mode(mode)
        target_runtime_dir = self._resolve_control_plane_runtime_dir(runtime_dir)
        workspace_path = Path(workspace).resolve() if workspace is not None else self.repo_root
        target_workspace = Path(task_workspace_root).resolve() if task_workspace_root is not None else workspace_path
        complexity_budget = self._load_complexity_estimate(target_runtime_dir)
        task_limit = max_tasks if max_tasks is not None else self._complexity_budget_value(
            complexity_budget,
            "max_tasks",
            self._control_plane_max_tasks_per_session(runtime_mode),
            minimum=1,
        )
        recovery_task_budget = (
            self._complexity_budget_value(
                complexity_budget,
                "recovery_budget",
                self._control_plane_recovery_task_budget(runtime_mode),
                minimum=0,
            )
            if max_tasks is None
            else 0
        )
        if task_limit < 1:
            raise AgentRuntimeControlPlaneError("invalid_task_limit", "max_tasks must be greater than 0")

        results: List[Dict[str, Any]] = []
        prepared = initial_prepared
        command: List[str] | str | None = initial_command
        stopped_reason = "queue_idle"
        lace_gate: Dict[str, Any] = {"status": "not_applicable"}
        final_tool_gate: Dict[str, Any] | None = None

        while len(results) < task_limit:
            if self._control_plane_session_stop_requested(session_id):
                stopped_reason = "stop_requested"
                break
            if prepared is None:
                if results:
                    self._reconcile_recovered_split_tasks_for_runtime(target_runtime_dir, target_workspace)
                if results and not self._control_plane_has_ready_task(target_runtime_dir):
                    lace_gate = self._apply_lace_closure_gate(
                        runtime_dir=target_runtime_dir,
                        workspace=target_workspace,
                        runtime_mode=runtime_mode,
                        session_id=session_id,
                        allow_enqueue=True,
                    )
                    if lace_gate.get("status") == "enqueued":
                        stopped_reason = "lace_cycles_enqueued"
                        continue
                    if lace_gate.get("status") == "blocked":
                        stopped_reason = "lace_cycles_pending"
                        break
                    stopped_reason = "queue_idle"
                    break
                try:
                    prepared = self._prepare_control_plane_directive(
                        requirement,
                        runtime_mode=runtime_mode,
                        runtime_dir=target_runtime_dir,
                        sprint_number=sprint_number,
                        directive_repo_root=directive_repo_root,
                        task_workspace_root=target_workspace,
                        directives_dir=directives_dir,
                    )
                except AgentRuntimeControlPlaneError as error:
                    if results and error.code == "control_plane_no_ready_task":
                        stopped_reason = "queue_idle"
                        break
                    raise

            directive = prepared["directive"]
            if command is None:
                command = (
                    command_builder(directive)
                    if command_builder is not None
                    else self._build_control_plane_worker_command(directive, workspace=workspace_path, session_id=session_id, task=prepared.get("task") if isinstance(prepared, dict) else None)
                )

            result = self._execute_prepared_control_plane_task(
                prepared,
                command=command,
                workspace=workspace_path,
                session_id=session_id,
            )
            results.append(result)
            self._reconcile_recovered_split_tasks_for_runtime(target_runtime_dir, target_workspace)
            if self._control_plane_session_stop_requested(session_id):
                stopped_reason = "stop_requested"
                break
            if result.get("status") in {"retry", "split"} and recovery_task_budget > 0:
                enqueued_count = len(result.get("enqueued_split_tasks") or [])
                extension = min(recovery_task_budget, max(1, enqueued_count))
                task_limit += extension
                recovery_task_budget -= extension
            if result.get("status") == "stopped":
                stopped_reason = "stop_requested"
                break
            if not self._control_plane_has_ready_task(target_runtime_dir):
                lace_gate = self._apply_lace_closure_gate(
                    runtime_dir=target_runtime_dir,
                    workspace=target_workspace,
                    runtime_mode=runtime_mode,
                    session_id=session_id,
                    allow_enqueue=True,
                )
                if lace_gate.get("status") == "enqueued":
                    stopped_reason = "lace_cycles_enqueued"
                    prepared = None
                    command = None
                    continue
                if lace_gate.get("status") == "blocked":
                    stopped_reason = "lace_cycles_pending"
                    break
                stopped_reason = "queue_idle"
                break
            prepared = None
            command = None
        else:
            stopped_reason = "max_tasks_reached"

        queue_snapshot = self._control_plane_queue_snapshot(target_runtime_dir)
        completed = bool(queue_snapshot["tasks"]) and all(
            task.get("status") == "completed" for task in queue_snapshot["tasks"]
        )
        if completed:
            lace_gate = self._apply_lace_closure_gate(
                runtime_dir=target_runtime_dir,
                workspace=target_workspace,
                runtime_mode=runtime_mode,
                session_id=session_id,
                allow_enqueue=False,
            )
            if lace_gate.get("status") == "blocked":
                completed = False
                stopped_reason = "lace_cycles_pending"
            else:
                final_tool_gate = self._run_control_plane_final_tool_gate(
                    runtime_dir=target_runtime_dir,
                    workspace=target_workspace,
                    session_id=session_id,
                )
                if isinstance(final_tool_gate, dict) and final_tool_gate.get("closureAllowed") is False:
                    completed = False
                    stopped_reason = "tool_policy_blocked"
        failed_or_blocked = [
            task for task in queue_snapshot["tasks"] if task.get("status") in {"failed", "blocked"}
        ]
        status = (
            "stopped"
            if stopped_reason == "stop_requested"
            else "completed"
            if completed
            else "blocked"
            if stopped_reason in {"lace_cycles_pending", "tool_policy_blocked"}
            else "failed"
            if failed_or_blocked
            else stopped_reason
        )
        return {
            "status": status,
            "stopped_reason": stopped_reason,
            "runtime_dir": str(target_runtime_dir),
            "workspace": str(workspace_path),
            "task_workspace_root": str(target_workspace),
            "tasks_executed": len(results),
            "results": results,
            "last_result": results[-1] if results else None,
            "queue": queue_snapshot,
            "lace_gate": lace_gate,
            "tool_policy_final": final_tool_gate,
        }

    def _apply_lace_closure_gate(
        self,
        *,
        runtime_dir: str | Path,
        workspace: str | Path,
        runtime_mode: str,
        session_id: str | None,
        allow_enqueue: bool,
    ) -> Dict[str, Any]:
        if normalize_agent_runtime_mode(runtime_mode) != "long-run":
            return {"status": "not_applicable", "reason": "runtime_mode_not_long_run"}

        workspace_path = Path(workspace).resolve()
        store = StateStore(runtime_dir)  # type: ignore[operator]
        queue = TaskQueue(store, bootstrap_empty=True)  # type: ignore[operator]
        queue_tasks = queue.list()
        if not queue_tasks or any(task.get("status") != "completed" for task in queue_tasks):
            return {"status": "not_ready", "reason": "queue_not_fully_completed"}

        if session_id:
            self._sync_lace_runtime(session_id)

        configured_required_cycles = self._resolve_lace_required_cycles(session_id=session_id, workspace=workspace_path)
        if configured_required_cycles <= 0:
            return {"status": "clear", "reason": "lace_not_active", "required_cycles": 0}

        preliminary_evidence = self._inspect_lace_closure_evidence(
            workspace_path,
            configured_required_cycles,
            store=store,
            queue_tasks=queue_tasks,
        )
        quality_gates = self._inspect_lace_quality_gates(workspace_path, queue_tasks)
        adaptive_lace = self._resolve_adaptive_lace_target(
            configured_required_cycles=configured_required_cycles,
            preliminary_evidence=preliminary_evidence,
            quality_gates=quality_gates,
        )
        required_cycles = int(adaptive_lace["effective_required_cycles"])
        evidence = preliminary_evidence
        if required_cycles != configured_required_cycles:
            evidence = self._inspect_lace_closure_evidence(
                workspace_path,
                required_cycles,
                store=store,
                queue_tasks=queue_tasks,
            )
        evidence["configured_required_cycles"] = configured_required_cycles
        evidence["adaptive_lace"] = adaptive_lace
        evidence["quality_gates"] = quality_gates
        if evidence["completed_cycles"] >= required_cycles and not evidence["missing_cycles"]:
            return self._complete_lace_closure(store, evidence)

        if allow_enqueue:
            pending_tasks = self._build_lace_cycle_tasks(queue_tasks, evidence["missing_cycles"], runtime_mode)
            existing_ids = {task["id"] for task in queue_tasks}
            new_tasks = [task for task in pending_tasks if task["id"] not in existing_ids]
            if new_tasks:
                queue.enqueue_many(new_tasks)
                checkpoint_key = "lace-closure-gate-pending"
                checkpoint_path = store.save_checkpoint(
                    checkpoint_key,
                    {
                        "reason": "lace_cycles_pending",
                        "required_cycles": required_cycles,
                        "configured_required_cycles": evidence.get("configured_required_cycles"),
                        "completed_cycles": evidence["completed_cycles"],
                        "missing_cycles": evidence["missing_cycles"],
                        "adaptive_lace": evidence.get("adaptive_lace"),
                        "quality_gates": evidence.get("quality_gates"),
                        "enqueued_task_ids": [task["id"] for task in new_tasks],
                    },
                )
                state = store.load_project_state()
                state["status"] = "preparing"
                state["current_task_id"] = None
                state["blocked_tasks"] = [item for item in state.get("blocked_tasks", []) if item != "lace_cycles_pending"]
                state["checkpoints"] = _append_unique(state.get("checkpoints", []), checkpoint_key)
                state["updated_at"] = utc_now()
                store.save_project_state(state)
                return {
                    "status": "enqueued",
                    **evidence,
                    "checkpoint": {"checkpoint_key": checkpoint_key, "path": str(checkpoint_path)},
                    "enqueued_task_ids": [task["id"] for task in new_tasks],
                }

        return self._block_lace_closure(store, evidence, reason="lace_cycles_pending")

    def _resolve_lace_required_cycles(self, *, session_id: str | None, workspace: Path) -> int:
        with self.lock:
            session = self.sessions.get(session_id or "") if session_id else None
            if session is not None and session.lace_required_cycles:
                return clamp_lace_required_cycles(int(session.lace_required_cycles))

        candidates = [workspace / "LACE_LOG.md", workspace / "LACE.md"]
        docs_dir = workspace / LACE_VISUAL_DIR
        if docs_dir.exists():
            candidates.extend(sorted(docs_dir.glob("ciclo-*.md")))

        for candidate in candidates:
            if not candidate.exists() or not candidate.is_file():
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except OSError:
                continue
            explicit = re.search(r"ciclos\s+requeridos\s*:\s*(\d+)", text, flags=re.IGNORECASE)
            if explicit:
                return clamp_lace_required_cycles(int(explicit.group(1)))
            active = re.search(r"Regla activa:\s*(\d+)\s+ciclos", text, flags=re.IGNORECASE)
            if active:
                return clamp_lace_required_cycles(int(active.group(1)))
            if candidate.name == "LACE.md":
                detected = detect_lace_required_cycles(text)
                if detected:
                    return clamp_lace_required_cycles(detected)
        return 0

    def _read_runtime_json_dict(self, path: Path) -> tuple[Dict[str, Any], str | None]:
        if not path.exists():
            return {}, "missing"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            return {}, f"invalid_json:{error.msg}"
        except OSError as error:
            return {}, f"read_error:{error}"
        if not isinstance(payload, dict):
            return {}, "not_json_object"
        return payload, None

    def _inspect_lace_quality_gates(self, workspace: Path, queue_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        runtime_dir = workspace / "runtime"
        artifacts_dir = runtime_dir / "artifacts"

        task_status_counts: Dict[str, int] = {}
        for task in queue_tasks:
            status = str(task.get("status") or "unknown")
            task_status_counts[status] = task_status_counts.get(status, 0) + 1
        queue_idle = bool(queue_tasks) and task_status_counts == {"completed": len(queue_tasks)}

        scanner_path = artifacts_dir / "final_code_scanner_report.json"
        scanner_report, scanner_error = self._read_runtime_json_dict(scanner_path)
        scanner_validation = scanner_report.get("validation") if isinstance(scanner_report.get("validation"), dict) else {}
        scanner = scanner_report.get("scanner") if isinstance(scanner_report.get("scanner"), dict) else {}
        scanner_passed = (
            scanner_error is None
            and scanner_validation.get("passed") is True
            and scanner_validation.get("blockers") == []
            and scanner.get("visual_playback") == "magnifier_line_by_line_to_last_line"
            and scanner.get("scrolls_to_last_line") is True
        )

        sandbox_path = runtime_dir / "sandbox.json"
        sandbox_report, sandbox_error = self._read_runtime_json_dict(sandbox_path)
        sandbox_healthcheck = (
            sandbox_report.get("healthcheck") if isinstance(sandbox_report.get("healthcheck"), dict) else {}
        )
        try:
            sandbox_status_code = int(sandbox_healthcheck.get("statusCode"))
        except (TypeError, ValueError):
            sandbox_status_code = 0
        sandbox_passed = (
            sandbox_error is None
            and sandbox_report.get("running") is True
            and sandbox_report.get("ready") is True
            and bool(sandbox_report.get("embedUrl") or sandbox_report.get("url"))
            and sandbox_healthcheck.get("ready") is True
            and 200 <= sandbox_status_code < 400
        )

        integrity_path = artifacts_dir / "file_integrity_report.json"
        integrity_report, integrity_error = self._read_runtime_json_dict(integrity_path)
        integrity_validation = (
            integrity_report.get("validation") if isinstance(integrity_report.get("validation"), dict) else {}
        )
        integrity_summary = integrity_report.get("summary") if isinstance(integrity_report.get("summary"), dict) else {}
        integrity_passed = (
            integrity_error is None
            and integrity_validation.get("passed") is True
            and integrity_validation.get("blockers") == []
            and int(integrity_summary.get("totalFindings") or 0) == 0
        )

        findings_path = artifacts_dir / "observer_findings.json"
        findings_report, findings_error = self._read_runtime_json_dict(findings_path)
        findings_summary = findings_report.get("summary") if isinstance(findings_report.get("summary"), dict) else {}
        findings_passed = findings_error is None and int(findings_summary.get("activeFindings") or 0) == 0

        checks = {
            "queue_idle": queue_idle,
            "scanner_ok": scanner_passed,
            "sandbox_ok": sandbox_passed,
            "integrity_ok": integrity_passed,
            "findings_ok": findings_passed,
        }
        issues = [name for name, passed in checks.items() if not passed]
        return {
            "passed": all(checks.values()),
            **checks,
            "issues": issues,
            "details": {
                "task_status_counts": task_status_counts,
                "scanner": {
                    "path": str(scanner_path),
                    "error": scanner_error,
                    "validation_passed": scanner_validation.get("passed"),
                    "blockers": scanner_validation.get("blockers"),
                    "visual_playback": scanner.get("visual_playback"),
                    "scrolls_to_last_line": scanner.get("scrolls_to_last_line"),
                },
                "sandbox": {
                    "path": str(sandbox_path),
                    "error": sandbox_error,
                    "running": sandbox_report.get("running"),
                    "ready": sandbox_report.get("ready"),
                    "url": sandbox_report.get("embedUrl") or sandbox_report.get("url"),
                    "healthcheck_ready": sandbox_healthcheck.get("ready"),
                    "statusCode": sandbox_status_code or sandbox_healthcheck.get("statusCode"),
                },
                "integrity": {
                    "path": str(integrity_path),
                    "error": integrity_error,
                    "validation_passed": integrity_validation.get("passed"),
                    "blockers": integrity_validation.get("blockers"),
                    "totalFindings": integrity_summary.get("totalFindings"),
                },
                "findings": {
                    "path": str(findings_path),
                    "error": findings_error,
                    "activeFindings": findings_summary.get("activeFindings"),
                },
            },
        }

    def _resolve_adaptive_lace_target(
        self,
        *,
        configured_required_cycles: int,
        preliminary_evidence: Dict[str, Any],
        quality_gates: Dict[str, Any],
    ) -> Dict[str, Any]:
        configured = clamp_lace_required_cycles(configured_required_cycles)
        completed = int(preliminary_evidence.get("completed_cycles") or 0)
        if configured <= 0:
            return {
                "min_required_cycles": 0,
                "max_required_cycles": LACE_MAX_REQUIRED_CYCLES,
                "configured_required_cycles": 0,
                "effective_required_cycles": 0,
                "completed_cycles_observed": completed,
                "early_exit": False,
                "reason": "lace_not_active",
            }

        min_required = min(LACE_MIN_REQUIRED_CYCLES, configured)
        if quality_gates.get("passed") is True:
            if completed >= min_required:
                effective = min(configured, max(min_required, completed))
                early_exit = effective < configured
                reason = "quality_gates_clear_early_exit" if early_exit else "quality_gates_clear_at_configured_max"
            else:
                effective = min_required
                early_exit = False
                reason = "quality_gates_clear_minimum_pending"
        else:
            effective = configured
            early_exit = False
            reason = "quality_gates_not_clear"

        return {
            "min_required_cycles": min_required,
            "max_required_cycles": LACE_MAX_REQUIRED_CYCLES,
            "configured_required_cycles": configured,
            "effective_required_cycles": effective,
            "completed_cycles_observed": completed,
            "early_exit": early_exit,
            "reason": reason,
            "quality_gates_passed": quality_gates.get("passed") is True,
            "quality_gate_issues": quality_gates.get("issues", []),
        }

    def _inspect_lace_closure_evidence(
        self,
        workspace: Path,
        required_cycles: int,
        *,
        store: Any,
        queue_tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        log_path = workspace / "LACE_LOG.md"
        log_valid_cycles: set[int] = set()
        log_issues: List[str] = []
        if log_path.exists():
            try:
                log_text = log_path.read_text(encoding="utf-8")
            except OSError:
                log_text = ""
                log_issues.append("No fue posible leer LACE_LOG.md.")
            if log_text:
                reports = inspect_lace_cycle_reports(log_text, required_cycles)
                log_valid_cycles = {int(report["cycle"]) for report in reports if report.get("valid")}
                _, log_issues = validate_lace_log(log_path, required_cycles)
        else:
            log_issues.append("No existe LACE_LOG.md.")

        queue_completed_cycles: set[int] = set()
        task_ids_by_cycle: Dict[int, List[str]] = {}
        for task in queue_tasks:
            task_id = str(task.get("id") or "")
            cycle_number = self._lace_cycle_from_task_id(task_id)
            if cycle_number is None:
                continue
            task_ids_by_cycle.setdefault(cycle_number, []).append(task_id)
            if task.get("status") == "completed":
                queue_completed_cycles.add(cycle_number)

        history_completed_cycles: set[int] = set()
        history_validated_cycles: set[int] = set()
        for event in store.load_task_history():
            result = event.get("result") if isinstance(event, dict) else None
            if not isinstance(result, dict):
                continue
            cycle_number = self._lace_cycle_from_task_id(str(result.get("task_id") or ""))
            if cycle_number is None:
                continue
            if result.get("completed") is True:
                history_completed_cycles.add(cycle_number)
            if result.get("validation_passed") is True:
                history_validated_cycles.add(cycle_number)

        checkpoint_cycles: set[int] = set()
        checkpoint_validated_cycles: set[int] = set()
        checkpoint_paths_by_cycle: Dict[int, str] = {}
        for cycle_number in range(1, required_cycles + 1):
            checkpoint_key = f"lace-cycle-{cycle_number:03d}-checkpoint"
            checkpoint_path = store.checkpoints_dir / f"{checkpoint_key}.json"
            if not checkpoint_path.exists():
                continue
            checkpoint_cycles.add(cycle_number)
            checkpoint_paths_by_cycle[cycle_number] = str(checkpoint_path)
            if self._lace_checkpoint_validation_passed(checkpoint_path):
                checkpoint_validated_cycles.add(cycle_number)

        doc_valid_cycles: set[int] = set()
        doc_files: List[str] = []
        doc_paths_by_cycle: Dict[int, str] = {}
        docs_dir = workspace / LACE_VISUAL_DIR
        for doc_path in sorted(docs_dir.glob("ciclo-*.md")) if docs_dir.exists() else []:
            match = re.search(r"ciclo-(\d+)\.md$", doc_path.name)
            if not match:
                continue
            cycle_number = int(match.group(1))
            try:
                text = doc_path.read_text(encoding="utf-8")
            except OSError:
                continue
            valid_doc = _has_canonical_lace_closure_marker(text)
            if valid_doc:
                doc_valid_cycles.add(cycle_number)
            relative_doc = doc_path.relative_to(workspace).as_posix()
            doc_files.append(relative_doc)
            doc_paths_by_cycle[cycle_number] = relative_doc

        canonical_completed_cycles = set()
        cycle_evidence: Dict[str, Dict[str, Any]] = {}
        for cycle_number in range(1, required_cycles + 1):
            has_completed_task = cycle_number in queue_completed_cycles or cycle_number in history_completed_cycles
            has_validation = cycle_number in history_validated_cycles or cycle_number in checkpoint_validated_cycles
            has_checkpoint = cycle_number in checkpoint_cycles
            has_valid_doc = cycle_number in doc_valid_cycles
            has_valid_lace_log = cycle_number in log_valid_cycles
            has_valid_lace_evidence = has_valid_doc or has_valid_lace_log
            if has_completed_task and has_validation and has_checkpoint and has_valid_lace_evidence:
                canonical_completed_cycles.add(cycle_number)
            cycle_evidence[str(cycle_number)] = {
                "task_ids": task_ids_by_cycle.get(cycle_number, []),
                "queue_completed": cycle_number in queue_completed_cycles,
                "history_completed": cycle_number in history_completed_cycles,
                "history_validation_passed": cycle_number in history_validated_cycles,
                "checkpoint_exists": has_checkpoint,
                "checkpoint_validation_passed": cycle_number in checkpoint_validated_cycles,
                "checkpoint_path": checkpoint_paths_by_cycle.get(cycle_number),
                "cycle_doc": doc_paths_by_cycle.get(cycle_number),
                "cycle_doc_valid": has_valid_doc,
                "lace_log_cycle_valid": has_valid_lace_log,
                "lace_evidence_valid": has_valid_lace_evidence,
                "lace_evidence_source": "canonical_header" if has_valid_doc else "lace_log" if has_valid_lace_log else "none",
                "canonical_complete": cycle_number in canonical_completed_cycles,
            }

        completed = sorted(canonical_completed_cycles)
        missing = [cycle for cycle in range(1, required_cycles + 1) if cycle not in canonical_completed_cycles]
        return {
            "required_cycles": required_cycles,
            "completed_cycles": len(completed),
            "completed_cycle_numbers": completed,
            "missing_cycles": missing,
            "lace_log_path": str(log_path),
            "cycle_docs": doc_files,
            "log_valid_cycle_numbers": sorted(log_valid_cycles),
            "queue_completed_cycle_numbers": sorted(queue_completed_cycles),
            "history_completed_cycle_numbers": sorted(history_completed_cycles),
            "history_validated_cycle_numbers": sorted(history_validated_cycles),
            "checkpoint_cycle_numbers": sorted(checkpoint_cycles),
            "checkpoint_validated_cycle_numbers": sorted(checkpoint_validated_cycles),
            "doc_valid_cycle_numbers": sorted(doc_valid_cycles),
            "cycle_evidence": cycle_evidence,
            "issues": log_issues,
        }

    def _lace_cycle_from_task_id(self, task_id: str) -> int | None:
        match = re.match(r"^LACE-\d{8}-(\d{3})$", str(task_id or ""))
        if not match:
            return None
        return int(match.group(1))

    def _lace_checkpoint_validation_passed(self, checkpoint_path: Path) -> bool:
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        payload = checkpoint.get("payload") if isinstance(checkpoint, dict) else None
        if not isinstance(payload, dict):
            return False
        candidates = [
            payload.get("task_result"),
            payload.get("validation"),
        ]
        validation = payload.get("validation")
        if isinstance(validation, dict):
            candidates.append(validation.get("task_result"))
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("validation_passed") is True:
                return True
        return False

    def _complete_lace_closure(self, store: Any, evidence: Dict[str, Any]) -> Dict[str, Any]:
        checkpoint_key = "lace-closure-gate-completed"
        stale_blocked_checkpoint = store.checkpoints_dir / "lace-closure-gate-blocked.json"
        try:
            if stale_blocked_checkpoint.exists():
                stale_blocked_checkpoint.unlink()
        except OSError:
            pass
        checkpoint_path = store.save_checkpoint(
            checkpoint_key,
            {
                "reason": "lace_cycles_completed",
                **evidence,
            },
        )
        state = store.load_project_state()
        state["status"] = "completed"
        state["current_task_id"] = None
        state["blocked_tasks"] = []
        state["failed_tasks"] = []
        state["checkpoints"] = _append_unique(
            [item for item in state.get("checkpoints", []) if item != "lace-closure-gate-blocked"],
            checkpoint_key,
        )
        state["updated_at"] = utc_now()
        store.save_project_state(state)
        return {
            "status": "clear",
            **evidence,
            "checkpoint": {"checkpoint_key": checkpoint_key, "path": str(checkpoint_path)},
        }

    def _build_lace_cycle_tasks(
        self,
        existing_tasks: List[Dict[str, Any]],
        missing_cycles: List[int],
        runtime_mode: str,
    ) -> List[Dict[str, Any]]:
        date_token = datetime.now(timezone.utc).strftime("%Y%m%d")
        previous_dependency = existing_tasks[-1]["id"] if existing_tasks else None
        tasks: List[Dict[str, Any]] = []
        for cycle_number in missing_cycles:
            task_id = f"LACE-{date_token}-{cycle_number:03d}"
            cycle_doc = lace_cycle_visual_relative_path(cycle_number)
            dependencies = [previous_dependency] if previous_dependency else []
            task = {
                "id": task_id,
                "title": f"Completar ciclo LACE {cycle_number:02d}",
                "goal": (
                    f"Completar el ciclo LACE {cycle_number:02d} como micro-tarea acotada. "
                    "Actualizar LACE_LOG.md con PROBLEMAS, MEJORA y COMPLETADO usando evidencia real; "
                    "sin convertir LACE en una tarea monolitica ni modificar producto salvo mejora verificable."
                ),
                "status": "pending",
                "priority": max(1, 100 - cycle_number),
                "dependencies": dependencies,
                "expected_files": ["LACE_LOG.md", cycle_doc],
                "validation_commands": [
                    (
                        "python3 -B -c \"from pathlib import Path; "
                        f"doc=Path('{cycle_doc}'); log=Path('LACE_LOG.md'); "
                        "assert log.exists(), 'missing LACE_LOG.md'; "
                        "assert doc.exists(), 'missing cycle doc'; "
                        "text=doc.read_text(encoding='utf-8').lower(); "
                        "assert 'valido para cierre lace: si' in text or 'válido para cierre lace: si' in text, "
                        "'cycle is not valid for LACE closure'\""
                    )
                ],
                "timeout_seconds": mode_timeout_seconds(runtime_mode),
                "max_retries": 2,
                "mode": runtime_mode,
                "checkpoint_key": f"lace-cycle-{cycle_number:03d}-checkpoint",
            }
            tasks.append(task)
            previous_dependency = task_id
        return tasks

    def _block_lace_closure(self, store: Any, evidence: Dict[str, Any], *, reason: str) -> Dict[str, Any]:
        checkpoint_key = "lace-closure-gate-blocked"
        checkpoint_path = store.save_checkpoint(
            checkpoint_key,
            {
                "reason": reason,
                **evidence,
            },
        )
        failure_event = store.append_failure(
            {
                "task_id": "lace-closure-gate",
                "failure_type": reason,
                "required_cycles": evidence.get("required_cycles"),
                "completed_cycles": evidence.get("completed_cycles"),
                "missing_cycles": evidence.get("missing_cycles"),
                "checkpoint_key": checkpoint_key,
            }
        )
        state = store.load_project_state()
        state["status"] = "blocked"
        state["current_task_id"] = None
        state["blocked_tasks"] = _append_unique(state.get("blocked_tasks", []), reason)
        state["checkpoints"] = _append_unique(state.get("checkpoints", []), checkpoint_key)
        state["updated_at"] = utc_now()
        store.save_project_state(state)
        return {
            "status": "blocked",
            "reason": reason,
            **evidence,
            "checkpoint": {"checkpoint_key": checkpoint_key, "path": str(checkpoint_path)},
            "failure_event": failure_event,
        }

    def _derive_canonical_control_plane_outcome(
        self,
        runtime_dir: str | Path,
        *,
        sequence_status: str,
        sequence_stopped_reason: str | None = None,
        blocked_by_lace: bool = False,
        lace_gate_message: str | None = None,
        lace_closure_message: str | None = None,
    ) -> Dict[str, Any]:
        try:
            store = StateStore(runtime_dir)  # type: ignore[operator]
            state = store.load_project_state()
            queue_tasks = TaskQueue(store, bootstrap_empty=True).list()  # type: ignore[operator]
            failures = store.load_failures()
        except Exception as error:
            return {
                "session_status": "failed",
                "event_op": "session_failed",
                "event_status": "failed",
                "phase": "failed",
                "error_code": "control_plane_state_unreadable",
                "message": f"No se pudo leer el estado canonico del runtime: {error}",
                "completed": False,
                "warnings": [],
            }

        failed_tasks = list(state.get("failed_tasks") or [])
        blocked_tasks = list(state.get("blocked_tasks") or [])
        queue_failed = [task["id"] for task in queue_tasks if task.get("status") == "failed"]
        queue_blocked = [task["id"] for task in queue_tasks if task.get("status") == "blocked"]
        queue_unfinished = [task["id"] for task in queue_tasks if task.get("status") != "completed"]
        state_completed = (
            state.get("status") == "completed"
            and state.get("current_task_id") is None
            and not failed_tasks
            and not blocked_tasks
            and bool(queue_tasks)
            and not queue_unfinished
        )

        failure_events = [event for event in failures if isinstance(event, dict)]
        warnings: List[str] = []
        if failure_events:
            warnings.append(f"failure_events={len(failure_events)}")

        if sequence_status == "stopped" or sequence_stopped_reason == "stop_requested":
            return {
                "session_status": "stopped",
                "event_op": "session_stopped",
                "event_status": "stopped",
                "phase": "stopped",
                "error_code": "control_plane_stopped",
                "message": "Sesion detenida por el usuario; no se lanzaran retries nuevos.",
                "completed": False,
                "warnings": warnings,
            }

        if state_completed:
            if warnings:
                return {
                    "session_status": "completed",
                    "event_op": "session_completed_with_warnings",
                    "event_status": "completed",
                    "phase": "complete",
                    "error_code": None,
                    "message": "La sesion termino segun estado canonico persistido, con advertencias: " + "; ".join(warnings),
                    "completed": True,
                    "warnings": warnings,
                }
            return {
                "session_status": "completed",
                "event_op": "session_completed",
                "event_status": "completed",
                "phase": "complete",
                "error_code": None,
                "message": "La sesion termino segun estado canonico persistido: cola completa, sin fallos ni bloqueos activos.",
                "completed": True,
                "warnings": [],
            }

        if state.get("status") == "failed" or failed_tasks or queue_failed:
            return {
                "session_status": "failed",
                "event_op": "session_failed",
                "event_status": "failed",
                "phase": "failed",
                "error_code": "control_plane_task_failed",
                "message": (
                    "El estado canonico contiene fallo real: "
                    f"failed_tasks={failed_tasks}, queue_failed={queue_failed}."
                ),
                "completed": False,
                "warnings": warnings,
            }

        if blocked_by_lace or state.get("status") == "blocked" or blocked_tasks or queue_blocked:
            return {
                "session_status": "blocked",
                "event_op": "session_blocked",
                "event_status": "blocked",
                "phase": "blocked",
                "error_code": "lace_cycles_pending" if blocked_by_lace else "control_plane_blocked",
                "message": (
                    lace_gate_message
                    or lace_closure_message
                    or "El estado canonico mantiene bloqueos activos: "
                    + f"blocked_tasks={blocked_tasks}, queue_blocked={queue_blocked}."
                ),
                "completed": False,
                "warnings": warnings,
            }

        return {
            "session_status": "failed",
            "event_op": "session_failed",
            "event_status": "failed",
            "phase": "failed",
            "error_code": "control_plane_incomplete",
            "message": (
                "La sesion no cumple cierre canonico: "
                f"project_status={state.get('status')}, unfinished_tasks={queue_unfinished}."
            ),
            "completed": False,
            "warnings": warnings,
        }

    def _recover_stale_running_tasks(self, store: Any, queue: Any) -> bool:
        """Requeue tasks left in running state after an interrupted backend process."""

        running_task_ids = [
            str(task.get("id") or "")
            for task in queue.list()
            if task.get("status") == "running" and str(task.get("id") or "")
        ]
        if not running_task_ids:
            return False

        for task_id in running_task_ids:
            queue.mark_task_status(task_id, "pending")

        checkpoint_key = "stale-running-recovered-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        store.save_checkpoint(
            checkpoint_key,
            {
                "reason": "stale_running_requeued",
                "task_ids": running_task_ids,
            },
        )
        state = store.load_project_state()
        state["status"] = "initialized"
        state["current_task_id"] = None
        state["failed_tasks"] = [
            item for item in state.get("failed_tasks", []) if str(item) not in running_task_ids
        ]
        state["blocked_tasks"] = [
            item for item in state.get("blocked_tasks", []) if str(item) not in running_task_ids
        ]
        state["checkpoints"] = _append_unique(state.get("checkpoints", []), checkpoint_key)
        state["updated_at"] = utc_now()
        store.save_project_state(state)
        return True

    def _control_plane_has_ready_task(self, runtime_dir: str | Path) -> bool:
        try:
            store = StateStore(runtime_dir)  # type: ignore[operator]
            return TaskQueue(store, bootstrap_empty=True).next_ready_task() is not None  # type: ignore[operator]
        except Exception:
            return False

    def _reconcile_recovered_split_tasks_for_runtime(
        self,
        runtime_dir: str | Path,
        workspace: str | Path,
    ) -> bool:
        try:
            store = StateStore(runtime_dir)  # type: ignore[operator]
            queue = TaskQueue(store, bootstrap_empty=True)  # type: ignore[operator]
            return self._reconcile_recovered_split_tasks(store, queue, Path(workspace).resolve())
        except Exception:
            return False

    def _reconcile_recovered_split_tasks(self, store: Any, queue: Any, workspace: Path) -> bool:
        """Complete blocked split parents only after descendant evidence validates on disk."""

        if validate_task_execution is None:
            return False

        changed = False
        reconciled_ids: List[str] = []
        workspace_path = Path(workspace).resolve()
        for _ in range(max(1, len(queue.list()))):
            tasks = queue.list()
            completed_descendants = self._completed_split_descendants(tasks, store.load_task_history())
            round_changed = False
            for task in tasks:
                task_id = str(task.get("id") or "")
                if task.get("status") not in {"blocked", "failed"}:
                    continue
                descendants = completed_descendants.get(task_id, [])
                if not descendants:
                    continue
                validation = self._validate_recovered_task_evidence(task, workspace_path)
                task_result = validation.get("task_result") if isinstance(validation, dict) else None
                if not isinstance(task_result, dict):
                    continue
                if not task_result.get("completed") or not task_result.get("validation_passed"):
                    continue

                queue.mark_task_status(task_id, "completed")
                checkpoint_key = task.get("checkpoint_key") or f"{task_id.lower()}-completed"
                checkpoint_path = store.save_checkpoint(
                    checkpoint_key,
                    {
                        "task": task,
                        "task_result": task_result,
                        "validation": validation.get("validation"),
                        "reconciled_from_split_descendants": descendants,
                    },
                )
                if not self._history_has_completed_task(store, task_id):
                    store.append_task_history(task_result)
                self._save_project_state_transition(store, task, "completed", checkpoint_key=checkpoint_key)
                reconciled_ids.append(task_id)
                changed = True
                round_changed = True
            if not round_changed:
                break

        if changed:
            self._refresh_project_state_after_reconciliation(store, queue, reconciled_ids)
        return changed

    def _completed_split_descendants(
        self,
        tasks: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        completed_ids = {
            str(task.get("id"))
            for task in tasks
            if task.get("status") == "completed" and str(task.get("id") or "")
        }
        for event in history:
            result = event.get("result") if isinstance(event, dict) else None
            if not isinstance(result, dict):
                continue
            task_id = str(result.get("task_id") or "")
            if task_id and result.get("completed") is True and result.get("validation_passed") is True:
                completed_ids.add(task_id)

        descendants_by_parent: Dict[str, List[str]] = {}
        for task in tasks:
            parent_id = str(task.get("id") or "")
            if not parent_id:
                continue
            prefix = f"{parent_id}-SPLIT-"
            descendants = sorted(task_id for task_id in completed_ids if task_id.startswith(prefix))
            if descendants:
                descendants_by_parent[parent_id] = descendants
        return descendants_by_parent

    def _validate_recovered_task_evidence(self, task: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
        expected_files = list(task.get("expected_files") or [])
        synthetic_result = {
            "task_id": task["id"],
            "completed": True,
            "files_created": [],
            "files_modified": expected_files,
            "validation_ran": [],
            "validation_passed": True,
            "blockers": [],
            "next_recommendation": "Tarea reconciliada desde subtareas split completadas y evidencia validada en disco.",
        }
        return validate_task_execution(  # type: ignore[misc]
            task,
            {"task_result": synthetic_result},
            workspace=workspace,
            command_timeout_seconds=max(1, min(300, int(task.get("timeout_seconds") or 300))),
        )

    def _history_has_completed_task(self, store: Any, task_id: str) -> bool:
        for event in store.load_task_history():
            result = event.get("result") if isinstance(event, dict) else None
            if (
                isinstance(result, dict)
                and result.get("task_id") == task_id
                and result.get("completed") is True
                and result.get("validation_passed") is True
            ):
                return True
        return False

    def _refresh_project_state_after_reconciliation(
        self,
        store: Any,
        queue: Any,
        reconciled_ids: List[str],
    ) -> None:
        tasks = queue.list()
        task_ids = {str(task.get("id") or "") for task in tasks}
        failed_ids = [task["id"] for task in tasks if task.get("status") == "failed"]
        blocked_ids = [task["id"] for task in tasks if task.get("status") == "blocked"]
        running_ids = [task["id"] for task in tasks if task.get("status") == "running"]
        completed_ids = [task["id"] for task in tasks if task.get("status") == "completed"]
        ready_ids = [task["id"] for task in queue.ready_tasks()]

        state = store.load_project_state()
        completed_state = list(state.get("completed_tasks", []))
        for task_id in completed_ids:
            completed_state = _append_unique(completed_state, task_id)
        state["completed_tasks"] = completed_state

        failed_state = list(state.get("failed_tasks", []))
        for task_id in failed_ids:
            failed_state = _append_unique(failed_state, task_id)
        state["failed_tasks"] = [item for item in failed_state if item in failed_ids and item not in reconciled_ids]

        blocked_state = list(state.get("blocked_tasks", []))
        for task_id in blocked_ids:
            blocked_state = _append_unique(blocked_state, task_id)
        state["blocked_tasks"] = [item for item in blocked_state if item in blocked_ids and item not in reconciled_ids]

        if running_ids:
            state["status"] = "running"
            state["current_task_id"] = running_ids[0]
        elif failed_ids:
            state["status"] = "failed"
            state["current_task_id"] = None
        elif blocked_ids and not ready_ids:
            state["status"] = "blocked"
            state["current_task_id"] = None
        elif tasks and len(completed_ids) == len(task_ids):
            state["status"] = "completed"
            state["current_task_id"] = None
        else:
            state["status"] = "initialized"
            state["current_task_id"] = None
        state["updated_at"] = utc_now()
        store.save_project_state(state)

    def _control_plane_queue_snapshot(self, runtime_dir: str | Path) -> Dict[str, Any]:
        store = StateStore(runtime_dir)  # type: ignore[operator]
        queue = TaskQueue(store, bootstrap_empty=True)  # type: ignore[operator]
        tasks = queue.list()
        return {
            "tasks": tasks,
            "ready_task_ids": [task["id"] for task in queue.ready_tasks()],
            "blocked_tasks": queue.blocked_tasks(),
        }

    def _build_control_plane_tool_policy(
        self,
        *,
        runtime_dir: str | Path,
        workspace: str | Path,
    ) -> Any:
        if ToolInvocationPolicy is None:
            return None
        return ToolInvocationPolicy(  # type: ignore[operator]
            runtime_dir=runtime_dir,
            workspace=workspace,
            project_slug=Path(workspace).resolve().name,
            strict_closure=env_flag_enabled(os.environ.get("HABLA_TOOL_POLICY_STRICT"), default=False),
        )

    def _append_control_plane_tool_summary(
        self,
        session_id: str | None,
        label: str,
        report: Dict[str, Any] | None,
    ) -> None:
        if not session_id or not isinstance(report, dict):
            return
        invocations = [
            {
                "tool": item.get("tool"),
                "ok": item.get("ok"),
                "statusCode": item.get("statusCode"),
                "required": item.get("required"),
                "artifactPath": item.get("artifactPath"),
            }
            for item in report.get("invocations", [])
            if isinstance(item, dict)
        ]
        summary = {
            "phase": report.get("phase"),
            "closureAllowed": report.get("closureAllowed"),
            "activeFindings": report.get("activeFindings"),
            "warnings": report.get("warnings"),
            "blockers": report.get("blockers"),
            "artifactPath": report.get("artifactPath"),
            "invocations": invocations,
        }
        self._append_output(
            session_id,
            f"[control-plane] Herramientas internas ({label}):\n"
            + json.dumps(summary, ensure_ascii=True, indent=2)
            + "\n",
        )

    def _run_control_plane_final_tool_gate(
        self,
        *,
        runtime_dir: str | Path,
        workspace: str | Path,
        session_id: str | None,
    ) -> Dict[str, Any] | None:
        policy = self._build_control_plane_tool_policy(runtime_dir=runtime_dir, workspace=workspace)
        if policy is None:
            return None
        report = policy.run_project_completion_gate()
        self._append_control_plane_tool_summary(session_id, "project_completion_gate", report)
        return report

    def _emit_control_plane_sync_file_events(
        self,
        session_id: str,
        workspace: str | Path,
        task_result: Dict[str, Any],
    ) -> None:
        workspace_path = Path(workspace).resolve()
        with self.lock:
            session = self.sessions.get(session_id)
            base_payload = {
                "sessionId": session.session_id,
                "projectSlug": session.project_slug,
                "projectDir": str(session.project_dir),
            } if session is not None else {}
        seen: set[str] = set()
        for raw_path in [
            *list(task_result.get("files_created") or []),
            *list(task_result.get("files_modified") or []),
        ]:
            relative = self._relative_workspace_file(workspace_path, str(raw_path))
            if (
                not relative
                or relative in seen
                or relative.startswith("runtime/")
                or relative.startswith("workspace/projects/")
                or is_runtime_control_path(relative)
                or is_control_plane_state_path(relative)
            ):
                continue
            seen.add(relative)
            source_path = (workspace_path / relative).resolve()
            if not source_path.exists() or not source_path.is_file():
                continue
            payload = {
                **base_payload,
                "op": "sync_file",
                "relativePath": relative,
                "sourcePath": str(source_path),
                "layer": self._visual_layer_for_relative_path(relative),
                "layerLabel": self._visual_layer_for_relative_path(relative).title(),
                "codeLanguage": self._visual_language_for_relative_path(relative),
                "status": "generated" if raw_path in task_result.get("files_created", []) else "modified",
                "description": f"Evidencia real sincronizada automaticamente para {task_result.get('task_id')}.",
                "message": f"Fallback visual: se sincronizo {relative} desde TaskResult.",
            }
            self._persist_runtime_trace(session_id, payload)
            self._dispatch_runtime_payload(session_id, payload, count_visual=True, track_activity=True)

    def _relative_workspace_file(self, workspace: Path, raw_path: str) -> str | None:
        try:
            candidate = Path(raw_path)
            resolved = candidate.resolve() if candidate.is_absolute() else (workspace / raw_path).resolve()
            resolved.relative_to(workspace)
        except (OSError, ValueError):
            return None
        return resolved.relative_to(workspace).as_posix()

    def _visual_layer_for_relative_path(self, relative_path: str) -> str:
        first = relative_path.split("/", 1)[0].lower()
        if first in {"frontend", "backend", "shared", "tests", "docs", "assets", "src"}:
            return "backend" if first == "src" else first
        suffix = Path(relative_path).suffix.lower()
        if suffix in {".html", ".css", ".jsx", ".tsx"}:
            return "frontend"
        if suffix in {".py"}:
            return "backend"
        if suffix in {".md"}:
            return "docs"
        return "shared"

    def _visual_language_for_relative_path(self, relative_path: str) -> str:
        suffix = Path(relative_path).suffix.lower()
        return {
            ".html": "html",
            ".css": "css",
            ".js": "javascript",
            ".jsx": "jsx",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".py": "python",
            ".json": "json",
            ".md": "markdown",
        }.get(suffix, suffix.lstrip(".") or "text")

    def _execute_prepared_control_plane_task(
        self,
        prepared: Dict[str, Any],
        *,
        command: List[str] | str,
        workspace: str | Path,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        self._require_control_plane_imports()
        store = StateStore(prepared["runtime_dir"])  # type: ignore[operator]
        task = dict(prepared["task"])
        directive = dict(prepared["directive"])
        queue = TaskQueue(store)  # type: ignore[operator]
        tool_policy = self._build_control_plane_tool_policy(
            runtime_dir=prepared["runtime_dir"],
            workspace=workspace,
        )
        self._save_project_state_transition(store, task, "preparing")
        if session_id:
            self._append_output(
                session_id,
                f"[control-plane] Preflight interno opcional para {task['id']}; si observer-status expira se continua.\n",
            )
        preflight_tools = tool_policy.run_preflight(task) if tool_policy is not None else None
        self._append_control_plane_tool_summary(session_id, "preflight", preflight_tools)

        existing_evidence_result = self._complete_prepared_control_plane_task_from_existing_evidence(
            store=store,
            queue=queue,
            task=task,
            directive=directive,
            prepared=prepared,
            workspace=workspace,
            session_id=session_id,
        )
        if existing_evidence_result is not None:
            existing_tools = {"preflight": preflight_tools}
            if tool_policy is not None and isinstance(existing_evidence_result.get("task_result"), dict):
                completion_tools = tool_policy.run_task_completion_gate(task, existing_evidence_result["task_result"])
                self._append_control_plane_tool_summary(session_id, "task_completion_gate", completion_tools)
                existing_tools["task_completion_gate"] = completion_tools
            existing_evidence_result["tool_invocations"] = existing_tools
            return existing_evidence_result

        cyberlace_tool_decision = self._cyberlace_guard(
            "tool",
            agent_id="control-plane-worker",
            session_id=session_id,
            tool_name="codex_worker",
            tool_args={
                "command": command if isinstance(command, list) else str(command),
                "workspace": str(Path(workspace).resolve()),
                "directive_json_path": prepared.get("directive_json_path"),
                "task_id": task.get("id"),
            },
            context={"task": task, "directive": {"source_hash": directive.get("traceability", {}).get("source_hash")}},
        )
        if self._cyberlace_should_block(cyberlace_tool_decision):
            task_result = {
                "task_id": task["id"],
                "completed": False,
                "files_created": [],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": False,
                "blockers": [self._cyberlace_block_message(cyberlace_tool_decision, stage="tool")],
                "next_recommendation": "Esperar revision humana o ajustar la directiva para reducir riesgo CyberLACE.",
            }
            validation = {"task_result": task_result, "validation": {"passed": False, "commands": [], "blockers": task_result["blockers"]}}
            queue.mark_task_status(task["id"], "blocked")
            history_event = store.append_task_history(task_result)
            checkpoint_key = f"{task['id'].lower()}-cyberlace-blocked"
            checkpoint_path = store.save_checkpoint(
                checkpoint_key,
                {"task": task, "task_result": task_result, "cyberlace": cyberlace_tool_decision, "reason": "cyberlace_tool_blocked"},
            )
            self._save_project_state_transition(store, task, "blocked", checkpoint_key=checkpoint_key)
            return {
                "status": "blocked",
                "task": task,
                "directive": directive,
                "directive_json_path": prepared.get("directive_json_path"),
                "directive_markdown_path": prepared.get("directive_markdown_path"),
                "execution": {"execution": {"returncode": 126, "stdout": "", "stderr": task_result["blockers"][0]}},
                "validation": validation,
                "task_result": task_result,
                "history_event": history_event,
                "checkpoint": {"checkpoint_key": checkpoint_key, "path": str(checkpoint_path)},
                "recovery": None,
                "tool_invocations": {"preflight": preflight_tools, "cyberlace_tool": cyberlace_tool_decision},
                "retry_count": self._next_retry_count_for_task(store, task["id"]),
                "enqueued_split_tasks": [],
            }

        if session_id:
            self._append_output(
                session_id,
                "[control-plane] Ejecutando tarea "
                f"{task['id']} con timeout {task['timeout_seconds']}s y directiva "
                f"{prepared.get('directive_json_path')}.\n",
            )

        active_process: subprocess.Popen[Any] | None = None

        def on_process_start(process: subprocess.Popen[Any]) -> None:
            nonlocal active_process
            active_process = process
            queue.mark_task_status(task["id"], "running")
            self._save_project_state_transition(store, task, "running")
            self._attach_control_plane_process(session_id, process)

        try:
            execution = execute_task_with_details(  # type: ignore[misc]
                task,
                workspace=workspace,
                command=command,
                shell=False,
                extra_env=self._control_plane_worker_env(
                    session_id=session_id,
                    workspace=workspace,
                    runtime_dir=prepared["runtime_dir"],
                ),
                on_process_start=on_process_start if session_id else None,
                should_stop=(lambda: self._control_plane_session_stop_requested(session_id)) if session_id else None,
            )
        finally:
            self._clear_control_plane_process(session_id, active_process)
        if session_id and any(str(path).startswith("docs/lace_cycles/") for path in task.get("expected_files", [])):
            self._sync_lace_runtime(session_id)
        validation = validate_task_execution(  # type: ignore[misc]
            task,
            execution,
            workspace=workspace,
            command_timeout_seconds=max(1, min(300, int(task["timeout_seconds"]))),
        )
        task_result = validation["task_result"]
        cyberlace_output_decision = self._cyberlace_guard(
            "output",
            agent_id="control-plane-worker",
            session_id=session_id,
            content=json.dumps({"task_result": task_result, "validation": validation.get("validation")}, ensure_ascii=True),
            context={"task": task, "workspace": str(Path(workspace).resolve())},
        )
        if self._cyberlace_should_redact(cyberlace_output_decision):
            task_result = {
                **task_result,
                "blockers": [*list(task_result.get("blockers") or []), "CyberLACE redacted sensitive output evidence."],
            }
        if self._cyberlace_should_block(cyberlace_output_decision):
            task_result = {
                **task_result,
                "completed": False,
                "validation_passed": False,
                "blockers": [
                    *list(task_result.get("blockers") or []),
                    self._cyberlace_block_message(cyberlace_output_decision, stage="output"),
                ],
                "next_recommendation": "Revisar salida bloqueada por CyberLACE antes de continuar.",
            }
            validation = {**validation, "task_result": task_result}
        stop_requested = self._control_plane_session_stop_requested(session_id) if session_id else False
        postflight_tools = None
        completion_tools = None
        recovery_preview_tools = None
        if tool_policy is not None:
            postflight_tools = tool_policy.run_postflight(task, task_result)
            self._append_control_plane_tool_summary(session_id, "postflight", postflight_tools)
            if task_result["completed"] and task_result["validation_passed"]:
                completion_tools = tool_policy.run_task_completion_gate(task, task_result)
                self._append_control_plane_tool_summary(session_id, "task_completion_gate", completion_tools)
                if completion_tools.get("closureAllowed") is False:
                    task_result = {
                        **task_result,
                        "completed": False,
                        "validation_passed": False,
                        "blockers": [
                            *list(task_result.get("blockers") or []),
                            "Tool Invocation Policy blocked task closure.",
                        ],
                        "next_recommendation": "Fix required internal-tool blockers, then rerun this task.",
                    }
            elif not stop_requested:
                recovery_preview_tools = tool_policy.run_recovery_preview(task, task_result)
                self._append_control_plane_tool_summary(session_id, "recovery_preview", recovery_preview_tools)
        tool_invocations = {
            "preflight": preflight_tools,
            "postflight": postflight_tools,
            "task_completion_gate": completion_tools,
            "recovery_preview": recovery_preview_tools,
            "cyberlace_tool": cyberlace_tool_decision,
            "cyberlace_output": cyberlace_output_decision,
        }
        if session_id:
            self._emit_control_plane_sync_file_events(session_id, workspace, task_result)
            self._sync_lace_runtime(session_id)
        history_event = store.append_task_history(task_result)
        if stop_requested:
            queue.mark_task_status(task["id"], "pending")
            checkpoint_key = f"{task['id'].lower()}-stopped"
            checkpoint_path = store.save_checkpoint(
                checkpoint_key,
                {
                    "task": task,
                    "task_result": task_result,
                    "validation": validation.get("validation"),
                    "tool_invocations": tool_invocations,
                    "reason": "stop_requested",
                },
            )
            self._save_project_state_transition(store, task, "stopped", checkpoint_key=checkpoint_key)
            return {
                "status": "stopped",
                "task": task,
                "directive": directive,
                "directive_json_path": prepared.get("directive_json_path"),
                "directive_markdown_path": prepared.get("directive_markdown_path"),
                "execution": execution,
                "validation": validation,
                "task_result": task_result,
                "history_event": history_event,
                "checkpoint": {"checkpoint_key": checkpoint_key, "path": str(checkpoint_path)},
                "recovery": None,
                "tool_invocations": tool_invocations,
                "retry_count": self._next_retry_count_for_task(store, task["id"]),
                "enqueued_split_tasks": [],
            }

        if task_result["completed"] and task_result["validation_passed"]:
            queue.mark_task_status(task["id"], "completed")
            checkpoint_key = task.get("checkpoint_key") or f"{task['id'].lower()}-completed"
            checkpoint_path = store.save_checkpoint(
                checkpoint_key,
                {
                    "task": task,
                    "task_result": task_result,
                    "validation": validation.get("validation"),
                    "tool_invocations": tool_invocations,
                    "directive": {
                        "json_path": prepared.get("directive_json_path"),
                        "markdown_path": prepared.get("directive_markdown_path"),
                        "source_hash": directive.get("traceability", {}).get("source_hash"),
                    },
                },
            )
            self._save_project_state_transition(store, task, "completed", checkpoint_key=checkpoint_key)
            return {
                "status": "completed",
                "task": task,
                "directive": directive,
                "directive_json_path": prepared.get("directive_json_path"),
                "directive_markdown_path": prepared.get("directive_markdown_path"),
                "execution": execution,
                "validation": validation,
                "task_result": task_result,
                "history_event": history_event,
                "checkpoint": {"checkpoint_key": checkpoint_key, "path": str(checkpoint_path)},
                "recovery": None,
                "tool_invocations": tool_invocations,
            }

        retry_count = self._next_retry_count_for_task(store, task["id"])
        recovery = recover_task(  # type: ignore[misc]
            task,
            {
                "task_result": task_result,
                "execution": execution.get("execution"),
                "validation": validation.get("validation"),
                "tool_invocations": tool_invocations,
            },
            retry_count=retry_count,
            store=store,
        )
        action = recovery["decision"]["action"]
        queue_status, enqueued_split_tasks = self._apply_recovery_decision(
            store,
            queue,
            task,
            recovery,
        )
        blanqueo = self._maybe_apply_control_plane_blanqueo_protocol(
            store=store,
            task=task,
            task_result=task_result,
            validation=validation,
            execution=execution,
            recovery=recovery,
            retry_count=retry_count,
            workspace=workspace,
            runtime_dir=prepared["runtime_dir"],
            session_id=session_id,
        )
        return {
            "status": queue_status,
            "task": task,
            "directive": directive,
            "directive_json_path": prepared.get("directive_json_path"),
            "directive_markdown_path": prepared.get("directive_markdown_path"),
            "execution": execution,
            "validation": validation,
            "task_result": task_result,
            "history_event": history_event,
            "checkpoint": recovery.get("checkpoint"),
            "recovery": recovery,
            "tool_invocations": tool_invocations,
            "blanqueo": blanqueo,
            "retry_count": retry_count,
            "enqueued_split_tasks": enqueued_split_tasks,
        }

    def _maybe_apply_control_plane_blanqueo_protocol(
        self,
        *,
        store: Any,
        task: Dict[str, Any],
        task_result: Dict[str, Any],
        validation: Dict[str, Any],
        execution: Dict[str, Any],
        recovery: Dict[str, Any],
        retry_count: int,
        workspace: str | Path,
        runtime_dir: str | Path,
        session_id: str | None,
    ) -> Dict[str, Any] | None:
        if decidir_y_justificar_blanqueo is None:
            return None
        failure_attempts = retry_count + 1
        if failure_attempts < 3:
            return None
        if not self._is_compile_or_validation_failure(task_result, validation, execution):
            return None

        task_id = str(task.get("id") or "")
        selective_already_attempted = self._blanqueo_decision_recorded(store, task_id, "selective")
        total_already_recorded = self._blanqueo_decision_recorded(store, task_id, "total")
        requested_scope = "total" if selective_already_attempted else "selective"
        if requested_scope == "total" and total_already_recorded:
            return None

        runtime_mode = normalize_agent_runtime_mode(task.get("mode") or "build")
        workspace_path = Path(workspace).resolve()
        runtime_path = Path(runtime_dir).resolve()
        backup_base = self.repo_root / "backups" / "blanqueo"
        blockers = [str(item) for item in task_result.get("blockers", []) if str(item).strip()]
        validation_body = validation.get("validation") if isinstance(validation, dict) else {}
        evidence = []
        if blockers:
            evidence.extend(blockers[:6])
        if isinstance(validation_body, dict):
            for command in validation_body.get("commands", []) or []:
                if isinstance(command, dict) and command.get("returncode") not in {0, None}:
                    evidence.append(
                        f"Validation command failed ({command.get('returncode')}): {command.get('command')}"
                    )
            validation_evidence = validation_body.get("evidence")
            if isinstance(validation_evidence, dict):
                missing = [
                    record.get("path")
                    for record in validation_evidence.get("records", [])
                    if isinstance(record, dict) and not record.get("exists")
                ]
                evidence.extend(f"Missing expected file: {path}" for path in missing if path)

        decision = decidir_y_justificar_blanqueo(
            task_id=task_id or "CONTROL-PLANE-TASK",
            mode=runtime_mode,
            requested_scope=requested_scope,
            source="agent_runtime",
            repair_attempts=failure_attempts,
            compile_failed=True,
            irrecoverable=False,
            selective_attempted=selective_already_attempted,
            root_cause=(
                "Fallo critico de compilacion/validacion end-to-end detectado por AgentRuntime "
                f"tras {failure_attempts} intentos consecutivos."
            ),
            attempted_repairs=[
                f"retry_count={retry_count}",
                f"recovery_action={recovery.get('decision', {}).get('action')}",
                f"checkpoint={recovery.get('checkpoint', {}).get('checkpoint_key')}",
            ],
            evidence=evidence or ["validation_passed=False", "task_result.completed=False"],
            risk_of_not_cleaning=[
                "seguir relanzando workers sobre un workspace degradado",
                "propagar codigo incompleto a tareas posteriores",
                "ocultar fallos end-to-end detras de retries",
            ],
            expected_benefits=[
                "restablecer estado limpio con auditoria",
                "forzar recuperacion posterior con POST-BLANQUEO-RECOVERY",
                "evitar bucles de reparacion sin evidencia funcional",
            ],
            planned_backup_dir=str(backup_base),
        )
        audit = record_blanqueo_decision(decision, runtime_path)  # type: ignore[misc]
        result: Dict[str, Any] = {
            "triggered": True,
            "attempts": failure_attempts,
            "decision": decision,
            "audit": audit,
            "backup": None,
            "cleanup": None,
            "recovery": None,
        }

        if not decision.get("allowed"):
            self._append_control_plane_blanqueo_notice(session_id, decision, audit, action_taken=False)
            self._emit_control_plane_blanqueo_event(session_id, workspace_path, decision, action_taken=False)
            return result

        backup = create_blanqueo_backup(  # type: ignore[misc]
            project_root=self.repo_root,
            workspace_root=workspace_path,
            runtime_dirs=[runtime_path],
            backup_base=backup_base,
            decision=decision,
        )
        if decision.get("scope") == "total":
            cleanup = apply_total_blanqueo(workspace_path)  # type: ignore[misc]
        else:
            cleanup = apply_selective_blanqueo(workspace_path, runtime_dirs=[runtime_path])  # type: ignore[misc]
        post_recovery = create_post_blanqueo_recovery(  # type: ignore[misc]
            runtime_dir=runtime_path,
            decision=decision,
            backup=backup,
        )
        result.update({"backup": backup, "cleanup": cleanup, "recovery": post_recovery})
        self._append_control_plane_blanqueo_notice(session_id, decision, audit, action_taken=True, backup=backup, cleanup=cleanup)
        self._emit_control_plane_blanqueo_event(session_id, workspace_path, decision, action_taken=True, backup=backup, cleanup=cleanup)
        return result

    def _is_compile_or_validation_failure(
        self,
        task_result: Dict[str, Any],
        validation: Dict[str, Any],
        execution: Dict[str, Any],
    ) -> bool:
        if task_result.get("validation_passed") is False or task_result.get("completed") is False:
            return True
        validation_body = validation.get("validation") if isinstance(validation, dict) else {}
        if isinstance(validation_body, dict) and validation_body.get("validation_passed") is False:
            return True
        execution_body = execution.get("execution") if isinstance(execution, dict) else {}
        return isinstance(execution_body, dict) and bool(execution_body.get("timed_out"))

    def _blanqueo_decision_recorded(self, store: Any, task_id: str, scope: str) -> bool:
        for event in store.load_failures():
            failure = event.get("failure") if isinstance(event, dict) else None
            if not isinstance(failure, dict):
                continue
            if failure.get("type") != "BLANQUEO_DECISION":
                continue
            if failure.get("task_id") == task_id and failure.get("scope") == scope:
                return True
        return False

    def _append_control_plane_blanqueo_notice(
        self,
        session_id: str | None,
        decision: Dict[str, Any],
        audit: Dict[str, Any],
        *,
        action_taken: bool,
        backup: Dict[str, Any] | None = None,
        cleanup: Dict[str, Any] | None = None,
    ) -> None:
        if not session_id:
            return
        summary = {
            "decision": decision.get("decision"),
            "scope": decision.get("scope"),
            "allowed": decision.get("allowed"),
            "requires_confirmation": decision.get("requires_confirmation"),
            "action_taken": action_taken,
            "backup_dir": (backup or {}).get("backup_dir"),
            "removed_count": (cleanup or {}).get("removedCount"),
            "decision_markdown": audit.get("decision_markdown"),
        }
        self._append_output(
            session_id,
            "[control-plane] Protocolo Blanquear Workspace activado:\n"
            + json.dumps(summary, ensure_ascii=True, indent=2)
            + "\n",
        )

    def _emit_control_plane_blanqueo_event(
        self,
        session_id: str | None,
        workspace: Path,
        decision: Dict[str, Any],
        *,
        action_taken: bool,
        backup: Dict[str, Any] | None = None,
        cleanup: Dict[str, Any] | None = None,
    ) -> None:
        if not session_id:
            return
        self.visual_event_handler(
            {
                "op": "workspace_blanqueo_protocol",
                "session_id": session_id,
                "project_id": workspace.name,
                "phase": "cleanup",
                "status": "completed" if action_taken else "blocked",
                "scope": decision.get("scope"),
                "message": (
                    f"{decision.get('decision')} "
                    + ("ejecutado" if action_taken else "requiere confirmacion humana")
                ),
                "backup_dir": (backup or {}).get("backup_dir"),
                "removed_count": (cleanup or {}).get("removedCount"),
                "decision": decision,
            }
        )

    def _apply_recovery_decision(
        self,
        store: Any,
        queue: Any,
        task: Dict[str, Any],
        recovery: Dict[str, Any],
    ) -> tuple[str, List[Dict[str, Any]]]:
        decision = dict(recovery.get("decision") or {})
        action = str(decision.get("action") or "")
        checkpoint_key = recovery.get("checkpoint", {}).get("checkpoint_key")

        if action == "retry":
            queue.mark_task_status(task["id"], "pending")
            self._save_project_state_transition(store, task, "retry", checkpoint_key=checkpoint_key)
            return "retry", []

        if action == "split":
            queue.mark_task_status(task["id"], "blocked")
            split_tasks = [dict(item) for item in decision.get("split_tasks", []) if isinstance(item, dict)]
            existing_ids = {item["id"] for item in queue.list()}
            new_split_tasks = [item for item in split_tasks if item.get("id") not in existing_ids]
            if new_split_tasks:
                queue.enqueue_many(new_split_tasks)
            self._save_project_state_transition(store, task, "split", checkpoint_key=checkpoint_key)
            return "split", new_split_tasks

        if action == "block":
            queue.mark_task_status(task["id"], "blocked")
            self._save_project_state_transition(store, task, "blocked", checkpoint_key=checkpoint_key)
            return "blocked", []

        queue.mark_task_status(task["id"], "failed")
        self._save_project_state_transition(store, task, "failed", checkpoint_key=checkpoint_key)
        return "failed", []

    def _complete_prepared_control_plane_task_from_existing_evidence(
        self,
        *,
        store: Any,
        queue: Any,
        task: Dict[str, Any],
        directive: Dict[str, Any],
        prepared: Dict[str, Any],
        workspace: str | Path,
        session_id: str | None,
    ) -> Dict[str, Any] | None:
        expected_files = [str(path) for path in task.get("expected_files", []) if str(path).strip()]
        if not expected_files:
            return None
        if not self._control_plane_task_can_close_from_existing_evidence(store, task, workspace=workspace):
            return None

        synthetic_execution = {
            "task_result": {
                "task_id": task["id"],
                "completed": True,
                "files_created": [],
                "files_modified": expected_files,
                "validation_ran": [],
                "validation_passed": True,
                "blockers": [],
                "next_recommendation": "Task evidence already existed before launching worker.",
            },
            "execution": {
                "skipped_worker": True,
                "reason": "existing_evidence_validated",
            },
        }
        validation = validate_task_execution(  # type: ignore[misc]
            task,
            synthetic_execution,
            workspace=workspace,
            command_timeout_seconds=max(1, min(300, int(task["timeout_seconds"]))),
        )
        task_result = validation["task_result"]
        if not (task_result["completed"] and task_result["validation_passed"]):
            return None

        queue.mark_task_status(task["id"], "completed")
        if session_id:
            self._append_output(
                session_id,
                "[control-plane] Tarea "
                f"{task['id']} cerrada sin relanzar worker: evidencia existente validada.\n",
            )
            self._emit_control_plane_sync_file_events(session_id, workspace, task_result)
            self._sync_lace_runtime(session_id)

        history_event = store.append_task_history(task_result)
        checkpoint_key = task.get("checkpoint_key") or f"{task['id'].lower()}-completed"
        checkpoint_path = store.save_checkpoint(
            checkpoint_key,
            {
                "task": task,
                "task_result": task_result,
                "validation": validation.get("validation"),
                "directive": {
                    "json_path": prepared.get("directive_json_path"),
                    "markdown_path": prepared.get("directive_markdown_path"),
                    "source_hash": directive.get("traceability", {}).get("source_hash"),
                },
                "execution": synthetic_execution["execution"],
            },
        )
        self._save_project_state_transition(store, task, "completed", checkpoint_key=checkpoint_key)
        return {
            "status": "completed",
            "task": task,
            "directive": directive,
            "directive_json_path": prepared.get("directive_json_path"),
            "directive_markdown_path": prepared.get("directive_markdown_path"),
            "execution": synthetic_execution,
            "validation": validation,
            "task_result": task_result,
            "history_event": history_event,
            "checkpoint": {"checkpoint_key": checkpoint_key, "path": str(checkpoint_path)},
            "recovery": None,
            "skipped_worker": True,
        }

    def _control_plane_task_can_close_from_existing_evidence(
        self,
        store: Any,
        task: Dict[str, Any],
        *,
        workspace: str | Path | None = None,
    ) -> bool:
        task_id = str(task.get("id") or "")
        workspace_path = Path(workspace).resolve() if workspace is not None else None
        expected_files = [str(path) for path in task.get("expected_files", []) if str(path).strip()]
        if self._requires_browser_render_validation(expected_files, workspace_path=workspace_path) and not self._has_browser_render_validation(task):
            return False
        if "-SPLIT-" in task_id:
            return True
        for event in store.load_failures():
            failure = event.get("failure") if isinstance(event, dict) else None
            if isinstance(failure, dict) and failure.get("task_id") == task_id:
                return True
        return False

    def _next_retry_count_for_task(self, store: Any, task_id: str) -> int:
        retry_counts: List[int] = []
        for event in store.load_failures():
            payload = event.get("failure") if isinstance(event, dict) else None
            if not isinstance(payload, dict) or payload.get("task_id") != task_id:
                continue
            retry_count = payload.get("retry_count")
            if isinstance(retry_count, int) and not isinstance(retry_count, bool):
                retry_counts.append(retry_count + 1)
            decision = payload.get("decision")
            if isinstance(decision, dict):
                next_retry_count = decision.get("next_retry_count")
                if isinstance(next_retry_count, int) and not isinstance(next_retry_count, bool):
                    retry_counts.append(next_retry_count)
        return max(retry_counts, default=0)

    def _save_project_state_transition(
        self,
        store: Any,
        task: Dict[str, Any],
        status: str,
        *,
        checkpoint_key: str | None = None,
    ) -> None:
        state = store.load_project_state()
        task_id = task["id"]
        if status in {"retry", "split", "preparing"}:
            state["status"] = "preparing"
        else:
            state["status"] = status
        state["mode"] = task["mode"]
        state["current_task_id"] = task_id if status in {"preparing", "running"} else None
        if status == "completed":
            state["completed_tasks"] = _append_unique(state.get("completed_tasks", []), task_id)
            state["failed_tasks"] = [item for item in state.get("failed_tasks", []) if item != task_id]
            state["blocked_tasks"] = [item for item in state.get("blocked_tasks", []) if item != task_id]
        elif status in {"retry", "preparing"}:
            state["failed_tasks"] = [item for item in state.get("failed_tasks", []) if item != task_id]
            state["blocked_tasks"] = [item for item in state.get("blocked_tasks", []) if item != task_id]
        elif status == "split":
            state["blocked_tasks"] = _append_unique(state.get("blocked_tasks", []), task_id)
            state["failed_tasks"] = [item for item in state.get("failed_tasks", []) if item != task_id]
        elif status == "failed":
            state["failed_tasks"] = _append_unique(state.get("failed_tasks", []), task_id)
        elif status == "blocked":
            state["blocked_tasks"] = _append_unique(state.get("blocked_tasks", []), task_id)
        elif status == "stopped":
            state["failed_tasks"] = [item for item in state.get("failed_tasks", []) if item != task_id]
            state["blocked_tasks"] = [item for item in state.get("blocked_tasks", []) if item != task_id]
        if checkpoint_key:
            state["checkpoints"] = _append_unique(state.get("checkpoints", []), checkpoint_key)
        state["updated_at"] = utc_now()
        store.save_project_state(state)

    def _hydrate_lace_context_from_session(self, session: AgentSession) -> LaceContext | None:
        if session.smoke_mode or session.lace_required_cycles <= 0:
            return None
        if session.lace_policy_path is None or session.lace_log_path is None:
            return None
        if not session.lace_policy_path.exists() or not session.lace_log_path.exists():
            return None
        try:
            policy_text = session.lace_policy_path.read_text(encoding="utf-8")
        except OSError:
            return None
        return LaceContext(
            policy_text=policy_text,
            directive=build_lace_compact_directive(
                session.lace_policy_path,
                session.lace_log_path,
                session.lace_required_cycles,
            ),
            policy_path=session.lace_policy_path,
            log_path=session.lace_log_path,
            required_cycles=session.lace_required_cycles,
        )

    def _describe_retry_checkpoint(self, session: AgentSession) -> str:
        parts: List[str] = []

        current_cycle = next((state for state in session.lace_cycle_states if state.get("isCurrent")), None)
        if current_cycle is None and session.lace_cycle_states:
            current_cycle = session.lace_cycle_states[-1]
        if current_cycle is not None:
            cycle_number = int(current_cycle.get("cycle") or 0)
            cycle_stage = str(current_cycle.get("stage") or "pending")
            cycle_focus = str(current_cycle.get("focus") or "").strip()
            cycle_description = str(current_cycle.get("description") or "").strip()
            cycle_label = f"ciclo {cycle_number:02d} en {cycle_stage}"
            if cycle_focus:
                cycle_label += f" sobre {cycle_focus}"
            if cycle_description:
                cycle_label += f" ({cycle_description})"
            parts.append(cycle_label)

        recent_events = collect_recent_visual_payloads(session.project_dir, limit=24)
        for payload in recent_events:
            op = str(payload.get("op") or "").strip().lower()
            candidate = (
                payload.get("relativePath")
                or payload.get("nodePath")
                or payload.get("toPath")
                or payload.get("fromPath")
                or ""
            )
            normalized_candidate = normalize_project_relative_path(candidate)
            if not normalized_candidate:
                continue
            description = str(payload.get("description") or payload.get("message") or "").strip()
            event_label = f"{op} en {normalized_candidate}"
            if description:
                event_label += f" ({description})"
            parts.append(event_label)
            break

        resume_context = inspect_project_resume_context(session.project_dir)
        pending_declared = list(resume_context.get("pendingDeclaredPaths") or [])
        if pending_declared:
            parts.append(f"archivo pendiente declarado {pending_declared[0]}")
        material_files = list(resume_context.get("materialFiles") or [])
        if not pending_declared and material_files:
            parts.append(f"ultimo archivo material visible {material_files[-1]}")

        if not parts:
            return "retoma desde la ultima evidencia real escrita en disco y en LACE_LOG.md"
        return "; ".join(parts[:3])

    def _build_timeout_retry_prompt(self, session: AgentSession, checkpoint: str) -> str:
        lace_context = self._hydrate_lace_context_from_session(session)
        base_prompt = self._build_codex_prompt(
            requirement=session.requirement,
            project_name=session.project_name,
            project_slug=session.project_slug,
            project_dir=session.project_dir,
            habla_prompt=session.habla_prompt,
            habla_available=session.habla_available,
            habla_state=session.habla_state,
            lace_context=lace_context,
            smoke_mode=session.smoke_mode,
            continuing_existing_project=True,
        )
        retry_intro = (
            "REINTENTO AUTOMATICO POR TIMEOUT DEL RUNTIME\n"
            f"- Reintento {session.retry_count}/{session.retry_limit} tras `session_idle_timeout`.\n"
            f"- Ultimo checkpoint real detectado: {checkpoint}\n"
            "- No reinicies analisis ni reconstruyas el proyecto desde cero.\n"
            "- Retoma exactamente desde ese punto funcional o desde la evidencia mas cercana si el punto ya quedo materializado.\n"
            "- En tus proximas 3 acciones como maximo debes producir salida real de terminal o del bridge sobre ese punto.\n"
            "- Si el archivo o ciclo ya esta resuelto, avanza al siguiente paso inmediato sin repetir lo ya hecho.\n"
            "- Si vuelves a atorarte, cambia estrategia pero sigue en la misma tarea especifica.\n"
        )
        return f"{base_prompt}\n\n{retry_intro}\n"

    def _prepare_retry_attempt(self, session_id: str) -> Dict[str, Any] | None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return None
            checkpoint = session.last_retry_checkpoint or self._describe_retry_checkpoint(session)
            session.last_retry_checkpoint = checkpoint
            session.prompt = self._build_timeout_retry_prompt(session, checkpoint)
            session.command = self._build_codex_command(session.project_dir, session.prompt)
            session.retry_pending = False
            session.status = "queued"
            session.returncode = None
            session.pid = None
            session.error_code = None
            session.error_message = None
            session.failure_event_emitted = False
            session.started_at = None
            session.ended_at = None
            session.first_output_at = None
            session.first_visual_event_at = None
            session.last_visual_event_at = None
            session.last_heartbeat_at = None
            session.start_monotonic = None
            session.last_agent_activity_monotonic = None
            session.first_visual_monotonic = None
            session.last_visual_monotonic = None
            session.last_heartbeat_monotonic = None
            session.process = None
            session.master_fd = None
            session.updated_at = utc_now()
            session.progress_percent = max(10, min(int(session.progress_percent or 0), 92))
            session.progress_label = (
                f"Reintentando tras timeout desde el ultimo checkpoint ({session.retry_count}/{session.retry_limit})"
            )
            snapshot = session.to_dict()
            session_ref = session
        self._append_output(
            session_id,
            (
                f"[agent-retry] Reintento {session_ref.retry_count}/{session_ref.retry_limit} "
                f"despues de timeout. Checkpoint: {session_ref.last_retry_checkpoint}\n"
            ),
        )
        self._emit_visual_runtime_event(
            session_ref,
            op="phase",
            status="running",
            phase="retry",
            message=(
                f"Timeout detectado. Reintentando desde el ultimo checkpoint "
                f"({session_ref.retry_count}/{session_ref.retry_limit})."
            ),
        )
        return snapshot

    def _schedule_timeout_retry(self, session_id: str, message: str) -> bool:
        snapshot = None
        session_ref = None
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return False
            if session.stop_requested or session.retry_pending:
                return False
            if session.retry_count >= session.retry_limit:
                return False
            session.retry_count += 1
            session.retry_pending = True
            session.last_retry_reason = "session_idle_timeout"
            session.last_retry_checkpoint = self._describe_retry_checkpoint(session)
            session.error_code = "session_idle_timeout"
            session.error_message = message
            session.updated_at = utc_now()
            session.progress_label = (
                f"Timeout detectado. Reintentando desde el ultimo checkpoint "
                f"({session.retry_count}/{session.retry_limit})"
            )
            snapshot = session.to_dict()
            session_ref = session
        if snapshot is not None:
            self.session_emitter(snapshot)
        self._append_output(
            session_id,
            (
                f"[agent-retry] Timeout detectado. Se programo reintento "
                f"{snapshot['retryCount']}/{snapshot['retryLimit']}.\n"
            ) if snapshot is not None else "[agent-retry] Timeout detectado. Se programo reintento.\n",
        )
        if session_ref is not None:
            self._emit_visual_runtime_event(
                session_ref,
                op="phase",
                status="running",
                phase="retry",
                message=(
                    f"Timeout detectado. Reintento programado "
                    f"({session_ref.retry_count}/{session_ref.retry_limit})."
                ),
            )
        return True

    def _persist_control_plane_manual_stop(self, session_snapshot: AgentSession) -> None:
        if not session_snapshot.control_plane_enabled:
            return
        if StateStore is None or TaskQueue is None:
            return
        runtime_dir = Path(session_snapshot.control_plane_runtime_dir or session_snapshot.project_dir / "runtime")
        store = StateStore(runtime_dir)
        queue = TaskQueue(store, bootstrap_empty=True)
        stopped_task_ids: List[str] = []
        for task in queue.list():
            task_id = str(task.get("id") or "")
            if not task_id:
                continue
            if task_id == session_snapshot.active_task_id or str(task.get("status") or "").lower() == "running":
                try:
                    queue.mark_task_status(task_id, "blocked")
                    stopped_task_ids = _append_unique(stopped_task_ids, task_id)
                except Exception:
                    continue

        state = store.load_project_state()
        previous_status = state.get("status")
        previous_current_task_id = state.get("current_task_id")
        checkpoint_key = f"manual-stop-{session_snapshot.session_id}"
        checkpoint_path = store.save_checkpoint(
            checkpoint_key,
            {
                "reason": "manual_stop",
                "session_id": session_snapshot.session_id,
                "project_slug": session_snapshot.project_slug,
                "active_task_id": session_snapshot.active_task_id,
                "blocked_task_ids": stopped_task_ids,
                "previous_status": previous_status,
                "previous_current_task_id": previous_current_task_id,
            },
        )
        blocked_tasks = [str(item) for item in state.get("blocked_tasks", []) if str(item)]
        for task_id in stopped_task_ids:
            blocked_tasks = _append_unique(blocked_tasks, task_id)
        state["status"] = "stopped"
        state["current_task_id"] = None
        state["blocked_tasks"] = blocked_tasks
        state["checkpoints"] = _append_unique(state.get("checkpoints", []), checkpoint_key)
        state["updated_at"] = utc_now()
        store.save_project_state(state)
        store.append_failure(
            {
                "task_id": session_snapshot.active_task_id or (stopped_task_ids[-1] if stopped_task_ids else "manual_stop"),
                "failure_type": "manual_stop",
                "session_id": session_snapshot.session_id,
                "blocked_task_ids": stopped_task_ids,
                "checkpoint_key": checkpoint_key,
                "checkpoint_path": str(checkpoint_path),
            }
        )

    def stop_session(self, session_id: str) -> Dict[str, Any] | None:
        session_snapshot: AgentSession | None = None
        process = None
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return None
            process = session.process
            now_value = utc_now()
            session.stop_requested = True
            session.updated_at = now_value
            if process is None or process.poll() is not None:
                session.status = "stopped"
                session.returncode = process.returncode if process is not None else -15
                session.ended_at = now_value
                session.error_code = session.error_code or "manual_stop_no_worker"
                session.error_message = session.error_message or "Sesion detenida; no habia worker vivo asociado."
                session.progress_label = "Sesion detenida por el usuario."
                session.progress_percent = max(session.progress_percent, 94)
                session_snapshot = session

        if process is not None and process.poll() is None:
            process.terminate()
            self._append_output(session_id, "\n[agent] Sesion detenida por el usuario.\n")
            with self.lock:
                live_session = self.sessions.get(session_id)
                if live_session is not None:
                    now_value = utc_now()
                    live_session.status = "stopped"
                    live_session.returncode = -15
                    live_session.ended_at = now_value
                    live_session.updated_at = now_value
                    live_session.error_code = live_session.error_code or "manual_stop"
                    live_session.error_message = live_session.error_message or "Sesion detenida por el usuario."
                    live_session.progress_label = "Sesion detenida por el usuario."
                    live_session.progress_percent = max(live_session.progress_percent, 94)
                    session_snapshot = live_session

        if session_snapshot is not None and session_snapshot.control_plane_enabled:
            try:
                self._persist_control_plane_manual_stop(session_snapshot)
            except Exception:
                pass
            self.session_emitter(session_snapshot.to_dict())
            self._emit_visual_runtime_event(
                session_snapshot,
                op="session_stopped",
                status="stopped",
                phase="stop",
                error_code=session_snapshot.error_code,
                message=session_snapshot.error_message or "Sesion detenida por el usuario.",
            )
        return self.get_session(session_id)

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.app_root))
        except ValueError:
            return str(path)

    def _load_project_metadata(self, project_dir: Path) -> Dict[str, Any]:
        metadata_path = project_dir / ".agent-project.json"
        if not metadata_path.exists():
            return {}
        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _resolve_habla_payload(self, requirement: str) -> tuple[str, bool, Dict[str, Any]]:
        if self.prompt_converter is None:
            return requirement, False, {}

        try:
            payload = self.prompt_converter(requirement)
        except Exception as error:  # pragma: no cover - defensive fallback for external runtimes
            return requirement, False, {"error": f"No fue posible ejecutar HABLA antes de lanzar Codex: {error}"}

        if isinstance(payload, dict):
            prompt = str(
                payload.get("prompt")
                or payload.get("convertedPrompt")
                or payload.get("protocolText")
                or requirement
            )
            state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
            if is_code_generation_requirement(requirement):
                normalized_state = dict(state)
                debug_lines = [str(item).strip() for item in normalized_state.get("debug") or [] if str(item).strip()]
                if normalized_state.get("blocked") or normalized_state.get("toolRequired") == "calculator":
                    debug_lines.append("OVERRIDE => coding_task_bypass_habla_block")
                normalized_state.update(
                    {
                        "knowledgeType": "PROYECTO_CODIGO",
                        "toolRequired": "filesystem",
                        "strategy": "construir_y_validar",
                        "safeToAnswer": True,
                        "blocked": False,
                        "blockReason": "",
                        "directive": (
                            "Esta sesion es de implementacion de codigo. Construye el proyecto solicitado en disco, "
                            "valida con archivos y pruebas reales, y no trates la tarea como una pregunta teorica bloqueada."
                        ),
                        "debug": debug_lines,
                    }
                )
                return build_habla_code_execution_prompt(requirement), True, normalized_state
            return prompt, bool(payload.get("available")), dict(state)

        return str(payload or requirement), True, {}

    def _write_habla_preflight(
        self,
        *,
        project_dir: Path,
        requirement: str,
        habla_prompt: str,
        habla_available: bool,
        habla_state: Dict[str, Any],
        lace_context: LaceContext | None,
    ) -> Path:
        preflight_path = project_dir / "docs" / "habla-session.md"
        preflight_path.parent.mkdir(parents=True, exist_ok=True)
        preflight_path.write_text(
            build_habla_preflight_markdown(
                requirement=requirement,
                habla_prompt=habla_prompt,
                habla_available=habla_available,
                habla_state=habla_state,
                lace_context=lace_context,
            ),
            encoding="utf-8",
        )
        return preflight_path

    def _emit_preflight_visuals(self, session: AgentSession) -> None:
        summary = session.habla_state
        phase_message = (
            f"HABLA preflight listo. Tipo={summary.get('knowledgeType') or 'desconocido'}; "
            f"estrategia={summary.get('strategy') or 'desconocida'}; "
            f"LACE={session.lace_required_cycles or 0} ciclo(s)."
        )
        base_payload = {
            "sessionId": session.session_id,
            "projectSlug": session.project_slug,
            "projectDir": str(session.project_dir),
        }
        self._dispatch_runtime_payload(
            session.session_id,
            {
                **base_payload,
                "op": "phase",
                "phase": "preflight",
                "message": phase_message,
            },
            count_visual=False,
            track_activity=False,
        )

        preflight_relative = (
            session.habla_preflight_path.relative_to(session.project_dir).as_posix()
            if session.habla_preflight_path is not None
            else None
        )
        if preflight_relative:
            self._dispatch_runtime_payload(
                session.session_id,
                {
                    **base_payload,
                    "op": "upsert_node",
                    "relativePath": preflight_relative,
                    "layer": "docs",
                    "layerLabel": "HABLA",
                    "codeLanguage": "markdown",
                    "status": "generated",
                    "description": "Preflight procedimental de HABLA antes de lanzar Codex.",
                    "position": {"x": 220.0, "y": 160.0},
                    "message": "Aparecio el nodo de preflight HABLA en el mapa.",
                },
                count_visual=True,
                track_activity=False,
            )
            self._dispatch_runtime_payload(
                session.session_id,
                {
                    **base_payload,
                    "op": "sync_file",
                    "relativePath": preflight_relative,
                    "sourcePath": str(session.habla_preflight_path),
                    "layer": "docs",
                    "layerLabel": "HABLA",
                    "codeLanguage": "markdown",
                    "status": "generated",
                    "description": "Resumen del motor HABLA, prompt procedural y directiva enviada a Codex.",
                    "position": {"x": 220.0, "y": 160.0},
                    "message": "Se sincronizo el resumen HABLA al inspector.",
                },
                count_visual=True,
                track_activity=False,
            )

        if session.lace_log_path is not None and session.lace_log_path.exists():
            lace_relative = session.lace_log_path.relative_to(session.project_dir).as_posix()
            self._dispatch_runtime_payload(
                session.session_id,
                {
                    **base_payload,
                    "op": "upsert_node",
                    "relativePath": lace_relative,
                    "layer": "docs",
                    "layerLabel": "LACE",
                    "codeLanguage": "markdown",
                    "status": "generated",
                    "description": "Bitacora viva de ciclos LACE y puerta de cierre.",
                    "position": {"x": 560.0, "y": 160.0},
                    "message": "Aparecio el nodo de control LACE en el mapa.",
                },
                count_visual=True,
                track_activity=False,
            )
            self._dispatch_runtime_payload(
                session.session_id,
                {
                    **base_payload,
                    "op": "sync_file",
                    "relativePath": lace_relative,
                    "sourcePath": str(session.lace_log_path),
                    "layer": "docs",
                    "layerLabel": "LACE",
                    "codeLanguage": "markdown",
                    "status": "generated",
                    "description": "Registro inicial de los ciclos adaptativos maximos de la sesion.",
                    "position": {"x": 560.0, "y": 160.0},
                    "message": "Se sincronizo LACE_LOG.md al inspector.",
                },
                count_visual=True,
                track_activity=False,
            )
            if preflight_relative:
                self._dispatch_runtime_payload(
                    session.session_id,
                    {
                        **base_payload,
                        "op": "upsert_edge",
                        "fromPath": preflight_relative,
                        "toPath": lace_relative,
                        "edgeType": "reference",
                        "label": "controla ciclos",
                        "message": "HABLA y LACE quedaron conectados en el mapa previo a la ejecucion.",
                    },
                    count_visual=True,
                    track_activity=False,
                )
        self._initialize_lace_cycle_visuals(session)

    def _initialize_lace_cycle_visuals(self, session: AgentSession) -> None:
        if session.smoke_mode or not session.lace_required_cycles:
            return
        self._sync_lace_runtime(session.session_id)

    def _sync_lace_runtime(self, session_id: str) -> None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or session.smoke_mode or not session.lace_required_cycles or session.lace_log_path is None:
                return
            log_path = session.lace_log_path
            current_digest = session.lace_log_digest
            start_monotonic = session.start_monotonic
            first_output_at = session.first_output_at
            first_visual_event_at = session.first_visual_event_at

        if (
            start_monotonic is not None
            and first_output_at is None
            and first_visual_event_at is None
            and (time.monotonic() - start_monotonic) >= FIRST_AGENT_SIGNAL_TIMEOUT_SECONDS
        ):
            self._fail_session(
                session_id,
                error_code="agent_start_timeout",
                message="La sesion no produjo salida de terminal ni eventos reales del bridge en el tiempo esperado.",
                returncode=123,
            )
            return
        if not log_path.exists():
            return

        try:
            text = log_path.read_text(encoding="utf-8")
        except OSError:
            return
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        if digest == current_digest:
            return

        sections_by_cycle = extract_lace_cycle_sections(text)
        cycle_numbers = sorted(
            cycle_number
            for cycle_number, cycle_sections in sections_by_cycle.items()
            if 1 <= cycle_number <= max(1, session.lace_required_cycles) and cycle_sections
        )
        cycle_states = []
        updated_signatures: Dict[int, str] = {}
        changed_cycle = None
        previous_relative = None
        lace_relative = log_path.relative_to(session.project_dir).as_posix()
        active_cycle_number = None
        running_now = str(session.status or "").lower() in {"queued", "preparing", "starting", "running"}
        for cycle_number in cycle_numbers:
            cycle_sections = sections_by_cycle.get(cycle_number, {})
            cycle_summary = summarize_lace_cycle_visual(cycle_number, cycle_sections)
            if running_now and not cycle_summary["valid"]:
                active_cycle_number = cycle_number
            cycle_relative = lace_cycle_visual_relative_path(cycle_number)
            cycle_path = session.project_dir / cycle_relative
            cycle_path.parent.mkdir(parents=True, exist_ok=True)
            cycle_markdown = build_lace_cycle_visual_markdown(cycle_number, cycle_summary, cycle_sections)
            signature = hashlib.sha1(cycle_markdown.encode("utf-8")).hexdigest()
            with self.lock:
                live_session = self.sessions.get(session_id)
                previous_signature = live_session.lace_cycle_signatures.get(cycle_number) if live_session is not None else None
            cycle_state = {
                "cycle": cycle_number,
                "path": cycle_relative,
                "stage": cycle_summary["stage"],
                "valid": cycle_summary["valid"],
                "focus": cycle_summary["focus"],
                "description": cycle_summary["description"],
                "isCurrent": False,
            }
            cycle_states.append(cycle_state)
            updated_signatures[cycle_number] = signature
            if signature == previous_signature:
                previous_relative = cycle_relative
                continue
            cycle_path.write_text(cycle_markdown, encoding="utf-8")
            changed_cycle = cycle_number
            position = {
                "x": 240.0 + ((cycle_number - 1) % 5) * 320.0,
                "y": 420.0 + ((cycle_number - 1) // 5) * 220.0,
            }
            self._dispatch_runtime_payload(
                session_id,
                {
                    "op": "phase",
                    "phase": f"lace-cycle-{cycle_number:02d}-{cycle_summary['stage']}",
                    "message": cycle_summary["description"],
                },
                count_visual=False,
                track_activity=False,
            )
            self._dispatch_runtime_payload(
                session_id,
                {
                    "op": "upsert_node",
                    "relativePath": cycle_relative,
                    "layer": "docs",
                    "layerLabel": "LACE Cycle",
                    "codeLanguage": "markdown",
                    "status": cycle_summary["stage"],
                    "color": lace_cycle_stage_color(cycle_summary["stage"]),
                    "description": cycle_summary["description"],
                    "position": position,
                    "message": f"Ciclo {cycle_number:02d} pasó a {cycle_summary['stage']}.",
                },
                count_visual=True,
                track_activity=False,
            )
            self._dispatch_runtime_payload(
                session_id,
                {
                    "op": "sync_file",
                    "relativePath": cycle_relative,
                    "sourcePath": str(cycle_path),
                    "layer": "docs",
                    "layerLabel": "LACE Cycle",
                    "codeLanguage": "markdown",
                    "status": cycle_summary["stage"],
                    "color": lace_cycle_stage_color(cycle_summary["stage"]),
                    "description": cycle_summary["description"],
                    "position": position,
                    "message": f"Se sincronizó el ciclo {cycle_number:02d} desde LACE_LOG.md.",
                },
                count_visual=True,
                track_activity=False,
            )
            self._dispatch_runtime_payload(
                session_id,
                {
                    "op": "upsert_edge",
                    "fromPath": lace_relative,
                    "toPath": cycle_relative,
                    "edgeType": "reference",
                    "label": f"ciclo {cycle_number:02d}",
                    "message": f"LACE_LOG.md quedó conectado con el ciclo {cycle_number:02d}.",
                },
                count_visual=True,
                track_activity=False,
            )
            if previous_relative:
                self._dispatch_runtime_payload(
                    session_id,
                    {
                        "op": "upsert_edge",
                        "fromPath": previous_relative,
                        "toPath": cycle_relative,
                        "edgeType": "uses",
                        "label": "siguiente ciclo",
                        "message": f"Se encadenó el ciclo {cycle_number - 1:02d} con el {cycle_number:02d}.",
                    },
                    count_visual=True,
                    track_activity=False,
                )
            with self.lock:
                live_session = self.sessions.get(session_id)
                if live_session is not None:
                    live_session.lace_cycle_signatures[cycle_number] = signature
            previous_relative = cycle_relative

        if active_cycle_number is not None:
            for cycle_state in cycle_states:
                cycle_state["isCurrent"] = cycle_state.get("cycle") == active_cycle_number

        with self.lock:
            live_session = self.sessions.get(session_id)
            if live_session is not None:
                live_session.lace_cycle_states = cycle_states
                live_session.lace_cycle_signatures = updated_signatures
                live_session.lace_log_digest = digest
                live_session.updated_at = utc_now()
        if changed_cycle is not None:
            completed_cycles = sum(1 for cycle in cycle_states if cycle.get("valid"))
            self._update_progress(
                session_id,
                min(99, 30 + completed_cycles * max(1, 55 // max(1, session.lace_required_cycles))),
                f"LACE en vivo: {completed_cycles}/{session.lace_required_cycles} ciclos validados",
                force=True,
            )
        snapshot = self.get_session(session_id)
        if snapshot is not None:
            self.session_emitter(snapshot)

    def _mark_lace_cycles_after_closure(self, session: AgentSession, *, failed: bool) -> None:
        if session.lace_log_path is None or not session.lace_log_path.exists() or not session.lace_required_cycles:
            return
        try:
            text = session.lace_log_path.read_text(encoding="utf-8")
        except OSError:
            return

        cycle_reports = inspect_lace_cycle_reports(text, session.lace_required_cycles)
        if not cycle_reports:
            return

        existing_by_cycle = {int(state.get("cycle") or 0): dict(state) for state in session.lace_cycle_states}
        updated_states = []
        for report in cycle_reports:
            cycle_number = int(report["cycle"])
            current_state = existing_by_cycle.get(
                cycle_number,
                {
                    "cycle": cycle_number,
                    "path": lace_cycle_visual_relative_path(cycle_number),
                    "focus": lace_focus_for_cycle(cycle_number),
                },
            )
            if report["valid"]:
                stage = "validated"
                description = current_state.get("description") or f"Ciclo {cycle_number:02d} validado por LACE."
            elif failed and (report["hasProblems"] or report["hasImprovements"] or report["hasCompleted"]):
                stage = "failed"
                missing = ", ".join(report["missingParts"]) or "evidencia obligatoria"
                description = f"Ciclo {cycle_number:02d} falló el cierre LACE: falta {missing}."
            else:
                stage = current_state.get("stage") or "pending"
                description = current_state.get("description") or f"Ciclo {cycle_number:02d} en espera."
            updated_states.append(
                {
                    **current_state,
                    "cycle": cycle_number,
                    "path": current_state.get("path") or lace_cycle_visual_relative_path(cycle_number),
                    "focus": current_state.get("focus") or lace_focus_for_cycle(cycle_number),
                    "stage": stage,
                    "valid": bool(report["valid"]),
                    "description": description,
                    "isCurrent": False,
                    "missingParts": list(report["missingParts"]),
                }
            )

        session.lace_cycle_states = updated_states
        for cycle_state in updated_states:
            cycle_relative = str(cycle_state.get("path") or lace_cycle_visual_relative_path(int(cycle_state["cycle"])))
            cycle_number = int(cycle_state["cycle"])
            stage = str(cycle_state.get("stage") or "pending")
            position = {
                "x": 240.0 + ((cycle_number - 1) % 5) * 320.0,
                "y": 420.0 + ((cycle_number - 1) // 5) * 220.0,
            }
            self._dispatch_runtime_payload(
                session.session_id,
                {
                    "op": "upsert_node",
                    "relativePath": cycle_relative,
                    "layer": "docs",
                    "layerLabel": "LACE Cycle",
                    "codeLanguage": "markdown",
                    "status": stage,
                    "color": lace_cycle_stage_color(stage),
                    "description": cycle_state.get("description"),
                    "position": position,
                    "message": f"Ciclo {cycle_number:02d} quedó en {stage}.",
                },
                count_visual=False,
                track_activity=False,
            )

    def _build_codex_prompt(
        self,
        *,
        requirement: str,
        project_name: str,
        project_slug: str,
        project_dir: Path,
        habla_prompt: str,
        habla_available: bool,
        habla_state: Dict[str, Any],
        lace_context: LaceContext | None,
        smoke_mode: bool,
        continuing_existing_project: bool,
    ) -> str:
        graph_summary = summarize_graph(scope_graph_to_project(self.graph_provider(), project_slug))
        bridge_command = f"{self.bridge_python} {self.bridge_script}"
        lace_block = ""
        lace_runtime_block = ""
        habla_block = ""
        smoke_block = ""
        resume_block = ""
        if smoke_mode:
            smoke_block = (
                "Modo de sesion: smoke tecnico de verificacion.\n"
                "- Mantén el alcance minimo y directo al objetivo pedido.\n"
                "- Ignora cualquier `LACE.md` o `LACE_LOG.md` que ya exista dentro del proyecto para esta sesion.\n"
                "- No abras ciclos LACE ni generes cierres de 10 ciclos.\n"
                "- Valida con evidencia tecnica puntual y termina al completar el smoke solicitado.\n\n"
            )
        if lace_context is not None:
            lace_block = (
                "Política LACE obligatoria para esta sesión:\n"
                f"{lace_context.directive}\n\n"
                f"Archivo LACE local del proyecto: {lace_context.policy_path}\n"
                f"Archivo de evidencia de ciclos: {lace_context.log_path}\n"
                "Debes leer `LACE.md` completo antes de actuar y mantener `LACE_LOG.md` actualizado durante toda la sesión.\n\n"
                "Contenido operativo de LACE.md:\n"
                f"{lace_context.policy_text}\n\n"
            )
            lace_runtime_block = (
                "Instrumentación LACE obligatoria:\n"
                "- Los ciclos LACE reservados del proyecto deben mantenerse alineados con la evidencia real.\n"
                "- En cada ciclo debes actualizar `LACE_LOG.md` con PROBLEMAS, MEJORA y COMPLETADO usando evidencia real.\n"
                "- Usa literalmente los encabezados `[CICLO-n PROBLEMAS]`, `[CICLO-n MEJORA]` y `[CICLO-n COMPLETADO]`; no mezcles la mejora dentro de otra sección.\n"
                "- Cada vez que cierres una parte del ciclo, sincroniza `LACE_LOG.md` al inspector.\n"
                "- Antes de pasar al siguiente ciclo, verifica si el ciclo actual quedó objetivamente mejor y documentado.\n\n"
            )
        resume_context = inspect_project_resume_context(project_dir)
        if continuing_existing_project or resume_context.get("shouldResume"):
            material_files = list(resume_context.get("materialFiles") or [])
            pending_declared = list(resume_context.get("pendingDeclaredPaths") or [])
            completed_cycles = int(resume_context.get("completedCycles") or 0)
            resume_lines = [
                "Contexto de continuidad del proyecto:",
                "- Esta carpeta ya tuvo trabajo previo. Continuar significa retomar evidencia existente, no reiniciar el proyecto desde cero.",
                f"- Ciclos LACE completados detectados: {completed_cycles}.",
            ]
            if resume_context.get("hasHablaInitial"):
                resume_lines.append("- `LACE_LOG.md` ya contiene `HABLA INICIAL`.")
            if resume_context.get("hasPreBase"):
                resume_lines.append("- `LACE_LOG.md` ya contiene `[PRE-BASE]`.")
            if resume_context.get("hasBase"):
                resume_lines.append("- `LACE_LOG.md` ya contiene `[BASE]`.")
            if material_files:
                resume_lines.append("- Archivos reales ya presentes: " + ", ".join(material_files[:10]))
            if pending_declared:
                resume_lines.append("- Archivos ya declarados en el mapa pero no materializados todavía: " + ", ".join(pending_declared[:10]))
            resume_lines.extend(
                [
                    "",
                    "Reglas estrictas de continuación:",
                    "- Usa como fuente de verdad la evidencia mas reciente en disco y las marcas ya escritas en `LACE_LOG.md`.",
                    "- No vuelvas a escribir `[COMPRENSIÓN DEL PROYECTO]`, `HABLA INICIAL` o `[PRE-BASE]` si ya existen.",
                    "- No vuelvas a reconstruir el mapa completo si los nodos principales ya fueron declarados.",
                    "- Retoma desde el punto material mas avanzado del proyecto.",
                    "- Si aun no hay archivos reales del producto, tu siguiente objetivo obligatorio es escribir y sincronizar inmediatamente uno de los archivos reales pendientes.",
                    "- Despues de 3 acciones visuales como maximo, debes crear o modificar un archivo real del proyecto y sincronizarlo.",
                    "- No consideres `LACE_LOG.md`, `LACE.md`, `docs/habla-session.md` ni archivos en `.vista/` como avance de producto.",
                    "- Si detectas varias sesiones previas sobre la misma carpeta, no reinicies metricas ni analisis: continua desde la evidencia mas reciente.",
                    "",
                ]
            )
            resume_block = "\n".join(resume_lines)
        if habla_prompt or habla_state:
            confidence = habla_state.get("confidence") if isinstance(habla_state.get("confidence"), dict) else {}
            debug_lines = [str(item).strip() for item in habla_state.get("debug") or [] if str(item).strip()]
            sources = [item for item in habla_state.get("sources") or [] if isinstance(item, dict)]
            habla_summary_lines = [
                "Preflight real de HABLA antes de lanzar Codex:",
                f"- motor disponible: {'si' if habla_available else 'no'}",
                f"- knowledgeType: {habla_state.get('knowledgeType') or 'desconocido'}",
                f"- toolRequired: {habla_state.get('toolRequired') or 'desconocido'}",
                f"- strategy: {habla_state.get('strategy') or 'desconocida'}",
                f"- safeToAnswer: {habla_state.get('safeToAnswer') if 'safeToAnswer' in habla_state else 'desconocido'}",
                f"- blocked: {habla_state.get('blocked') if 'blocked' in habla_state else 'desconocido'}",
            ]
            if habla_state.get("blockReason"):
                habla_summary_lines.append(f"- blockReason: {habla_state['blockReason']}")
            if confidence:
                habla_summary_lines.append(
                    "- confidence: "
                    f"dato={confidence.get('dato', 0)}, fecha={confidence.get('fecha', 0)}, "
                    f"fuente={confidence.get('fuente', 0)}, calculo={confidence.get('calculo', 0)}, "
                    f"inferencia={confidence.get('inferencia', 0)}, global={confidence.get('global', 0)}"
                )
            if habla_state.get("triangulatedText"):
                habla_summary_lines.append(f"- triangulation: {shorten_text(habla_state.get('triangulatedText'))}")
            if sources:
                habla_summary_lines.append("- evidencia:")
                for source in sources[:4]:
                    habla_summary_lines.append(
                        f"  - {source.get('source') or 'fuente'}: {shorten_text(source.get('text') or '')}"
                    )
            if debug_lines:
                habla_summary_lines.append("- traza:")
                for item in debug_lines[:HABLA_DEBUG_LINES_LIMIT]:
                    habla_summary_lines.append(f"  - {item}")
            if habla_state.get("directive"):
                habla_summary_lines.extend(
                    [
                        "",
                        "Directiva HABLA ya razonada para guiar a Codex:",
                        str(habla_state["directive"]).strip(),
                    ]
                )
            habla_summary_lines.extend(
                [
                    "",
                    "Prompt procedural HABLA BASIC usado como base:",
                    str(habla_prompt or "").strip(),
                    "",
                ]
            )
            habla_block = "\n".join(habla_summary_lines)
        return (
            "Eres Codex CLI ejecutandote dentro del editor visual de arquitectura y flujo.\n\n"
            f"Proyecto activo: {project_name}\n"
            f"Slug del proyecto: {project_slug}\n"
            f"Directorio de trabajo: {project_dir}\n"
            f"Workspace de proyectos: {self.projects_root}\n\n"
            "Objetivo del usuario:\n"
            f"{requirement}\n\n"
            f"{smoke_block}"
            f"{resume_block}"
            "Contexto del ecosistema visible en el editor:\n"
            f"{graph_summary}\n\n"
            f"{habla_block}"
            f"{lace_block}"
            "Reglas de trabajo:\n"
            "- Trabaja primero dentro de este proyecto.\n"
            "- Usa y respeta la estructura src/, backend/, frontend/, shared/, tests/, docs/, algorithms/ y assets/.\n"
            "- Si necesitas otro subprograma, crealo dentro de este proyecto y conectalo con imports, API o sockets reales.\n"
            "- Mantiene los archivos ordenados por dominio y responsabilidad.\n"
            "- Deja huellas arquitectonicas claras para que el mapa conceptual y los diagramas puedan detectar relaciones.\n"
            "- Mientras trabajas, actualiza el editor visual en tiempo real usando el bridge CLI del proyecto.\n"
            "- Si produces una aplicacion ejecutable, deja un entrypoint detectable por Runtime Sandbox: package.json con script dev/start, frontend/package.json con script dev/start, app.py/server.py/main.py Flask/FastAPI, o frontend/index.html para estatico.\n"
            "- Si la app usa servidor web, debe poder escuchar en 127.0.0.1 usando PORT del entorno o el puerto indicado por la sandbox.\n"
            "- Imprime en la terminal los pasos importantes, los archivos que creas y las decisiones tomadas.\n"
            "- Al terminar, resume archivos creados o modificados y el siguiente paso recomendado.\n\n"
            "Bridge visual obligatorio:\n"
            f"- Comando base: `{bridge_command}`\n"
            "- Secuencia esperada:\n"
            "  1. Primero declara la arquitectura visible del proyecto con nodos y conexiones.\n"
            "  2. Luego enfoca cada archivo importante y construye su diagrama de flujo interno.\n"
            "  3. Despues escribe el archivo real en disco.\n"
            "  4. Inmediatamente sincroniza el archivo al inspector de codigo del editor.\n"
            "- Ejemplos de uso:\n"
            f"  - `{bridge_command} phase --label plan --message \"Disenando el ecosistema inicial\"`\n"
            f"  - `{bridge_command} upsert-node --path frontend/index.html --layer frontend --layer-label Frontend --language html --description \"Pantalla principal\" --x 220 --y 180`\n"
            f"  - `{bridge_command} connect-nodes --from-path frontend/game.js --to-path backend/app.py --type socket --label \"envia score\"`\n"
            f"  - `{bridge_command} focus-node --path frontend/game.js`\n"
            f"  - `{bridge_command} upsert-step --node-path frontend/game.js --step-id start --type start --label Inicio --x 300 --y 70`\n"
            f"  - `{bridge_command} upsert-step --node-path frontend/game.js --step-id loop --type process --label \"Loop principal\" --x 300 --y 220`\n"
            f"  - `{bridge_command} connect-steps --node-path frontend/game.js --from-step start --to-step loop`\n"
            f"  - `{bridge_command} sync-file --path frontend/game.js --language javascript --description \"Loop del juego\"`\n"
            "- No esperes al final: el usuario debe ver en vivo como aparecen los bloques, las flechas, el flujo y el codigo.\n\n"
            f"{lace_runtime_block}"
            "Protocolo HABLA para guiar el razonamiento:\n"
            f"{habla_prompt}\n"
        )

    def _emit_session(self, session: AgentSession) -> None:
        self.session_emitter(session.to_dict())

    def _update_progress(self, session_id: str, percent: int, label: str, *, force: bool = False) -> Dict[str, Any] | None:
        clamped_percent = max(0, min(100, int(percent)))
        next_label = str(label or "").strip() or "En progreso"
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return None
            should_update = force or clamped_percent > session.progress_percent or next_label != session.progress_label
            if not should_update:
                return None
            if force or clamped_percent >= session.progress_percent:
                session.progress_percent = clamped_percent
            session.progress_label = next_label
            session.updated_at = utc_now()
            return session.to_dict()

    def _advance_progress_for_op(self, session_id: str, op: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        normalized_op = str(op or "").strip().lower()
        phase = str(payload.get("phase") or payload.get("label") or "").strip().lower()

        if normalized_op == "phase":
            if phase == "preflight":
                return self._update_progress(session_id, 6, "LACE activo; leyendo política y preparando el log de ciclos")
            if phase == "start":
                return self._update_progress(session_id, 8, "Sesion creada, preparando runtime")
            if phase == "plan":
                return self._update_progress(session_id, 18, "Codex esta entendiendo el problema y trazando el plan")
            if phase == "base":
                return self._update_progress(session_id, 28, "Construyendo la versión base antes de los ciclos LACE")
            if phase == "map":
                return self._update_progress(session_id, 35, "Construyendo el mapa conceptual del proyecto")
            if phase == "flow":
                return self._update_progress(session_id, 58, "Dibujando los algoritmos y el flujo interno")
            if phase == "sync":
                return self._update_progress(session_id, 82, "Sincronizando archivos reales al inspector")
            if phase == "audit":
                return self._update_progress(session_id, 92, "Auditando consistencia, cableado y resultados")
            if phase == "verify":
                return self._update_progress(session_id, 94, "Validando cambios y cerrando el ciclo actual")
            if phase == "gate":
                return self._update_progress(session_id, 97, "Evaluando la puerta de cierre LACE")
            if phase == "done":
                return self._update_progress(session_id, 99, "LACE reporta que la puerta de cierre fue superada")

        if normalized_op == "upsert_node":
            return self._update_progress(session_id, 38, "Aparecieron los primeros bloques del mapa")
        if normalized_op == "upsert_edge":
            return self._update_progress(session_id, 46, "Conectando bloques y dependencias")
        if normalized_op == "upsert_flow_step":
            return self._update_progress(session_id, 62, "Construyendo pasos del diagrama de flujo")
        if normalized_op == "upsert_flow_edge":
            return self._update_progress(session_id, 72, "Cableando rutas internas del algoritmo")
        if normalized_op == "sync_file":
            relative_path = normalize_project_relative_path(payload.get("relativePath") or "")
            if is_runtime_control_path(relative_path):
                return self._update_progress(session_id, 26, "Sincronizando bitacoras y contexto de trabajo")
            return self._update_progress(session_id, 85, "Volcando codigo real al inspector")
        if normalized_op == "audit_summary":
            return self._update_progress(session_id, 94, "Cerrando auditoria y consistencia final")
        if normalized_op in {"session_complete", "session_completed", "session_completed_with_warnings"}:
            return self._update_progress(session_id, 100, "Trabajo completado")
        return None

    def _emit_visual_runtime_event(
        self,
        session: AgentSession,
        *,
        op: str,
        message: str,
        status: str | None = None,
        phase: str | None = None,
        error_code: str | None = None,
        **extra: Any,
    ) -> None:
        payload = {
            "op": op,
            "sessionId": session.session_id,
            "projectSlug": session.project_slug,
            "projectDir": str(session.project_dir),
            "message": message,
        }
        if status:
            payload["status"] = status
        if phase:
            payload["phase"] = phase
        elif status and op == "phase":
            payload["phase"] = status
        if error_code:
            payload["errorCode"] = error_code
        for key, value in extra.items():
            if value is not None:
                payload[key] = value
        self._dispatch_runtime_payload(session.session_id, payload, count_visual=False, track_activity=False)
        if op in {
            "session_start",
            "session_complete",
            "session_completed",
            "session_completed_with_warnings",
            "session_blocked",
            "session_failed",
            "session_stopped",
        }:
            self._persist_runtime_trace(session.session_id, payload)

    def _persist_runtime_trace(self, session_id: str, payload: Dict[str, Any]) -> None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or session.event_file is None:
                return
            event_file = session.event_file

        event_payload = dict(payload)
        event_payload.setdefault("timestamp", utc_now())
        serialized = json.dumps(event_payload, ensure_ascii=True)
        try:
            event_file.parent.mkdir(parents=True, exist_ok=True)
            with event_file.open("a", encoding="utf-8") as handle:
                handle.write(f"{serialized}\n")
            next_offset = event_file.stat().st_size
        except OSError:
            return

        with self.lock:
            live_session = self.sessions.get(session_id)
            if live_session is not None and live_session.event_file == event_file:
                live_session.event_offset = max(int(live_session.event_offset or 0), next_offset)

    def _dispatch_runtime_payload(
        self,
        session_id: str,
        payload: Dict[str, Any],
        *,
        count_visual: bool,
        track_activity: bool,
    ) -> None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            payload.setdefault("sessionId", session.session_id)
            payload.setdefault("projectSlug", session.project_slug)
            payload.setdefault("projectDir", str(session.project_dir))
        if track_activity:
            self._mark_agent_activity(session_id)
        snapshot = self._record_bridge_event(session_id, count_visual=count_visual, track_activity=track_activity)
        if snapshot is not None:
            self.session_emitter(snapshot)
        if track_activity:
            progress_snapshot = self._advance_progress_for_op(session_id, str(payload.get("op") or ""), payload)
            if progress_snapshot is not None:
                self.session_emitter(progress_snapshot)
        try:
            self.visual_event_handler(payload)
        except Exception as error:
            self._append_output(
                session_id,
                "[control-plane] Evento visual ignorado por error no critico: "
                f"{type(error).__name__}: {error}\n",
            )

    def _mark_agent_activity(self, session_id: str) -> Dict[str, Any] | None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return None
            session.last_agent_activity_monotonic = time.monotonic()
            session.updated_at = utc_now()
            return session.to_dict()

    def _record_bridge_event(
        self,
        session_id: str,
        *,
        count_visual: bool = False,
        track_activity: bool = True,
    ) -> Dict[str, Any] | None:
        now = utc_now()
        monotonic_now = time.monotonic()
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return None
            if count_visual and track_activity:
                session.visual_event_count += 1
            if track_activity:
                session.last_visual_event_at = now
                session.last_visual_monotonic = monotonic_now
                session.last_agent_activity_monotonic = monotonic_now
            session.updated_at = now
            if track_activity and session.first_visual_event_at is None:
                session.first_visual_event_at = now
                session.first_visual_monotonic = monotonic_now
            return session.to_dict()

    def _emit_heartbeat(self, session_id: str) -> None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or session.status != "running":
                return
            now = utc_now()
            session.last_heartbeat_at = now
            session.last_heartbeat_monotonic = time.monotonic()
            session.updated_at = now
            snapshot = session.to_dict()
        self.session_emitter(snapshot)
        self._emit_visual_runtime_event(
            session,
            op="heartbeat",
            status="running",
            phase="heartbeat",
            message=f"Sesion viva. Progreso {session.progress_percent}%. {session.visual_event_count} evento(s) visual(es) detectado(s).",
        )

    def _fail_session(self, session_id: str, *, error_code: str, message: str, returncode: int, terminate: bool = True) -> None:
        process = None
        should_emit_failure = False
        snapshot = None
        if error_code == "session_idle_timeout" and self._schedule_timeout_retry(session_id, message):
            with self.lock:
                session = self.sessions.get(session_id)
                process = session.process if session is not None else None
            if terminate and process is not None and process.poll() is None:
                process.terminate()
            return
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            if session.status in {"failed", "completed", "stopped"}:
                return
            session.status = "failed"
            session.returncode = returncode
            session.error_code = error_code
            session.error_message = message
            session.progress_label = message
            session.updated_at = utc_now()
            session.ended_at = session.updated_at
            process = session.process
            should_emit_failure = not session.failure_event_emitted
            session.failure_event_emitted = True
            snapshot = session.to_dict()
            session_ref = session
        self._append_output(session_id, f"[agent-guard] {message}\n")
        if terminate and process is not None and process.poll() is None:
            process.terminate()
        if snapshot is not None:
            self.session_emitter(snapshot)
        if should_emit_failure:
            self._emit_visual_runtime_event(
                session_ref,
                op="session_failed",
                status="failed",
                phase="failed",
                error_code=error_code,
                message=message,
            )

    def _check_session_guardrails(self, session_id: str) -> bool:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or session.status != "running":
                return False
            now = time.monotonic()
            started = session.start_monotonic or now
            last_agent_activity = session.last_agent_activity_monotonic or started
            last_heartbeat = session.last_heartbeat_monotonic or started
            first_visual = session.first_visual_monotonic
            has_real_activity = session.first_output_at is not None or first_visual is not None

        if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
            self._emit_heartbeat(session_id)

        if not has_real_activity and now - started >= FIRST_AGENT_SIGNAL_TIMEOUT_SECONDS:
            self._fail_session(
                session_id,
                error_code="agent_start_timeout",
                message="La sesion no produjo salida de terminal ni eventos reales del bridge en el tiempo esperado.",
                returncode=123,
            )
            return True

        if first_visual is None and now - started >= FIRST_VISUAL_TIMEOUT_SECONDS:
            self._fail_session(
                session_id,
                error_code="bridge_timeout",
                message="La sesion no emitio el primer evento visual dentro del tiempo permitido. El agente no entro al bridge visual.",
                returncode=124,
            )
            return True

        if has_real_activity and now - last_agent_activity >= SESSION_IDLE_TIMEOUT_SECONDS:
            self._fail_session(
                session_id,
                error_code="session_idle_timeout",
                message="La sesion quedo en silencio demasiado tiempo sin salida de terminal ni eventos del bridge.",
                returncode=125,
            )
            return True

        return False

    def _append_output(self, session_id: str, chunk: str) -> None:
        cleaned = strip_ansi(chunk)
        if not cleaned:
            return
        terminal_file = None
        progress_snapshot = None
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            session.output = f"{session.output}{cleaned}"[-MAX_OUTPUT_CHARS:]
            session.updated_at = utc_now()
            if session.first_output_at is None:
                session.first_output_at = session.updated_at
                if session.progress_percent < 12:
                    session.progress_percent = 12
                    session.progress_label = "Codex respondio y esta preparando el trabajo"
            session.last_agent_activity_monotonic = time.monotonic()
            terminal_file = session.terminal_file
            payload = {
                "sessionId": session.session_id,
                "projectName": session.project_name,
                "status": session.status,
                "chunk": cleaned,
                "output": session.output,
                "updatedAt": session.updated_at,
            }
            progress_snapshot = session.to_dict()
        if terminal_file is not None:
            try:
                terminal_file.parent.mkdir(parents=True, exist_ok=True)
                with terminal_file.open("a", encoding="utf-8") as handle:
                    handle.write(cleaned)
            except OSError:
                pass
        self.terminal_emitter(payload)
        if progress_snapshot is not None:
            self.session_emitter(progress_snapshot)

    def _start_visual_event_consumer(self, session_id: str) -> tuple[threading.Event, threading.Thread]:
        stop_event = threading.Event()

        def consume_until_stopped() -> None:
            while not stop_event.wait(0.2):
                self._consume_visual_events(session_id)
            self._consume_visual_events(session_id)

        thread = threading.Thread(target=consume_until_stopped, daemon=True)
        thread.start()
        return stop_event, thread

    def _stop_visual_event_consumer(
        self,
        stop_event: threading.Event | None,
        thread: threading.Thread | None,
    ) -> None:
        if stop_event is None or thread is None:
            return
        stop_event.set()
        thread.join(timeout=3)

    def _start_live_reviewer(self, session_id: str) -> tuple[threading.Event | None, threading.Thread | None]:
        if LiveReviewer is None:
            return None, None
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return None, None
            runtime_dir = Path(session.control_plane_runtime_dir or session.project_dir / "runtime")
            reviewer_log_path = runtime_dir / "logs" / f"{session.session_id}-reviewer.jsonl"
            session.reviewer_log_path = str(reviewer_log_path)
            session_ref = session

        def worker_status() -> Dict[str, Any]:
            with self.lock:
                live_session = self.sessions.get(session_id)
                if live_session is None:
                    return {"worker_alive": False, "worker_pid": None, "session_status": "missing"}
                process = live_session.process
                worker_alive = process.poll() is None if process is not None else None
                return {
                    "worker_alive": worker_alive,
                    "worker_pid": live_session.pid,
                    "session_status": live_session.status,
                }

        reviewer = LiveReviewer(  # type: ignore[operator]
            session_id=session_ref.session_id,
            project_id=session_ref.project_slug,
            project_root=session_ref.project_dir,
            runtime_dir=runtime_dir,
            event_handler=self.reviewer_event_handler,
            worker_status_provider=worker_status,
        )
        stop_event = threading.Event()
        thread = threading.Thread(target=reviewer.run_until_stopped, args=(stop_event,), daemon=True)
        thread.start()
        return stop_event, thread

    def _stop_live_reviewer(
        self,
        stop_event: threading.Event | None,
        thread: threading.Thread | None,
    ) -> None:
        if stop_event is None or thread is None:
            return
        stop_event.set()
        thread.join(timeout=3)

    def _maybe_create_human_alignment_review(
        self,
        session: AgentSession,
        result: Dict[str, Any],
        sequence: Dict[str, Any],
    ) -> Dict[str, Any] | None:
        if create_human_alignment_review is None:
            return None
        if str(sequence.get("status") or "") != "completed":
            return None
        task = result.get("task") if isinstance(result.get("task"), dict) else {}
        runtime_dir = Path(session.control_plane_runtime_dir or session.project_dir / "runtime")
        try:
            har_result = create_human_alignment_review(  # type: ignore[misc]
                project_root=session.project_dir,
                runtime_dir=runtime_dir,
                source="automatic",
                trigger="project_completed",
                reason="Proyecto completado; abrir Human Alignment Review antes de cambios V2.",
                task_id=str(task.get("id") or session.active_task_id or ""),
                session_id=session.session_id,
                dedupe=True,
            )
        except Exception as error:
            return {
                "created": False,
                "error": "human_alignment_review_failed",
                "message": str(error),
            }
        review = har_result.get("review") if isinstance(har_result, dict) else None
        self._emit_visual_runtime_event(
            session,
            op="human_alignment_review_created",
            status="waiting_for_human",
            phase="human_alignment_review",
            message="HAR creado: esperando preferencias humanas antes de tocar codigo.",
            review=review,
            created=bool(har_result.get("created")) if isinstance(har_result, dict) else False,
        )
        return har_result

    def _run_control_plane_session(self, session_id: str) -> None:
        visual_stop = None
        visual_thread = None
        reviewer_stop = None
        reviewer_thread = None
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            session.status = "preparing"
            session.updated_at = utc_now()
            session.progress_percent = max(session.progress_percent, 6)
            session.progress_label = "Preparando runtime, LACE y directiva del control plane"
            session_ref = session
        self.session_emitter(session_ref.to_dict())
        self._append_output(
            session_id,
            "[control-plane] Preparando runtime y directiva; preflight interno no bloqueante.\n",
        )

        try:
            with self.lock:
                current_session = self.sessions.get(session_id)
                if current_session is None:
                    return
                needs_prepare = not current_session.active_task or not current_session.directive or not current_session.command
                session_ref = current_session

            if needs_prepare:
                project_dir = session_ref.project_dir
                session_runtime_dir = project_dir / "runtime"
                runtime_mode = session_ref.runtime_mode
                smoke_mode = runtime_mode == "smoke"
                complexity_estimate = self._build_complexity_estimate(project_dir, session_ref.requirement, runtime_mode)
                lace_context = None if smoke_mode else self._prepare_lace_context(
                    project_dir,
                    session_ref.requirement,
                    complexity_estimate=complexity_estimate,
                )
                habla_prompt, habla_available, habla_state = self._resolve_habla_payload(session_ref.requirement)
                habla_preflight_path = self._write_habla_preflight(
                    project_dir=project_dir,
                    requirement=session_ref.requirement,
                    habla_prompt=habla_prompt,
                    habla_available=habla_available,
                    habla_state=habla_state,
                    lace_context=lace_context,
                )
                self._ensure_control_plane_runtime(session_runtime_dir, session_ref.project_slug, runtime_mode)
                self._persist_complexity_estimate(session_runtime_dir, complexity_estimate)
                prepared = self._prepare_control_plane_directive(
                    session_ref.requirement,
                    runtime_mode=runtime_mode,
                    runtime_dir=session_runtime_dir,
                    sprint_number=self.control_plane_sprint_number,
                    directive_repo_root=self.repo_root,
                    task_workspace_root=project_dir,
                    complexity_estimate=complexity_estimate,
                )
                task = prepared["task"]
                directive = prepared["directive"]
                command = self._build_control_plane_worker_command(
                    directive,
                    workspace=project_dir,
                    session_id=session_id,
                    task=task,
                )
                with self.lock:
                    prepared_session = self.sessions.get(session_id)
                    if prepared_session is None:
                        return
                    prepared_session.prompt = directive["rendered_instruction"]
                    prepared_session.command = command
                    prepared_session.habla_prompt = habla_prompt
                    prepared_session.habla_available = habla_available
                    prepared_session.habla_state = habla_state
                    prepared_session.habla_preflight_path = habla_preflight_path
                    prepared_session.lace_policy_path = lace_context.policy_path if lace_context is not None else None
                    prepared_session.lace_log_path = lace_context.log_path if lace_context is not None else None
                    prepared_session.lace_required_cycles = lace_context.required_cycles if lace_context is not None else 0
                    prepared_session.complexity_estimate = complexity_estimate
                    prepared_session.smoke_mode = task["mode"] == "smoke"
                    prepared_session.runtime_mode = task["mode"]
                    prepared_session.control_plane_runtime_dir = str(prepared["runtime_dir"])
                    prepared_session.active_task_id = task["id"]
                    prepared_session.active_task = task
                    prepared_session.directive = directive
                    prepared_session.directive_json_path = prepared["directive_json_path"]
                    prepared_session.directive_markdown_path = prepared["directive_markdown_path"]
                    prepared_session.directive_source_hash = directive["traceability"]["source_hash"]
                    prepared_session.reviewer_log_path = str(session_runtime_dir / "logs" / f"{session_id}-reviewer.jsonl")
                    prepared_session.status = "preparing"
                    prepared_session.progress_percent = max(prepared_session.progress_percent, 10)
                    prepared_session.progress_label = "Directiva generada; esperando worker Codex"
                    prepared_session.updated_at = utc_now()
                    session_ref = prepared_session
                self.session_emitter(session_ref.to_dict())
            else:
                prepared = {
                    "runtime_dir": str(self._resolve_control_plane_runtime_dir(session=session_ref)),
                    "task": dict(session_ref.active_task),
                    "directive": dict(session_ref.directive),
                    "directive_json_path": session_ref.directive_json_path,
                    "directive_markdown_path": session_ref.directive_markdown_path,
                }

            self._emit_visual_runtime_event(
                session_ref,
                op="session_preparing",
                status="preparing",
                phase="prepare",
                message=(
                    f"Control plane preparo la tarea {session_ref.active_task_id} "
                    f"con directiva {session_ref.directive_json_path}."
                ),
            )
            self._emit_preflight_visuals(session_ref)

            visual_stop, visual_thread = self._start_visual_event_consumer(session_id)
            reviewer_stop, reviewer_thread = self._start_live_reviewer(session_id)
            sequence = self.run_control_plane_until_idle(
                session_ref.requirement,
                mode=session_ref.runtime_mode,
                runtime_dir=self._resolve_control_plane_runtime_dir(session=session_ref),
                sprint_number=self.control_plane_sprint_number,
                workspace=session_ref.project_dir,
                directive_repo_root=self.repo_root,
                task_workspace_root=session_ref.project_dir,
                session_id=session_id,
                initial_prepared=prepared,
                initial_command=list(session_ref.command),
            )
            result = sequence.get("last_result") or {}
            completed = sequence["status"] == "completed"
            lace_gate = sequence.get("lace_gate") if isinstance(sequence.get("lace_gate"), dict) else {}
            blocked_by_lace = (
                sequence.get("status") == "blocked"
                and sequence.get("stopped_reason") == "lace_cycles_pending"
            ) or lace_gate.get("status") == "blocked"
            lace_gate_message = None
            if blocked_by_lace:
                lace_gate_message = (
                    "Cierre bloqueado por LACE: "
                    f"{lace_gate.get('completed_cycles', 0)}/{lace_gate.get('required_cycles', '?')} ciclos validos. "
                    f"Faltan: {lace_gate.get('missing_cycles', [])}."
                )
            lace_closure_message = None
            if completed and session_ref.lace_required_cycles and not session_ref.smoke_mode:
                self._sync_lace_runtime(session_id)
                can_close, lace_closure_message = lace_closure_status(
                    session_ref.lace_log_path,
                    session_ref.lace_required_cycles,
                )
                if not can_close:
                    completed = False
                    sequence["status"] = "failed"
                    sequence["stopped_reason"] = "lace_closure_blocked"
            canonical_outcome = self._derive_canonical_control_plane_outcome(
                str(self._resolve_control_plane_runtime_dir(session=session_ref)),
                sequence_status=str(sequence.get("status") or ""),
                sequence_stopped_reason=str(sequence.get("stopped_reason") or "") or None,
                blocked_by_lace=blocked_by_lace,
                lace_gate_message=lace_gate_message,
                lace_closure_message=lace_closure_message,
            )
            completed = bool(canonical_outcome.get("completed"))
            human_alignment_review = (
                self._maybe_create_human_alignment_review(session_ref, result, sequence)
                if completed
                else None
            )
            with self.lock:
                finished_session = self.sessions.get(session_id)
                if finished_session is None:
                    return
                last_task = result.get("task") if isinstance(result.get("task"), dict) else {}
                last_directive = result.get("directive") if isinstance(result.get("directive"), dict) else {}
                if last_task:
                    finished_session.active_task_id = last_task.get("id") or finished_session.active_task_id
                    finished_session.active_task = dict(last_task)
                if last_directive:
                    finished_session.directive = dict(last_directive)
                    traceability = last_directive.get("traceability")
                    if isinstance(traceability, dict):
                        finished_session.directive_source_hash = traceability.get("source_hash") or finished_session.directive_source_hash
                finished_session.directive_json_path = result.get("directive_json_path") or finished_session.directive_json_path
                finished_session.directive_markdown_path = result.get("directive_markdown_path") or finished_session.directive_markdown_path
                finished_session.task_result = dict(result.get("task_result") or {})
                finished_session.validation_result = dict(result.get("validation") or {})
                recovery_payload = dict(result.get("recovery") or {})
                if isinstance(result.get("blanqueo"), dict):
                    recovery_payload["blanqueo"] = dict(result.get("blanqueo") or {})
                if isinstance(human_alignment_review, dict):
                    recovery_payload["humanAlignmentReview"] = human_alignment_review
                finished_session.recovery_result = recovery_payload
                finished_session.checkpoint_result = dict(
                    result.get("checkpoint") or lace_gate.get("checkpoint") or {}
                )
                finished_session.returncode = 0 if completed else 126
                finished_session.status = str(canonical_outcome["session_status"])
                finished_session.error_code = canonical_outcome.get("error_code")
                finished_session.error_message = None if completed else str(canonical_outcome["message"])
                finished_session.progress_percent = 100 if completed else max(finished_session.progress_percent, 94)
                finished_session.progress_label = (
                    f"Cola completada: {sequence['tasks_executed']} tareas ejecutadas"
                    if completed
                    else str(canonical_outcome["message"])
                )
                finished_session.pid = None
                finished_session.process = None
                finished_session.updated_at = utc_now()
                finished_session.ended_at = finished_session.updated_at
                finished_session_ref = finished_session
            self._append_output(
                session_id,
                "[control-plane] Resumen de cola:\n"
                + json.dumps(
                    {
                        "status": sequence.get("status"),
                        "stopped_reason": sequence.get("stopped_reason"),
                        "tasks_executed": sequence.get("tasks_executed"),
                        "ready_task_ids": sequence.get("queue", {}).get("ready_task_ids"),
                        "lace_gate": sequence.get("lace_gate"),
                        "tool_policy_final": sequence.get("tool_policy_final"),
                        "blanqueo": result.get("blanqueo"),
                        "human_alignment_review": human_alignment_review,
                        "canonical_outcome": canonical_outcome,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
                + "\n",
            )
            self.session_emitter(finished_session_ref.to_dict())
            self._emit_visual_runtime_event(
                finished_session_ref,
                op=str(canonical_outcome["event_op"]),
                status=str(canonical_outcome["event_status"]),
                phase=str(canonical_outcome["phase"]),
                error_code=canonical_outcome.get("error_code"),
                message=str(canonical_outcome["message"]),
            )
        except Exception as error:
            if getattr(error, "code", "") == "cyberlace_sensitive_document_blocked":
                details = getattr(error, "details", {}) if isinstance(getattr(error, "details", {}), dict) else {}
                decision = details.get("decision") if isinstance(details.get("decision"), dict) else {
                    "message": str(error),
                    "reason": str(error),
                    "blocked": True,
                    "blocksRuntime": True,
                    "runtimeAction": "QUARANTINE",
                    "severity": "CRITICAL",
                    "riskScore": 100.0,
                    "evidence": [],
                    "blockedPaths": [],
                }
                checkpoint = details.get("checkpoint") if isinstance(details.get("checkpoint"), dict) else None
                with self.lock:
                    blocked_session = self.sessions.get(session_id)
                if blocked_session is not None:
                    self._block_session_for_cyberlace_document(blocked_session, decision, checkpoint=checkpoint)
                return

            message = f"Control plane fallo durante la ejecucion de la tarea: {error}"
            with self.lock:
                failed_session = self.sessions.get(session_id)
                if failed_session is None:
                    return
                failed_session.status = "failed"
                failed_session.returncode = 126
                failed_session.pid = None
                failed_session.process = None
                failed_session.error_code = getattr(error, "code", "control_plane_execution_error")
                failed_session.error_message = message
                failed_session.progress_label = message
                failed_session.updated_at = utc_now()
                failed_session.ended_at = failed_session.updated_at
                failed_session_ref = failed_session
            self._append_output(session_id, f"[control-plane] {message}\n")
            self.session_emitter(failed_session_ref.to_dict())
            self._emit_visual_runtime_event(
                failed_session_ref,
                op="session_failed",
                status="failed",
                phase="failed",
                error_code=failed_session_ref.error_code or "control_plane_execution_error",
                message=message,
            )
        finally:
            self._stop_visual_event_consumer(visual_stop, visual_thread)
            self._stop_live_reviewer(reviewer_stop, reviewer_thread)

    def _run_session(self, session_id: str) -> None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return
            if session.control_plane_enabled:
                session.status = "preparing"
                session.progress_label = "Preparando control plane y directiva"
            else:
                session.status = "starting"
                session.progress_label = "Preparando el proceso del agente"
            session.progress_percent = max(session.progress_percent, 2)
            session.updated_at = utc_now()
        self._emit_session(session)
        adapter = self._session_worker_adapter(session)
        adapter.run(self, session_id)

    def _session_worker_adapter(self, session: AgentSession) -> SessionWorkerAdapter:
        if select_session_worker_adapter is None:
            raise RuntimeError("session worker adapters are unavailable")
        return select_session_worker_adapter(bool(session.control_plane_enabled))  # type: ignore[misc]

    def _run_legacy_pty_session(self, session_id: str) -> None:
        try:
            master_fd, slave_fd = pty.openpty()
            env_extra = {
                "PATH": self.codex_launch_path,
                "VISTA_AGENT_SESSION_ID": session.session_id,
                "VISTA_AGENT_PROJECT_SLUG": session.project_slug,
                "VISTA_AGENT_PROJECT_DIR": str(session.project_dir),
                "VISTA_AGENT_BRIDGE": f"{self.bridge_python} {self.bridge_script}",
            }
            if session.event_file is not None:
                env_extra["VISTA_AGENT_EVENT_FILE"] = str(session.event_file)
            if safe_child_process_env is not None:
                env = safe_child_process_env(os.environ, extra=env_extra)
            else:
                env = env_extra
            process = subprocess.Popen(
                session.command,
                cwd=session.project_dir,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=env,
            )
            os.close(slave_fd)
        except FileNotFoundError:
            display_cmd = " ".join(self.codex_command_tokens or [self.codex_cmd])
            self._append_output(session_id, f"[agent] No se encontro el comando `{display_cmd}`.\n")
            with self.lock:
                failed_session = self.sessions.get(session_id)
                if failed_session is not None:
                    failed_session.status = "failed"
                    failed_session.returncode = 127
                    failed_session.updated_at = utc_now()
                    failed_session.ended_at = failed_session.updated_at
                    failed_session.progress_label = f"No se encontro el comando `{display_cmd}`."
                    failed_session.error_code = "codex_command_not_found"
                    failed_session.error_message = f"No se encontro el comando `{display_cmd}`."
            snapshot = self.get_session(session_id)
            if snapshot is not None:
                self.session_emitter(snapshot)
            if failed_session is not None:
                self._emit_visual_runtime_event(
                    failed_session,
                    op="session_failed",
                    message="La sesion fallo al arrancar Codex.",
                    status="failed",
                    phase="failed",
                    error_code="codex_command_not_found",
                )
            return
        except Exception as error:  # pragma: no cover - guard rail for runtime launches
            self._append_output(session_id, f"[agent] No fue posible iniciar Codex: {error}\n")
            with self.lock:
                failed_session = self.sessions.get(session_id)
                if failed_session is not None:
                    failed_session.status = "failed"
                    failed_session.returncode = 1
                    failed_session.updated_at = utc_now()
                    failed_session.ended_at = failed_session.updated_at
                    failed_session.progress_label = f"No fue posible iniciar Codex: {error}"
                    failed_session.error_code = "codex_launch_error"
                    failed_session.error_message = f"No fue posible iniciar Codex: {error}"
            snapshot = self.get_session(session_id)
            if snapshot is not None:
                self.session_emitter(snapshot)
            if failed_session is not None:
                self._emit_visual_runtime_event(
                    failed_session,
                    op="session_failed",
                    message="La sesion encontro un error al iniciar.",
                    status="failed",
                    phase="failed",
                    error_code="codex_launch_error",
                )
            return

        with self.lock:
            live_session = self.sessions.get(session_id)
            if live_session is None:
                return
            live_session.process = process
            live_session.master_fd = master_fd
            live_session.pid = process.pid
            live_session.status = "running"
            live_session.started_at = utc_now()
            live_session.updated_at = live_session.started_at
            live_session.start_monotonic = time.monotonic()
            live_session.last_agent_activity_monotonic = live_session.start_monotonic
            live_session.last_heartbeat_monotonic = live_session.start_monotonic
            live_session.last_heartbeat_at = live_session.started_at
            live_session.progress_percent = max(live_session.progress_percent, 5)
            live_session.progress_label = "Proceso lanzado, esperando respuesta de Codex"
        snapshot = self.get_session(session_id)
        if snapshot is not None:
            self.session_emitter(snapshot)
        self._emit_preflight_visuals(live_session)
        self._emit_visual_runtime_event(
            live_session,
            op="session_start",
            status="running",
            phase="start",
            message=(
                "Sesion smoke tecnica iniciada. LACE desactivado para esta prueba."
                if live_session.smoke_mode
                else (
                    f"Sesion iniciada. LACE activo con maximo {live_session.lace_required_cycles} ciclo(s); cierre temprano si las compuertas estan limpias."
                    if live_session.lace_required_cycles
                    else "Sesion iniciada. Esperando el primer evento visual del bridge."
                )
            ),
        )

        last_graph_sync = 0.0
        try:
            while True:
                if process.poll() is not None:
                    self._drain_output(master_fd, session_id)
                    break

                ready, _, _ = select.select([master_fd], [], [], 0.2)
                if ready:
                    self._read_once(master_fd, session_id)

                self._consume_visual_events(session_id)
                self._sync_lace_runtime(session_id)
                if self._check_session_guardrails(session_id):
                    break

                if time.monotonic() - last_graph_sync >= 2.0:
                    self.graph_sync(False)
                    last_graph_sync = time.monotonic()
        finally:
            self._consume_visual_events(session_id)
            self._sync_lace_runtime(session_id)
            try:
                os.close(master_fd)
            except OSError:
                pass

        returncode = process.wait()
        should_retry = False
        with self.lock:
            finished_session = self.sessions.get(session_id)
            if finished_session is not None:
                if finished_session.retry_pending and not finished_session.stop_requested:
                    finished_session.process = None
                    finished_session.master_fd = None
                    finished_session.pid = None
                    finished_session.returncode = returncode
                    finished_session.updated_at = utc_now()
                    finished_session.ended_at = finished_session.updated_at
                    finished_session_ref = finished_session
                    should_retry = True
                else:
                    if finished_session.returncode is None:
                        finished_session.returncode = returncode
                    if finished_session.stop_requested:
                        final_status = "stopped"
                        finished_session.progress_label = "Sesion detenida por el usuario"
                    elif finished_session.status == "failed":
                        final_status = "failed"
                    elif finished_session.returncode == 0 and finished_session.first_visual_event_at is None:
                        final_status = "failed"
                        finished_session.error_code = finished_session.error_code or "no_visual_events"
                        finished_session.error_message = finished_session.error_message or "La sesion termino sin emitir ningun evento visual util."
                        finished_session.returncode = 126
                        finished_session.progress_label = finished_session.error_message
                    elif finished_session.returncode == 0 and finished_session.lace_required_cycles and not finished_session.smoke_mode:
                        can_close, closure_status = lace_closure_status(
                            finished_session.lace_log_path,
                            finished_session.lace_required_cycles,
                        )
                        if not can_close:
                            self._mark_lace_cycles_after_closure(finished_session, failed=True)
                            final_status = "failed"
                            finished_session.error_code = "lace_closure_blocked"
                            finished_session.error_message = closure_status
                            finished_session.returncode = 126
                            finished_session.progress_label = closure_status
                        else:
                            self._mark_lace_cycles_after_closure(finished_session, failed=False)
                            final_status = "completed"
                            finished_session.progress_percent = 100
                            finished_session.progress_label = "Trabajo completado"
                    elif finished_session.returncode == 0:
                        final_status = "completed"
                        finished_session.progress_percent = 100
                        finished_session.progress_label = "Trabajo completado"
                    else:
                        final_status = "failed"
                        finished_session.error_code = finished_session.error_code or "process_exit_nonzero"
                        finished_session.error_message = finished_session.error_message or "La sesion termino con codigo de salida distinto de cero."
                        finished_session.progress_label = finished_session.error_message
                    finished_session.status = final_status
                    finished_session.updated_at = utc_now()
                    finished_session.ended_at = finished_session.updated_at
                    finished_session.process = None
                    finished_session.master_fd = None
                    finished_session_ref = finished_session
            else:
                finished_session_ref = None
        if should_retry and finished_session_ref is not None:
            self.graph_sync(True)
            retry_snapshot = self._prepare_retry_attempt(session_id)
            if retry_snapshot is not None:
                self.session_emitter(retry_snapshot)
            self._run_session(session_id)
            return
        self._cyberlace_finalize_session_output(session_id)
        self.graph_sync(True)
        final_snapshot = self.get_session(session_id)
        if final_snapshot is not None:
            self.session_emitter(final_snapshot)
        if finished_session_ref is not None:
            if finished_session_ref.status == "completed":
                self._emit_visual_runtime_event(
                    finished_session_ref,
                    op="session_complete",
                    message="La sesion termino y libero el foco del editor.",
                    status="completed",
                    phase="complete",
                )
            elif finished_session_ref.status == "stopped":
                self._emit_visual_runtime_event(
                    finished_session_ref,
                    op="session_stopped",
                    message="La sesion fue detenida por el usuario y libero el foco del editor.",
                    status="stopped",
                    phase="stopped",
                )
            elif not finished_session_ref.failure_event_emitted:
                finished_session_ref.failure_event_emitted = True
                self._emit_visual_runtime_event(
                    finished_session_ref,
                    op="session_failed",
                    message=finished_session_ref.error_message or "La sesion termino con error y libero el foco del editor.",
                    status="failed",
                    phase="failed",
                    error_code=finished_session_ref.error_code or "process_exit_nonzero",
                )

    def _read_once(self, master_fd: int, session_id: str) -> None:
        try:
            data = os.read(master_fd, READ_CHUNK_SIZE)
        except OSError:
            return
        if not data:
            return
        self._append_output(session_id, data.decode("utf-8", errors="replace"))

    def _drain_output(self, master_fd: int, session_id: str) -> None:
        while True:
            ready, _, _ = select.select([master_fd], [], [], 0)
            if not ready:
                return
            try:
                data = os.read(master_fd, READ_CHUNK_SIZE)
            except OSError:
                return
            if not data:
                return
            self._append_output(session_id, data.decode("utf-8", errors="replace"))

    def _consume_visual_events(self, session_id: str) -> None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or session.event_file is None:
                return
            event_file = session.event_file
            current_offset = session.event_offset
            project_slug = session.project_slug
            project_dir = session.project_dir

        if not event_file.exists():
            return

        try:
            file_size = event_file.stat().st_size
        except OSError:
            return

        if file_size < current_offset:
            current_offset = 0

        try:
            with event_file.open("r", encoding="utf-8") as handle:
                handle.seek(current_offset)
                lines = handle.readlines()
                next_offset = handle.tell()
        except OSError:
            return

        if next_offset == current_offset:
            return

        with self.lock:
            live_session = self.sessions.get(session_id)
            if live_session is not None:
                live_session.event_offset = next_offset

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                self._append_output(session_id, f"[agent-visual] Evento invalido ignorado: {line[:120]}\n")
                continue

            op = str(payload.get("op") or "").strip().lower()
            if self._is_internal_visual_payload(op, payload):
                continue
            self._dispatch_runtime_payload(session_id, payload, count_visual=op in VISUAL_EVENT_OPS, track_activity=True)

    def _is_internal_visual_payload(self, op: str, payload: Dict[str, Any]) -> bool:
        if op != "sync_file":
            return False
        relative_path = normalize_project_relative_path(
            payload.get("relativePath") or payload.get("sourcePath") or ""
        )
        return (
            is_runtime_control_path(relative_path)
            or is_control_plane_state_path(relative_path)
            or relative_path == "workspace/projects"
            or relative_path.startswith("workspace/projects/")
        )

    def _prepare_lace_context(
        self,
        project_dir: Path,
        requirement: str,
        *,
        complexity_estimate: Dict[str, Any] | None = None,
    ) -> LaceContext | None:
        policy_source = self.lace_policy_source
        if policy_source is None or not policy_source.exists():
            return None
        if is_observational_smoke_requirement(requirement):
            return None

        policy_text = policy_source.read_text(encoding="utf-8")
        validate_lace_policy_text(policy_text)
        estimated_cycles = 0
        if isinstance(complexity_estimate, dict):
            try:
                estimated_cycles = int(complexity_estimate.get("recommended_lace_cycles") or 0)
            except (TypeError, ValueError):
                estimated_cycles = 0
        required_cycles = clamp_lace_required_cycles(estimated_cycles) if estimated_cycles else detect_lace_required_cycles(policy_text)
        project_policy_path = project_dir / "LACE.md"
        project_policy_path.parent.mkdir(parents=True, exist_ok=True)

        current_policy_text = ""
        if project_policy_path.exists():
            try:
                current_policy_text = project_policy_path.read_text(encoding="utf-8")
            except OSError:
                current_policy_text = ""
        if current_policy_text != policy_text:
            project_policy_path.write_text(policy_text, encoding="utf-8")

        log_path = project_dir / "LACE_LOG.md"
        initialize_lace_log(
            log_path,
            project_prompt=requirement,
            policy_path=project_policy_path,
            required_cycles=required_cycles,
        )

        return LaceContext(
            policy_text=policy_text,
            directive=build_lace_compact_directive(project_policy_path, log_path, required_cycles),
            policy_path=project_policy_path,
            log_path=log_path,
            required_cycles=required_cycles,
        )
