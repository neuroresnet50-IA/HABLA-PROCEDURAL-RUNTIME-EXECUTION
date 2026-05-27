from __future__ import annotations

import contextlib
import hashlib
import importlib
import io
import json
import mimetypes
import os
import re
import signal
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any, Dict, List

from agent_repair_service import (
    build_agent_repair_requirement as build_agent_repair_requirement_service,
    build_repair_validation_commands as build_repair_validation_commands_service,
    queue_agent_repair_task as queue_agent_repair_task_service,
    suggested_repair_files as suggested_repair_files_service,
)
from agent_runtime import AgentRuntime, normalize_agent_runtime_mode
from auth_routes import register_auth_routes, verify_current_user_password
from architecture_ir import (
    build_architecture_ir,
    build_project_descriptor,
    canonicalize_findings_as_issues,
    canonicalize_nodes,
    merge_issue_lists,
)
from code_scanner_service import (
    build_code_scanner_report as build_code_scanner_report_service,
    persist_code_scanner_report as persist_code_scanner_report_service,
)
from cyberlace_routes import register_cyberlace_routes
from editor_routes import register_editor_routes
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from human_alignment_routes import register_human_alignment_routes
from integrity_routes import register_integrity_routes
from map_lint import lint_graph
from orchestrator.complexity_estimator import estimate_complexity
from orchestrator.email_command_plane import EmailCommandConfig, EmailCommandPlane
from orchestrator.live_reviewer import build_reviewer_status, load_reviewer_events
from orchestrator.observer_plane import ObserverConfig, ObserverPlane, build_observer_findings_report
from orchestrator.state_store import StateStore
from observer_runtime_service import ObserverRuntimeFacade
from project_graph import (
    build_project_graph,
    default_color_for_layer,
    detect_code_language,
    infer_layer,
    layer_label_for_path,
    node_id_for_path,
)
from reverse_engineering import build_analysis_entry
from runtime_admin_routes import register_runtime_admin_routes
from runtime_admin_service import RuntimeAdminService
from sandbox_service import SandboxService
from sandbox_routes import register_sandbox_routes
from safety_learning_core import (
    build_safety_learning_status,
    learn_from_harness_result,
    queue_repair_recommendation,
    record_human_feedback,
)
from integrity_service import IntegrityService
from workspace_blanqueo import (
    apply_selective_blanqueo,
    create_blanqueo_backup,
    create_post_blanqueo_recovery,
    decidir_y_justificar_blanqueo,
    record_blanqueo_decision,
)

try:
    from flask_cors import CORS
except ImportError:
    CORS = None

SOCKET_ASYNC_MODE = os.environ.get("NEURO_LACE_SOCKET_ASYNC_MODE", "threading")


def env_flag_enabled(value: str | None, *, default: bool = False) -> bool:
    raw = str(value or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


SOCKET_POLLING_ONLY = env_flag_enabled(
    os.environ.get("NEURO_LACE_SOCKET_POLLING_ONLY"),
    default=SOCKET_ASYNC_MODE == "threading",
)
SOCKETIO_OPTIONS: Dict[str, Any] = {}
if SOCKET_POLLING_ONLY:
    SOCKETIO_OPTIONS.update({"allow_upgrades": False, "transports": ["polling"]})

app = Flask(__name__)
app.config["SECRET_KEY"] = "architecture-view-dev"
if CORS is not None:
    CORS(app, resources={r"/*": {"origins": "*"}})


@app.after_request
def apply_cors_headers(response):
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
    return response


socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode=SOCKET_ASYNC_MODE,
    **SOCKETIO_OPTIONS,
)
register_auth_routes(app, secret_key=str(app.config.get("SECRET_KEY") or "architecture-view-dev"))
register_cyberlace_routes(app, socketio)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VISTA_ROOT = PROJECT_ROOT.parent
METACOG_ROOT = VISTA_ROOT.parent
DEFAULT_HABLA_V5_ROOT = METACOG_ROOT / "habla_agentic_engine_v5_1_lace_visual"
DEFAULT_HABLA_V4_ROOT = VISTA_ROOT / "habla_agentic_engine"
FRONTEND_DIST_ROOT = PROJECT_ROOT / "frontend" / "dist"
EDITOR_STATE_FILE = Path(__file__).resolve().with_name("editor_state.json")
ANALYSIS_STATE_FILE = Path(__file__).resolve().with_name("reverse_engineering_state.json")
AGENT_WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
AGENT_PROJECTS_ROOT = AGENT_WORKSPACE_ROOT / "projects"
PROTECTED_AGENT_PROJECTS = {"sesion-20260524210420", "sesion-20260524233805", "sesion-20260518014728-jeego-en-3d"}
WORKSPACE_PATH_PREFIX = "workspace/projects/"
ANALYSIS_PATH_PREFIX = "analysis/projects/"
ACTIVE_AGENT_SESSION_STATUSES = {"queued", "preparing", "starting", "running"}
CLOSED_AGENT_SESSION_STATUSES = {"completed", "failed", "stopped", "blocked"}
CLOSED_AGENT_VISUAL_OPS = {
    "session_complete",
    "session_completed",
    "session_completed_with_warnings",
    "session_blocked",
    "session_failed",
    "session_stopped",
}
RUNTIME_ROOT = PROJECT_ROOT / ".runtime"
RUNTIME_LOG_ROOT = RUNTIME_ROOT / "logs"
BASELINE_ANCHOR_ROOT = Path(os.environ.get("HABLA_BASELINE_ANCHOR_ROOT", str(RUNTIME_ROOT / "baseline_anchors"))).expanduser()
RUNTIME_RESET_LOG = RUNTIME_LOG_ROOT / "runtime-reset.log"
OBSERVER_ROOT = RUNTIME_ROOT / "observer"
OBSERVER_MEMORY_FILE = OBSERVER_ROOT / "memory.json"
OBSERVER_TIMELINE_FILE = OBSERVER_ROOT / "timeline.jsonl"
OBSERVER_BEHAVIOR_FILE = OBSERVER_ROOT / "behavior_tree.json"
OBSERVER_MANUAL_PIN_FILE = OBSERVER_ROOT / "manual_pin.json"
OBSERVER_INCIDENT_DIR = OBSERVER_ROOT / "incidents"
EMAIL_COMMAND_ROOT = RUNTIME_ROOT / "email_commands"
EMAIL_COMMAND_CONFIG_FILE = EMAIL_COMMAND_ROOT / "config.json"
DEFAULT_RUNTIME_RESET_HOST = os.environ.get("RUNTIME_RESET_HOST", "127.0.0.1")
DEFAULT_RUNTIME_RESET_PORT = int(os.environ.get("RUNTIME_RESET_PORT", "5001"))
DEFAULT_RUNTIME_RESET_DELAY_MS = int(os.environ.get("RUNTIME_RESET_DELAY_MS", "3500"))
CLEAN_WORKSPACE_KEYWORD = "HABLA"
EDITOR_MAX_FILE_BYTES = int(os.environ.get("NEURO_LACE_EDITOR_MAX_FILE_BYTES", "1000000"))
EDITOR_EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "runtime",
}
CODE_SCANNER_REPORT_NAME = "final_code_scanner_report.json"
CODE_SCANNER_CHECKPOINT_NAME = "final-code-scanner-checkpoint.json"
TYPEWRITER_REPORT_NAME = "final_typewriter_report.json"
TYPEWRITER_CHECKPOINT_NAME = "final-typewriter-checkpoint.json"
AGENT_FILE_MANIFEST_NAME = "agent_file_manifest.json"
AGENT_FILE_MANIFEST_SEAL_NAME = "agent_file_manifest.seal.json"
AGENT_BASELINE_SEAL_LEDGER_NAME = "baseline_seals.jsonl"
FILE_INTEGRITY_REPORT_NAME = "file_integrity_report.json"
OBSERVER_FINDINGS_REPORT_NAME = "observer_findings.json"
FROZEN_SNIPER_REPORT_NAME = "frozen_sniper_recovery_report.json"
FROZEN_SNIPER_CONFIRMATION = "FROZEN_SNIPER"
FILE_WRITE_LEDGER_NAME = "file_write_ledger.jsonl"
SANDBOX_HOST = os.environ.get("NEURO_LACE_SANDBOX_HOST", "127.0.0.1")
SANDBOX_PORT_START = int(os.environ.get("NEURO_LACE_SANDBOX_PORT_START", "5600"))
SANDBOX_PORT_END = int(os.environ.get("NEURO_LACE_SANDBOX_PORT_END", "5699"))
SANDBOX_READY_TIMEOUT_SECONDS = float(os.environ.get("NEURO_LACE_SANDBOX_READY_TIMEOUT_SECONDS", "12"))
SANDBOX_READY_POLL_SECONDS = float(os.environ.get("NEURO_LACE_SANDBOX_READY_POLL_SECONDS", "0.25"))
SANDBOX_STATE_NAME = "sandbox.json"
SANDBOX_LOG_NAME = "sandbox.log"
sandbox_service = SandboxService(
    host=SANDBOX_HOST,
    port_start=SANDBOX_PORT_START,
    port_end=SANDBOX_PORT_END,
    ready_timeout_seconds=SANDBOX_READY_TIMEOUT_SECONDS,
    ready_poll_seconds=SANDBOX_READY_POLL_SECONDS,
    state_name=SANDBOX_STATE_NAME,
    log_name=SANDBOX_LOG_NAME,
    load_json_file=lambda path, default: load_json_file(path, default),
    now_provider=lambda: utc_now(),
)
code_scanner_locks: Dict[str, threading.Lock] = {}
integrity_action_locks: Dict[str, threading.Lock] = {}
runtime_action_locks_lock = threading.Lock()
frontend_asset_cache: Dict[str, Dict[str, Any]] = {}
frontend_asset_cache_lock = threading.Lock()
cyberlace_training_runs: Dict[str, Dict[str, Any]] = {}
cyberlace_training_runs_lock = threading.RLock()
continuity_probe_runs: Dict[str, Dict[str, Any]] = {}
continuity_probe_runs_lock = threading.RLock()
NORMALIZED_GRAPH_CACHE_TTL_SECONDS = float(os.environ.get("NEURO_LACE_GRAPH_CACHE_TTL_SECONDS", "8"))
CYBERLACE_TRAINING_SCENARIOS = {
    "obfuscated-secret",
    "external-login",
    "prompt-injection-readme",
    "payment-data",
    "multi-provider-token",
}
CYBERLACE_TRAINING_INTENSITIES = {"baseline", "hard", "extreme"}
CYBERLACE_TRAINING_CASES_DIR = PROJECT_ROOT / "runtime" / "cyberlace" / "training_cases"
CYBERLACE_TRAINING_REPORTS_DIR = PROJECT_ROOT / "runtime" / "cyberlace" / "training_reports"
CYBERLACE_TRAINING_CHECKPOINTS_DIR = PROJECT_ROOT / "runtime" / "cyberlace" / "training_checkpoints"
CYBERLACE_TRAINING_CAMPAIGNS_DIR = PROJECT_ROOT / "runtime" / "cyberlace" / "training_campaigns"
CYBERLACE_TRAINING_MEMORY_PATH = CYBERLACE_TRAINING_CAMPAIGNS_DIR / "memory.json"
CYBERLACE_TRAINING_RUNS_DIR = PROJECT_ROOT / "runtime" / "cyberlace" / "training_runs"
CYBERLACE_TRAINING_RUN_ACTIVE_STATUSES = {"queued", "running", "stopping"}
CYBERLACE_TRAINING_RUN_TERMINAL_STATUSES = {"completed", "failed", "stopped", "interrupted"}
CYBERLACE_TRAINING_ALLOWED_ROOTS = (
    CYBERLACE_TRAINING_CASES_DIR,
    CYBERLACE_TRAINING_REPORTS_DIR,
    CYBERLACE_TRAINING_CHECKPOINTS_DIR,
    CYBERLACE_TRAINING_CAMPAIGNS_DIR,
    CYBERLACE_TRAINING_RUNS_DIR,
)
LINT_FULL_IR_MAX_NODES = int(os.environ.get("NEURO_LACE_LINT_FULL_IR_MAX_NODES", "40"))
LINT_FULL_IR_MAX_BYTES = int(os.environ.get("NEURO_LACE_LINT_FULL_IR_MAX_BYTES", "250000"))
normalized_graph_cache: Dict[str, Dict[str, Any]] = {}
normalized_graph_cache_lock = threading.Lock()


def _runtime_action_lock(registry: Dict[str, threading.Lock], project_slug: str) -> threading.Lock:
    with runtime_action_locks_lock:
        lock = registry.get(project_slug)
        if lock is None:
            lock = threading.Lock()
            registry[project_slug] = lock
        return lock


def _safe_frontend_file(root: Path, relative_path: str) -> Path | None:
    normalized = str(PurePosixPath(str(relative_path or "").replace("\\", "/"))).lstrip("/")
    try:
        root_resolved = root.resolve()
        candidate = (root / normalized).resolve()
        candidate.relative_to(root_resolved)
    except (OSError, ValueError):
        return None
    if not candidate.is_file():
        return None
    return candidate


def send_cached_frontend_file(root: Path, relative_path: str):
    candidate = _safe_frontend_file(root, relative_path)
    if candidate is None:
        return jsonify({"ok": False, "error": "frontend_asset_not_found"}), 404

    stat = candidate.stat()
    cache_key = str(candidate)
    with frontend_asset_cache_lock:
        cached = frontend_asset_cache.get(cache_key)
        if (
            not cached
            or cached.get("mtime_ns") != stat.st_mtime_ns
            or cached.get("size") != stat.st_size
        ):
            data = candidate.read_bytes()
            cached = {
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
                "data": data,
                "mimetype": mimetypes.guess_type(candidate.name)[0] or "application/octet-stream",
            }
            frontend_asset_cache[cache_key] = cached

    data = cached["data"]
    response = Response(data, mimetype=cached["mimetype"])
    response.headers["Content-Length"] = str(len(data))
    response.headers["Cache-Control"] = "no-cache"
    return response


def normalized_graph_cache_key(payload: Dict[str, Any]) -> str:
    try:
        encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    except (TypeError, ValueError):
        encoded = repr(payload)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def get_cached_normalized_graph(cache_key: str) -> Dict[str, Any] | None:
    now = time.time()
    with normalized_graph_cache_lock:
        cached = normalized_graph_cache.get(cache_key)
        if not cached:
            return None
        if now - float(cached.get("created_at") or 0) > NORMALIZED_GRAPH_CACHE_TTL_SECONDS:
            normalized_graph_cache.pop(cache_key, None)
            return None
        graph = cached.get("graph")
    return deepcopy(graph) if isinstance(graph, dict) else None


def remember_normalized_graph(cache_key: str, graph: Dict[str, Any]) -> None:
    with normalized_graph_cache_lock:
        normalized_graph_cache[cache_key] = {
            "created_at": time.time(),
            "graph": deepcopy(graph),
        }


def graph_code_weight(graph: Dict[str, Any]) -> tuple[int, int]:
    nodes = graph.get("nodes") if isinstance(graph, dict) else []
    if not isinstance(nodes, list):
        return 0, 0
    code_bytes = sum(len(str(node.get("code") or "").encode("utf-8")) for node in nodes if isinstance(node, dict))
    return len(nodes), code_bytes


def should_use_full_lint_ir(graph: Dict[str, Any]) -> bool:
    node_count, code_bytes = graph_code_weight(graph)
    return node_count <= LINT_FULL_IR_MAX_NODES and code_bytes <= LINT_FULL_IR_MAX_BYTES


def canonicalize_light_graph(graph: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    project = build_project_descriptor(graph, PROJECT_ROOT)
    nodes = canonicalize_nodes(graph.get("nodes") or [], project)
    return project, nodes


def _configured_path(*names: str) -> Path | None:
    for name in names:
        raw_value = str(os.environ.get(name) or "").strip()
        if raw_value:
            return Path(raw_value).expanduser()
    return None


def _candidate_habla_roots() -> list[Path]:
    explicit = _configured_path("HABLA_ENGINE_ROOT", "VISTA_HABLA_ENGINE_ROOT")
    if explicit is not None:
        return [explicit]
    return [DEFAULT_HABLA_V5_ROOT, DEFAULT_HABLA_V4_ROOT]


def _purge_runtime_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "runtime" or module_name.startswith("runtime."):
            del sys.modules[module_name]


def _load_habla_engine(root: Path) -> dict[str, Any]:
    root = root.expanduser()
    if not root.exists():
        raise ImportError(f"HABLA engine root does not exist: {root}")
    root_path = str(root)
    if root_path in sys.path:
        sys.path.remove(root_path)
    sys.path.insert(0, root_path)
    _purge_runtime_modules()
    engine_module = importlib.import_module("runtime.engine")
    prompt_module = importlib.import_module("runtime.prompt_converter")
    if hasattr(engine_module, "HablaEngineV5"):
        return {
            "root": root,
            "engine_class": getattr(engine_module, "HablaEngineV5"),
            "engine_name": "HablaEngineV5",
            "engine_version": "v5.1",
            "convert_to_habla": getattr(prompt_module, "convert_to_habla", None),
        }
    if hasattr(engine_module, "HablaEngineV4"):
        return {
            "root": root,
            "engine_class": getattr(engine_module, "HablaEngineV4"),
            "engine_name": "HablaEngineV4",
            "engine_version": "v4.2",
            "convert_to_habla": getattr(prompt_module, "convert_to_habla", None),
        }
    raise ImportError(f"No supported HABLA engine class found in {root}")


HABLA_ENGINE_IMPORT_ERRORS: list[str] = []
HABLA_ENGINE_CLASS: Any = None
HABLA_ENGINE_CLASS_NAME = "unavailable"
HABLA_ENGINE_VERSION = "unavailable"
HABLA_ROOT = _candidate_habla_roots()[0]
convert_to_habla: Any = None

for candidate_root in _candidate_habla_roots():
    try:
        loaded_habla_engine = _load_habla_engine(candidate_root)
    except Exception as error:  # pragma: no cover - surfaced through preflight state.
        HABLA_ENGINE_IMPORT_ERRORS.append(f"{candidate_root}: {error}")
        continue
    HABLA_ROOT = loaded_habla_engine["root"]
    HABLA_ENGINE_CLASS = loaded_habla_engine["engine_class"]
    HABLA_ENGINE_CLASS_NAME = loaded_habla_engine["engine_name"]
    HABLA_ENGINE_VERSION = loaded_habla_engine["engine_version"]
    convert_to_habla = loaded_habla_engine["convert_to_habla"]
    break


def _resolve_habla_lace_policy_path() -> Path | None:
    explicit = _configured_path("VISTA_LACE_POLICY_PATH", "HABLA_LACE_POLICY_PATH")
    if explicit is not None:
        return explicit
    policy_path = HABLA_ROOT / "LACE.md"
    return policy_path if policy_path.exists() else None


HABLA_LACE_POLICY_PATH = _resolve_habla_lace_policy_path()


def _build_habla_engine(memory_path: Path, requirement: str) -> Any:
    if HABLA_ENGINE_CLASS is None:
        raise RuntimeError("HABLA engine class is unavailable")
    kwargs: dict[str, Any] = {"memory_path": str(memory_path)}
    if HABLA_ENGINE_CLASS_NAME == "HablaEngineV5":
        habla_runtime_root = RUNTIME_ROOT / "habla"
        habla_runtime_root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(str(requirement or "").encode("utf-8")).hexdigest()[:12]
        kwargs.update(
            {
                "lace_enabled": HABLA_LACE_POLICY_PATH is not None and HABLA_LACE_POLICY_PATH.exists(),
                "lace_path": str(HABLA_LACE_POLICY_PATH) if HABLA_LACE_POLICY_PATH is not None else "LACE.md",
                "lace_log_path": str(habla_runtime_root / f"preflight-{digest}.md"),
            }
        )
    return HABLA_ENGINE_CLASS(**kwargs)


def build_habla_runtime_status() -> Dict[str, Any]:
    policy_path = HABLA_LACE_POLICY_PATH
    policy_exists = bool(policy_path is not None and policy_path.exists())
    primary_engine = HABLA_ENGINE_CLASS_NAME == "HablaEngineV5"
    return {
        "available": HABLA_ENGINE_CLASS is not None,
        "runtime": HABLA_ENGINE_CLASS_NAME if HABLA_ENGINE_CLASS is not None else "unavailable",
        "engineVersion": HABLA_ENGINE_VERSION,
        "engineRoot": str(HABLA_ROOT),
        "engineRootExists": HABLA_ROOT.exists(),
        "primaryEngine": primary_engine,
        "status": "primary_v5" if primary_engine else "fallback_or_unavailable",
        "candidateRoots": [str(path) for path in _candidate_habla_roots()],
        "memoryPath": str(HABLA_ROOT / "memory" / "episodic_memory.jsonl"),
        "lacePolicyPath": str(policy_path) if policy_path is not None else "",
        "lacePolicyExists": policy_exists,
        "lacePolicyLoaded": bool(primary_engine and policy_exists),
        "laceRuntime": "HablaEngineV5 preflight" if primary_engine else "not_active",
        "importErrors": list(HABLA_ENGINE_IMPORT_ERRORS),
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_unique(values: Any, value: str) -> List[str]:
    result = [str(item) for item in values if str(item)] if isinstance(values, list) else []
    if value and value not in result:
        result.append(value)
    return result


def runtime_reset_urls(port: int = DEFAULT_RUNTIME_RESET_PORT, host: str = DEFAULT_RUNTIME_RESET_HOST) -> Dict[str, Any]:
    normalized_port = int(port or DEFAULT_RUNTIME_RESET_PORT)
    normalized_host = str(host or DEFAULT_RUNTIME_RESET_HOST).strip() or DEFAULT_RUNTIME_RESET_HOST
    app_url = f"http://{normalized_host}:{normalized_port}/"
    backend_url = f"{app_url}api/architecture"
    return {
        "host": normalized_host,
        "port": normalized_port,
        "appUrl": app_url,
        "backendUrl": backend_url,
    }


def schedule_runtime_reset(
    *,
    port: int = DEFAULT_RUNTIME_RESET_PORT,
    host: str = DEFAULT_RUNTIME_RESET_HOST,
    open_browser: bool = False,
) -> Dict[str, Any]:
    urls = runtime_reset_urls(port=port, host=host)
    RUNTIME_LOG_ROOT.mkdir(parents=True, exist_ok=True)

    python_bin = os.environ.get("PYTHON_BIN") or sys.executable or "/home/neurodriver/ferrari_env/bin/python"
    node_bin_dir = os.environ.get("NODE_BIN_DIR") or "/home/neurodriver/Downloads/node-v24.14.1-linux-x64/bin"
    npm_bin = os.environ.get("NPM_BIN") or str(Path(node_bin_dir) / "npm")
    backend_path = PROJECT_ROOT / "backend" / "app.py"
    backend_pid_file = PROJECT_ROOT / ".runtime" / "pids" / "backend.pid"
    frontend_pid_file = PROJECT_ROOT / ".runtime" / "pids" / "frontend.pid"
    start_script = PROJECT_ROOT / "start.sh"

    reset_script = "\n".join(
        [
            "sleep 1",
            f"pkill -f {shlex.quote(str(backend_path))} || true",
            f"rm -f {shlex.quote(str(backend_pid_file))} {shlex.quote(str(frontend_pid_file))}",
            f"cd {shlex.quote(str(PROJECT_ROOT))}",
            f"exec bash {shlex.quote(str(start_script))} start",
        ]
    )

    env = os.environ.copy()
    env.update(
        {
            "PYTHON_BIN": str(python_bin),
            "NODE_BIN_DIR": str(node_bin_dir),
            "NPM_BIN": str(npm_bin),
            "PORT": str(urls["port"]),
            "OPEN_BROWSER": "1" if open_browser else "0",
            "APP_URL": str(urls["appUrl"]),
            "BACKEND_URL": str(urls["backendUrl"]),
        }
    )

    with RUNTIME_RESET_LOG.open("a", encoding="utf-8") as reset_log:
        reset_log.write(f"[{utc_now()}] Programando restablecimiento de runtime hacia {urls['appUrl']}\n")
        subprocess.Popen(
            ["/bin/bash", "-lc", reset_script],
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=reset_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    return {
        **urls,
        "message": "Restablecimiento del runtime programado.",
        "redirectDelayMs": DEFAULT_RUNTIME_RESET_DELAY_MS,
        "logPath": str(RUNTIME_RESET_LOG),
    }


def build_habla_payload(requirement: str) -> Dict[str, Any]:
    normalized_requirement = str(requirement or "").strip()
    procedural_prompt = convert_to_habla(normalized_requirement) if convert_to_habla is not None else normalized_requirement
    memory_path = HABLA_ROOT / "memory" / "episodic_memory.jsonl"
    engine_state: Dict[str, Any] = {
        "runtime": HABLA_ENGINE_CLASS_NAME if HABLA_ENGINE_CLASS is not None else "unavailable",
        "engineVersion": HABLA_ENGINE_VERSION,
        "engineRoot": str(HABLA_ROOT),
        "memoryPath": str(memory_path),
        "lacePolicyPath": str(HABLA_LACE_POLICY_PATH) if HABLA_LACE_POLICY_PATH is not None else "",
        "laceRuntime": "HablaEngineV5 preflight" if HABLA_ENGINE_CLASS_NAME == "HablaEngineV5" else "not_active",
    }
    if HABLA_ENGINE_IMPORT_ERRORS:
        engine_state["importErrors"] = list(HABLA_ENGINE_IMPORT_ERRORS)
    payload: Dict[str, Any] = {
        "available": False,
        "prompt": procedural_prompt,
        "state": engine_state,
    }
    if not normalized_requirement:
        payload["state"]["error"] = "No hubo requerimiento legible para ejecutar el preflight HABLA."
        return payload
    if HABLA_ENGINE_CLASS is None:
        payload["state"]["error"] = "El runtime HABLA no esta disponible en esta instancia."
        return payload

    try:
        engine = _build_habla_engine(memory_path, normalized_requirement)
        state = engine.run(normalized_requirement)
    except Exception as error:  # pragma: no cover - preflight guard rail
        payload["state"]["error"] = f"Fallo el preflight HABLA: {error}"
        return payload

    payload["available"] = True
    payload["state"] = {
        **engine_state,
        "protocolText": state.protocol_text,
        "knowledgeType": state.knowledge_type,
        "toolRequired": state.tool_required,
        "strategy": state.strategy,
        "lacePolicyLoaded": bool(getattr(state, "lace_policy_loaded", False)),
        "laceDirective": getattr(state, "lace_directive", ""),
        "laceLogPath": getattr(state, "lace_log_path", ""),
        "isCompound": bool(getattr(state, "is_compound", False)),
        "compoundGoal": getattr(state, "compound_goal", ""),
        "subTasks": [
            {
                "taskId": task.task_id,
                "description": task.description,
                "toolName": task.tool_name,
                "query": task.query,
                "status": task.status,
                "resultValue": task.result_value,
                "resultText": task.result_text,
                "confidence": task.confidence,
            }
            for task in getattr(state, "sub_tasks", [])
        ],
        "triangulatedText": state.triangulated_text,
        "answerPreview": state.answer,
        "safeToAnswer": bool(state.safe_to_answer),
        "blocked": bool(state.blocked),
        "blockReason": state.block_reason,
        "directive": state.llm_directive,
        "debug": list(state.debug[-12:]),
        "sources": [
            {
                "source": evidence.source,
                "value": evidence.value,
                "text": evidence.text,
                "confidenceHint": evidence.confidence_hint,
            }
            for evidence in state.observations
        ],
        "confidence": {
            "dato": state.confidence.dato,
            "fecha": state.confidence.fecha,
            "fuente": state.confidence.fuente,
            "calculo": state.confidence.calculo,
            "inferencia": state.confidence.inferencia,
            "global": state.confidence.global_score,
        },
    }
    return payload


DEMO_GRAPH: Dict[str, Any] = {
    "metadata": {
        "projectName": "Vista IA Session Map",
        "sessionId": "turno-demo-002",
        "source": "agent_result",
        "generatedCount": 12,
        "connectionCount": 14,
        "isolatedCount": 1,
        "updatedAt": utc_now(),
        "note": "Composicion demo inspirada en un mapa tecnico por capas con archivos generados y modificados.",
    },
    "nodes": [
        {
            "id": "page-dashboard",
            "name": "page-dashboard.tsx",
            "path": "frontend/pages/",
            "layer": "frontend",
            "status": "generated",
            "size": "4.2 KB",
            "lines": 128,
            "description": "Pantalla principal que consume la sesion y monta la pagina del dashboard.",
            "imports": ["frontend/App.tsx"],
            "dependents": ["App.tsx"],
            "position": {"x": -5.85, "y": 5.95},
        },
        {
            "id": "ui-button",
            "name": "ui/Button.tsx",
            "path": "frontend/components/ui/",
            "layer": "frontend",
            "status": "generated",
            "size": "2.0 KB",
            "lines": 74,
            "description": "Boton reutilizable del sistema visual usado por la vista principal.",
            "imports": [],
            "dependents": ["App.tsx"],
            "position": {"x": 0.0, "y": 5.95},
        },
        {
            "id": "use-session",
            "name": "hooks/useSession.ts",
            "path": "frontend/hooks/",
            "layer": "frontend",
            "status": "generated",
            "size": "1.7 KB",
            "lines": 66,
            "description": "Hook que encapsula la carga y sincronizacion de la sesion desde el backend.",
            "imports": ["backend/server.py"],
            "dependents": ["App.tsx"],
            "position": {"x": 5.85, "y": 5.95},
        },
        {
            "id": "app",
            "name": "App.tsx",
            "path": "frontend/App.tsx",
            "layer": "frontend",
            "status": "modified",
            "size": "5.0 KB",
            "lines": 188,
            "description": "Shell principal que compone pagina, hook de sesion y componentes de UI.",
            "imports": ["page-dashboard.tsx", "ui/Button.tsx", "hooks/useSession.ts"],
            "dependents": [],
            "position": {"x": -2.1, "y": 4.15},
        },
        {
            "id": "index-css",
            "name": "index.css",
            "path": "frontend/index.css",
            "layer": "frontend",
            "status": "modified",
            "size": "2.8 KB",
            "lines": 140,
            "description": "Estilos base del frontend con tipografia, reseteo y tokens del tema.",
            "imports": ["shared/styles/theme.css"],
            "dependents": ["App.tsx", "hooks/useSession.ts"],
            "position": {"x": 2.15, "y": 4.15},
        },
        {
            "id": "api-sessions",
            "name": "api/routes/sessions.py",
            "path": "backend/api/routes/",
            "layer": "backend",
            "status": "generated",
            "size": "2.6 KB",
            "lines": 92,
            "description": "Define las rutas HTTP para leer y actualizar la sesion actual.",
            "imports": ["services/session_service.py"],
            "dependents": ["server.py"],
            "position": {"x": -5.85, "y": 0.75},
        },
        {
            "id": "session-service",
            "name": "services/session_service.py",
            "path": "backend/services/",
            "layer": "backend",
            "status": "generated",
            "size": "3.4 KB",
            "lines": 128,
            "description": "Concentra la logica de negocio y normaliza datos de la sesion.",
            "imports": ["shared/types/session.ts", "shared/utils/format.ts"],
            "dependents": ["api/routes/sessions.py", "server.py"],
            "position": {"x": 0.0, "y": 0.75},
        },
        {
            "id": "server",
            "name": "server.py",
            "path": "backend/",
            "layer": "backend",
            "status": "modified",
            "size": "2.2 KB",
            "lines": 77,
            "description": "Punto de entrada del backend que expone API y sincroniza el frontend.",
            "imports": ["api/routes/sessions.py", "services/session_service.py"],
            "dependents": ["hooks/useSession.ts", "index.css", "scripts/generate-types.ts"],
            "position": {"x": 5.85, "y": 0.75},
        },
        {
            "id": "types-session",
            "name": "types/session.ts",
            "path": "shared/types/",
            "layer": "shared",
            "status": "generated",
            "size": "1.1 KB",
            "lines": 36,
            "description": "Contrato compartido para la sesion usado por backend y frontend.",
            "imports": [],
            "dependents": ["services/session_service.py", "theme.css"],
            "position": {"x": -3.55, "y": -2.95},
        },
        {
            "id": "utils-format",
            "name": "utils/format.ts",
            "path": "shared/utils/",
            "layer": "shared",
            "status": "generated",
            "size": "1.6 KB",
            "lines": 54,
            "description": "Funciones compartidas para formatear texto y payloads de sesion.",
            "imports": [],
            "dependents": ["services/session_service.py"],
            "position": {"x": 3.55, "y": -2.95},
        },
        {
            "id": "theme-css",
            "name": "theme.css",
            "path": "shared/styles/",
            "layer": "style",
            "status": "generated",
            "size": "1.4 KB",
            "lines": 48,
            "description": "Variables visuales y tema base compartido por el frontend.",
            "imports": ["types/session.ts"],
            "dependents": ["index.css"],
            "position": {"x": -7.65, "y": -6.45},
        },
        {
            "id": "tsconfig",
            "name": "tsconfig.json",
            "path": "config/",
            "layer": "config",
            "status": "modified",
            "size": "0.9 KB",
            "lines": 22,
            "description": "Configuracion de TypeScript para alias, paths y resolucion de modulos.",
            "imports": [],
            "dependents": [],
            "position": {"x": 0.0, "y": -6.45},
        },
        {
            "id": "generate-types",
            "name": "scripts/generate-types.ts",
            "path": "scripts/",
            "layer": "script",
            "status": "isolated",
            "size": "1.3 KB",
            "lines": 44,
            "description": "Script auxiliar que regenera tipos desde el backend y hoy corre aislado.",
            "imports": ["backend/server.py"],
            "dependents": [],
            "position": {"x": 7.55, "y": -6.45},
        },
    ],
    "edges": [
        {
            "id": "edge-page-app",
            "from": "page-dashboard",
            "to": "app",
            "type": "reference",
            "label": "usa vista",
            "sourceAnchor": "bottom",
            "targetAnchor": "top",
            "control": {"x": -4.9, "y": 4.85},
        },
        {
            "id": "edge-button-app",
            "from": "ui-button",
            "to": "app",
            "type": "reference",
            "label": "inyecta UI",
            "sourceAnchor": "bottom",
            "targetAnchor": "top",
            "control": {"x": -0.3, "y": 4.85},
        },
        {
            "id": "edge-hook-app",
            "from": "use-session",
            "to": "app",
            "type": "reference",
            "label": "consume hook",
            "sourceAnchor": "bottom",
            "targetAnchor": "right",
            "control": {"x": 4.95, "y": 4.35},
        },
        {
            "id": "edge-index-hook",
            "from": "index-css",
            "to": "use-session",
            "type": "reference",
            "label": "estilo global",
            "sourceAnchor": "right",
            "targetAnchor": "bottom",
            "control": {"x": 8.25, "y": 4.95},
            "dashed": True,
        },
        {
            "id": "edge-index-app",
            "from": "index-css",
            "to": "app",
            "type": "reference",
            "label": "aplica tema",
            "sourceAnchor": "left",
            "targetAnchor": "right",
            "control": {"x": 1.4, "y": 4.55},
            "dashed": True,
        },
        {
            "id": "edge-app-api",
            "from": "app",
            "to": "api-sessions",
            "type": "uses",
            "label": "consulta API",
            "sourceAnchor": "bottom",
            "targetAnchor": "top",
            "control": {"x": -3.9, "y": 2.25},
        },
        {
            "id": "edge-app-service",
            "from": "app",
            "to": "session-service",
            "type": "uses",
            "label": "orquesta sesion",
            "sourceAnchor": "bottom",
            "targetAnchor": "top",
            "control": {"x": -0.8, "y": 2.2},
        },
        {
            "id": "edge-service-api",
            "from": "session-service",
            "to": "api-sessions",
            "type": "socket",
            "label": "expone servicio",
            "sourceAnchor": "left",
            "targetAnchor": "right",
            "control": {"x": -2.75, "y": 0.75},
        },
        {
            "id": "edge-service-server",
            "from": "session-service",
            "to": "server",
            "type": "socket",
            "label": "sincroniza backend",
            "sourceAnchor": "right",
            "targetAnchor": "left",
            "control": {"x": 2.75, "y": 0.75},
        },
        {
            "id": "edge-server-index",
            "from": "server",
            "to": "index-css",
            "type": "socket",
            "label": "inyecta payload",
            "sourceAnchor": "top",
            "targetAnchor": "bottom",
            "control": {"x": 5.85, "y": 2.55},
        },
        {
            "id": "edge-service-types",
            "from": "session-service",
            "to": "types-session",
            "type": "socket",
            "label": "usa contrato",
            "sourceAnchor": "bottom",
            "targetAnchor": "top",
            "control": {"x": -1.3, "y": -1.3},
        },
        {
            "id": "edge-service-format",
            "from": "session-service",
            "to": "utils-format",
            "type": "socket",
            "label": "formatea salida",
            "sourceAnchor": "bottom",
            "targetAnchor": "top",
            "control": {"x": 1.45, "y": -1.3},
        },
        {
            "id": "edge-types-theme",
            "from": "types-session",
            "to": "theme-css",
            "type": "reference",
            "label": "mapea tokens",
            "sourceAnchor": "bottom",
            "targetAnchor": "top",
            "control": {"x": -5.2, "y": -4.95},
            "dashed": True,
        },
        {
            "id": "edge-server-script",
            "from": "server",
            "to": "generate-types",
            "type": "import",
            "label": "regenera tipos",
            "sourceAnchor": "bottom",
            "targetAnchor": "top",
            "control": {"x": 6.85, "y": -3.2},
            "dashed": True,
        },
    ],
}


VALID_ANCHORS = {"top", "right", "bottom", "left"}
VALID_FLOW_TYPES = {"start", "end", "process", "decision", "io"}
VISUAL_LAYER_ORDER = ["frontend", "backend", "data", "microservice", "shared", "docs", "style", "config", "script"]
PERSISTED_WORKSPACE_FLOW_SOURCES = {"agent_live", "editor"}
PROJECT_CONTENT_FOLDERS = {"src", "backend", "frontend", "shared", "tests", "docs", "algorithms", "assets"}
VIRTUAL_WORKSPACE_CONTENT_FOLDERS = {"functions", "routes", "embedded", "deps"}
SCENE_COLUMNS = 2
SCENE_GAP_X = 1680.0
SCENE_GAP_Y = 1360.0
SCENE_BASE_X = 80.0
SCENE_BASE_Y = 80.0


def load_saved_graph_state() -> Dict[str, Any] | None:
    if EDITOR_STATE_FILE.exists():
        try:
            with EDITOR_STATE_FILE.open("r", encoding="utf-8") as state_file:
                saved_payload = json.load(state_file)
            if isinstance(saved_payload, dict):
                return saved_payload
        except json.JSONDecodeError:
            pass
    return None


def load_analysis_state() -> Dict[str, Any]:
    if ANALYSIS_STATE_FILE.exists():
        try:
            with ANALYSIS_STATE_FILE.open("r", encoding="utf-8") as state_file:
                saved_payload = json.load(state_file)
            if isinstance(saved_payload, dict):
                analyses = saved_payload.get("analyses")
                if isinstance(analyses, list):
                    return {"analyses": analyses}
        except json.JSONDecodeError:
            pass
    return {"analyses": []}


def save_analysis_state(state: Dict[str, Any]) -> None:
    payload = {"analyses": state.get("analyses") or []}
    with ANALYSIS_STATE_FILE.open("w", encoding="utf-8") as state_file:
        json.dump(payload, state_file, ensure_ascii=True, indent=2)


def is_analysis_node(node: Dict[str, Any]) -> bool:
    return str(node.get("path") or "").startswith(ANALYSIS_PATH_PREFIX)


def strip_analysis_nodes(graph: Dict[str, Any]) -> Dict[str, Any]:
    nodes = [deepcopy(node) for node in graph.get("nodes") or [] if not is_analysis_node(node)]
    valid_node_ids = {str(node.get("id") or "") for node in nodes}
    edges = [
        deepcopy(edge)
        for edge in graph.get("edges") or []
        if str(edge.get("from") or "") in valid_node_ids and str(edge.get("to") or "") in valid_node_ids
    ]
    return {
        "metadata": deepcopy(graph.get("metadata") or {}),
        "nodes": nodes,
        "edges": edges,
    }


def merge_analysis_graphs(base_graph: Dict[str, Any], analysis_state: Dict[str, Any]) -> Dict[str, Any]:
    analyses = analysis_state.get("analyses") if isinstance(analysis_state, dict) else []
    if not isinstance(analyses, list) or not analyses:
        return base_graph

    merged_nodes = [deepcopy(node) for node in base_graph.get("nodes") or []]
    merged_edges = [deepcopy(edge) for edge in base_graph.get("edges") or []]
    node_ids = {str(node.get("id") or "") for node in merged_nodes}
    edge_ids = {str(edge.get("id") or "") for edge in merged_edges}

    for analysis in analyses:
        graph = analysis.get("graph") if isinstance(analysis, dict) else None
        if not isinstance(graph, dict):
            continue

        for node in graph.get("nodes") or []:
            node_id = str(node.get("id") or "")
            if not node_id or node_id in node_ids:
                continue
            merged_nodes.append(deepcopy(node))
            node_ids.add(node_id)

        for edge in graph.get("edges") or []:
            edge_id = str(edge.get("id") or "")
            source = str(edge.get("from") or "")
            target = str(edge.get("to") or "")
            if not edge_id or edge_id in edge_ids or source not in node_ids or target not in node_ids or source == target:
                continue
            merged_edges.append(deepcopy(edge))
            edge_ids.add(edge_id)

    metadata = {
        **(base_graph.get("metadata") or {}),
    }
    metadata["analysisCount"] = len(analyses)
    if analyses:
        metadata["note"] = "Editor visual combinado con escenas de ingenieria inversa cargadas desde rutas locales."

    return {
        "metadata": metadata,
        "nodes": merged_nodes,
        "edges": merged_edges,
    }


def load_default_graph() -> Dict[str, Any]:
    base_graph = load_saved_graph_state() or build_project_graph(PROJECT_ROOT)
    return merge_analysis_graphs(base_graph, load_analysis_state())


def create_blank_view_graph() -> Dict[str, Any]:
    return {
        "metadata": {
            "projectName": "Vista en blanco",
            "source": "blank_view",
            "note": "Lienzo reiniciado manualmente. No hay nodos, flujo ni analisis cargados.",
            "generatedCount": 0,
            "connectionCount": 0,
            "isolatedCount": 0,
            "updatedAt": utc_now(),
            "blankView": True,
        },
        "nodes": [],
        "edges": [],
    }


def create_habla_architecture_demo_graph() -> Dict[str, Any]:
    graph = build_project_graph(PROJECT_ROOT)
    metadata = dict(graph.get("metadata") or {})
    metadata.update(
        {
            "projectName": "Demo arquitectura HABLA",
            "source": "habla_architecture_demo",
            "note": "Vista demo de la arquitectura interna del runtime HABLA. No crea proyectos ni ejecuta cola.",
            "demoMode": True,
            "workspaceRuntimeIsolated": True,
            "updatedAt": utc_now(),
        }
    )
    graph["metadata"] = metadata
    return graph


def save_graph_state(graph: Dict[str, Any]) -> None:
    graph = strip_analysis_nodes(graph)
    with EDITOR_STATE_FILE.open("w", encoding="utf-8") as state_file:
        json.dump(graph, state_file, ensure_ascii=True, indent=2)


def is_workspace_node(node: Dict[str, Any]) -> bool:
    return str(node.get("path") or "").startswith(WORKSPACE_PATH_PREFIX)


def is_virtual_workspace_relative_path(relative_path: str) -> bool:
    resolved = workspace_path_parts(relative_path)
    if resolved is None:
        return False

    _, remainder = resolved
    for index, part in enumerate(remainder):
        if part in VIRTUAL_WORKSPACE_CONTENT_FOLDERS and index < len(remainder) - 1:
            return True
    return False


def is_virtual_workspace_node(node: Dict[str, Any]) -> bool:
    if not is_workspace_node(node):
        return False
    if bool(node.get("virtualNode")):
        return True
    return is_virtual_workspace_relative_path(str(node.get("path") or ""))


def is_scene_managed_node(node: Dict[str, Any]) -> bool:
    path = str(node.get("path") or "")
    return path.startswith(WORKSPACE_PATH_PREFIX) or path.startswith(ANALYSIS_PATH_PREFIX)


def scene_path_parts(relative_path: str) -> tuple[str, str, List[str]] | None:
    path = PurePosixPath(normalize_relative_fragment(relative_path))
    parts = list(path.parts)
    if len(parts) < 3:
        return None
    if parts[0] == "workspace" and parts[1] == "projects":
        return "workspace", normalize_layer_name(parts[2]), parts[3:]
    if parts[0] == "analysis" and parts[1] == "projects":
        return "analysis", normalize_layer_name(parts[2]), parts[3:]
    return None


def workspace_path_parts(relative_path: str) -> tuple[str, List[str]] | None:
    resolved = scene_path_parts(relative_path)
    if resolved is None:
        return None
    _, project_slug, remainder = resolved
    return project_slug, remainder


def workspace_scene_segments(relative_path: str) -> List[str]:
    resolved = workspace_path_parts(relative_path)
    if resolved is None:
        return []

    _, remainder = resolved
    segments: List[str] = []
    for index, part in enumerate(remainder):
        if part in PROJECT_CONTENT_FOLDERS or part in VIRTUAL_WORKSPACE_CONTENT_FOLDERS:
            break
        if index == len(remainder) - 1:
            break
        segments.append(part)
    return segments


def workspace_project_for_path(relative_path: str) -> str | None:
    resolved = workspace_path_parts(relative_path)
    if resolved is None:
        return None
    return resolved[0]


def workspace_scene_key_for_path(relative_path: str) -> str | None:
    resolved = workspace_path_parts(relative_path)
    if resolved is None:
        return None

    project_slug, _ = resolved
    segments = workspace_scene_segments(relative_path)
    if not segments:
        return project_slug
    return "/".join([project_slug, *segments])


def workspace_scene_label_for_path(relative_path: str) -> str | None:
    scene_key = workspace_scene_key_for_path(relative_path)
    if not scene_key:
        return None
    return " / ".join(segment.replace("-", " ").title() for segment in scene_key.split("/"))


def infer_workspace_visual_layer(relative_path: str) -> str | None:
    resolved = workspace_path_parts(relative_path)
    if resolved is None:
        return None

    _, remainder = resolved
    scene_segments = workspace_scene_segments(relative_path)
    content_parts = remainder[len(scene_segments):]
    if not content_parts:
        return None

    root_folder = content_parts[0]
    suffix = PurePosixPath(relative_path).suffix.lower()
    if suffix == ".md":
        return "docs"
    if root_folder == "frontend":
        return "style" if suffix == ".css" else "frontend"
    if root_folder in {"functions", "routes"}:
        return "backend"
    if root_folder == "embedded":
        return "frontend"
    if root_folder == "deps":
        return "external"
    if root_folder == "backend" and len(content_parts) > 1 and content_parts[1] == "data":
        return "data"
    if root_folder in {"backend", "shared", "docs", "tests", "algorithms", "assets", "src"}:
        return root_folder
    return None


def should_prefer_workspace_layer(raw_layer: str, workspace_visual_layer: str | None, workspace_project: str | None) -> bool:
    if not workspace_visual_layer:
        return False
    normalized_project = normalize_layer_name(workspace_project or "")
    if not raw_layer or raw_layer == normalized_project:
        return True
    if workspace_visual_layer == "data" and raw_layer == "backend":
        return True
    if workspace_visual_layer == "docs" and raw_layer in {"backend", "frontend", "script", "docs"}:
        return True
    if workspace_visual_layer == "style" and raw_layer == "frontend":
        return True
    return False


def normalize_point(value: Any) -> Dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    x = value.get("x")
    y = value.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    return {"x": float(x), "y": float(y)}


def node_workspace_scene(node: Dict[str, Any]) -> str | None:
    explicit = str(node.get("workspaceScene") or "").strip()
    if explicit:
        return explicit
    return workspace_scene_key_for_path(str(node.get("path") or ""))


def node_scene_origin(node: Dict[str, Any]) -> Dict[str, float] | None:
    return normalize_point(node.get("sceneOrigin"))


def scene_origin_for_index(index: int) -> Dict[str, float]:
    return {
        "x": SCENE_BASE_X + (index % SCENE_COLUMNS) * SCENE_GAP_X,
        "y": SCENE_BASE_Y + (index // SCENE_COLUMNS) * SCENE_GAP_Y,
    }


def suggest_scene_origin(graph: Dict[str, Any], scene_key: str) -> Dict[str, float]:
    for node in graph.get("nodes") or []:
        if node_workspace_scene(node) != scene_key:
            continue
        origin = node_scene_origin(node)
        if origin is not None:
            return origin

    scene_keys: List[str] = []
    for node in graph.get("nodes") or []:
        key = node_workspace_scene(node)
        if key and key not in scene_keys:
            scene_keys.append(key)
    if scene_key not in scene_keys:
        scene_keys.append(scene_key)
    index = scene_keys.index(scene_key)
    return scene_origin_for_index(index)


def apply_workspace_scene_layout(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scene_keys: List[str] = []
    scene_origins: Dict[str, Dict[str, float]] = {}
    scene_layer_counts: Dict[tuple[str, str], int] = {}

    for node in nodes:
        if not is_scene_managed_node(node):
            continue
        scene_key = node_workspace_scene(node)
        if not scene_key:
            continue
        if scene_key not in scene_keys:
            scene_keys.append(scene_key)
        origin = node_scene_origin(node)
        if origin is not None and scene_key not in scene_origins:
            scene_origins[scene_key] = origin

    for index, scene_key in enumerate(scene_keys):
        scene_origins.setdefault(scene_key, scene_origin_for_index(index))

    adjusted_nodes: List[Dict[str, Any]] = []
    for raw_node in nodes:
        node = deepcopy(raw_node)
        if not is_scene_managed_node(node):
            adjusted_nodes.append(node)
            continue

        path = str(node.get("path") or "")
        scene_key = node_workspace_scene(node)
        if not scene_key:
            adjusted_nodes.append(node)
            continue

        origin = scene_origins[scene_key]
        node["workspaceProject"] = str(node.get("workspaceProject") or workspace_project_for_path(path) or "")
        node["workspaceScene"] = str(node.get("workspaceScene") or scene_key)
        node["workspaceSceneLabel"] = str(node.get("workspaceSceneLabel") or workspace_scene_label_for_path(path) or scene_key)

        position = normalize_point(node.get("position"))
        existing_origin = node_scene_origin(node)
        node_layer = normalize_layer_name(node.get("layer") or infer_workspace_visual_layer(path) or infer_layer(path))
        layer_index = VISUAL_LAYER_ORDER.index(node_layer) if node_layer in VISUAL_LAYER_ORDER else len(VISUAL_LAYER_ORDER)
        layer_count_key = (scene_key, node_layer)
        layer_offset = scene_layer_counts.get(layer_count_key, 0)
        scene_layer_counts[layer_count_key] = layer_offset + 1
        fallback_position = {
            "x": origin["x"] + 220.0 + layer_index * 320.0,
            "y": origin["y"] + 180.0 + layer_offset * 180.0,
        }

        if existing_origin is None:
            if position is not None:
                node["position"] = {"x": origin["x"] + position["x"], "y": origin["y"] + position["y"]}
            else:
                node["position"] = fallback_position
            node["sceneOrigin"] = origin
        elif position is not None and (position["x"] < origin["x"] or position["y"] < origin["y"]):
            # Repair nodes that were stored with scene-local coordinates after sync_file.
            node["position"] = {"x": origin["x"] + position["x"], "y": origin["y"] + position["y"]}
        elif position is None:
            node["position"] = fallback_position

        adjusted_nodes.append(node)

    return adjusted_nodes


def merge_live_workspace_graph(base_graph: Dict[str, Any], live_graph: Dict[str, Any]) -> Dict[str, Any]:
    base_nodes = base_graph.get("nodes") or []
    base_edges = base_graph.get("edges") or []
    live_nodes = live_graph.get("nodes") or []
    live_edges = live_graph.get("edges") or []

    persisted_workspace_nodes = {node.get("path"): node for node in base_nodes if is_workspace_node(node)}
    merged_nodes = [node for node in base_nodes if not is_workspace_node(node)]
    live_workspace_nodes = []
    live_workspace_paths = set()

    for live_node in live_nodes:
        if not is_workspace_node(live_node):
            continue

        live_workspace_paths.add(str(live_node.get("path") or ""))
        persisted_node = persisted_workspace_nodes.get(live_node.get("path"))
        if persisted_node:
            merged_node = {
                **live_node,
                "layer": persisted_node.get("layer") or infer_workspace_visual_layer(str(live_node.get("path") or "")) or live_node.get("layer"),
                "position": persisted_node.get("position") or live_node.get("position"),
                "color": persisted_node.get("color") or live_node.get("color"),
                "layerLabel": persisted_node.get("layerLabel") or live_node.get("layerLabel"),
                "description": persisted_node.get("description") or live_node.get("description"),
                "status": persisted_node.get("status") or live_node.get("status"),
                "workspaceProject": persisted_node.get("workspaceProject") or workspace_project_for_path(str(live_node.get("path") or "")),
                "workspaceScene": persisted_node.get("workspaceScene") or workspace_scene_key_for_path(str(live_node.get("path") or "")),
                "workspaceSceneLabel": persisted_node.get("workspaceSceneLabel") or workspace_scene_label_for_path(str(live_node.get("path") or "")),
                "sceneOrigin": persisted_node.get("sceneOrigin") or live_node.get("sceneOrigin"),
                "virtualNode": bool(persisted_node.get("virtualNode")) or is_virtual_workspace_node(persisted_node),
            }
            persisted_algorithm = persisted_node.get("algorithm")
            if isinstance(persisted_algorithm, dict) and str(persisted_algorithm.get("source") or "") in PERSISTED_WORKSPACE_FLOW_SOURCES:
                merged_node["algorithm"] = persisted_algorithm
            live_workspace_nodes.append(
                merged_node
            )
        else:
            live_workspace_nodes.append(live_node)

    for path, persisted_node in persisted_workspace_nodes.items():
        if path in live_workspace_paths or not is_virtual_workspace_node(persisted_node):
            continue
        live_workspace_nodes.append(persisted_node)

    merged_nodes.extend(live_workspace_nodes)

    valid_node_ids = {node.get("id") for node in merged_nodes}
    merged_edges = []
    seen_edge_pairs = set()

    for edge in [*base_edges, *live_edges]:
        source = edge.get("from")
        target = edge.get("to")
        if source not in valid_node_ids or target not in valid_node_ids or source == target:
            continue
        edge_pair = (source, target)
        if edge_pair in seen_edge_pairs:
            continue
        seen_edge_pairs.add(edge_pair)
        merged_edges.append(edge)

    return {
        "metadata": {
            **(base_graph.get("metadata") or {}),
            "source": "editor_with_agent_workspace",
            "note": "Editor visual combinado con archivos reales creados por el agente dentro del workspace.",
        },
        "nodes": merged_nodes,
        "edges": merged_edges,
    }


def sync_runtime_graph(save_state: bool = False) -> Dict[str, Any]:
    base_graph = load_saved_graph_state() or build_project_graph(PROJECT_ROOT)
    live_graph = build_project_graph(PROJECT_ROOT)
    merged_workspace_graph = merge_live_workspace_graph(base_graph, live_graph)
    merged_graph = normalize_graph(merge_analysis_graphs(merged_workspace_graph, load_analysis_state()))
    if save_state:
        save_graph_state(merged_graph)
    socketio.emit("architecture:update", merged_graph)
    return merged_graph


def current_graph_context() -> Dict[str, Any]:
    return normalize_graph(load_default_graph())


def summarize_analysis_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    graph = entry.get("graph") if isinstance(entry.get("graph"), dict) else {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    edges = graph.get("edges") if isinstance(graph.get("edges"), list) else []
    metadata = graph.get("metadata") if isinstance(graph.get("metadata"), dict) else {}
    primary_node_id = str(entry.get("primaryNodeId") or "")
    if not primary_node_id:
        target_path = str(entry.get("targetPath") or "")
        for node in nodes:
            if str(node.get("sourcePath") or "") == target_path:
                primary_node_id = str(node.get("id") or "")
                break
    if not primary_node_id and nodes:
        primary_node_id = str(nodes[0].get("id") or "")
    return {
        "id": str(entry.get("id") or ""),
        "label": str(entry.get("label") or entry.get("id") or "Analisis"),
        "targetPath": str(entry.get("targetPath") or ""),
        "mode": str(entry.get("mode") or metadata.get("mode") or "file"),
        "createdAt": str(entry.get("createdAt") or metadata.get("updatedAt") or ""),
        "scene": str(metadata.get("sessionId") or entry.get("id") or ""),
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "primaryNodeId": primary_node_id,
    }


def list_analysis_sessions() -> List[Dict[str, Any]]:
    state = load_analysis_state()
    analyses = state.get("analyses") if isinstance(state, dict) else []
    if not isinstance(analyses, list):
        return []
    return [summarize_analysis_entry(entry) for entry in analyses if isinstance(entry, dict)]


def upsert_analysis_entry(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    next_entries = [entry]
    save_analysis_state({"analyses": next_entries})
    return [summarize_analysis_entry(item) for item in next_entries]


def remove_analysis_entry(analysis_id: str) -> List[Dict[str, Any]]:
    state = load_analysis_state()
    analyses = state.get("analyses") if isinstance(state.get("analyses"), list) else []
    next_entries = [item for item in analyses if isinstance(item, dict) and item.get("id") != analysis_id]
    save_analysis_state({"analyses": next_entries})
    return [summarize_analysis_entry(item) for item in next_entries]


def build_agent_transcription_requirement(target_path: str) -> str:
    resolved_target = Path(target_path).expanduser().resolve()
    target_kind = "carpeta" if resolved_target.is_dir() else "archivo"
    mirror_root = f"source-mirror/{resolved_target.stem if resolved_target.is_file() else resolved_target.name}"
    return (
        f"Transcribe al editor visual el {target_kind} existente ubicado en: {resolved_target}\n\n"
        "Este no es un proyecto nuevo. Debes leer el codigo existente y representarlo fielmente dentro del sistema.\n\n"
        "Objetivos obligatorios:\n"
        "1. No inventes arquitectura nueva.\n"
        "2. No modifiques la ruta fuente original salvo que el usuario lo pida despues.\n"
        "3. Usa el bridge visual para crear el mapa conceptual y el diagrama de flujo en vivo.\n"
        "4. Sincroniza el codigo real al inspector usando `sync-file --source-path` con la ruta absoluta original.\n"
        f"5. Usa paths visuales internos bajo `{mirror_root}/...` para que el editor mantenga orden.\n"
        "6. Si la ruta es un archivo, toma ese archivo como foco principal.\n"
        "7. Si la ruta es una carpeta, prioriza entrypoints, modulos locales, handlers, rutas, eventos y archivos que realmente participan en la ejecucion.\n"
        "8. Si detectas incoherencias reales en el codigo, reportalas en la terminal y en la descripcion del nodo.\n\n"
        "Reglas de fidelidad:\n"
        "- El mapa debe reflejar imports, dependencias locales, rutas, eventos, sockets y puntos de entrada reales.\n"
        "- El flujo debe representar el script completo o la funcion principal completa, no solo el bloque final.\n"
        "- Si el archivo contiene funciones, rutas Flask, handlers Socket.IO o clases relevantes, separalos como nodos o subflujos comprensibles.\n"
        "- Si no puedes reconstruir una conexion con certeza, indica en la terminal que es una inferencia.\n\n"
        "Secuencia esperada:\n"
        f"- Primero crea la escena visual del codigo fuente bajo `{mirror_root}`.\n"
        "- Luego conecta modulos, rutas y handlers reales.\n"
        "- Luego enfoca el archivo principal y construye su flujo interno completo.\n"
        "- Despues sincroniza el codigo real desde la ruta fuente original.\n"
        "- Repite para archivos secundarios importantes.\n\n"
        "Importante:\n"
        "- Este trabajo es de transcripcion y comprension del sistema existente.\n"
        "- No conviertas esto en un scaffold nuevo.\n"
        "- No reemplaces el codigo fuente real con versiones simplificadas.\n"
    )


def suggested_repair_files(relative_path: str, issue: Dict[str, Any]) -> List[str]:
    return suggested_repair_files_service(relative_path, issue)


def build_agent_repair_requirement(
    *,
    project_slug: str,
    relative_path: str,
    issue: Dict[str, Any],
    extra_instruction: str,
) -> str:
    return build_agent_repair_requirement_service(
        project_slug=project_slug,
        relative_path=relative_path,
        issue=issue,
        extra_instruction=extra_instruction,
    )


def build_repair_validation_commands(repair_files: List[str]) -> List[str]:
    smoke_script = (Path(__file__).resolve().parent / "browser_render_smoke.py").resolve()
    return build_repair_validation_commands_service(repair_files, smoke_script_path=smoke_script)


def queue_agent_repair_task(
    *,
    project_slug: str,
    project_dir: Path,
    relative_path: str,
    repair_files: List[str],
    requirement: str,
) -> Dict[str, Any]:
    smoke_script = (Path(__file__).resolve().parent / "browser_render_smoke.py").resolve()
    return queue_agent_repair_task_service(
        project_slug=project_slug,
        project_dir=project_dir,
        relative_path=relative_path,
        repair_files=repair_files,
        requirement=requirement,
        now_provider=utc_now,
        smoke_script_path=smoke_script,
    )


def normalize_layer_name(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "script").strip().lower()).strip("-")
    return normalized or "script"


def default_layer_label(layer: str) -> str:
    return {
        "frontend": "Frontend",
        "backend": "Backend",
        "data": "Data",
        "microservice": "Microservice",
        "shared": "Shared",
        "docs": "Docs",
        "style": "Style",
        "config": "Config",
        "script": "Script",
    }.get(layer, layer.replace("-", " ").title())


def wrap_flow_label(value: Any, max_chars: int = 18, max_lines: int = 3) -> str:
    words = str(value or "").replace("_", " ").replace("/", "/ ").split()
    if not words:
        return ""

    lines: List[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or len(candidate) <= max_chars:
            current = candidate
            continue

        lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            break

    if current and len(lines) < max_lines:
        lines.append(current)

    remainder = words[len(" ".join(lines).split()):]
    if remainder and lines:
        lines[-1] = f"{lines[-1]}..."

    return "\n".join(lines[:max_lines])


def build_default_algorithm(node: Dict[str, Any]) -> Dict[str, Any]:
    imports = node.get("imports") or []
    dependents = node.get("dependents") or []

    first_import = imports[0] if imports else "flujo local"
    first_dependent = dependents[0] if dependents else "resultado final"

    return {
        "title": f"Algoritmo interno de {node.get('name') or node.get('id')}",
        "source": "fallback",
        "steps": [
            {"id": "start", "type": "start", "label": "Inicio", "x": 300, "y": 46},
            {
                "id": "input",
                "type": "io",
                "label": wrap_flow_label(f"Leer {node.get('name')}", 16, 2),
                "x": 300,
                "y": 156,
            },
            {
                "id": "process",
                "type": "process",
                "label": wrap_flow_label(node.get("description") or f"Procesar {node.get('name')}", 19, 3),
                "x": 300,
                "y": 282,
            },
            {
                "id": "decision",
                "type": "decision",
                "label": "Requiere\ncoordinacion?",
                "x": 300,
                "y": 432,
            },
            {
                "id": "sync",
                "type": "process",
                "label": wrap_flow_label(f"Coordinar con {first_import}", 17, 3),
                "x": 142,
                "y": 584,
            },
            {
                "id": "local",
                "type": "process",
                "label": wrap_flow_label(f"Preparar salida para {first_dependent}", 17, 3),
                "x": 458,
                "y": 584,
            },
            {
                "id": "output",
                "type": "io",
                "label": wrap_flow_label("Emitir resultado actualizado", 18, 3),
                "x": 300,
                "y": 742,
            },
            {"id": "end", "type": "end", "label": "Fin", "x": 300, "y": 854},
        ],
        "edges": [
            {"from": "start", "to": "input"},
            {"from": "input", "to": "process"},
            {"from": "process", "to": "decision"},
            {"from": "decision", "to": "sync", "label": "Si"},
            {"from": "decision", "to": "local", "label": "No"},
            {"from": "sync", "to": "output"},
            {"from": "local", "to": "output"},
            {"from": "output", "to": "end"},
        ],
    }


def normalize_algorithm(algorithm: Any, node: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(algorithm, dict):
        return build_default_algorithm(node)

    steps = algorithm.get("steps")
    edges = algorithm.get("edges")
    if not isinstance(steps, list) or not steps:
        return build_default_algorithm(node)
    if not isinstance(edges, list):
        edges = []

    normalized_steps = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue

        step_id = str(step.get("id") or f"step-{index}")
        step_type = str(step.get("type") or "process").lower()
        if step_type not in VALID_FLOW_TYPES:
            step_type = "process"

        x = step.get("x")
        y = step.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue

        normalized_steps.append(
            {
                "id": step_id,
                "type": step_type,
                "label": str(step.get("label") or step_id),
                "x": float(x),
                "y": float(y),
                "code": str(step.get("code") or ""),
                "codeLanguage": str(step.get("codeLanguage") or node.get("codeLanguage") or "text"),
                "color": step.get("color") if isinstance(step.get("color"), str) else None,
            }
        )

    if not normalized_steps:
        return build_default_algorithm(node)

    step_ids = {step["id"] for step in normalized_steps}
    normalized_edges = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue

        source = edge.get("from")
        target = edge.get("to")
        if source not in step_ids or target not in step_ids:
            continue

        normalized_edges.append(
            {
                "from": source,
                "to": target,
                "label": str(edge.get("label") or ""),
            }
        )

    return {
        "title": str(algorithm.get("title") or f"Algoritmo interno de {node.get('name') or node.get('id')}"),
        "source": str(algorithm.get("source") or "provided"),
        "steps": normalized_steps,
        "edges": normalized_edges,
    }


def normalize_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Acepta un grafo externo y lo normaliza para no romper el cliente."""
    cache_key = normalized_graph_cache_key(payload if isinstance(payload, dict) else {})
    cached_graph = get_cached_normalized_graph(cache_key)
    if cached_graph is not None:
        return cached_graph

    graph = deepcopy(load_default_graph())

    raw_nodes = payload.get("nodes") if isinstance(payload, dict) and "nodes" in payload else graph["nodes"]
    raw_edges = payload.get("edges") if isinstance(payload, dict) and "edges" in payload else graph["edges"]
    raw_metadata = payload.get("metadata") if isinstance(payload, dict) and "metadata" in payload else {}
    raw_issues = payload.get("issues") if isinstance(payload, dict) and isinstance(payload.get("issues"), list) else []

    nodes: List[Dict[str, Any]] = apply_workspace_scene_layout(raw_nodes if isinstance(raw_nodes, list) else graph["nodes"])
    edges: List[Dict[str, Any]] = raw_edges if isinstance(raw_edges, list) else graph["edges"]
    metadata: Dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}

    normalized_nodes = []
    for index, node in enumerate(nodes):
        node_path = str(node.get("path") or node.get("id") or f"node-{index}")
        node_id = str(node.get("id") or node_path or f"node-{index}")
        workspace_project = workspace_project_for_path(node_path)
        workspace_visual_layer = infer_workspace_visual_layer(node_path)
        raw_layer = normalize_layer_name(node.get("layer"))
        prefer_workspace_layer = should_prefer_workspace_layer(raw_layer, workspace_visual_layer, workspace_project)
        if prefer_workspace_layer:
            layer = workspace_visual_layer
        else:
            layer = raw_layer
        workspace_project_label = default_layer_label(normalize_layer_name(workspace_project or "")) if workspace_project else ""
        raw_layer_label = str(node.get("layerLabel") or "").strip()
        if prefer_workspace_layer and (not raw_layer_label or raw_layer_label == workspace_project_label):
            layer_label = default_layer_label(layer)
        else:
            layer_label = raw_layer_label or default_layer_label(layer)
        raw_color = node.get("color") if isinstance(node.get("color"), str) else None
        if prefer_workspace_layer and (not raw_color or raw_layer == normalize_layer_name(workspace_project or "")):
            color = default_color_for_layer(layer)
        else:
            color = raw_color
        position = node.get("position")
        normalized_position = None
        if isinstance(position, dict):
            x = position.get("x")
            y = position.get("y")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                normalized_position = {"x": float(x), "y": float(y)}

        normalized_node = {
            "id": node_id,
            "name": node.get("name") or node_id,
            "path": node_path,
            "sourcePath": str(node.get("sourcePath") or ""),
            "layer": layer,
            "layerLabel": layer_label,
            "status": node.get("status") or "generated",
            "size": node.get("size") or "—",
            "lines": node.get("lines") or 0,
            "description": node.get("description") or "Archivo producido o modificado por el agente.",
            "imports": node.get("imports") or [],
            "dependents": node.get("dependents") or [],
            "position": normalized_position,
            "color": color,
            "code": str(node.get("code") or ""),
            "codeLanguage": str(node.get("codeLanguage") or "text"),
            "workspaceProject": str(node.get("workspaceProject") or workspace_project_for_path(str(node.get("path") or "")) or ""),
            "workspaceScene": str(node.get("workspaceScene") or workspace_scene_key_for_path(str(node.get("path") or "")) or ""),
            "workspaceSceneLabel": str(node.get("workspaceSceneLabel") or workspace_scene_label_for_path(str(node.get("path") or "")) or ""),
            "sceneOrigin": normalize_point(node.get("sceneOrigin")),
            "readOnly": bool(node.get("readOnly")),
            "virtualNode": bool(node.get("virtualNode")) or is_virtual_workspace_relative_path(node_path),
            "analysisId": str(node.get("analysisId") or ""),
            "analysisLabel": str(node.get("analysisLabel") or ""),
        }
        normalized_node["algorithm"] = normalize_algorithm(node.get("algorithm"), normalized_node)
        normalized_nodes.append(normalized_node)

    node_ids = {node["id"] for node in normalized_nodes}
    normalized_edges = []
    for index, edge in enumerate(edges):
        source = edge.get("from")
        target = edge.get("to")
        if source in node_ids and target in node_ids and source != target:
            control = edge.get("control")
            normalized_control = None
            if isinstance(control, dict):
                x = control.get("x")
                y = control.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    normalized_control = {"x": float(x), "y": float(y)}

            source_anchor = edge.get("sourceAnchor")
            target_anchor = edge.get("targetAnchor")
            normalized_edges.append(
                {
                    "id": edge.get("id") or f"edge-{index}",
                    "from": source,
                    "to": target,
                    "type": edge.get("type") or "uses",
                    "label": edge.get("label") or "dependencia",
                    "dashed": bool(edge.get("dashed")),
                    "sourceAnchor": source_anchor if source_anchor in VALID_ANCHORS else None,
                    "targetAnchor": target_anchor if target_anchor in VALID_ANCHORS else None,
                    "control": normalized_control,
                }
            )

    connected = set()
    for edge in normalized_edges:
        connected.add(edge["from"])
        connected.add(edge["to"])

    graph = {
        "metadata": {
            **graph["metadata"],
            **metadata,
            "generatedCount": len(normalized_nodes),
            "connectionCount": len(normalized_edges),
            "isolatedCount": len([node for node in normalized_nodes if node["id"] not in connected]),
            "updatedAt": utc_now(),
        },
        "nodes": normalized_nodes,
        "edges": normalized_edges,
    }

    analysis_sessions = list_analysis_sessions() if "list_analysis_sessions" in globals() else []
    runtime = globals().get("agent_runtime")
    agent_sessions = runtime.list_sessions() if runtime is not None else []
    normalized_graph = build_architecture_ir(
        graph,
        project_root=PROJECT_ROOT,
        analysis_sessions=analysis_sessions,
        agent_sessions=agent_sessions,
        issues=raw_issues,
    )
    remember_normalized_graph(cache_key, normalized_graph)
    return normalized_graph


def normalize_relative_fragment(value: Any) -> str:
    normalized = str(PurePosixPath(os.path.normpath(str(value or ".")))).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    while normalized.startswith("../"):
        normalized = normalized[3:]
    return normalized.lstrip("/")


def lint_severity_order(value: Any) -> int:
    return {
        "error": 0,
        "warning": 1,
        "info": 2,
    }.get(str(value or "").strip().lower(), 9)


def summarize_lint_findings(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    summary = {"error": 0, "warning": 0, "info": 0, "total": len(findings)}
    for finding in findings:
        severity = str(finding.get("severity") or "info").strip().lower()
        if severity not in summary:
            summary[severity] = 0
        summary[severity] += 1
    return summary


def empty_lint_report(scene: str | None = None) -> Dict[str, Any]:
    return {
        "generatedAt": utc_now(),
        "scope": {
            "scene": scene or "",
            "label": scene.replace("-", " ").title() if scene else "Mapa completo",
        },
        "summary": {"error": 0, "warning": 0, "info": 0, "total": 0},
        "findings": [],
    }


def nearest_algorithm_step_id(node: Dict[str, Any], line: int | None) -> str:
    if not isinstance(line, int) or line <= 0:
        return ""

    algorithm = node.get("algorithm") if isinstance(node.get("algorithm"), dict) else {}
    steps = algorithm.get("steps") if isinstance(algorithm.get("steps"), list) else []
    candidates = [
        step for step in steps
        if isinstance(step, dict)
        and isinstance(step.get("line"), int)
        and int(step.get("line") or 0) > 0
        and str(step.get("id") or "") not in {"start", "end"}
    ]
    if not candidates:
        return ""

    nearest = min(candidates, key=lambda step: abs(int(step.get("line") or 0) - line))
    return str(nearest.get("id") or "")


def issue_host_node(
    issue: Dict[str, Any],
    *,
    nodes_by_id: Dict[str, Dict[str, Any]],
    nodes_by_path: Dict[str, Dict[str, Any]],
) -> Dict[str, Any] | None:
    direct_node = nodes_by_id.get(str(issue.get("nodeId") or ""))
    if direct_node is not None:
        return direct_node

    metadata = issue.get("metadata") if isinstance(issue.get("metadata"), dict) else {}
    for key in ("sourcePath", "path"):
        for candidate in (issue.get(key), metadata.get(key)):
            normalized = str(candidate or "").strip()
            if normalized and normalized in nodes_by_path:
                return nodes_by_path[normalized]
    return None


def issue_matches_lint_scope(issue: Dict[str, Any], scene_filter: str | None, host_node: Dict[str, Any] | None) -> bool:
    if not scene_filter:
        return True

    if isinstance(host_node, dict) and str(host_node.get("workspaceScene") or "") == scene_filter:
        return True

    scene_id = str(issue.get("sceneId") or "").strip()
    if scene_id.removeprefix("scene:") == scene_filter:
        return True

    source_path = str(issue.get("sourcePath") or "").strip()
    if source_path and workspace_scene_key_for_path(source_path) == scene_filter:
        return True

    return False


def semantic_issue_to_lint_finding(
    issue: Dict[str, Any],
    *,
    host_node: Dict[str, Any] | None,
) -> Dict[str, Any]:
    line_start = issue.get("lineStart")
    line = int(line_start) if isinstance(line_start, (int, float)) else None
    issue_path = str(issue.get("sourcePath") or (host_node.get("path") if isinstance(host_node, dict) else "") or "")
    scene_key = str(
        (host_node.get("workspaceScene") if isinstance(host_node, dict) else "")
        or str(issue.get("sceneId") or "").removeprefix("scene:")
        or workspace_scene_key_for_path(issue_path)
        or ""
    )
    step_id = str(issue.get("stepId") or "")
    if not step_id and isinstance(host_node, dict):
        step_id = nearest_algorithm_step_id(host_node, line)

    return {
        "severity": str(issue.get("severity") or "warning").strip().lower() or "warning",
        "code": str(issue.get("issueType") or "semantic_issue"),
        "message": str(issue.get("message") or "Issue semantico detectado."),
        "path": issue_path,
        "scene": scene_key,
        "hint": str(issue.get("suggestedAction") or ""),
        "evidence": {
            "issueId": str(issue.get("id") or ""),
            "metadata": deepcopy(issue.get("metadata") or {}),
            "evidence": list(issue.get("evidence") or []),
        },
        "line": line,
        "stepId": step_id,
        "nodeId": str((host_node.get("id") if isinstance(host_node, dict) else "") or issue.get("nodeId") or ""),
        "source": "semantic",
    }


WORKSPACE_EXTERNAL_SPECIFIER_PREFIXES = ("http://", "https://", "//", "data:", "mailto:", "tel:", "#")
WORKSPACE_JS_IMPORT_RE = re.compile(
    r"""(?mx)
    ^\s*import\s+(?:[^;]*?\s+from\s+)?["'](?P<import_from>[^"']+)["']
    |^\s*export\s+[^;]*?\s+from\s+["'](?P<export_from>[^"']+)["']
    |import\s*\(\s*["'](?P<dynamic_import>[^"']+)["']\s*\)
    """
)
WORKSPACE_HTML_SCRIPT_RE = re.compile(r"""<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>""", re.IGNORECASE)
WORKSPACE_HTML_STYLE_RE = re.compile(
    r"""<link\b[^>]*\brel=["'][^"']*stylesheet[^"']*["'][^>]*\bhref=["']([^"']+)["'][^>]*>""",
    re.IGNORECASE,
)
WORKSPACE_CSS_IMPORT_RE = re.compile(r"""@import\s+(?:url\()?["']?([^"'()]+)["']?\)?""", re.IGNORECASE)
WORKSPACE_JS_FUNCTION_RE = re.compile(
    r"^\s*(?:export\s+)?function\s+([A-Za-z_]\w*)\s*\(|^\s*(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
    re.MULTILINE,
)
WORKSPACE_IMPORT_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".css", ".html", ".md")
GENERIC_AGENT_FLOW_STEP_IDS = {"init", "render", "start", "load", "main"}
DEFAULT_WORKSPACE_FLOW_STEP_IDS = {"start", "input", "process", "decision", "sync", "local", "output", "end"}


def normalize_workspace_dependency_path(
    project_slug: str,
    source_relative_path: str,
    specifier: str,
) -> str | None:
    raw_specifier = str(specifier or "").strip()
    if not raw_specifier or raw_specifier.startswith(WORKSPACE_EXTERNAL_SPECIFIER_PREFIXES):
        return None

    if raw_specifier.startswith("/"):
        candidate = normalize_relative_fragment(raw_specifier.lstrip("/"))
    elif raw_specifier.startswith("."):
        base_dir = PurePosixPath(normalize_relative_fragment(source_relative_path)).parent
        candidate = normalize_relative_fragment(str(base_dir / raw_specifier))
    elif "/" in raw_specifier and raw_specifier.split("/", 1)[0] in {"frontend", "src", "tests", "docs", "shared", "backend", "algorithms", "assets"}:
        candidate = normalize_relative_fragment(raw_specifier)
    else:
        return None

    if not candidate:
        return None

    project_dir = workspace_project_dir(project_slug)
    direct_path = project_dir / candidate
    if direct_path.exists() and direct_path.is_file():
        return candidate

    suffix = PurePosixPath(candidate).suffix.lower()
    if not suffix:
        for extension in WORKSPACE_IMPORT_EXTENSIONS:
            extended = project_dir / f"{candidate}{extension}"
            if extended.exists() and extended.is_file():
                return normalize_relative_fragment(f"{candidate}{extension}")
            index_extended = project_dir / candidate / f"index{extension}"
            if index_extended.exists() and index_extended.is_file():
                return normalize_relative_fragment(str(PurePosixPath(candidate) / f"index{extension}"))

    return None


def infer_workspace_dependencies(
    project_slug: str,
    relative_path: str,
    code_language: str,
    code: str,
) -> List[Dict[str, str]]:
    normalized_language = str(code_language or "").strip().lower()
    dependencies: List[Dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def register(specifier: str, edge_type: str, label: str) -> None:
        target_relative_path = normalize_workspace_dependency_path(project_slug, relative_path, specifier)
        if not target_relative_path:
            return
        key = (target_relative_path, edge_type)
        if key in seen:
            return
        seen.add(key)
        dependencies.append(
            {
                "relativePath": target_relative_path,
                "edgeType": edge_type,
                "label": label,
            }
        )

    if normalized_language in {"javascript", "jsx", "typescript", "tsx", "mjs", "cjs"}:
        for match in WORKSPACE_JS_IMPORT_RE.finditer(code or ""):
            specifier = match.group("import_from") or match.group("export_from") or match.group("dynamic_import")
            if specifier:
                register(specifier, "import", "importa")
    elif normalized_language == "html":
        for specifier in WORKSPACE_HTML_SCRIPT_RE.findall(code or ""):
            register(specifier, "import", "carga modulos")
        for specifier in WORKSPACE_HTML_STYLE_RE.findall(code or ""):
            register(specifier, "style", "aplica estilos")
    elif normalized_language == "css":
        for specifier in WORKSPACE_CSS_IMPORT_RE.findall(code or ""):
            register(specifier, "style", "importa estilos")

    return dependencies


def humanize_workspace_step_label(name: str) -> str:
    normalized = re.sub(r"[_-]+", " ", str(name or "").strip())
    normalized = re.sub(r"(?<!^)(?=[A-Z])", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return "Paso"
    return normalized[:1].upper() + normalized[1:]


def normalize_workspace_step_id(name: str) -> str:
    raw_name = str(name or "").strip()
    if raw_name == "initApp":
        return "init"
    normalized = re.sub(r"(?<!^)(?=[A-Z])", "-", raw_name)
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "step"


def infer_workspace_algorithm(relative_path: str, code_language: str, code: str) -> Dict[str, Any] | None:
    normalized_language = str(code_language or "").strip().lower()
    if normalized_language not in {"javascript", "jsx", "typescript", "tsx", "mjs", "cjs"}:
        return None

    steps: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for match in WORKSPACE_JS_FUNCTION_RE.finditer(code or ""):
        function_name = match.group(1) or match.group(2)
        if not function_name:
            continue
        step_id = normalize_workspace_step_id(function_name)
        if step_id in seen_ids:
            continue
        seen_ids.add(step_id)
        line = code[: match.start()].count("\n") + 1
        lowered_name = function_name.lower()
        if lowered_name.startswith("init"):
            step_type = "start"
        elif lowered_name.startswith(("persist", "save", "load")):
            step_type = "io"
        elif lowered_name.startswith(("is", "validate")):
            step_type = "decision"
        else:
            step_type = "process"
        steps.append(
            {
                "id": step_id,
                "type": step_type,
                "label": humanize_workspace_step_label(function_name),
                "x": 300.0,
                "y": 80.0 + len(steps) * 136.0,
                "line": line,
                "code": "",
                "codeLanguage": normalized_language,
                "color": None,
            }
        )
        if len(steps) >= 8:
            break

    if len(steps) < 2:
        return None

    edges = []
    for index in range(len(steps) - 1):
        edges.append(
            {
                "from": steps[index]["id"],
                "to": steps[index + 1]["id"],
                "label": "",
            }
        )

    return {
        "title": f"Algoritmo interno de {PurePosixPath(relative_path).name}",
        "source": "real_source",
        "steps": steps,
        "edges": edges,
    }


def merge_workspace_algorithm(
    current_algorithm: Dict[str, Any] | None,
    inferred_algorithm: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not inferred_algorithm:
        return current_algorithm
    if not isinstance(current_algorithm, dict) or not current_algorithm:
        return inferred_algorithm

    current_steps = list(current_algorithm.get("steps") or [])
    current_edges = list(current_algorithm.get("edges") or [])
    current_source = str(current_algorithm.get("source") or "")
    current_ids = {str(step.get("id") or "") for step in current_steps}
    inferred_ids = {str(step.get("id") or "") for step in inferred_algorithm.get("steps") or []}
    if current_source == "fallback":
        return inferred_algorithm
    generic_default_flow = current_ids.issubset(DEFAULT_WORKSPACE_FLOW_STEP_IDS) and len(current_ids) >= 4
    sparse_agent_flow = (
        current_source == "agent_live"
        and len(current_steps) <= 2
        and all(str(step.get("id") or "") in GENERIC_AGENT_FLOW_STEP_IDS for step in current_steps)
        and len(inferred_ids) > len(current_ids)
    )
    if sparse_agent_flow or generic_default_flow:
        return inferred_algorithm

    if len(current_steps) >= len(inferred_algorithm.get("steps") or []):
        return current_algorithm

    merged = deepcopy(current_algorithm)
    merged_steps = list(current_steps)
    max_y = max((float(step.get("y") or 0.0) for step in merged_steps), default=0.0)
    for step in inferred_algorithm.get("steps") or []:
        step_id = str(step.get("id") or "")
        if not step_id or step_id in current_ids:
            continue
        next_step = deepcopy(step)
        max_y += 136.0
        next_step["y"] = max_y
        merged_steps.append(next_step)
        current_ids.add(step_id)

    merged_edges = list(current_edges)
    seen_edges = {
        (str(edge.get("from") or ""), str(edge.get("to") or ""))
        for edge in merged_edges
        if isinstance(edge, dict)
    }
    for edge in inferred_algorithm.get("edges") or []:
        edge_key = (str(edge.get("from") or ""), str(edge.get("to") or ""))
        if not all(edge_key) or edge_key in seen_edges:
            continue
        if edge_key[0] not in current_ids or edge_key[1] not in current_ids:
            continue
        merged_edges.append(deepcopy(edge))
        seen_edges.add(edge_key)

    merged["steps"] = merged_steps
    merged["edges"] = merged_edges
    merged["source"] = current_source or inferred_algorithm.get("source") or "real_source"
    return merged


def merge_lint_report_with_semantic_issues(
    report: Dict[str, Any],
    *,
    graph: Dict[str, Any],
    scene_filter: str | None,
) -> Dict[str, Any]:
    merged_report = deepcopy(report)
    findings = [deepcopy(finding) for finding in (merged_report.get("findings") or []) if isinstance(finding, dict)]
    nodes = graph.get("nodes") or []
    nodes_by_id = {str(node.get("id") or ""): node for node in nodes if isinstance(node, dict) and str(node.get("id") or "")}
    nodes_by_path: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for key in ("path", "sourcePath", "canonicalPath"):
            node_path = str(node.get(key) or "").strip()
            if node_path and node_path not in nodes_by_path:
                nodes_by_path[node_path] = node

    seen_keys = {
        (
            str(finding.get("severity") or ""),
            str(finding.get("code") or ""),
            str(finding.get("path") or ""),
            str(finding.get("nodeId") or ""),
            str(finding.get("stepId") or ""),
            int(finding.get("line")) if isinstance(finding.get("line"), (int, float)) else None,
            str(finding.get("message") or ""),
        )
        for finding in findings
    }

    for issue in graph.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        host_node = issue_host_node(issue, nodes_by_id=nodes_by_id, nodes_by_path=nodes_by_path)
        if not issue_matches_lint_scope(issue, scene_filter, host_node):
            continue

        finding = semantic_issue_to_lint_finding(issue, host_node=host_node)
        finding_key = (
            str(finding.get("severity") or ""),
            str(finding.get("code") or ""),
            str(finding.get("path") or ""),
            str(finding.get("nodeId") or ""),
            str(finding.get("stepId") or ""),
            int(finding.get("line")) if isinstance(finding.get("line"), (int, float)) else None,
            str(finding.get("message") or ""),
        )
        if finding_key in seen_keys:
            continue
        seen_keys.add(finding_key)
        findings.append(finding)

    findings.sort(key=lambda item: (lint_severity_order(item.get("severity")), str(item.get("path") or ""), str(item.get("code") or "")))
    merged_report["findings"] = findings
    merged_report["summary"] = summarize_lint_findings(findings)
    return merged_report


def workspace_graph_path(project_slug: str, relative_path: Any) -> str:
    return f"{WORKSPACE_PATH_PREFIX}{normalize_layer_name(project_slug)}/{normalize_relative_fragment(relative_path)}"


def workspace_project_dir(project_slug: str) -> Path:
    return AGENT_PROJECTS_ROOT / normalize_layer_name(project_slug)


def strip_workspace_project(graph: Dict[str, Any], project_slug: str) -> Dict[str, Any]:
    normalized_slug = normalize_layer_name(project_slug)
    if not normalized_slug:
        return graph

    project_prefix = f"{WORKSPACE_PATH_PREFIX}{normalized_slug}/"
    kept_nodes = []
    removed_ids = set()
    for node in graph.get("nodes") or []:
        if str(node.get("path") or "").startswith(project_prefix):
            removed_ids.add(node.get("id"))
            continue
        kept_nodes.append(node)

    kept_edges = []
    for edge in graph.get("edges") or []:
        if edge.get("from") in removed_ids or edge.get("to") in removed_ids:
            continue
        kept_edges.append(edge)

    return {
        "metadata": deepcopy(graph.get("metadata") or {}),
        "nodes": kept_nodes,
        "edges": kept_edges,
    }


def default_edge_label(edge_type: str) -> str:
    return {
        "socket": "sincroniza",
        "reference": "referencia",
        "import": "importa",
        "uses": "usa",
    }.get(edge_type, "conecta")


def find_node_index_by_path(graph: Dict[str, Any], node_path: str) -> int:
    for index, node in enumerate(graph.get("nodes") or []):
        if node.get("path") == node_path:
            return index
    return -1


def suggest_node_position(
    graph: Dict[str, Any],
    layer: str,
    *,
    scene_key: str | None = None,
    scene_origin: Dict[str, float] | None = None,
) -> Dict[str, float]:
    nodes = graph.get("nodes") or []
    if scene_key:
        if scene_origin is None:
            scene_origin = suggest_scene_origin(graph, scene_key)

        scene_nodes = [node for node in nodes if node_workspace_scene(node) == scene_key and isinstance(node.get("position"), dict)]
        same_layer = [node for node in scene_nodes if node.get("layer") == layer]
        if same_layer:
            anchor = same_layer[0]
            local_x = float(anchor.get("position", {}).get("x") or 0.0) - scene_origin["x"]
            local_y_values = []
            for node in same_layer:
                node_origin = node_scene_origin(node) or scene_origin
                local_y_values.append(float(node.get("position", {}).get("y") or 0.0) - node_origin["y"])
            return {"x": scene_origin["x"] + local_x, "y": scene_origin["y"] + max(local_y_values) + 180.0}

        present_layers = []
        for node in scene_nodes:
            node_layer = str(node.get("layer") or "script")
            if node_layer not in present_layers:
                present_layers.append(node_layer)

        ordered_layers = [name for name in VISUAL_LAYER_ORDER if name in present_layers]
        custom_layers = sorted(name for name in present_layers if name not in ordered_layers)
        layer_order = ordered_layers + custom_layers
        if layer not in layer_order:
            layer_order.append(layer)
        index = layer_order.index(layer)
        return {"x": scene_origin["x"] + 220.0 + index * 320.0, "y": scene_origin["y"] + 180.0}

    same_layer = [node for node in nodes if node.get("layer") == layer and isinstance(node.get("position"), dict)]
    if same_layer:
        anchor = same_layer[0]
        max_y = max(float(node.get("position", {}).get("y") or 0.0) for node in same_layer)
        x = float(anchor.get("position", {}).get("x") or 220.0)
        return {"x": x, "y": max_y + 180.0}

    present_layers = []
    for node in nodes:
        node_layer = str(node.get("layer") or "script")
        if node_layer not in present_layers:
            present_layers.append(node_layer)

    ordered_layers = [name for name in VISUAL_LAYER_ORDER if name in present_layers]
    custom_layers = sorted(name for name in present_layers if name not in ordered_layers)
    layer_order = ordered_layers + custom_layers
    if layer not in layer_order:
        layer_order.append(layer)
    index = layer_order.index(layer)
    return {"x": 220.0 + index * 320.0, "y": 180.0}


def translate_scene_position(
    graph: Dict[str, Any],
    full_path: str,
    layer: str,
    local_position: Dict[str, Any] | None,
) -> tuple[Dict[str, float], Dict[str, float] | None, str | None, str | None]:
    scene_key = workspace_scene_key_for_path(full_path)
    scene_label = workspace_scene_label_for_path(full_path)
    if not scene_key:
        if isinstance(local_position, dict):
            return local_position, None, None, None
        return suggest_node_position(graph, layer), None, None, None

    scene_origin = suggest_scene_origin(graph, scene_key)
    if isinstance(local_position, dict):
        x = local_position.get("x")
        y = local_position.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return (
                {"x": scene_origin["x"] + float(x), "y": scene_origin["y"] + float(y)},
                scene_origin,
                scene_key,
                scene_label,
            )

    suggested_position = suggest_node_position(
        graph,
        layer,
        scene_key=scene_key,
        scene_origin=scene_origin,
    )
    return suggested_position, scene_origin, scene_key, scene_label


def suggest_flow_step_position(node: Dict[str, Any]) -> Dict[str, float]:
    algorithm = node.get("algorithm") or {}
    steps = algorithm.get("steps") or []
    if not steps:
        return {"x": 300.0, "y": 220.0}
    max_y = max(float(step.get("y") or 0.0) for step in steps)
    return {"x": 300.0, "y": max_y + 150.0}


def upsert_workspace_node(graph: Dict[str, Any], payload: Dict[str, Any], *, preserve_code: bool = False) -> Dict[str, Any]:
    project_slug = str(payload.get("projectSlug") or "")
    relative_path = payload.get("relativePath")
    if not project_slug or not relative_path:
        return graph

    full_path = workspace_graph_path(project_slug, relative_path)
    node_index = find_node_index_by_path(graph, full_path)
    existing_node = graph["nodes"][node_index] if node_index >= 0 else None

    layer = normalize_layer_name(payload.get("layer") or infer_workspace_visual_layer(full_path) or infer_layer(full_path))
    node_name = str(payload.get("name") or PurePosixPath(full_path).name or full_path)
    code_language = str(payload.get("codeLanguage") or detect_code_language(full_path) or "text")
    scene_key = workspace_scene_key_for_path(full_path)
    scene_label = workspace_scene_label_for_path(full_path)
    scene_origin = node_scene_origin(existing_node or {}) if existing_node else None

    explicit_position = payload.get("position") if isinstance(payload.get("position"), dict) else None
    if existing_node and explicit_position is None and existing_node.get("position") is not None:
        next_position = existing_node.get("position")
    else:
        next_position, next_scene_origin, derived_scene_key, derived_scene_label = translate_scene_position(
            graph,
            full_path,
            layer,
            explicit_position,
        )
        scene_origin = next_scene_origin or scene_origin
        scene_key = derived_scene_key or scene_key
        scene_label = derived_scene_label or scene_label

    next_node = {
        "id": node_id_for_path(full_path),
        "name": node_name,
        "path": full_path,
        "layer": layer,
        "layerLabel": str(payload.get("layerLabel") or layer_label_for_path(full_path)),
        "status": str(payload.get("status") or (existing_node or {}).get("status") or "generated"),
        "size": str(payload.get("size") or (existing_node or {}).get("size") or "editor"),
        "lines": int(payload.get("lines") or (existing_node or {}).get("lines") or 0),
        "description": str(payload.get("description") or (existing_node or {}).get("description") or "Bloque coordinado en vivo por el agente."),
        "imports": list((existing_node or {}).get("imports") or []),
        "dependents": list((existing_node or {}).get("dependents") or []),
        "position": next_position,
        "color": payload.get("color") if isinstance(payload.get("color"), str) else (existing_node or {}).get("color") or default_color_for_layer(layer),
        "code": str((existing_node or {}).get("code") or ""),
        "codeLanguage": code_language,
        "workspaceProject": workspace_project_for_path(full_path) or project_slug,
        "workspaceScene": scene_key or "",
        "workspaceSceneLabel": scene_label or "",
        "sceneOrigin": scene_origin,
        "virtualNode": bool(payload.get("virtualNode")) or is_virtual_workspace_relative_path(full_path),
        "algorithm": deepcopy((existing_node or {}).get("algorithm") or build_default_algorithm({"name": node_name, "id": node_name, "description": payload.get("description"), "codeLanguage": code_language, "imports": [], "dependents": []})),
    }

    if existing_node and preserve_code:
        next_node["code"] = str(existing_node.get("code") or "")
        next_node["lines"] = int(existing_node.get("lines") or 0)

    if node_index >= 0:
        graph["nodes"][node_index] = normalize_graph({"nodes": [next_node], "edges": []})["nodes"][0]
    else:
        graph["nodes"].append(normalize_graph({"nodes": [next_node], "edges": []})["nodes"][0])
    return graph


def upsert_workspace_edge(graph: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    project_slug = str(payload.get("projectSlug") or "")
    from_path = payload.get("fromPath")
    to_path = payload.get("toPath")
    if not project_slug or not from_path or not to_path:
        return graph

    source_path = workspace_graph_path(project_slug, from_path)
    target_path = workspace_graph_path(project_slug, to_path)
    source_id = node_id_for_path(source_path)
    target_id = node_id_for_path(target_path)
    if source_id == target_id:
        return graph

    if find_node_index_by_path(graph, source_path) < 0 or find_node_index_by_path(graph, target_path) < 0:
        return graph

    edge_type = str(payload.get("edgeType") or "uses")
    label = str(payload.get("label") or default_edge_label(edge_type))

    existing_index = -1
    for index, edge in enumerate(graph.get("edges") or []):
        if edge.get("from") == source_id and edge.get("to") == target_id:
            existing_index = index
            break

    next_edge = {
        "id": f"edge-{source_id}-{target_id}",
        "from": source_id,
        "to": target_id,
        "type": edge_type,
        "label": label,
        "dashed": False,
    }

    if existing_index >= 0:
        graph["edges"][existing_index] = next_edge
    else:
        graph["edges"].append(next_edge)
    return graph


def upsert_flow_step(graph: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    project_slug = str(payload.get("projectSlug") or "")
    relative_path = payload.get("nodePath")
    step = payload.get("step") if isinstance(payload.get("step"), dict) else None
    if not project_slug or not relative_path or not step:
        return graph

    full_path = workspace_graph_path(project_slug, relative_path)
    node_index = find_node_index_by_path(graph, full_path)
    if node_index < 0:
        graph = upsert_workspace_node(graph, {"projectSlug": project_slug, "relativePath": relative_path})
        node_index = find_node_index_by_path(graph, full_path)
        if node_index < 0:
            return graph

    node = deepcopy(graph["nodes"][node_index])
    algorithm = deepcopy(node.get("algorithm") or build_default_algorithm(node))
    if str(algorithm.get("source") or "") != "agent_live":
        algorithm = {
            "title": f"Algoritmo interno de {node.get('name') or node.get('id')}",
            "source": "agent_live",
            "steps": [],
            "edges": [],
        }
    else:
        algorithm["source"] = "agent_live"
    step_list = algorithm.get("steps") or []

    position = {
        "x": float(step.get("x")) if isinstance(step.get("x"), (int, float)) else suggest_flow_step_position(node)["x"],
        "y": float(step.get("y")) if isinstance(step.get("y"), (int, float)) else suggest_flow_step_position(node)["y"],
    }

    next_step = {
        "id": str(step.get("id") or f"step-{len(step_list) + 1}"),
        "type": str(step.get("type") or "process"),
        "label": str(step.get("label") or "Nuevo bloque"),
        "x": position["x"],
        "y": position["y"],
        "code": str(step.get("code") or ""),
        "codeLanguage": str(step.get("codeLanguage") or node.get("codeLanguage") or "text"),
        "color": str(step.get("color")) if isinstance(step.get("color"), str) else None,
    }

    replaced = False
    updated_steps = []
    for current in step_list:
        if current.get("id") == next_step["id"]:
            updated_steps.append(next_step)
            replaced = True
        else:
            updated_steps.append(current)
    if not replaced:
        updated_steps.append(next_step)

    algorithm["steps"] = updated_steps
    algorithm["edges"] = algorithm.get("edges") or []
    node["algorithm"] = normalize_algorithm(algorithm, node)
    graph["nodes"][node_index] = node
    return graph


def upsert_flow_edge(graph: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    project_slug = str(payload.get("projectSlug") or "")
    relative_path = payload.get("nodePath")
    source_step = payload.get("fromStep")
    target_step = payload.get("toStep")
    if not project_slug or not relative_path or not source_step or not target_step:
        return graph

    full_path = workspace_graph_path(project_slug, relative_path)
    node_index = find_node_index_by_path(graph, full_path)
    if node_index < 0:
        return graph

    node = deepcopy(graph["nodes"][node_index])
    algorithm = deepcopy(node.get("algorithm") or build_default_algorithm(node))
    algorithm["source"] = "agent_live"
    steps = algorithm.get("steps") or []
    step_ids = {step.get("id") for step in steps}
    if source_step not in step_ids or target_step not in step_ids:
        return graph

    next_edge = {
        "from": str(source_step),
        "to": str(target_step),
        "label": str(payload.get("label") or ""),
    }
    updated_edges = []
    replaced = False
    for current in algorithm.get("edges") or []:
        if current.get("from") == next_edge["from"] and current.get("to") == next_edge["to"]:
            updated_edges.append(next_edge)
            replaced = True
        else:
            updated_edges.append(current)
    if not replaced:
        updated_edges.append(next_edge)

    algorithm["edges"] = updated_edges
    node["algorithm"] = normalize_algorithm(algorithm, node)
    graph["nodes"][node_index] = node
    return graph


def sync_workspace_file(graph: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    project_slug = str(payload.get("projectSlug") or "")
    relative_path = payload.get("relativePath")
    if not project_slug or not relative_path:
        return graph

    source_reference = str(payload.get("sourcePath") or relative_path)
    absolute_source_path = Path(source_reference) if Path(source_reference).is_absolute() else workspace_project_dir(project_slug) / normalize_relative_fragment(source_reference)

    graph = upsert_workspace_node(graph, payload)

    full_path = workspace_graph_path(project_slug, relative_path)
    node_index = find_node_index_by_path(graph, full_path)
    if node_index < 0:
        return graph

    node = deepcopy(graph["nodes"][node_index])
    if absolute_source_path.exists() and absolute_source_path.is_file():
        try:
            code = absolute_source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            code = ""
        node["code"] = code
        node["lines"] = max(1, len(code.splitlines())) if code else 0
        node["size"] = f"{max(1, absolute_source_path.stat().st_size / 1024):.1f} KB"
        if code:
            inferred_algorithm = infer_workspace_algorithm(relative_path, str(node.get("codeLanguage") or ""), code)
            node["algorithm"] = normalize_algorithm(
                merge_workspace_algorithm(
                    node.get("algorithm") if isinstance(node.get("algorithm"), dict) else None,
                    inferred_algorithm,
                ) or build_default_algorithm(node),
                node,
            )
    node["status"] = str(payload.get("status") or "modified")
    if payload.get("description"):
        node["description"] = str(payload.get("description"))
    if payload.get("codeLanguage"):
        node["codeLanguage"] = str(payload.get("codeLanguage"))
    if isinstance(payload.get("position"), dict):
        translated_position, _, _, _ = translate_scene_position(
            graph,
            full_path,
            str(node.get("layer") or infer_workspace_visual_layer(full_path) or "script"),
            payload["position"],
        )
        node["position"] = translated_position
    graph["nodes"][node_index] = node

    inferred_dependencies = infer_workspace_dependencies(
        project_slug,
        normalize_relative_fragment(relative_path),
        str(node.get("codeLanguage") or ""),
        str(node.get("code") or ""),
    ) if str(node.get("code") or "") else []
    for dependency in inferred_dependencies:
        graph = upsert_workspace_node(
            graph,
            {
                "projectSlug": project_slug,
                "relativePath": dependency["relativePath"],
            },
            preserve_code=True,
        )
        graph = upsert_workspace_edge(
            graph,
            {
                "projectSlug": project_slug,
                "fromPath": normalize_relative_fragment(relative_path),
                "toPath": dependency["relativePath"],
                "edgeType": dependency["edgeType"],
                "label": dependency["label"],
            },
        )
    return graph


def consume_agent_visual_event(payload: Dict[str, Any]) -> None:
    op = str((payload or {}).get("op") or "").strip().lower()
    visual_payload = {
        "op": op,
        "sessionId": payload.get("sessionId"),
        "projectSlug": payload.get("projectSlug"),
        "message": payload.get("message"),
        "phase": payload.get("phase"),
        "status": payload.get("status"),
        "errorCode": payload.get("errorCode"),
    }
    for key in ("relativePath", "sourcePath", "nodePath", "fromPath", "toPath", "focusPath", "focusNodeId", "stepId"):
        if payload.get(key):
            visual_payload[key] = payload.get(key)

    observer = globals().get("observer_plane")
    if observer is not None:
        try:
            observer.record_external_event(visual_payload)
        except Exception:
            pass

    if op in CLOSED_AGENT_VISUAL_OPS:
        disable_observer_after_runtime_closed(
            f"Observer Plane apagado automaticamente por cierre de runtime: {op}.",
            visual_payload,
        )

    if op in {
        "session_start",
        "phase",
        "heartbeat",
        *CLOSED_AGENT_VISUAL_OPS,
    }:
        socketio.emit("agent:visual", visual_payload)
        return

    graph = normalize_graph(load_default_graph())
    focus_path = None

    if op == "upsert_node":
        graph = upsert_workspace_node(graph, payload)
        focus_path = workspace_graph_path(str(payload.get("projectSlug") or ""), payload.get("relativePath"))
    elif op == "upsert_edge":
        graph = upsert_workspace_edge(graph, payload)
        focus_path = workspace_graph_path(str(payload.get("projectSlug") or ""), payload.get("fromPath"))
    elif op == "focus_node":
        focus_path = workspace_graph_path(str(payload.get("projectSlug") or ""), payload.get("relativePath"))
    elif op == "upsert_flow_step":
        graph = upsert_flow_step(graph, payload)
        focus_path = workspace_graph_path(str(payload.get("projectSlug") or ""), payload.get("nodePath"))
        visual_payload["stepId"] = ((payload.get("step") or {}).get("id"))
    elif op == "upsert_flow_edge":
        graph = upsert_flow_edge(graph, payload)
        focus_path = workspace_graph_path(str(payload.get("projectSlug") or ""), payload.get("nodePath"))
    elif op == "sync_file":
        graph = sync_workspace_file(graph, payload)
        focus_path = workspace_graph_path(str(payload.get("projectSlug") or ""), payload.get("relativePath"))
    else:
        return

    if op != "focus_node":
        graph = normalize_graph(graph)
        save_graph_state(graph)
        socketio.emit("architecture:update", graph)

    if focus_path:
        visual_payload["focusPath"] = focus_path
        visual_payload["focusNodeId"] = node_id_for_path(focus_path)
    socketio.emit("agent:visual", visual_payload)


def emit_agent_session(payload: Dict[str, Any]) -> None:
    session_payload = dict(payload or {})
    socketio.emit("agent:session", session_payload)
    status = str(session_payload.get("status") or "").lower()
    if status in CLOSED_AGENT_SESSION_STATUSES:
        disable_observer_after_runtime_closed(
            f"Observer Plane apagado automaticamente porque la sesion quedo {status}.",
            {
                "sessionId": session_payload.get("sessionId"),
                "projectSlug": session_payload.get("projectSlug"),
                "status": status,
            },
        )


agent_runtime = AgentRuntime(
    app_root=PROJECT_ROOT,
    workspace_root=AGENT_WORKSPACE_ROOT,
    projects_root=AGENT_PROJECTS_ROOT,
    codex_cmd=os.environ.get("CODEX_CMD", "codex"),
    prompt_converter=build_habla_payload,
    graph_provider=current_graph_context,
    graph_sync=sync_runtime_graph,
    terminal_emitter=lambda payload: socketio.emit("agent:terminal", payload),
    session_emitter=emit_agent_session,
    visual_event_handler=consume_agent_visual_event,
    reviewer_event_handler=lambda payload: socketio.emit("agent:reviewer", payload),
    lace_policy_source=HABLA_LACE_POLICY_PATH,
)

OBSERVER_STOP_EVENT = threading.Event()
OBSERVER_START_LOCK = threading.Lock()
observer_background_started = False



observer_runtime_facade = ObserverRuntimeFacade(
    projects_root_provider=lambda: AGENT_PROJECTS_ROOT,
    workspace_project_dir=lambda project_slug: workspace_project_dir(project_slug),
    normalize_project_slug=lambda value: normalize_layer_name(value),
    normalize_graph=lambda payload: normalize_graph(payload),
    load_default_graph=lambda: load_default_graph(),
    load_json_file=lambda path, fallback: load_json_file(path, fallback),
    list_sessions=lambda: agent_runtime.list_sessions(),
    lint_graph=lint_graph,
    merge_lint_report=lambda report, **kwargs: merge_lint_report_with_semantic_issues(report, **kwargs),
    build_integrity_report=lambda project_slug, project_dir, persist=False: build_file_integrity_report(
        project_slug,
        project_dir,
        persist=persist,
    ),
    project_root=PROJECT_ROOT,
    active_session_statuses=ACTIVE_AGENT_SESSION_STATUSES,
    code_scanner_report_name=CODE_SCANNER_REPORT_NAME,
    typewriter_report_name=TYPEWRITER_REPORT_NAME,
    agent_file_manifest_name=AGENT_FILE_MANIFEST_NAME,
    file_integrity_report_name=FILE_INTEGRITY_REPORT_NAME,
    observer_findings_report_name=OBSERVER_FINDINGS_REPORT_NAME,
    sandbox_state_name=SANDBOX_STATE_NAME,
    now_provider=lambda: utc_now(),
)

active_observer_project_slug = observer_runtime_facade.active_project_slug
latest_workspace_project_slug = observer_runtime_facade.latest_workspace_project_slug
build_observer_project_runtime_snapshot = observer_runtime_facade.build_project_runtime_snapshot
build_observer_snapshot = observer_runtime_facade.build_snapshot

def emit_observer_event(payload: Dict[str, Any]) -> None:
    event = {key: value for key, value in dict(payload or {}).items() if value is not None}
    socketio.emit("agent:observer", event)
    socketio.emit("agent:visual", event)


observer_plane = ObserverPlane(
    snapshot_provider=build_observer_snapshot,
    event_handler=emit_observer_event,
    config=ObserverConfig(
        poll_seconds=float(os.environ.get("OBSERVER_PLANE_POLL_SECONDS", "6")),
        min_emit_interval_seconds=float(os.environ.get("OBSERVER_PLANE_MIN_EMIT_SECONDS", "2")),
        idle_emit_interval_seconds=float(os.environ.get("OBSERVER_PLANE_IDLE_EMIT_SECONDS", "25")),
        max_incident_runtime_seconds=float(os.environ.get("OBSERVER_INCIDENT_MAX_RUNTIME_SECONDS", "180")),
        max_incident_ticks=int(os.environ.get("OBSERVER_INCIDENT_MAX_TICKS", "30")),
        max_repeated_events=int(os.environ.get("OBSERVER_MAX_REPEATED_EVENTS", "3")),
        incident_cooldown_seconds=float(os.environ.get("OBSERVER_INCIDENT_COOLDOWN_SECONDS", "60")),
    ),
    memory_path=OBSERVER_MEMORY_FILE,
    timeline_path=OBSERVER_TIMELINE_FILE,
    behavior_path=OBSERVER_BEHAVIOR_FILE,
    incident_dir=OBSERVER_INCIDENT_DIR,
)
observer_plane.enabled = False


def _read_email_command_config_file() -> Dict[str, Any]:
    if not EMAIL_COMMAND_CONFIG_FILE.exists():
        return {}
    try:
        payload = json.loads(EMAIL_COMMAND_CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_email_command_config_file(payload: Dict[str, Any]) -> None:
    EMAIL_COMMAND_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    EMAIL_COMMAND_CONFIG_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    try:
        EMAIL_COMMAND_CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def _bool_config(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si"}


def _int_config(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sender_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return tuple(sender.strip() for sender in str(value or "").split(",") if sender.strip())


def build_email_command_config(overrides: Dict[str, Any] | None = None) -> EmailCommandConfig:
    saved = _read_email_command_config_file()
    if overrides:
        saved.update({key: value for key, value in overrides.items() if value is not None})
    default_mode = str(saved.get("defaultRuntimeMode") or os.environ.get("HABLA_EMAIL_DEFAULT_MODE", "long-run")).strip()
    if default_mode not in {"smoke", "build", "medium", "long-run"}:
        default_mode = "long-run"
    return EmailCommandConfig(
        enabled=_bool_config(saved.get("enabled"), os.environ.get("HABLA_EMAIL_COMMANDS_ENABLED", "0").lower() in {"1", "true", "yes", "on"}),
        subject_prefix=str(saved.get("subjectPrefix") or os.environ.get("HABLA_EMAIL_SUBJECT_PREFIX", "[HABLA]")),
        allowed_senders=_sender_list(saved.get("allowedSenders", os.environ.get("HABLA_EMAIL_ALLOWED_SENDERS", ""))),
        command_token=str(saved.get("commandToken") if saved.get("commandToken") is not None else os.environ.get("HABLA_EMAIL_COMMAND_TOKEN", "")),
        default_runtime_mode=default_mode,
        max_body_chars=_int_config(saved.get("maxBodyChars"), _int_config(os.environ.get("HABLA_EMAIL_MAX_BODY_CHARS"), 20000)),
        imap_host=str(saved.get("imapHost") or os.environ.get("HABLA_EMAIL_IMAP_HOST", "")),
        imap_port=_int_config(saved.get("imapPort"), _int_config(os.environ.get("HABLA_EMAIL_IMAP_PORT"), 993)),
        imap_username=str(saved.get("imapUsername") or os.environ.get("HABLA_EMAIL_IMAP_USERNAME", "")),
        imap_password=str(saved.get("imapPassword") if saved.get("imapPassword") is not None else os.environ.get("HABLA_EMAIL_IMAP_PASSWORD", "")),
        imap_mailbox=str(saved.get("imapMailbox") or os.environ.get("HABLA_EMAIL_IMAP_MAILBOX", "INBOX")),
        imap_ssl=_bool_config(saved.get("imapSsl"), os.environ.get("HABLA_EMAIL_IMAP_SSL", "1").lower() not in {"0", "false", "no"}),
    )


def update_email_command_config_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = email_command_plane.public_config()
    existing = _read_email_command_config_file()
    next_payload = {
        "enabled": _bool_config(payload.get("enabled"), bool(current.get("enabled"))),
        "subjectPrefix": str(payload.get("subjectPrefix") or current.get("subjectPrefix") or "[HABLA]"),
        "allowedSenders": _sender_list(payload.get("allowedSenders", current.get("allowedSenders", []))),
        "commandToken": str(payload.get("commandToken") if payload.get("commandToken") is not None else current.get("commandToken", "")),
        "defaultRuntimeMode": str(payload.get("defaultRuntimeMode") or current.get("defaultRuntimeMode") or "long-run"),
        "maxBodyChars": _int_config(payload.get("maxBodyChars"), _int_config(current.get("maxBodyChars"), 20000)),
        "imapHost": str(payload.get("imapHost") or ""),
        "imapPort": _int_config(payload.get("imapPort"), 993),
        "imapUsername": str(payload.get("imapUsername") or ""),
        "imapPassword": str(payload.get("imapPassword") if payload.get("imapPassword") not in {None, ""} else existing.get("imapPassword", "")),
        "imapMailbox": str(payload.get("imapMailbox") or "INBOX"),
        "imapSsl": _bool_config(payload.get("imapSsl"), True),
    }
    if next_payload["defaultRuntimeMode"] not in {"smoke", "build", "medium", "long-run"}:
        next_payload["defaultRuntimeMode"] = "long-run"
    _write_email_command_config_file(next_payload)
    email_command_plane.update_config(build_email_command_config())
    return email_command_plane.public_config()


email_command_plane = EmailCommandPlane(
    EMAIL_COMMAND_ROOT,
    build_email_command_config(),
)
EMAIL_COMMAND_STOP_EVENT = threading.Event()
EMAIL_COMMAND_START_LOCK = threading.Lock()
email_command_dispatcher_started = False


def start_observer_plane() -> None:
    global observer_background_started
    with OBSERVER_START_LOCK:
        if observer_background_started:
            return
        observer_background_started = True
        socketio.start_background_task(observer_plane.run_forever, OBSERVER_STOP_EVENT, socketio.sleep)


def observe_with_tool_event(
    op: str,
    *,
    project_slug: str = "",
    reason: str = "",
    persistent: bool = False,
) -> Dict[str, Any] | None:
    previous_enabled = bool(observer_plane.enabled)
    observer_plane.enabled = True
    try:
        observer_plane.record_external_event(
            {
                "op": str(op or "observe_now"),
                "projectSlug": str(project_slug or ""),
                "reason": str(reason or ""),
                "source": "observer_tool_event",
                "timestamp": utc_now(),
            }
        )
        if persistent:
            start_observer_plane()
        return observer_plane.observe_once(force=True)
    except Exception as error:
        return {
            "op": "observer_tool_error",
            "source": "observer_tool_event",
            "projectSlug": str(project_slug or ""),
            "requestedOp": str(op or "observe_now"),
            "error": str(error),
            "timestamp": utc_now(),
        }
    finally:
        if not persistent and not observer_manual_pin_enabled() and not active_agent_session_exists():
            observer_plane.enabled = previous_enabled


def active_agent_session_exists() -> bool:
    return any(str(session.get("status") or "").lower() in ACTIVE_AGENT_SESSION_STATUSES for session in agent_runtime.list_sessions())


def read_observer_manual_pin() -> Dict[str, Any]:
    if not OBSERVER_MANUAL_PIN_FILE.exists():
        return {"enabled": False}
    try:
        payload = json.loads(OBSERVER_MANUAL_PIN_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False}
    return payload if isinstance(payload, dict) else {"enabled": False}


def write_observer_manual_pin(enabled: bool, *, source: str = "", reason: str = "") -> Dict[str, Any]:
    payload = {
        "enabled": bool(enabled),
        "source": str(source or "runtime"),
        "reason": str(reason or ""),
        "updatedAt": utc_now(),
    }
    OBSERVER_MANUAL_PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    OBSERVER_MANUAL_PIN_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return payload


def observer_manual_pin_enabled() -> bool:
    return bool(read_observer_manual_pin().get("enabled"))


def observer_request_is_human_pinned(payload: Dict[str, Any]) -> bool:
    source = str(payload.get("source") or "").strip().lower()
    return bool(payload.get("allowIdle") or payload.get("humanPinned") or source in {"human", "manual", "ui", "button"})


def apply_observer_enabled_request(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    requested_enabled = bool(payload.get("enabled", True))
    manual_request = observer_request_is_human_pinned(payload)
    source = str(payload.get("source") or ("human" if manual_request else "runtime"))
    reason = str(payload.get("reason") or "")

    if requested_enabled and manual_request:
        write_observer_manual_pin(True, source=source, reason=reason or "Activacion humana desde UI/API.")
    elif not requested_enabled:
        write_observer_manual_pin(False, source=source, reason=reason or "Desactivado por usuario o runtime.")

    if requested_enabled and not active_agent_session_exists() and not observer_manual_pin_enabled():
        observer_plane.enabled = False
        return {
            "ok": True,
            "enabled": False,
            "state": observer_plane.context.state,
            "observer": observer_status_payload(),
            "message": "Observer Plane no se activo porque no hay sesion activa de runtime.",
            "reason": "no_active_runtime_session",
        }

    observer_plane.enabled = requested_enabled
    event = None
    if observer_plane.enabled:
        start_observer_plane()
        event = observer_plane.observe_once(force=True)

    return {
        "ok": True,
        "enabled": observer_plane.enabled,
        "state": observer_plane.context.state,
        "observer": observer_status_payload(),
        "event": event,
        "message": "Observer Plane activado por humano." if observer_plane.enabled and observer_manual_pin_enabled() else (
            "Observer Plane activado." if observer_plane.enabled else "Observer Plane desactivado por el usuario."
        ),
    }


def emit_email_command_event(op: str, command: Dict[str, Any] | None = None, **extra: Any) -> None:
    payload = {
        "op": op,
        "source": "email_command_plane",
        "command": command,
        "status": command.get("status") if isinstance(command, dict) else extra.get("status"),
        "message": extra.get("message") or "",
        "emailStatus": email_command_plane.status(),
    }
    payload.update({key: value for key, value in extra.items() if value is not None})
    socketio.emit("agent:email_command", payload)


def dispatch_next_email_command() -> Dict[str, Any]:
    command = email_command_plane.next_pending()
    if command is None:
        return {"ok": True, "status": "idle", "message": "No hay correos pendientes."}
    if active_agent_session_exists():
        emit_email_command_event(
            "email_command_waiting",
            command,
            message="Correo recibido, esperando que termine la sesion activa antes de ejecutar.",
        )
        return {"ok": True, "status": "waiting_active_session", "command": command}

    starting = email_command_plane.mark_command(command["id"], "starting")
    emit_email_command_event(
        "email_command_starting",
        starting or command,
        message="Correo autorizado: llenando requerimiento y arrancando proyecto nuevo.",
    )
    try:
        session = agent_runtime.start_session(
            requirement=str(command.get("requirement") or ""),
            project_name=str(command.get("projectName") or command.get("projectSlug") or ""),
            project_slug=str(command.get("projectSlug") or "") or None,
            bootstrap=bool(command.get("bootstrapProject", False)),
            ensure_new_project=bool(command.get("ensureNewProject", True)),
            mode=str(command.get("runtimeMode") or "long-run"),
        )
        sync_runtime_graph(save_state=True)
        projects = list_agent_projects_snapshot()
        socketio.emit("agent:projects", {"projects": projects})
        started = email_command_plane.mark_command(command["id"], "started", sessionId=session.get("sessionId"))
        emit_email_command_event(
            "email_command_started",
            started or command,
            session=session,
            projects=projects,
            message="Proyecto iniciado desde correo ejecutable.",
        )
        return {"ok": True, "status": "started", "command": started or command, "session": session, "projects": projects}
    except Exception as error:
        failed = email_command_plane.mark_command(command["id"], "failed", error=str(error))
        emit_email_command_event(
            "email_command_failed",
            failed or command,
            error=str(error),
            message="No fue posible ejecutar el correo recibido.",
        )
        return {"ok": False, "status": "failed", "command": failed or command, "error": str(error)}


def email_command_dispatch_loop(stop_event: Any = None, sleep_fn: Any = None) -> None:
    sleep = sleep_fn or socketio.sleep
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        poll_result = email_command_plane.poll_imap_once()
        if poll_result.get("imported"):
            emit_email_command_event(
                "email_command_imported",
                None,
                status="imported",
                message=f"IMAP importo {poll_result.get('imported')} correo(s) ejecutable(s).",
            )
        dispatch_next_email_command()
        sleep(max(1.0, float(os.environ.get("HABLA_EMAIL_DISPATCH_SECONDS", "5"))))


def start_email_command_dispatcher() -> None:
    global email_command_dispatcher_started
    with EMAIL_COMMAND_START_LOCK:
        if email_command_dispatcher_started:
            return
        email_command_dispatcher_started = True
        socketio.start_background_task(email_command_dispatch_loop, EMAIL_COMMAND_STOP_EVENT, socketio.sleep)


def lightweight_observer_status_payload(error: str | None = None) -> Dict[str, Any]:
    context = getattr(observer_plane, "context", None)
    try:
        behavior_tree = observer_plane.behavior_tree.to_dict()
    except Exception:
        behavior_tree = {}
    try:
        memory = observer_plane.memory.summary("")
    except Exception:
        memory = {}
    try:
        incident = observer_plane._incident_status()
    except Exception:
        incident = None
    status: Dict[str, Any] = {
        "enabled": bool(getattr(observer_plane, "enabled", False)),
        "state": str(getattr(context, "state", "idle") or "idle"),
        "tickCount": int(getattr(context, "tick_count", 0) or 0),
        "behaviorTree": behavior_tree,
        "activeProjectSlug": "",
        "memory": memory if isinstance(memory, dict) else {},
        "timeline": [],
        "incident": incident,
        "lightweight": True,
    }
    if error:
        status["degraded"] = True
        status["warning"] = f"observer_status_degraded: {error}"
    return status


def observer_status_payload(*, full: bool = False) -> Dict[str, Any]:
    if full:
        try:
            status = observer_plane.status()
        except Exception as error:
            status = lightweight_observer_status_payload(str(error))
    else:
        status = lightweight_observer_status_payload()
    manual_pin = read_observer_manual_pin()
    human_pinned = bool(manual_pin.get("enabled"))
    status["runtimePath"] = str(OBSERVER_ROOT)
    status["memoryPath"] = str(OBSERVER_MEMORY_FILE)
    status["timelinePath"] = str(OBSERVER_TIMELINE_FILE)
    status["behaviorPath"] = str(OBSERVER_BEHAVIOR_FILE)
    status["manualPinPath"] = str(OBSERVER_MANUAL_PIN_FILE)
    status["humanPinned"] = human_pinned
    status["manualPin"] = manual_pin
    status["mode"] = "human-pinned" if human_pinned else "runtime-bound"
    return status


def disable_observer_after_runtime_closed(reason: str, source_payload: Dict[str, Any] | None = None) -> None:
    observer = globals().get("observer_plane")
    if observer is None:
        return
    source_payload = source_payload if isinstance(source_payload, dict) else {}
    if observer_manual_pin_enabled():
        observer.enabled = True
        observer.context.recent_external_event = None
        observer.context.last_signature = ""
        observer.context.last_event_at = 0.0
        observer.context.state = "idle"
        start_observer_plane()
        observer.observe_once(force=True)
        socketio.emit(
            "agent:observer",
            {
                "op": "observer_auto_disable_skipped",
                "enabled": True,
                "state": observer.context.state,
                "observer": observer_status_payload(),
                "sessionId": source_payload.get("sessionId"),
                "projectSlug": source_payload.get("projectSlug"),
                "message": f"{reason} Modo autonomo humano sigue activo para inspeccion visual real.",
            },
        )
        return
    was_enabled = bool(getattr(observer, "enabled", False))
    observer.enabled = False
    observer.context.recent_external_event = None
    observer.context.last_signature = ""
    observer.context.last_event_at = 0.0
    observer.context.state = "idle"
    if not was_enabled:
        return
    socketio.emit(
        "agent:observer",
        {
            "op": "observer_auto_disabled",
            "enabled": False,
            "state": observer.context.state,
            "observer": observer_status_payload(),
            "sessionId": source_payload.get("sessionId"),
            "projectSlug": source_payload.get("projectSlug"),
            "message": reason,
        },
    )


def execute_observer_safe_action(action_id: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    normalized_action = str(action_id or "").strip()
    if normalized_action == "refresh_graph":
        graph = sync_runtime_graph(save_state=True)
        event = observer_plane.observe_once(force=True)
        return {"ok": True, "action": normalized_action, "graph": graph, "event": event}
    if normalized_action == "audit_map":
        scene = str(payload.get("scene") or payload.get("projectSlug") or "").strip() or None
        graph = normalize_graph(load_default_graph())
        report = lint_graph(graph, PROJECT_ROOT, scene_filter=scene)
        report = merge_lint_report_with_semantic_issues(report, graph=graph, scene_filter=scene)
        socketio.emit("agent:observer", {
            "op": "observer_safe_action",
            "action": normalized_action,
            "status": "completed",
            "message": f"Observer reaudito mapa: {report.get('summary', {}).get('total', 0)} hallazgo(s).",
            "report": report,
        })
        return {"ok": True, "action": normalized_action, "report": report}
    if normalized_action == "prepare_repair":
        event = {
            "op": "observer_authorization_required",
            "source": "observer_plane",
            "action": normalized_action,
            "status": "waiting_human",
            "message": "Observer preparo reparacion. Requiere autorizacion humana desde el editor.",
            "projectSlug": payload.get("projectSlug"),
            "relativePath": payload.get("path") or payload.get("relativePath"),
            "focusPath": payload.get("focusPath"),
            "line": payload.get("line"),
            "code": payload.get("code"),
            "reason": "El observer nunca lanza reparacion destructiva sin permiso humano.",
        }
        socketio.emit("agent:observer", event)
        socketio.emit("agent:visual", event)
        return {"ok": True, "action": normalized_action, "event": event}
    return {"ok": False, "error": "unsupported_observer_action", "action": normalized_action}


@app.get("/api/architecture")
def get_architecture():
    return jsonify(normalize_graph(load_default_graph()))


@app.get("/api/runtime/habla-status")
def get_habla_status():
    status = build_habla_runtime_status()
    status["agentRuntime"] = {
        "lacePolicySource": str(agent_runtime.lace_policy_source),
        "lacePolicySourceExists": agent_runtime.lace_policy_source.exists(),
    }
    return jsonify({"ok": True, "habla": status})


def _load_continuity_probe_module():
    return importlib.import_module("orchestrator.continuity_probe")


def _continuity_probe_public_state(trace_id: str) -> Dict[str, Any] | None:
    run_id = str(trace_id or "").strip()
    if not run_id:
        return None
    with continuity_probe_runs_lock:
        state = deepcopy(continuity_probe_runs.get(run_id) or {})
    try:
        module = _load_continuity_probe_module()
        report = module.load_continuity_report(repo_root=PROJECT_ROOT, trace_id=run_id)
    except Exception:
        report = None
    if isinstance(report, dict):
        state.update(
            {
                "traceId": run_id,
                "status": report.get("status"),
                "result": report.get("result"),
                "mode": report.get("mode"),
                "project": report.get("project"),
                "summary": report.get("summary"),
                "reportPath": report.get("reportPath"),
                "eventsPath": report.get("eventsPath"),
                "finishedAt": report.get("finishedAt"),
                "report": report,
            }
        )
    return state or None


def _run_continuity_probe_background(trace_id: str, payload: Dict[str, Any]) -> None:
    with continuity_probe_runs_lock:
        state = continuity_probe_runs.setdefault(trace_id, {"traceId": trace_id})
        state.update({"status": "running", "startedAt": utc_now()})
    socketio.emit("agent:observer", {"op": "continuity_probe_started", "traceId": trace_id, "status": "running"})
    try:
        module = _load_continuity_probe_module()
        report = module.run_continuity_probe(
            repo_root=PROJECT_ROOT,
            mode=str(payload.get("mode") or "active_canary"),
            project=str(payload.get("project") or module.DEFAULT_PROJECT),
            base_url=str(payload.get("baseUrl") or ""),
            trace_id=trace_id,
            timeout_seconds=int(payload.get("timeoutSeconds") or 45),
            include_harness=bool(payload.get("includeHarness", True)),
        )
        ok = report.get("result") == "continuity_ok"
        with continuity_probe_runs_lock:
            continuity_probe_runs[trace_id] = {
                "ok": ok,
                "traceId": trace_id,
                "status": report.get("status"),
                "result": report.get("result"),
                "mode": report.get("mode"),
                "project": report.get("project"),
                "summary": report.get("summary"),
                "reportPath": report.get("reportPath"),
                "finishedAt": report.get("finishedAt"),
            }
        socketio.emit("agent:observer", {"op": "continuity_probe_completed", "traceId": trace_id, "status": report.get("status"), "result": report.get("result")})
    except Exception as error:
        app.logger.exception("continuity_probe_failed")
        with continuity_probe_runs_lock:
            continuity_probe_runs[trace_id] = {
                "ok": False,
                "traceId": trace_id,
                "status": "failed",
                "result": "continuity_failed",
                "error": str(error),
                "finishedAt": utc_now(),
            }
        socketio.emit("agent:observer", {"op": "continuity_probe_failed", "traceId": trace_id, "status": "failed", "message": str(error)})


@app.post("/api/continuity-probe/start")
def start_continuity_probe():
    payload = request.get_json(silent=True) or {}
    try:
        module = _load_continuity_probe_module()
        mode = str(payload.get("mode") or "active_canary").strip().lower()
        if mode not in module.VALID_MODES:
            return jsonify({"ok": False, "error": "invalid_mode", "modes": sorted(module.VALID_MODES)}), 400
        trace_id = module.safe_slug(payload.get("traceId") or module.new_trace_id(), "continuity")
        project = module.safe_slug(payload.get("project") or module.DEFAULT_PROJECT)
        base_url_raw = payload.get("baseUrl") if "baseUrl" in payload else (request.host_url.rstrip("/") or "http://127.0.0.1:5001")
        base_url = str(base_url_raw or "").rstrip("/")
        timeout_seconds = max(5, min(int(payload.get("timeoutSeconds") or 45), 300))
        include_harness = bool(payload.get("includeHarness", True))
        run_payload = {
            "mode": mode,
            "project": project,
            "baseUrl": base_url,
            "timeoutSeconds": timeout_seconds,
            "includeHarness": include_harness,
        }
        initial = {
            "ok": True,
            "traceId": trace_id,
            "status": "queued",
            "result": "queued",
            "mode": mode,
            "project": project,
            "baseUrl": base_url,
            "includeHarness": include_harness,
            "createdAt": utc_now(),
        }
        with continuity_probe_runs_lock:
            continuity_probe_runs[trace_id] = initial
        if bool(payload.get("sync")):
            report = module.run_continuity_probe(
                repo_root=PROJECT_ROOT,
                mode=mode,
                project=project,
                base_url=base_url,
                trace_id=trace_id,
                timeout_seconds=timeout_seconds,
                include_harness=include_harness,
            )
            ok = report.get("result") == "continuity_ok"
            with continuity_probe_runs_lock:
                continuity_probe_runs[trace_id] = {
                    **initial,
                    "ok": ok,
                    "status": report.get("status"),
                    "result": report.get("result"),
                    "summary": report.get("summary"),
                    "reportPath": report.get("reportPath"),
                    "finishedAt": report.get("finishedAt"),
                }
            return jsonify({"ok": ok, "traceId": trace_id, "run": continuity_probe_runs[trace_id], "report": report})
        socketio.start_background_task(_run_continuity_probe_background, trace_id, run_payload)
        return jsonify({"ok": True, "traceId": trace_id, "run": initial})
    except Exception as error:
        app.logger.exception("continuity_probe_start_failed")
        return jsonify({"ok": False, "error": "continuity_probe_start_failed", "message": str(error)}), 500


@app.get("/api/continuity-probe/status/<trace_id>")
def get_continuity_probe_status(trace_id: str):
    state = _continuity_probe_public_state(trace_id)
    if state is None:
        return jsonify({"ok": False, "error": "continuity_probe_not_found"}), 404
    return jsonify({"ok": True, "run": state})


@app.get("/api/continuity-probe/report/<trace_id>")
def get_continuity_probe_report(trace_id: str):
    try:
        module = _load_continuity_probe_module()
        report = module.load_continuity_report(repo_root=PROJECT_ROOT, trace_id=trace_id)
    except Exception as error:
        return jsonify({"ok": False, "error": "continuity_probe_report_failed", "message": str(error)}), 500
    if report is None:
        return jsonify({"ok": False, "error": "continuity_probe_report_not_found"}), 404
    return jsonify({"ok": True, "traceId": trace_id, "report": report})


@app.get("/api/continuity-probe/runs")
def list_continuity_probe_runs():
    try:
        module = _load_continuity_probe_module()
        reports = module.list_continuity_reports(repo_root=PROJECT_ROOT, limit=30)
    except Exception:
        reports = []
    with continuity_probe_runs_lock:
        memory_runs = list(continuity_probe_runs.values())
    return jsonify({"ok": True, "runs": reports, "memoryRuns": memory_runs})


@app.post("/api/continuity-probe/prompt-flight")
def run_continuity_prompt_flight():
    payload = request.get_json(silent=True) or {}
    try:
        module = _load_continuity_probe_module()
        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"ok": False, "error": "missing_prompt"}), 400
        mode = str(payload.get("mode") or "trace_only").strip().lower()
        if mode not in module.PROMPT_FLIGHT_MODES:
            return jsonify({"ok": False, "error": "invalid_mode", "modes": sorted(module.PROMPT_FLIGHT_MODES)}), 400
        trace_id = module.safe_slug(payload.get("traceId") or module.new_prompt_trace_id(), "prompt-flight")
        project = module.safe_slug(payload.get("project") or module.DEFAULT_PROJECT)
        base_url_raw = payload.get("baseUrl") if "baseUrl" in payload else (request.host_url.rstrip("/") or "http://127.0.0.1:5001")
        base_url = str(base_url_raw or "").rstrip("/")
        timeout_seconds = max(5, min(int(payload.get("timeoutSeconds") or 90), 300))
        include_harness = bool(payload.get("includeHarness", True))
        report = module.run_prompt_flight_probe(
            repo_root=PROJECT_ROOT,
            prompt=prompt,
            mode=mode,
            project=project,
            base_url=base_url,
            trace_id=trace_id,
            timeout_seconds=timeout_seconds,
            include_harness=include_harness,
        )
        ok = report.get("result") == "prompt_flight_ok"
        run = {
            "ok": ok,
            "traceId": trace_id,
            "type": "prompt_flight",
            "status": report.get("status"),
            "result": report.get("result"),
            "mode": mode,
            "project": project,
            "summary": report.get("summary"),
            "reportPath": report.get("reportPath"),
            "finishedAt": report.get("finishedAt"),
        }
        with continuity_probe_runs_lock:
            continuity_probe_runs[trace_id] = run
        socketio.emit("agent:observer", {"op": "prompt_flight_completed", "traceId": trace_id, "status": report.get("status"), "result": report.get("result")})
        return jsonify({"ok": ok, "traceId": trace_id, "run": run, "report": report})
    except Exception as error:
        app.logger.exception("continuity_prompt_flight_failed")
        return jsonify({"ok": False, "error": "continuity_prompt_flight_failed", "message": str(error)}), 500


@app.get("/api/continuity-probe/prompt-flight/report/<trace_id>")
def get_continuity_prompt_flight_report(trace_id: str):
    try:
        module = _load_continuity_probe_module()
        report = module.load_prompt_flight_report(repo_root=PROJECT_ROOT, trace_id=trace_id)
    except Exception as error:
        return jsonify({"ok": False, "error": "prompt_flight_report_failed", "message": str(error)}), 500
    if report is None:
        return jsonify({"ok": False, "error": "prompt_flight_report_not_found"}), 404
    return jsonify({"ok": True, "traceId": trace_id, "report": report})


@app.get("/api/observer/status")
def get_observer_status():
    full = env_flag_enabled(request.args.get("full"), default=False)
    return jsonify({"ok": True, "observer": observer_status_payload(full=full)})


@app.post("/api/observer/enabled")
def set_observer_enabled():
    payload = request.get_json(silent=True) or {}
    result = apply_observer_enabled_request(payload)
    return jsonify(result)


@app.post("/api/observer/behavior")
def update_observer_behavior():
    payload = request.get_json(silent=True) or {}
    behavior_tree = payload.get("behaviorTree") if isinstance(payload.get("behaviorTree"), dict) else payload
    next_tree = observer_plane.update_behavior_tree(behavior_tree)
    socketio.emit(
        "agent:observer",
        {
            "op": "observer_behavior_updated",
            "enabled": observer_plane.enabled,
            "state": observer_plane.context.state,
            "behaviorTree": next_tree,
            "message": "Behavior tree del Observer Plane actualizado.",
        },
    )
    return jsonify({"ok": True, "behaviorTree": next_tree, "observer": observer_status_payload()})


@app.post("/api/observer/observe-once")
def observer_observe_once():
    event = observe_with_tool_event("observe_now", reason="Observacion puntual solicitada por usuario.", persistent=False)
    return jsonify({"ok": True, "event": event, "observer": observer_status_payload()})


@app.post("/api/observer/action")
def observer_safe_action():
    payload = request.get_json(silent=True) or {}
    result = execute_observer_safe_action(str(payload.get("action") or ""), payload.get("payload") if isinstance(payload.get("payload"), dict) else {})
    status = 200 if result.get("ok") else 400
    result["observer"] = observer_status_payload()
    return jsonify(result), status


@app.get("/api/email-commands/status")
def get_email_commands_status():
    start_email_command_dispatcher()
    return jsonify({"ok": True, "email": email_command_plane.status(), "config": email_command_plane.public_config()})


@app.get("/api/email-commands/config")
def get_email_commands_config():
    return jsonify({"ok": True, "config": email_command_plane.public_config(), "email": email_command_plane.status()})


@app.put("/api/email-commands/config")
def update_email_commands_config():
    payload = request.get_json(silent=True) or {}
    config = update_email_command_config_from_payload(payload if isinstance(payload, dict) else {})
    emit_email_command_event(
        "email_command_config_updated",
        None,
        status="configured",
        message="Configuracion de correo entrante actualizada desde la UI.",
    )
    start_email_command_dispatcher()
    return jsonify({"ok": True, "config": config, "email": email_command_plane.status()})


@app.post("/api/email-commands/inbound")
def receive_email_command():
    payload = request.get_json(silent=True) or {}
    result = email_command_plane.ingest_email(
        sender=str(payload.get("from") or payload.get("sender") or ""),
        subject=str(payload.get("subject") or ""),
        body=str(payload.get("body") or payload.get("text") or ""),
        message_id=str(payload.get("messageId") or payload.get("message_id") or ""),
        source=str(payload.get("source") or "api"),
    )
    command = result.get("command") if isinstance(result.get("command"), dict) else None
    if result.get("ok"):
        emit_email_command_event(
            "email_command_received",
            command,
            duplicate=bool(result.get("duplicate")),
            message="Correo ejecutable recibido y persistido.",
        )
        start_email_command_dispatcher()
        socketio.start_background_task(dispatch_next_email_command)
    else:
        emit_email_command_event(
            "email_command_rejected",
            command,
            error=result.get("error"),
            message="Correo rechazado por politica de seguridad.",
        )
    status = 200 if result.get("ok") else 400
    return jsonify({**result, "email": email_command_plane.status()}), status


@app.post("/api/email-commands/dispatch")
def dispatch_email_command_http():
    start_email_command_dispatcher()
    result = dispatch_next_email_command()
    status = 200 if result.get("ok") else 500
    result["email"] = email_command_plane.status()
    return jsonify(result), status


@app.post("/api/email-commands/poll")
def poll_email_commands_http():
    poll_result = email_command_plane.poll_imap_once()
    if poll_result.get("imported"):
        emit_email_command_event(
            "email_command_imported",
            None,
            status="imported",
            message=f"IMAP importo {poll_result.get('imported')} correo(s) ejecutable(s).",
        )
        socketio.start_background_task(dispatch_next_email_command)
    status = 200 if poll_result.get("ok") else 500
    return jsonify({"ok": poll_result.get("ok", False), "poll": poll_result, "email": email_command_plane.status()}), status


@app.get("/")
def serve_frontend_index():
    if not FRONTEND_DIST_ROOT.exists():
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "frontend_dist_missing",
                    "message": "No existe frontend/dist. Ejecuta el build del frontend antes de abrir la UI consumible.",
                }
            ),
            503,
        )
    return send_cached_frontend_file(FRONTEND_DIST_ROOT, "index.html")


@app.get("/assets/<path:asset_path>")
def serve_frontend_asset(asset_path: str):
    assets_dir = FRONTEND_DIST_ROOT / "assets"
    return send_cached_frontend_file(assets_dir, asset_path)


@app.get("/<path:frontend_path>")
def serve_frontend_spa(frontend_path: str):
    if frontend_path.startswith("api/") or frontend_path.startswith("socket.io"):
        return jsonify({"ok": False, "error": "not_found"}), 404
    if not FRONTEND_DIST_ROOT.exists():
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "frontend_dist_missing",
                    "message": "No existe frontend/dist. Ejecuta el build del frontend antes de abrir la UI consumible.",
                }
            ),
            503,
        )

    candidate = FRONTEND_DIST_ROOT / frontend_path
    if candidate.exists() and candidate.is_file():
        return send_cached_frontend_file(FRONTEND_DIST_ROOT, frontend_path)
    return send_cached_frontend_file(FRONTEND_DIST_ROOT, "index.html")


@app.get("/api/reverse-engineering/sessions")
def get_reverse_engineering_sessions():
    return jsonify({"ok": True, "sessions": list_analysis_sessions()})


@app.post("/api/reverse-engineering/analyze")
def analyze_reverse_engineering_target():
    payload = request.get_json(silent=True) or {}
    target_path = str(payload.get("targetPath") or "").strip()
    if not target_path:
        return jsonify({"ok": False, "error": "missing_target_path"}), 400

    try:
        entry = build_analysis_entry(target_path)
    except FileNotFoundError as error:
        return jsonify({"ok": False, "error": "target_not_found", "message": str(error)}), 404
    except ValueError as error:
        return jsonify({"ok": False, "error": "analysis_failed", "message": str(error)}), 400
    except OSError as error:
        return jsonify({"ok": False, "error": "analysis_io_error", "message": str(error)}), 500

    sessions = upsert_analysis_entry(entry)
    graph = normalize_graph(load_default_graph())
    socketio.emit("architecture:update", graph)
    socketio.emit("reverse:sessions", {"sessions": sessions})
    return jsonify({"ok": True, "entry": summarize_analysis_entry(entry), "graph": graph, "sessions": sessions})


@app.delete("/api/reverse-engineering/session/<analysis_id>")
def delete_reverse_engineering_session(analysis_id: str):
    sessions = remove_analysis_entry(analysis_id)
    graph = normalize_graph(load_default_graph())
    socketio.emit("architecture:update", graph)
    socketio.emit("reverse:sessions", {"sessions": sessions})
    return jsonify({"ok": True, "sessions": sessions, "graph": graph})


@app.get("/api/architecture/lint")
def get_architecture_lint():
    scene = str(request.args.get("scene") or "").strip() or None
    full_scan = str(request.args.get("full") or "").strip().lower() in {"1", "true", "yes"}
    raw_graph = load_default_graph()
    if scene is not None and not full_scan:
        graph = raw_graph
        project, nodes = canonicalize_light_graph(raw_graph)
        report = empty_lint_report(scene)
    elif should_use_full_lint_ir(raw_graph):
        graph = normalize_graph(raw_graph)
        project = graph["project"]
        nodes = graph["nodes"]
        report = lint_graph(graph, PROJECT_ROOT, scene_filter=scene, include_workspace_doc_scan=scene is None)
    else:
        graph = raw_graph
        project, nodes = canonicalize_light_graph(raw_graph)
        report = lint_graph(graph, PROJECT_ROOT, scene_filter=scene, include_workspace_doc_scan=scene is None)
    merged_report = merge_lint_report_with_semantic_issues(report, graph=graph, scene_filter=scene)
    report_issues = canonicalize_findings_as_issues(merged_report.get("findings") or [], project=project, nodes=nodes)
    issues = merge_issue_lists(graph.get("issues") or [], report_issues)
    return jsonify({"ok": True, "report": merged_report, "issues": issues})


@app.post("/api/architecture")
def update_architecture():
    payload = request.get_json(silent=True) or {}
    graph = normalize_graph(payload)
    save_graph_state(graph)
    socketio.emit("architecture:update", graph)
    return jsonify({"ok": True, "graph": graph})


@app.post("/api/architecture/rescan")
def rescan_architecture():
    graph = sync_runtime_graph(save_state=True)
    return jsonify({"ok": True, "graph": graph})


@app.post("/api/architecture/reset-view")
def reset_architecture_view():
    save_analysis_state({"analyses": []})
    graph = normalize_graph(create_blank_view_graph())
    save_graph_state(graph)
    socketio.emit("reverse:sessions", {"sessions": []})
    socketio.emit("architecture:update", graph)
    return jsonify({"ok": True, "graph": graph, "sessions": []})


@app.post("/api/architecture/demo/habla")
def load_habla_architecture_demo():
    save_analysis_state({"analyses": []})
    graph = normalize_graph(create_habla_architecture_demo_graph())
    save_graph_state(graph)
    socketio.emit("reverse:sessions", {"sessions": []})
    socketio.emit("architecture:update", graph)
    socketio.emit(
        "agent:visual",
        {
            "op": "habla_architecture_demo",
            "phase": "demo",
            "status": "loaded",
            "message": "Demo de arquitectura HABLA cargada sin tocar el runtime de proyectos.",
        },
    )
    return jsonify({"ok": True, "graph": graph, "sessions": []})



def _relative_repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _artifact_time(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return ""


def _list_cyberlace_training_artifacts(root: Path, *, suffixes: tuple[str, ...], limit: int = 30) -> List[Dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    for path in sorted(root.glob("*"), key=lambda item: item.stat().st_mtime if item.exists() else 0, reverse=True):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        rows.append(
            {
                "name": path.name,
                "path": _relative_repo_path(path),
                "updatedAt": _artifact_time(path),
                "bytes": size,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _load_cyberlace_training_loop_module():
    tools_root = PROJECT_ROOT / "tools"
    tools_path = str(tools_root)
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    return importlib.import_module("cyberlace_training_loop")


def _training_case_id(value: Any, scenario: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        raw = f"ui-{scenario}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-._")
    return cleaned[:90] or f"ui-{scenario}"


def _training_artifact_path(relative_path: str) -> Path | None:
    raw = str(relative_path or "").strip().lstrip("/")
    if not raw:
        return None
    candidate = (PROJECT_ROOT / raw).resolve()
    allowed_roots = [root.resolve() for root in CYBERLACE_TRAINING_ALLOWED_ROOTS]
    if not any(str(candidate).startswith(str(root) + os.sep) or candidate == root for root in allowed_roots):
        return None
    if candidate.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
        return None
    return candidate if candidate.exists() and candidate.is_file() else None


@app.get("/api/harness/training/summary")
def get_harness_training_summary():
    return jsonify(
        {
            "ok": True,
            "scenarios": sorted(CYBERLACE_TRAINING_SCENARIOS),
            "intensities": sorted(CYBERLACE_TRAINING_INTENSITIES),
            "cases": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_CASES_DIR, suffixes=(".json",)),
            "reports": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_REPORTS_DIR, suffixes=(".md",)),
            "checkpoints": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_CHECKPOINTS_DIR, suffixes=(".json",)),
            "campaigns": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_CAMPAIGNS_DIR, suffixes=(".json", ".md")),
            "runs": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_RUNS_DIR, suffixes=(".json", ".jsonl")),
            "memory": {
                "path": _relative_repo_path(CYBERLACE_TRAINING_MEMORY_PATH),
                "exists": CYBERLACE_TRAINING_MEMORY_PATH.exists(),
                "updatedAt": _artifact_time(CYBERLACE_TRAINING_MEMORY_PATH) if CYBERLACE_TRAINING_MEMORY_PATH.exists() else "",
            },
            "safetyLearning": build_safety_learning_status(limit=8),
        }
    )


@app.get("/api/harness/safety-learning/status")
def get_harness_safety_learning_status():
    return jsonify(build_safety_learning_status(limit=12))


@app.post("/api/harness/safety-learning/feedback")
def post_harness_safety_learning_feedback():
    payload = request.get_json(silent=True) or {}
    return jsonify(record_human_feedback(payload))


@app.post("/api/harness/safety-learning/repair-request")
def post_harness_safety_learning_repair_request():
    payload = request.get_json(silent=True) or {}
    return jsonify(queue_repair_recommendation(payload))


@app.get("/api/harness/training/artifact")
def get_harness_training_artifact():
    artifact = _training_artifact_path(str(request.args.get("path") or ""))
    if artifact is None:
        return jsonify({"ok": False, "error": "artifact_not_found"}), 404
    try:
        content = artifact.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return jsonify({"ok": False, "error": "artifact_read_failed", "message": str(error)}), 500
    return jsonify({"ok": True, "path": _relative_repo_path(artifact), "content": content})


@app.post("/api/harness/training/generate-run")
def post_harness_training_generate_run():
    payload = request.get_json(silent=True) or {}
    scenario = str(payload.get("scenario") or "").strip().lower()
    if scenario not in CYBERLACE_TRAINING_SCENARIOS:
        return jsonify({"ok": False, "error": "invalid_scenario", "scenarios": sorted(CYBERLACE_TRAINING_SCENARIOS)}), 400
    case_id = _training_case_id(payload.get("caseId") or payload.get("case_id"), scenario)
    base_url = str(payload.get("baseUrl") or request.host_url.rstrip("/") or "http://127.0.0.1:5001").rstrip("/")
    try:
        loop = _load_cyberlace_training_loop_module()
        loop.ensure_dirs()
        case = loop.generated_case(scenario, case_id)
        case_path = loop.TRAINING_CASES_DIR / f"{case['id']}.json"
        loop.write_json(case_path, case)
        args = SimpleNamespace(case=str(case_path), base_url=base_url)
        output_buffer = io.StringIO()
        with contextlib.redirect_stdout(output_buffer):
            result = loop.run_case(args)
        learning = learn_from_harness_result(
            result,
            case=case,
            context={"source": "manual", "casePath": _relative_repo_path(case_path), "cycle": 1},
        )
        result["learning"] = {
            "experienceId": learning.get("experience", {}).get("id"),
            "diagnosis": learning.get("evaluation", {}).get("diagnosis"),
            "severity": learning.get("evaluation", {}).get("severity"),
            "recommendation": learning.get("recommendation"),
        }
        console_lines = [line for line in output_buffer.getvalue().splitlines() if line.strip()]
        socketio.start_background_task(sync_runtime_graph, True)
        socketio.start_background_task(lambda: socketio.emit("agent:projects", {"projects": list_agent_projects_snapshot()}))
        return jsonify(
            {
                "ok": True,
                "case": {"id": case.get("id"), "path": _relative_repo_path(case_path), "scenario": scenario},
                "result": result,
                "console": console_lines[-30:],
                "summary": {
                    "reports": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_REPORTS_DIR, suffixes=(".md",), limit=8),
                    "checkpoints": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_CHECKPOINTS_DIR, suffixes=(".json",), limit=8),
                    "safetyLearning": build_safety_learning_status(limit=8),
                },
                "safetyLearning": learning,
            }
        )
    except Exception as error:
        app.logger.exception("cyberlace_training_generate_run_failed")
        return jsonify({"ok": False, "error": "training_run_failed", "message": str(error)}), 500




def _training_run_paths(run_id: str) -> tuple[Path, Path]:
    safe_run_id = _training_case_id(run_id, "autopilot-run")
    return (
        CYBERLACE_TRAINING_RUNS_DIR / f"{safe_run_id}.json",
        CYBERLACE_TRAINING_RUNS_DIR / f"{safe_run_id}.jsonl",
    )


def _training_run_status_active(status: Any) -> bool:
    return str(status or "").lower() in CYBERLACE_TRAINING_RUN_ACTIVE_STATUSES


def _training_run_resume_from_cycle(state: Dict[str, Any]) -> int:
    results = state.get("results") if isinstance(state.get("results"), list) else []
    return max(1, len(results) + 1)


def _training_run_attach_paths(run_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    state = dict(state)
    state_path, events_path = _training_run_paths(run_id)
    state.setdefault("runId", run_id)
    state["runPath"] = _relative_repo_path(state_path)
    state["eventsPath"] = _relative_repo_path(events_path)
    return state


def _training_run_persist_state(run_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    CYBERLACE_TRAINING_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    state = _training_run_attach_paths(run_id, state)
    state_path, _ = _training_run_paths(run_id)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return state


def _training_run_append_event_record(run_id: str, event: Dict[str, Any]) -> None:
    CYBERLACE_TRAINING_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    _, events_path = _training_run_paths(run_id)
    payload = dict(event)
    payload.setdefault("runId", run_id)
    payload.setdefault("at", datetime.now(timezone.utc).isoformat())
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _training_run_load_from_disk(run_id: str) -> Dict[str, Any] | None:
    state_path, _ = _training_run_paths(run_id)
    data = load_json_file(state_path, None)
    if not isinstance(data, dict):
        return None
    return _training_run_attach_paths(str(data.get("runId") or run_id), data)


def _training_run_mark_interrupted(run_id: str, state: Dict[str, Any], *, reason: str) -> Dict[str, Any]:
    updated = _training_run_attach_paths(run_id, state)
    now = datetime.now(timezone.utc).isoformat()
    updated.update(
        {
            "status": "interrupted",
            "phase": "interrupted",
            "message": "Campaña interrumpida: el backend no conserva una tarea viva para este run.",
            "interruptedAt": now,
            "interruptionReason": reason,
            "resumable": True,
            "resumeFromCycle": _training_run_resume_from_cycle(updated),
            "stopRequested": False,
            "updatedAt": now,
        }
    )
    steps = updated.setdefault("steps", [])
    if isinstance(steps, list):
        steps.append(
            {
                "cycle": None,
                "phase": "interrupted",
                "message": updated["message"],
                "status": "interrupted",
                "at": now,
            }
        )
        if len(steps) > 120:
            del steps[:-120]
    updated = _training_run_persist_state(run_id, updated)
    _training_run_append_event_record(
        run_id,
        {
            "type": "run_interrupted",
            "phase": "interrupted",
            "status": "interrupted",
            "reason": reason,
            "resumeFromCycle": updated.get("resumeFromCycle"),
        },
    )
    return updated


def _training_recover_orphaned_runs() -> None:
    CYBERLACE_TRAINING_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with cyberlace_training_runs_lock:
        live_run_ids = {run_id for run_id, state in cyberlace_training_runs.items() if _training_run_status_active((state or {}).get("status"))}
    for state_path in CYBERLACE_TRAINING_RUNS_DIR.glob("*.json"):
        state = load_json_file(state_path, None)
        if not isinstance(state, dict):
            continue
        run_id = str(state.get("runId") or state_path.stem)
        if run_id in live_run_ids:
            continue
        if _training_run_status_active(state.get("status")):
            _training_run_mark_interrupted(run_id, state, reason="backend_process_restart_or_memory_loss")


def _training_active_run_state() -> Dict[str, Any] | None:
    _training_recover_orphaned_runs()
    with cyberlace_training_runs_lock:
        for state in cyberlace_training_runs.values():
            if isinstance(state, dict) and _training_run_status_active(state.get("status")):
                return deepcopy(state)
    return None


def _training_run_public_state(run_id: str) -> Dict[str, Any] | None:
    with cyberlace_training_runs_lock:
        state = cyberlace_training_runs.get(run_id)
        if isinstance(state, dict):
            return deepcopy(state)
    state = _training_run_load_from_disk(run_id)
    if state is None:
        return None
    if _training_run_status_active(state.get("status")):
        state = _training_run_mark_interrupted(run_id, state, reason="backend_process_restart_or_memory_loss")
    return deepcopy(state)


def _training_run_update(run_id: str, **updates: Any) -> Dict[str, Any]:
    with cyberlace_training_runs_lock:
        state = cyberlace_training_runs.setdefault(run_id, {"runId": run_id})
        state.update(updates)
        state["updatedAt"] = datetime.now(timezone.utc).isoformat()
        state = _training_run_persist_state(run_id, state)
        cyberlace_training_runs[run_id] = state
        return deepcopy(state)


def _training_run_append_step(run_id: str, *, cycle: int | None, phase: str, message: str, status: str = "running") -> None:
    now = datetime.now(timezone.utc).isoformat()
    step = {
        "cycle": cycle,
        "phase": phase,
        "message": message,
        "status": status,
        "at": now,
    }
    with cyberlace_training_runs_lock:
        state = cyberlace_training_runs.setdefault(run_id, {"runId": run_id})
        steps = state.setdefault("steps", [])
        steps.append(step)
        state["phase"] = phase
        state["message"] = message
        state["updatedAt"] = now
        if len(steps) > 120:
            del steps[:-120]
        state = _training_run_persist_state(run_id, state)
        cyberlace_training_runs[run_id] = state
    _training_run_append_event_record(run_id, {"type": "step", **step})


def _training_run_stop_requested(run_id: str) -> bool:
    with cyberlace_training_runs_lock:
        return bool((cyberlace_training_runs.get(run_id) or {}).get("stopRequested"))


def _training_wait_between_autopilot_tasks(run_id: str, *, cycle: int, next_cycle: int, seconds: float) -> bool:
    delay = max(1.0, min(float(seconds or 8.0), 300.0))
    deadline = time.monotonic() + delay
    _training_run_append_step(
        run_id,
        cycle=cycle,
        phase="cooldown",
        message=f"Pausa de {delay:g}s antes de lanzar la tarea {next_cycle}; protegiendo el runtime de solapamientos.",
        status="running",
    )
    while True:
        if _training_run_stop_requested(run_id):
            _training_run_update(run_id, phase="stopping", delayRemainingSeconds=0)
            return False
        remaining = max(0.0, deadline - time.monotonic())
        _training_run_update(
            run_id,
            phase="cooldown",
            delayRemainingSeconds=round(remaining, 1),
            message=f"Pausa entre tareas: {remaining:.1f}s antes de la tarea {next_cycle}.",
        )
        if remaining <= 0:
            break
        time.sleep(min(1.0, remaining))
    _training_run_update(run_id, delayRemainingSeconds=0)
    _training_run_append_step(
        run_id,
        cycle=cycle,
        phase="cooldown",
        message=f"Pausa completada; la tarea {next_cycle} puede iniciar.",
        status="completed",
    )
    return True


def _run_harness_training_autopilot_background(
    *,
    run_id: str,
    campaign_id: str,
    cycles: int,
    intensity: str,
    objective: str,
    base_url: str,
    continuous: bool = False,
    task_delay_seconds: float = 8.0,
    start_cycle: int = 1,
    initial_results: List[Dict[str, Any]] | None = None,
) -> None:
    try:
        loop = _load_cyberlace_training_loop_module()
        loop.ensure_dirs()
        memory = loop.load_training_memory()
        results: List[Dict[str, Any]] = deepcopy(initial_results or [])
        _training_run_update(run_id, status="running", phase="bootstrap", message="Inicializando agente generador y memoria de entrenamiento.")
        _training_run_append_step(run_id, cycle=None, phase="bootstrap", message="Memoria cargada; iniciando campaña autónoma.", status="completed")

        max_cycles = 1000 if continuous else cycles
        stopped_by_user = False
        for cycle in range(max(1, int(start_cycle or 1)), max_cycles + 1):
            if _training_run_stop_requested(run_id):
                stopped_by_user = True
                _training_run_append_step(run_id, cycle=None, phase="stopping", message="Solicitud humana de detener recibida; cerrando campaña con evidencia acumulada.", status="completed")
                break
            _training_run_append_step(run_id, cycle=cycle, phase="metacognitive-plan", message=f"Ciclo {cycle}: analizando memoria previa y seleccionando familia de ataque.")
            case = loop.build_autonomous_case(
                campaign_id=campaign_id,
                cycle=cycle,
                intensity=intensity,
                objective=objective,
                previous_results=results,
            )
            scenario = str(case.get("scenario") or "unknown")
            case_path = loop.TRAINING_CASES_DIR / f"{case['id']}.json"
            loop.write_json(case_path, case)
            _training_run_update(
                run_id,
                currentCycle=cycle,
                currentScenario=scenario,
                currentCase=case.get("id"),
                currentCasePath=_relative_repo_path(case_path),
            )
            _training_run_append_step(run_id, cycle=cycle, phase="case-generated", message=f"Ciclo {cycle}: caso fabricado ({scenario}) y fixture escrito.", status="completed")
            _training_run_append_step(run_id, cycle=cycle, phase="runtime-dispatch", message=f"Ciclo {cycle}: enviando caso al runtime real por /api/agent/session.")

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                result = loop.run_case(SimpleNamespace(case=str(case_path), base_url=base_url))
            result["cycle"] = cycle
            result["scenario"] = scenario
            result["casePath"] = _relative_repo_path(case_path)
            result["selectionReason"] = (case.get("campaign") or {}).get("selectionReason")
            learning = learn_from_harness_result(
                result,
                case=case,
                context={
                    "source": "autopilot",
                    "campaignId": campaign_id,
                    "cycle": cycle,
                    "casePath": _relative_repo_path(case_path),
                },
            )
            result["learning"] = {
                "experienceId": learning.get("experience", {}).get("id"),
                "diagnosis": learning.get("evaluation", {}).get("diagnosis"),
                "severity": learning.get("evaluation", {}).get("severity"),
                "needsRepair": learning.get("evaluation", {}).get("needsRepair"),
                "recommendation": learning.get("recommendation"),
            }
            results.append(result)
            _training_run_update(run_id, results=deepcopy(results), learningStatus=build_safety_learning_status(limit=8))
            _training_run_append_step(
                run_id,
                cycle=cycle,
                phase="evaluation",
                message=f"Ciclo {cycle}: evaluación {'PASSED' if result.get('passed') else 'FAILED'} con status={result.get('status')} action={result.get('runtimeAction')}.",
                status="completed" if result.get("passed") else "failed",
            )
            _training_run_append_step(
                run_id,
                cycle=cycle,
                phase="learning",
                message=f"Ciclo {cycle}: Safety Learning Core clasificó {result['learning'].get('diagnosis')} y recomienda {((result['learning'].get('recommendation') or {}).get('action') or 'generate_next_case')}.",
                status="completed",
            )

            lessons = memory.setdefault("lessons", [])
            lessons.append(
                {
                    "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "campaignId": campaign_id,
                    "cycle": cycle,
                    "scenario": scenario,
                    "case": case.get("id"),
                    "passed": result.get("passed"),
                    "status": result.get("status"),
                    "runtimeAction": result.get("runtimeAction"),
                    "failures": result.get("failures") or [],
                    "report": result.get("report"),
                    "checkpoint": result.get("checkpoint"),
                }
            )
            loop.save_training_memory(memory)
            _training_run_append_step(run_id, cycle=cycle, phase="memory", message=f"Ciclo {cycle}: memoria actualizada para orientar el siguiente caso.", status="completed")
            if cycle < max_cycles:
                if not _training_wait_between_autopilot_tasks(run_id, cycle=cycle, next_cycle=cycle + 1, seconds=task_delay_seconds):
                    stopped_by_user = True
                    _training_run_append_step(run_id, cycle=None, phase="stopping", message="Loop detenido durante la pausa entre tareas.", status="completed")
                    break

        campaign = {
            "schemaVersion": 1,
            "id": campaign_id,
            "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "objective": objective,
            "intensity": intensity,
            "cycles": len(results),
            "requestedCycles": cycles,
            "continuous": continuous,
            "taskDelaySeconds": task_delay_seconds,
            "stoppedByUser": stopped_by_user,
            "passed": bool(results) and all(item.get("passed") for item in results),
            "results": results,
            "memoryPath": _relative_repo_path(CYBERLACE_TRAINING_MEMORY_PATH),
            "learningSummary": build_safety_learning_status(limit=8),
        }
        run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        checkpoint_path = CYBERLACE_TRAINING_CAMPAIGNS_DIR / f"{campaign_id}-{run_stamp}.json"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(json.dumps(campaign, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report_path = CYBERLACE_TRAINING_CAMPAIGNS_DIR / f"{campaign_id}-{run_stamp}.md"
        report_path.write_text(loop.campaign_markdown_report(campaign, checkpoint_path), encoding="utf-8")

        memory.setdefault("campaigns", []).append(
            {
                "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "campaignId": campaign_id,
                "cycles": len(results),
                "requestedCycles": cycles,
                "continuous": continuous,
                "taskDelaySeconds": task_delay_seconds,
                "stoppedByUser": stopped_by_user,
                "intensity": intensity,
                "passed": campaign["passed"],
                "report": _relative_repo_path(report_path),
                "checkpoint": _relative_repo_path(checkpoint_path),
            }
        )
        loop.save_training_memory(memory)
        socketio.start_background_task(sync_runtime_graph, True)
        socketio.start_background_task(lambda: socketio.emit("agent:projects", {"projects": list_agent_projects_snapshot()}))
        final_status = "stopped" if stopped_by_user else "completed"
        final_message = "Loop autónomo detenido por el usuario; reporte, checkpoint y memoria listos." if stopped_by_user else "Campaña autónoma finalizada; reporte, checkpoint y memoria listos."
        _training_run_append_step(run_id, cycle=None, phase=final_status, message=final_message, status="completed")
        _training_run_update(
            run_id,
            status=final_status,
            passed=campaign["passed"],
            campaign={
                "ok": True,
                "campaignId": campaign_id,
                "passed": campaign["passed"],
                "cycles": len(results),
                "requestedCycles": cycles,
                "continuous": continuous,
                "taskDelaySeconds": task_delay_seconds,
                "stoppedByUser": stopped_by_user,
                "results": results,
                "report": _relative_repo_path(report_path),
                "checkpoint": _relative_repo_path(checkpoint_path),
                "memory": _relative_repo_path(CYBERLACE_TRAINING_MEMORY_PATH),
            },
            report=_relative_repo_path(report_path),
            checkpoint=_relative_repo_path(checkpoint_path),
            memory=_relative_repo_path(CYBERLACE_TRAINING_MEMORY_PATH),
            learningStatus=build_safety_learning_status(limit=8),
        )
    except Exception as error:
        app.logger.exception("cyberlace_training_autopilot_background_failed")
        _training_run_append_step(run_id, cycle=None, phase="failed", message=f"Campaña falló: {error}", status="failed")
        _training_run_update(run_id, status="failed", passed=False, error=str(error))


@app.post("/api/harness/training/autopilot-start")
def post_harness_training_autopilot_start():
    payload = request.get_json(silent=True) or {}
    continuous = bool(payload.get("continuous"))
    try:
        cycles = max(1, min(int(payload.get("cycles", 50)), 1000))
    except (TypeError, ValueError):
        cycles = 50
    if continuous:
        cycles = 1000
    try:
        task_delay_seconds = max(1.0, min(float(payload.get("taskDelaySeconds", payload.get("task_delay_seconds", 8))), 300.0))
    except (TypeError, ValueError):
        task_delay_seconds = 8.0
    intensity = str(payload.get("intensity") or "hard").strip().lower()
    if intensity not in CYBERLACE_TRAINING_INTENSITIES:
        return jsonify({"ok": False, "error": "invalid_intensity", "intensities": sorted(CYBERLACE_TRAINING_INTENSITIES)}), 400
    campaign_id = _training_case_id(payload.get("campaignId") or payload.get("campaign_id"), f"autopilot-{intensity}")
    run_id = _training_case_id(f"{campaign_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}", "autopilot-run")
    objective = str(payload.get("objective") or "Entrenamiento autonomo de seguridad operacional para agentes IA.").strip()
    base_url = str(payload.get("baseUrl") or request.host_url.rstrip("/") or "http://127.0.0.1:5001").rstrip("/")
    active_run = _training_active_run_state()
    if active_run is not None:
        return jsonify({"ok": False, "error": "training_run_active", "message": "Ya hay una campaña autónoma activa; detén o espera ese run antes de iniciar otro.", "activeRun": active_run}), 409
    created_at = datetime.now(timezone.utc).isoformat()
    initial = {
        "ok": True,
        "runId": run_id,
        "campaignId": campaign_id,
        "status": "queued",
        "phase": "queued",
        "message": "Campaña en cola; preparando agente generador.",
        "createdAt": created_at,
        "updatedAt": created_at,
        "cycles": cycles,
        "continuous": continuous,
        "taskDelaySeconds": task_delay_seconds,
        "delayRemainingSeconds": 0,
        "stopRequested": False,
        "intensity": intensity,
        "objective": objective,
        "baseUrl": base_url,
        "resumable": False,
        "resumeFromCycle": 1,
        "results": [],
        "steps": [],
        "passed": None,
    }
    with cyberlace_training_runs_lock:
        initial = _training_run_persist_state(run_id, initial)
        cyberlace_training_runs[run_id] = initial
        _training_run_append_event_record(run_id, {"type": "run_created", "phase": "queued", "status": "queued", "campaignId": campaign_id, "cycles": cycles})
        if len(cyberlace_training_runs) > 40:
            for old_key in list(cyberlace_training_runs.keys())[:-40]:
                old_state = cyberlace_training_runs.get(old_key) or {}
                if not _training_run_status_active(old_state.get("status")):
                    cyberlace_training_runs.pop(old_key, None)
    socketio.start_background_task(
        _run_harness_training_autopilot_background,
        run_id=run_id,
        campaign_id=campaign_id,
        cycles=cycles,
        intensity=intensity,
        objective=objective,
        base_url=base_url,
        continuous=continuous,
        task_delay_seconds=task_delay_seconds,
    )
    return jsonify({"ok": True, "run": initial})


@app.post("/api/harness/training/autopilot-stop/<run_id>")
def post_harness_training_autopilot_stop(run_id: str):
    with cyberlace_training_runs_lock:
        state = cyberlace_training_runs.get(run_id)
        if not isinstance(state, dict):
            disk_state = _training_run_public_state(run_id)
            if disk_state is None:
                return jsonify({"ok": False, "error": "training_run_not_found"}), 404
            return jsonify({"ok": True, "run": disk_state})
        if str(state.get("status") or "").lower() in CYBERLACE_TRAINING_RUN_TERMINAL_STATUSES:
            return jsonify({"ok": True, "run": deepcopy(state)})
        state["stopRequested"] = True
        state["status"] = "stopping"
        state["phase"] = "stopping"
        state["message"] = "Detencion solicitada; el loop cerrara al terminar el ciclo actual."
        state["updatedAt"] = datetime.now(timezone.utc).isoformat()
        state = _training_run_persist_state(run_id, state)
        cyberlace_training_runs[run_id] = state
        run = deepcopy(state)
    _training_run_append_step(run_id, cycle=None, phase="stopping", message="Usuario solicito detener el loop autonomo.", status="running")
    return jsonify({"ok": True, "run": _training_run_public_state(run_id) or run})


@app.post("/api/harness/training/autopilot-resume/<run_id>")
def post_harness_training_autopilot_resume(run_id: str):
    state = _training_run_public_state(run_id)
    if state is None:
        return jsonify({"ok": False, "error": "training_run_not_found"}), 404
    if str(state.get("status") or "").lower() != "interrupted":
        return jsonify({"ok": False, "error": "training_run_not_resumable", "run": state}), 409
    active_run = _training_active_run_state()
    if active_run is not None and active_run.get("runId") != run_id:
        return jsonify({"ok": False, "error": "training_run_active", "message": "Ya hay una campaña autónoma activa; no se puede reanudar otra.", "activeRun": active_run}), 409

    results = state.get("results") if isinstance(state.get("results"), list) else []
    cycles = max(1, min(int(state.get("cycles") or state.get("requestedCycles") or len(results) or 1), 1000))
    start_cycle = _training_run_resume_from_cycle(state)
    if start_cycle > cycles and not bool(state.get("continuous")):
        state["status"] = "completed"
        state["phase"] = "completed"
        state["message"] = "No quedan ciclos pendientes para reanudar."
        state["updatedAt"] = datetime.now(timezone.utc).isoformat()
        state = _training_run_persist_state(run_id, state)
        return jsonify({"ok": True, "run": state})

    campaign_id = str(state.get("campaignId") or _training_case_id(run_id, "autopilot-resume"))
    intensity = str(state.get("intensity") or "hard")
    objective = str(state.get("objective") or "Entrenamiento autonomo de seguridad operacional para agentes IA.")
    base_url = str(state.get("baseUrl") or request.host_url.rstrip("/") or "http://127.0.0.1:5001").rstrip("/")
    task_delay_seconds = float(state.get("taskDelaySeconds") or 8.0)
    continuous = bool(state.get("continuous"))
    now = datetime.now(timezone.utc).isoformat()
    state.update(
        {
            "status": "queued",
            "phase": "queued",
            "message": f"Reanudando campaña desde ciclo {start_cycle}.",
            "stopRequested": False,
            "resumable": False,
            "resumeFromCycle": start_cycle,
            "resumedAt": now,
            "updatedAt": now,
        }
    )
    with cyberlace_training_runs_lock:
        state = _training_run_persist_state(run_id, state)
        cyberlace_training_runs[run_id] = state
    _training_run_append_step(run_id, cycle=None, phase="resume", message=state["message"], status="running")
    socketio.start_background_task(
        _run_harness_training_autopilot_background,
        run_id=run_id,
        campaign_id=campaign_id,
        cycles=cycles,
        intensity=intensity,
        objective=objective,
        base_url=base_url,
        continuous=continuous,
        task_delay_seconds=task_delay_seconds,
        start_cycle=start_cycle,
        initial_results=deepcopy(results),
    )
    return jsonify({"ok": True, "run": _training_run_public_state(run_id) or state})


@app.get("/api/harness/training/autopilot-status/<run_id>")
def get_harness_training_autopilot_status(run_id: str):
    state = _training_run_public_state(run_id)
    if state is None:
        return jsonify({"ok": False, "error": "training_run_not_found"}), 404
    return jsonify({"ok": True, "run": state})


@app.post("/api/harness/training/autopilot-run")
def post_harness_training_autopilot_run():
    payload = request.get_json(silent=True) or {}
    raw_cycles = payload.get("cycles", 50)
    try:
        cycles = max(1, min(int(raw_cycles), 1000))
    except (TypeError, ValueError):
        cycles = 50
    intensity = str(payload.get("intensity") or "hard").strip().lower()
    if intensity not in CYBERLACE_TRAINING_INTENSITIES:
        return jsonify({"ok": False, "error": "invalid_intensity", "intensities": sorted(CYBERLACE_TRAINING_INTENSITIES)}), 400
    campaign_id = _training_case_id(payload.get("campaignId") or payload.get("campaign_id"), f"autopilot-{intensity}")
    objective = str(payload.get("objective") or "Entrenamiento autonomo de seguridad operacional para agentes IA.").strip()
    base_url = str(payload.get("baseUrl") or request.host_url.rstrip("/") or "http://127.0.0.1:5001").rstrip("/")
    try:
        task_delay_seconds = max(1.0, min(float(payload.get("taskDelaySeconds", payload.get("task_delay_seconds", 8))), 300.0))
    except (TypeError, ValueError):
        task_delay_seconds = 8.0
    try:
        loop = _load_cyberlace_training_loop_module()
        loop.ensure_dirs()
        args = SimpleNamespace(
            campaign_id=campaign_id,
            cycles=cycles,
            intensity=intensity,
            objective=objective,
            base_url=base_url,
            task_delay_seconds=task_delay_seconds,
        )
        output_buffer = io.StringIO()
        with contextlib.redirect_stdout(output_buffer):
            campaign = loop.run_campaign(args)
        console_lines = [line for line in output_buffer.getvalue().splitlines() if line.strip()]
        socketio.start_background_task(sync_runtime_graph, True)
        socketio.start_background_task(lambda: socketio.emit("agent:projects", {"projects": list_agent_projects_snapshot()}))
        return jsonify(
            {
                "ok": True,
                "campaign": campaign,
                "console": console_lines[-60:],
                "summary": {
                    "campaigns": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_CAMPAIGNS_DIR, suffixes=(".json", ".md"), limit=12),
                    "reports": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_REPORTS_DIR, suffixes=(".md",), limit=12),
                    "checkpoints": _list_cyberlace_training_artifacts(CYBERLACE_TRAINING_CHECKPOINTS_DIR, suffixes=(".json",), limit=12),
                    "memory": _relative_repo_path(CYBERLACE_TRAINING_MEMORY_PATH),
                },
            }
        )
    except Exception as error:
        app.logger.exception("cyberlace_training_autopilot_run_failed")
        return jsonify({"ok": False, "error": "training_autopilot_failed", "message": str(error)}), 500

def list_agent_projects_snapshot() -> List[Dict[str, Any]]:
    """Return a fast, disk-only projects snapshot for UI hydration.

    This endpoint is on the critical UI path. It intentionally avoids runtime
    session state so stale workers, sockets, or queues cannot freeze the
    project picker.
    """

    AGENT_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    AGENT_PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    projects: List[Dict[str, Any]] = []
    source_suffixes = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".html", ".css",
        ".scss", ".yaml", ".yml", ".txt", ".sh", ".sql", ".toml", ".ini",
    }
    ignored_dirs = {".git", ".pytest_cache", ".ruff_cache", ".vista", "node_modules", "__pycache__", ".venv", "venv", "runtime", "dist", "build", "coverage"}

    def titleize_project(value: str) -> str:
        return " ".join(part.capitalize() for part in str(value or "").replace("-", " ").split()) or "Nuevo Proyecto"

    def count_files_fast(project_dir: Path) -> int:
        count = 0
        try:
            for root_dir, dirnames, filenames in os.walk(project_dir):
                dirnames[:] = [name for name in dirnames if name not in ignored_dirs and not name.startswith(".")]
                for filename in filenames:
                    if Path(filename).suffix.lower() in source_suffixes:
                        count += 1
        except OSError:
            return count
        return count

    for project_dir in sorted(AGENT_PROJECTS_ROOT.iterdir(), key=lambda item: item.name):
        if not project_dir.is_dir():
            continue
        metadata: Dict[str, Any] = {}
        metadata_path = project_dir / ".agent-project.json"
        if metadata_path.exists() and metadata_path.is_file():
            try:
                loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata = loaded if isinstance(loaded, dict) else {}
            except (json.JSONDecodeError, OSError):
                metadata = {}
        try:
            relative_path = str(project_dir.relative_to(PROJECT_ROOT))
        except ValueError:
            relative_path = str(project_dir)
        now_value = utc_now()
        projects.append(
            {
                "name": metadata.get("name") or titleize_project(project_dir.name),
                "slug": project_dir.name,
                "path": str(project_dir),
                "relativePath": relative_path,
                "updatedAt": metadata.get("updatedAt") or now_value,
                "createdAt": metadata.get("createdAt") or now_value,
                "fileCount": count_files_fast(project_dir),
                "demoLabel": metadata.get("demoLabel") or "",
                "description": metadata.get("description") or "",
                "demoRole": metadata.get("demoRole") or "",
                "systemDemo": bool(metadata.get("systemDemo")),
                "nativeExample": bool(metadata.get("nativeExample")),
                "evaluatedProject": bool(metadata.get("evaluatedProject")),
                "learningMode": bool(metadata.get("learningMode")),
                "protected": bool(metadata.get("protected") or project_dir.name in PROTECTED_AGENT_PROJECTS),
                "protectedReason": metadata.get("protectedReason") or ("Proyecto protegido del sistema." if project_dir.name in PROTECTED_AGENT_PROJECTS else ""),
            }
        )
    return projects



@app.get("/api/agent/projects")
def get_agent_projects():
    return jsonify({"projects": list_agent_projects_snapshot()})


def resolve_reviewer_project(project_id: str) -> Path | None:
    project_dir = workspace_project_dir(project_id).resolve()
    try:
        project_dir.relative_to(AGENT_PROJECTS_ROOT.resolve())
    except ValueError:
        return None
    if not project_dir.exists() or not project_dir.is_dir():
        return None
    return project_dir


def is_editor_hidden_path(relative_path: str) -> bool:
    path = PurePosixPath(normalize_relative_fragment(relative_path))
    return any(part in EDITOR_EXCLUDED_PARTS or part.startswith(".") for part in path.parts)


def resolve_editor_project(project_id: str) -> tuple[str, Path] | None:
    slug = normalize_layer_name(project_id)
    project_dir = workspace_project_dir(slug).resolve()
    try:
        project_dir.relative_to(AGENT_PROJECTS_ROOT.resolve())
    except ValueError:
        return None
    if not project_dir.exists() or not project_dir.is_dir():
        return None
    return slug, project_dir


def resolve_editor_file(project_dir: Path, relative_path: Any, *, must_exist: bool = True) -> tuple[str, Path] | None:
    normalized = normalize_relative_fragment(relative_path)
    if not normalized or normalized == "." or is_editor_hidden_path(normalized):
        return None
    target_path = (project_dir / normalized).resolve()
    try:
        target_path.relative_to(project_dir.resolve())
    except ValueError:
        return None
    if must_exist and (not target_path.exists() or not target_path.is_file()):
        return None
    if target_path.exists() and not target_path.is_file():
        return None
    return normalized, target_path


def load_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def build_editor_lock_state(project_slug: str, project_dir: Path) -> Dict[str, Any]:
    active_statuses = {"queued", "preparing", "starting", "running"}
    terminal_state_statuses = {"blocked", "completed", "failed", "stopped"}
    active_sessions = [
        session
        for session in agent_runtime.list_sessions()
        if session.get("projectSlug") == project_slug and str(session.get("status") or "").lower() in active_statuses
    ]
    if active_sessions:
        session = active_sessions[-1]
        return {
            "locked": True,
            "reason": "agent_session_active",
            "message": "Agente activo: el editor esta en lectura viva hasta que cierre la sesion.",
            "sessionId": session.get("sessionId"),
            "projectStatus": session.get("status"),
            "currentTaskId": session.get("currentTaskId") or session.get("currentTask"),
        }

    runtime_dir = project_dir / "runtime"
    state = load_json_file(runtime_dir / "project_state.json", {})
    queue = load_json_file(runtime_dir / "task_queue.json", [])
    queue_tasks = queue.get("tasks") if isinstance(queue, dict) else queue
    queue_tasks = queue_tasks if isinstance(queue_tasks, list) else []
    running_task = next((task for task in queue_tasks if str(task.get("status") or "").lower() == "running"), None)
    state_status = str(state.get("status") or "").lower()
    current_task_id = state.get("current_task_id") or state.get("currentTaskId")

    if running_task or state_status in active_statuses or (current_task_id and state_status not in terminal_state_statuses):
        return {
            "locked": True,
            "reason": "control_plane_active",
            "message": "Control plane activo: solo lectura mientras haya tarea en ejecucion.",
            "sessionId": state.get("session_id") or state.get("sessionId"),
            "projectStatus": state_status or "unknown",
            "currentTaskId": current_task_id or running_task.get("id") if running_task else current_task_id,
        }

    return {
        "locked": False,
        "reason": "project_idle",
        "message": "Proyecto sin agente activo: edicion humana habilitada.",
        "sessionId": state.get("session_id") or state.get("sessionId"),
        "projectStatus": state_status or "idle",
        "currentTaskId": None,
    }


def editor_file_payload(project_dir: Path, relative_path: str, file_path: Path) -> Dict[str, Any]:
    stat = file_path.stat()
    return {
        "path": relative_path,
        "name": PurePosixPath(relative_path).name,
        "size": stat.st_size,
        "language": detect_code_language(relative_path) or "text",
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def list_editor_files(project_dir: Path) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    for root, dir_names, file_names in os.walk(project_dir):
        root_path = Path(root)
        try:
            relative_root = normalize_relative_fragment(root_path.relative_to(project_dir))
        except ValueError:
            continue

        dir_names[:] = sorted(
            [
                dirname
                for dirname in dir_names
                if not is_editor_hidden_path(
                    normalize_relative_fragment(PurePosixPath(relative_root) / dirname)
                )
            ],
            key=str.lower,
        )

        for file_name in sorted(file_names, key=str.lower):
            relative_path = normalize_relative_fragment(PurePosixPath(relative_root) / file_name)
            if is_editor_hidden_path(relative_path):
                continue
            file_path = root_path / file_name
            if not file_path.is_file():
                continue
            try:
                stat = file_path.stat()
            except OSError:
                continue
            if stat.st_size > EDITOR_MAX_FILE_BYTES:
                continue
            files.append(editor_file_payload(project_dir, relative_path, file_path))
    return sorted(files, key=lambda item: str(item.get("path") or "").lower())


def build_code_scanner_report(project_slug: str, project_dir: Path) -> Dict[str, Any]:
    return build_code_scanner_report_service(
        project_slug,
        project_dir,
        list_editor_files=list_editor_files,
        resolve_editor_file=resolve_editor_file,
        report_name=CODE_SCANNER_REPORT_NAME,
        checkpoint_name=CODE_SCANNER_CHECKPOINT_NAME,
        now_provider=utc_now,
    )


def persist_code_scanner_report(project_dir: Path, report: Dict[str, Any]) -> Dict[str, str]:
    return persist_code_scanner_report_service(
        project_dir,
        report,
        report_name=CODE_SCANNER_REPORT_NAME,
        checkpoint_name=CODE_SCANNER_CHECKPOINT_NAME,
        build_agent_file_manifest=build_agent_file_manifest,
        persist_agent_file_manifest=persist_agent_file_manifest,
    )



integrity_service = IntegrityService(
    baseline_anchor_root=BASELINE_ANCHOR_ROOT,
    agent_file_manifest_name=AGENT_FILE_MANIFEST_NAME,
    agent_file_manifest_seal_name=AGENT_FILE_MANIFEST_SEAL_NAME,
    agent_baseline_seal_ledger_name=AGENT_BASELINE_SEAL_LEDGER_NAME,
    file_integrity_report_name=FILE_INTEGRITY_REPORT_NAME,
    observer_findings_report_name=OBSERVER_FINDINGS_REPORT_NAME,
    frozen_sniper_report_name=FROZEN_SNIPER_REPORT_NAME,
    file_write_ledger_name=FILE_WRITE_LEDGER_NAME,
    list_editor_files=lambda project_dir: list_editor_files(project_dir),
    resolve_editor_file=lambda project_dir, relative_path, must_exist=True: resolve_editor_file(
        project_dir,
        relative_path,
        must_exist=must_exist,
    ),
    load_json_file=lambda path, fallback: load_json_file(path, fallback),
    normalize_relative_fragment=lambda value: normalize_relative_fragment(value),
    normalize_project_id=lambda value: normalize_layer_name(value),
    now_provider=lambda: utc_now(),
)

integrity_artifacts_dir = integrity_service.artifacts_dir
agent_file_manifest_path = integrity_service.agent_file_manifest_path
agent_file_manifest_seal_path = integrity_service.agent_file_manifest_seal_path
baseline_vault_root = integrity_service.baseline_vault_root
baseline_seal_ledger_path = integrity_service.baseline_seal_ledger_path
baseline_vault_manifest_path = integrity_service.baseline_vault_manifest_path
baseline_external_anchor_dir = integrity_service.baseline_external_anchor_dir
baseline_external_anchor_path = integrity_service.baseline_external_anchor_path
baseline_external_anchor_ledger_path = integrity_service.baseline_external_anchor_ledger_path
file_integrity_report_path = integrity_service.file_integrity_report_path
observer_findings_report_path = integrity_service.observer_findings_report_path
frozen_sniper_report_path = integrity_service.frozen_sniper_report_path
frozen_sniper_root = integrity_service.frozen_sniper_root
file_write_ledger_path = integrity_service.file_write_ledger_path
build_agent_file_manifest = integrity_service.build_agent_file_manifest
canonical_json_sha256 = integrity_service.canonical_json_sha256
seal_sha256 = integrity_service.seal_sha256
baseline_signing_key = integrity_service.baseline_signing_key
baseline_anchor_signature = integrity_service.baseline_anchor_signature
build_baseline_external_anchor = integrity_service.build_baseline_external_anchor
build_agent_file_manifest_seal = integrity_service.build_agent_file_manifest_seal
persist_agent_file_manifest = integrity_service.persist_agent_file_manifest
append_file_write_ledger = integrity_service.append_file_write_ledger
read_file_write_ledger = integrity_service.read_file_write_ledger
registered_write_after_baseline = integrity_service.registered_write_after_baseline
line_col_for_content = integrity_service.line_col_for_content
integrity_text_findings = integrity_service.integrity_text_findings
baseline_protection_finding = integrity_service.baseline_protection_finding
load_external_anchor_manifest = integrity_service.load_external_anchor_manifest
verify_baseline_external_anchor = integrity_service.verify_baseline_external_anchor
load_protected_agent_file_manifest = integrity_service.load_protected_agent_file_manifest
build_file_integrity_report = integrity_service.build_file_integrity_report
frozen_sniper_run_id = integrity_service.frozen_sniper_run_id
relative_project_path = integrity_service.relative_project_path
unique_nested_path = integrity_service.unique_nested_path
freeze_existing_file = integrity_service.freeze_existing_file
build_frozen_sniper_recovery = integrity_service.build_frozen_sniper_recovery
persist_file_integrity_report = integrity_service.persist_file_integrity_report
persist_frozen_sniper_report = integrity_service.persist_frozen_sniper_report

def build_final_typewriter_report(
    project_slug: str,
    project_dir: Path,
    *,
    played_files: List[Any] | None = None,
    trigger: str = "runtime_terminal",
) -> Dict[str, Any]:
    editor_files = list_editor_files(project_dir)
    visible_paths = {str(entry["path"]) for entry in editor_files}
    requested_paths: List[str] = []
    for item in played_files or []:
        candidate = item.get("path") if isinstance(item, dict) else item
        normalized = normalize_relative_fragment(candidate)
        if normalized and normalized not in requested_paths:
            requested_paths.append(normalized)
    target_paths = requested_paths or [str(entry["path"]) for entry in editor_files]

    files: List[Dict[str, Any]] = []
    blockers: List[str] = []
    total_characters = 0
    total_lines = 0
    for relative_path in target_paths:
        if relative_path not in visible_paths:
            blockers.append(f"Archivo no visible para typewriter final: {relative_path}")
            continue
        resolved_file = resolve_editor_file(project_dir, relative_path)
        if resolved_file is None:
            blockers.append(f"Archivo no resoluble para typewriter final: {relative_path}")
            continue
        _, file_path = resolved_file
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            blockers.append(f"Archivo binario o no UTF-8: {relative_path}")
            continue
        except OSError as error:
            blockers.append(f"No se pudo leer {relative_path}: {error}")
            continue
        line_count = len(content.splitlines()) if content else 0
        character_count = len(content)
        total_lines += line_count
        total_characters += character_count
        files.append(
            {
                "path": relative_path,
                "language": detect_code_language(relative_path) or "text",
                "lineCount": line_count,
                "characterCount": character_count,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )

    if not files:
        blockers.append("El typewriter final no tiene archivos visibles para reproducir.")

    validation_passed = not blockers
    return {
        "schema_version": 1,
        "report_type": "final_typewriter",
        "projectId": project_slug,
        "generatedAt": utc_now(),
        "trigger": str(trigger or "runtime_terminal"),
        "typewriter": {
            "mode": "final-code-replay",
            "scope": "workspace_visible_source_files",
            "starts_at_line": 1,
            "left_to_right": True,
            "client_playback_required": True,
        },
        "summary": {
            "filesPlayed": len(files),
            "linesPlayed": total_lines,
            "charactersPlayed": total_characters,
        },
        "validation": {
            "passed": validation_passed,
            "blockers": blockers,
            "artifact": f"runtime/artifacts/{TYPEWRITER_REPORT_NAME}",
            "checkpoint": f"runtime/checkpoints/{TYPEWRITER_CHECKPOINT_NAME}",
        },
        "files": files,
    }


def persist_final_typewriter_report(project_dir: Path, report: Dict[str, Any]) -> Dict[str, str]:
    runtime_dir = project_dir / "runtime"
    artifacts_dir = runtime_dir / "artifacts"
    checkpoints_dir = runtime_dir / "checkpoints"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifacts_dir / TYPEWRITER_REPORT_NAME
    checkpoint_path = checkpoints_dir / TYPEWRITER_CHECKPOINT_NAME
    payload = json.dumps(report, ensure_ascii=True, indent=2)
    artifact_path.write_text(payload + "\n", encoding="utf-8")
    checkpoint_path.write_text(payload + "\n", encoding="utf-8")
    return {
        "artifactPath": str(artifact_path),
        "checkpointPath": str(checkpoint_path),
    }


def sandbox_state_path(project_dir: Path) -> Path:
    return sandbox_service.state_path(project_dir)


def sandbox_log_path(project_dir: Path) -> Path:
    return sandbox_service.log_path(project_dir)


def read_sandbox_state(project_dir: Path) -> Dict[str, Any]:
    return sandbox_service.read_state(project_dir)


def write_sandbox_state(project_dir: Path, state: Dict[str, Any]) -> None:
    sandbox_service.write_state(project_dir, state)


def pid_is_running(pid: Any) -> bool:
    return sandbox_service.pid_is_running(pid)


def port_is_available(port: int, host: str = SANDBOX_HOST) -> bool:
    return SandboxService.port_is_available(port, host)


def allocate_sandbox_port(project_slug: str) -> int:
    return sandbox_service.allocate_port(project_slug)


def detect_sandbox_plan(project_dir: Path, port: int) -> Dict[str, Any] | None:
    return sandbox_service.detect_plan(project_dir, port)


def sandbox_env(port: int) -> Dict[str, str]:
    return sandbox_service.env(port)


def sandbox_preview_url(port: int) -> str:
    return sandbox_service.preview_url(port)


def wait_for_sandbox_http_ready(
    url: str,
    process: subprocess.Popen[Any],
    *,
    timeout_seconds: float = SANDBOX_READY_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    return sandbox_service.wait_for_http_ready(url, process, timeout_seconds=timeout_seconds)


def terminate_process_group(process: subprocess.Popen[Any], *, timeout_seconds: float = 2.0) -> None:
    SandboxService.terminate_process_group(process, timeout_seconds=timeout_seconds)


def refresh_sandbox_state(project_slug: str, project_dir: Path) -> Dict[str, Any]:
    return sandbox_service.refresh_state(project_slug, project_dir)


def terminate_sandbox_process(project_slug: str, project_dir: Path, reason: str = "human_stop") -> Dict[str, Any]:
    return sandbox_service.terminate_process(project_slug, project_dir, reason=reason)


def start_project_sandbox(project_slug: str, project_dir: Path) -> Dict[str, Any]:
    return sandbox_service.start(project_slug, project_dir, allocate_port=allocate_sandbox_port)


def sandbox_log_tail(project_dir: Path, limit: int = 80) -> List[str]:
    return sandbox_service.log_tail(project_dir, limit=limit)



register_human_alignment_routes(
    app,
    resolve_editor_project=resolve_editor_project,
    build_editor_lock_state=build_editor_lock_state,
    socketio=socketio,
    agent_runtime=agent_runtime,
)


register_editor_routes(
    app,
    resolve_editor_project=lambda project_id: resolve_editor_project(project_id),
    build_editor_lock_state=lambda project_slug, project_dir: build_editor_lock_state(project_slug, project_dir),
    list_editor_files=lambda project_dir: list_editor_files(project_dir),
    resolve_editor_file=lambda project_dir, relative_path, must_exist=True: resolve_editor_file(
        project_dir,
        relative_path,
        must_exist=must_exist,
    ),
    editor_file_payload=lambda project_dir, relative_path, file_path: editor_file_payload(
        project_dir,
        relative_path,
        file_path,
    ),
    editor_max_file_bytes=EDITOR_MAX_FILE_BYTES,
    append_file_write_ledger=lambda *args, **kwargs: append_file_write_ledger(*args, **kwargs),
    load_json_file=lambda path, fallback: load_json_file(path, fallback),
    now_provider=lambda: utc_now(),
    normalize_graph=lambda payload: normalize_graph(payload),
    load_default_graph=lambda: load_default_graph(),
    sync_workspace_file=lambda graph, payload: sync_workspace_file(graph, payload),
    save_graph_state=lambda graph: save_graph_state(graph),
    socketio=socketio,
    workspace_graph_path=lambda project_slug, relative_path: workspace_graph_path(project_slug, relative_path),
    node_id_for_path=node_id_for_path,
    detect_code_language=detect_code_language,
    build_agent_repair_requirement=lambda *args, **kwargs: build_agent_repair_requirement(*args, **kwargs),
    suggested_repair_files=lambda relative_path, issue: suggested_repair_files(relative_path, issue),
    queue_agent_repair_task=lambda *args, **kwargs: queue_agent_repair_task(*args, **kwargs),
    agent_runtime=agent_runtime,
    sync_runtime_graph=lambda *args, **kwargs: sync_runtime_graph(*args, **kwargs),
    observer_plane_provider=lambda: observer_plane,
)

register_integrity_routes(
    app,
    resolve_editor_project=lambda project_id: resolve_editor_project(project_id),
    build_editor_lock_state=lambda project_slug, project_dir: build_editor_lock_state(project_slug, project_dir),
    observe_with_tool_event=lambda op, **kwargs: observe_with_tool_event(op, **kwargs),
    runtime_action_lock=_runtime_action_lock,
    code_scanner_locks=code_scanner_locks,
    integrity_action_locks=integrity_action_locks,
    load_json_file=lambda path, fallback: load_json_file(path, fallback),
    build_code_scanner_report=lambda project_slug, project_dir: build_code_scanner_report(project_slug, project_dir),
    persist_code_scanner_report=lambda project_dir, report: persist_code_scanner_report(project_dir, report),
    build_agent_file_manifest=lambda *args, **kwargs: build_agent_file_manifest(*args, **kwargs),
    persist_agent_file_manifest=lambda project_dir, manifest: persist_agent_file_manifest(project_dir, manifest),
    file_integrity_report_path=lambda project_dir: file_integrity_report_path(project_dir),
    observer_findings_report_path=lambda project_dir: observer_findings_report_path(project_dir),
    frozen_sniper_report_path=lambda project_dir: frozen_sniper_report_path(project_dir),
    build_file_integrity_report=lambda *args, **kwargs: build_file_integrity_report(*args, **kwargs),
    build_frozen_sniper_recovery=lambda *args, **kwargs: build_frozen_sniper_recovery(*args, **kwargs),
    build_observer_project_runtime_snapshot=lambda project_slug: build_observer_project_runtime_snapshot(project_slug),
    build_observer_findings_report=build_observer_findings_report,
    socketio=socketio,
    code_scanner_report_name=CODE_SCANNER_REPORT_NAME,
    agent_file_manifest_name=AGENT_FILE_MANIFEST_NAME,
    file_integrity_report_name=FILE_INTEGRITY_REPORT_NAME,
    frozen_sniper_report_name=FROZEN_SNIPER_REPORT_NAME,
    frozen_sniper_confirmation=FROZEN_SNIPER_CONFIRMATION,
)

@app.post("/api/projects/<project_id>/typewriter-final")
def persist_project_final_typewriter(project_id: str):
    resolved = resolve_editor_project(project_id)
    if resolved is None:
        return jsonify({"ok": False, "error": "project_not_found"}), 404
    project_slug, project_dir = resolved
    lock_state = build_editor_lock_state(project_slug, project_dir)
    if lock_state.get("locked"):
        return jsonify({"ok": False, "error": "project_locked", "lock": lock_state}), 423

    payload = request.get_json(silent=True) or {}
    try:
        report = build_final_typewriter_report(
            project_slug,
            project_dir,
            played_files=payload.get("playedFiles") if isinstance(payload, dict) else None,
            trigger=str(payload.get("trigger") or "runtime_terminal") if isinstance(payload, dict) else "runtime_terminal",
        )
        paths = persist_final_typewriter_report(project_dir, report)
    except OSError as error:
        return jsonify({"ok": False, "error": "typewriter_persist_failed", "message": str(error)}), 500

    socketio.emit(
        "agent:visual",
        {
            "op": "final_typewriter_complete",
            "projectSlug": project_slug,
            "message": (
                "Typewriter final persistido."
                if report["validation"]["passed"]
                else "Typewriter final bloqueado; revisa blockers."
            ),
            "phase": "final-typewriter",
            "status": "passed" if report["validation"]["passed"] else "blocked",
            "relativePath": f"runtime/artifacts/{TYPEWRITER_REPORT_NAME}",
        },
    )
    return jsonify(
        {
            "ok": True,
            "projectId": project_slug,
            "lock": lock_state,
            "report": report,
            **paths,
        }
    )



register_sandbox_routes(
    app,
    resolve_editor_project=lambda project_id: resolve_editor_project(project_id),
    refresh_sandbox_state=lambda project_slug, project_dir: refresh_sandbox_state(project_slug, project_dir),
    start_project_sandbox=lambda project_slug, project_dir: start_project_sandbox(project_slug, project_dir),
    terminate_sandbox_process=lambda *args, **kwargs: terminate_sandbox_process(*args, **kwargs),
    sandbox_log_tail=lambda project_dir, limit: sandbox_log_tail(project_dir, limit),
    socketio=socketio,
)

@app.get("/api/projects/<project_id>/reviewer-events")
def get_project_reviewer_events(project_id: str):
    project_dir = resolve_reviewer_project(project_id)
    if project_dir is None:
        return jsonify({"ok": False, "error": "project_not_found"}), 404
    session_id = str(request.args.get("sessionId") or "").strip() or None
    try:
        limit = int(request.args.get("limit") or 500)
    except ValueError:
        limit = 500
    events = load_reviewer_events(project_dir, session_id=session_id, limit=max(1, min(limit, 2000)))
    return jsonify({"ok": True, "projectId": normalize_layer_name(project_id), "events": events})


@app.get("/api/projects/<project_id>/reviewer-status")
def get_project_reviewer_status(project_id: str):
    project_dir = resolve_reviewer_project(project_id)
    if project_dir is None:
        return jsonify({"ok": False, "error": "project_not_found"}), 404
    requested_session_id = str(request.args.get("sessionId") or "").strip() or None
    active_session_ids = {
        str(session.get("sessionId") or "")
        for session in agent_runtime.list_sessions()
        if str(session.get("status") or "").strip().lower() in ACTIVE_AGENT_SESSION_STATUSES
    }
    session_id = requested_session_id if requested_session_id in active_session_ids else None
    status = build_reviewer_status(
        project_root=project_dir,
        runtime_dir=project_dir / "runtime",
        session_id=session_id,
        project_id=normalize_layer_name(project_id),
    )
    if requested_session_id and session_id is None and isinstance(status, dict):
        status["requested_session_id"] = requested_session_id
        status["requested_session_stale"] = True
        status["worker_alive"] = None
        status["worker_pid"] = None
    events = load_reviewer_events(project_dir, session_id=session_id, limit=200) if session_id else []
    return jsonify({"ok": True, "projectId": normalize_layer_name(project_id), "sessionId": session_id, "status": status, "events": events})


RUNTIME_TRUTH_STALE_SECONDS = 300


def _runtime_truth_queue_tasks(queue_payload: Any) -> List[Dict[str, Any]]:
    tasks = queue_payload.get("tasks") if isinstance(queue_payload, dict) else queue_payload
    return tasks if isinstance(tasks, list) else []


def _runtime_truth_queue_counts(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "blocked": 0}
    for task in tasks:
        status = str(task.get("status") or "pending").strip().lower() or "pending"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _runtime_truth_integrity(project_dir: Path) -> Dict[str, Any]:
    report = load_json_file(project_dir / "runtime" / "artifacts" / "file_integrity_report.json", {})
    findings = report.get("findings") if isinstance(report, dict) else []
    findings = findings if isinstance(findings, list) else []
    return {
        "hasReport": isinstance(report, dict) and bool(report),
        "baselineExists": report.get("baselineExists") if isinstance(report, dict) else None,
        "findings": len(findings),
        "status": report.get("status") if isinstance(report, dict) else None,
    }


def _runtime_truth_current_task(state: Any, queue_tasks: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    current_task_id = state.get("current_task_id") if isinstance(state, dict) else None
    if current_task_id:
        for task in queue_tasks:
            if task.get("id") == current_task_id:
                return task
    for target_status in ("running", "queued", "starting", "pending"):
        for task in queue_tasks:
            if str(task.get("status") or "").strip().lower() == target_status:
                return task
    return queue_tasks[-1] if queue_tasks else None


def _runtime_truth_latest_jsonl(path: Path) -> Dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        return payload if isinstance(payload, dict) else None
    return None


def _runtime_truth_latest_name(directory: Path) -> str | None:
    if not directory.exists() or not directory.is_dir():
        return None
    latest: tuple[float, str] | None = None
    try:
        for item in directory.iterdir():
            if not item.is_file():
                continue
            try:
                candidate = (item.stat().st_mtime, item.name)
            except OSError:
                continue
            if latest is None or candidate[0] > latest[0]:
                latest = candidate
    except OSError:
        return None
    return latest[1] if latest else None


def _runtime_truth_last_activity_epoch(project_dir: Path, runtime_dir: Path, current_task: Dict[str, Any] | None) -> float | None:
    # Keep this endpoint cheap enough for UI polling. Do not scan full logs/checkpoints.
    candidates: List[Path] = [
        runtime_dir / "project_state.json",
        runtime_dir / "task_queue.json",
        runtime_dir / "task_history.jsonl",
        runtime_dir / "failures.jsonl",
    ]
    expected_files = current_task.get("expected_files") if isinstance(current_task, dict) else []
    expected_files = expected_files if isinstance(expected_files, list) else []
    for relative_path in expected_files:
        try:
            candidate = (project_dir / str(relative_path)).resolve()
            candidate.relative_to(project_dir.resolve())
            candidates.append(candidate)
        except (OSError, ValueError):
            continue
    latest_epoch: float | None = None
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                mtime = candidate.stat().st_mtime
                latest_epoch = mtime if latest_epoch is None else max(latest_epoch, mtime)
        except OSError:
            continue
    return latest_epoch


def _runtime_truth_iso_from_epoch(epoch: float | None) -> str | None:
    if not isinstance(epoch, (int, float)):
        return None
    return datetime.fromtimestamp(float(epoch), timezone.utc).isoformat().replace("+00:00", "Z")


def _pid_is_alive(pid: Any) -> bool | None:
    try:
        normalized_pid = int(pid)
    except (TypeError, ValueError):
        return None
    if normalized_pid <= 0:
        return False
    try:
        os.kill(normalized_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _build_project_runtime_truth(project_slug: str, project_dir: Path) -> Dict[str, Any]:
    runtime_dir = project_dir / "runtime"
    lock_state = build_editor_lock_state(project_slug, project_dir)
    state = load_json_file(runtime_dir / "project_state.json", {})
    queue_payload = load_json_file(runtime_dir / "task_queue.json", [])
    queue_tasks = _runtime_truth_queue_tasks(queue_payload)
    queue_counts = _runtime_truth_queue_counts(queue_tasks)
    current_task = _runtime_truth_current_task(state, queue_tasks)
    running_tasks = [
        task
        for task in queue_tasks
        if str(task.get("status") or "").strip().lower() in ACTIVE_AGENT_SESSION_STATUSES
    ]
    runtime_sessions = agent_runtime.list_sessions()
    active_sessions = [
        session
        for session in runtime_sessions
        if session.get("projectSlug") == project_slug
        and str(session.get("status") or "").strip().lower() in ACTIVE_AGENT_SESSION_STATUSES
    ]
    sandbox = load_json_file(runtime_dir / "sandbox.json", {})
    last_epoch = _runtime_truth_last_activity_epoch(project_dir, runtime_dir, current_task)
    last_activity_age_seconds = None
    if isinstance(last_epoch, (int, float)):
        last_activity_age_seconds = max(0.0, time.time() - float(last_epoch))

    state_status = str(state.get("status") or "").strip().lower() if isinstance(state, dict) else ""
    current_task_id = (
        (current_task.get("id") if isinstance(current_task, dict) else None)
        or (state.get("current_task_id") if isinstance(state, dict) else None)
        or lock_state.get("currentTaskId")
    )
    persisted_running = bool(
        running_tasks
        or state_status in ACTIVE_AGENT_SESSION_STATUSES
        or (lock_state.get("locked") and lock_state.get("reason") == "control_plane_active")
    )
    worker_alive = None
    worker_pid = None
    running_without_pid = False
    for session in active_sessions:
        status = str(session.get("status") or "").strip().lower()
        session_pid = session.get("pid")
        if status == "running" and not session_pid:
            running_without_pid = True
            continue
        pid_alive = _pid_is_alive(session_pid)
        if pid_alive is not None:
            worker_pid = session_pid
            worker_alive = pid_alive
            if pid_alive:
                break
    has_recent_activity = last_activity_age_seconds is not None and last_activity_age_seconds < RUNTIME_TRUTH_STALE_SECONDS
    has_preparing_session = any(str(session.get("status") or "").strip().lower() == "preparing" for session in active_sessions)
    orphaned_persisted_running = bool(persisted_running and not active_sessions and worker_alive is not True)
    stale = bool(
        persisted_running
        and not has_preparing_session
        and worker_alive is not True
        and (not has_recent_activity or orphaned_persisted_running or running_without_pid)
    )
    if stale:
        verdict = "zombie"
    elif active_sessions or worker_alive is True:
        verdict = "live"
    elif persisted_running:
        verdict = "unverified_running"
    else:
        verdict = "idle"

    reasons: List[str] = []
    if not active_sessions:
        reasons.append("no_active_agent_session")
    if worker_alive is not True:
        reasons.append("no_live_worker_pid")
    if persisted_running:
        reasons.append("persisted_control_plane_running")
    if running_without_pid:
        reasons.append("running_session_without_pid")
    if not has_recent_activity:
        reasons.append("no_recent_disk_activity")
    if isinstance(sandbox, dict) and sandbox.get("running") is False:
        reasons.append("sandbox_stopped")

    latest_history = _runtime_truth_latest_jsonl(runtime_dir / "task_history.jsonl")
    warnings: List[Dict[str, Any]] = []
    if stale:
        warnings.append(
            {
                "code": "runtime_zombie_state",
                "severity": "error",
                "message": "Persisted running state without active preparing/running session or worker pid.",
            }
        )
    if running_without_pid:
        warnings.append(
            {
                "code": "running_session_without_pid",
                "severity": "error",
                "message": "A runtime session reported running with pid=null; this must be repaired to preparing or failed.",
            }
        )
    if state_status == "blocked" and queue_counts.get("pending", 0) and not queue_counts.get("blocked", 0) and not queue_counts.get("failed", 0):
        warnings.append(
            {
                "code": "blocked_state_with_pending_queue",
                "severity": "warning",
                "message": "Project state is blocked but the queue only has pending work.",
            }
        )

    return {
        "ok": True,
        "projectId": project_slug,
        "generatedAt": utc_now(),
        "verdict": verdict,
        "stale": stale,
        "staleThresholdSeconds": RUNTIME_TRUTH_STALE_SECONDS,
        "canReleaseZombie": stale,
        "reasons": reasons,
        "lock": lock_state,
        "sessions": {
            "activeCount": len(active_sessions),
            "active": active_sessions,
            "totalRuntimeSessions": len(runtime_sessions),
        },
        "controlPlane": {
            "persistedRunning": persisted_running,
            "projectStatus": state_status or lock_state.get("projectStatus") or "unknown",
            "currentTaskId": current_task_id,
            "currentTaskTitle": current_task.get("title") if isinstance(current_task, dict) else "",
            "currentTaskStatus": current_task.get("status") if isinstance(current_task, dict) else None,
            "queueCounts": queue_counts,
            "tasksTotal": len(queue_tasks),
            "tasksCompleted": queue_counts.get("completed", 0),
        },
        "worker": {
            "alive": worker_alive,
            "pid": worker_pid,
        },
        "disk": {
            "lastActivityAt": _runtime_truth_iso_from_epoch(last_epoch),
            "lastActivityAgeSeconds": last_activity_age_seconds,
        },
        "sandbox": {
            "status": sandbox.get("status") if isinstance(sandbox, dict) else None,
            "running": sandbox.get("running") if isinstance(sandbox, dict) else None,
            "ready": sandbox.get("ready") if isinstance(sandbox, dict) else None,
            "url": sandbox.get("url") if isinstance(sandbox, dict) else "",
            "stopReason": sandbox.get("stopReason") if isinstance(sandbox, dict) else None,
        },
        "integrity": _runtime_truth_integrity(project_dir),
        "reviewer": {
            "warningCount": len(warnings),
            "warnings": warnings,
            "latestHistory": latest_history,
            "latestCheckpoint": (state.get("checkpoints")[-1] if isinstance(state, dict) and isinstance(state.get("checkpoints"), list) and state.get("checkpoints") else None),
        },
    }


@app.get("/api/projects/<project_id>/runtime-truth")
def get_project_runtime_truth(project_id: str):
    resolved = resolve_editor_project(project_id)
    if resolved is None:
        return jsonify({"ok": False, "error": "project_not_found"}), 404
    project_slug, project_dir = resolved
    return jsonify(_build_project_runtime_truth(project_slug, project_dir))


def _latest_jsonl_records(path: Path, limit: int = 8) -> List[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    records: List[Dict[str, Any]] = []
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
        if len(records) >= limit:
            break
    return list(reversed(records))


def _latest_runtime_event_records(runtime_dir: Path, limit: int = 8) -> List[Dict[str, Any]]:
    logs_dir = runtime_dir / "logs"
    if not logs_dir.exists():
        return []
    event_files = sorted(logs_dir.glob("*-events.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    records: List[Dict[str, Any]] = []
    for event_file in event_files[:4]:
        records.extend(_latest_jsonl_records(event_file, limit=limit))
        if len(records) >= limit:
            break
    return records[-limit:]


def _build_runtime_monitor_response(project_slug: str, project_dir: Path, question: str) -> Dict[str, Any]:
    runtime_dir = project_dir / "runtime"
    truth = _build_project_runtime_truth(project_slug, project_dir)
    queue_payload = load_json_file(runtime_dir / "task_queue.json", [])
    queue_tasks = _runtime_truth_queue_tasks(queue_payload)
    queue_counts = _runtime_truth_queue_counts(queue_tasks)
    pending_tasks = [task for task in queue_tasks if str(task.get("status") or "").lower() == "pending"]
    running_tasks = [task for task in queue_tasks if str(task.get("status") or "").lower() == "running"]
    blocked_tasks = [task for task in queue_tasks if str(task.get("status") or "").lower() == "blocked"]
    failed_tasks = [task for task in queue_tasks if str(task.get("status") or "").lower() == "failed"]
    lace_pending = [task for task in pending_tasks if str(task.get("id") or "").startswith("LACE-")]
    latest_history = truth.get("reviewer", {}).get("latestHistory") if isinstance(truth.get("reviewer"), dict) else None
    latest_result = latest_history.get("result") if isinstance(latest_history, dict) else None
    latest_events = _latest_runtime_event_records(runtime_dir, limit=8)
    control_plane = truth.get("controlPlane") if isinstance(truth.get("controlPlane"), dict) else {}
    reviewer = truth.get("reviewer") if isinstance(truth.get("reviewer"), dict) else {}
    project_status = str(control_plane.get("projectStatus") or "").lower()
    latest_checkpoint = str(reviewer.get("latestCheckpoint") or "")
    latest_event = latest_events[-1] if latest_events else {}
    latest_event_op = str(latest_event.get("op") or latest_event.get("phase") or "") if isinstance(latest_event, dict) else ""
    active_sessions = truth.get("sessions", {}).get("active") if isinstance(truth.get("sessions"), dict) else []
    active_sessions = active_sessions if isinstance(active_sessions, list) else []

    observations: List[str] = []
    verdict = str(truth.get("verdict") or "unknown")
    observations.append(f"veredicto runtime: {verdict}")
    if project_status:
        observations.append(f"estado proyecto: {project_status}")
    if latest_checkpoint:
        observations.append(f"ultimo checkpoint: {latest_checkpoint}")
    observations.append(
        "cola: "
        f"{queue_counts.get('completed', 0)} completadas, "
        f"{queue_counts.get('pending', 0)} pendientes, "
        f"{queue_counts.get('running', 0)} corriendo, "
        f"{queue_counts.get('blocked', 0)} bloqueadas, "
        f"{queue_counts.get('failed', 0)} fallidas"
    )
    if active_sessions:
        session_labels = [str(session.get("sessionId") or "sin-id") + ":" + str(session.get("status") or "unknown") for session in active_sessions]
        observations.append("sesiones activas en memoria: " + ", ".join(session_labels[:4]))
    else:
        observations.append("no hay sesiones activas en memoria")
    if running_tasks:
        observations.append("tarea corriendo en cola: " + ", ".join(str(task.get("id")) for task in running_tasks[:4]))
    if pending_tasks:
        observations.append("siguiente pendiente: " + str(pending_tasks[0].get("id") or pending_tasks[0].get("title") or "sin-id"))
    if latest_result:
        task_id = latest_result.get("task_id") or "sin-id"
        validation = "paso" if latest_result.get("validation_passed") else "no paso"
        observations.append(f"ultimo cierre registrado: {task_id}, validacion {validation}")
    if latest_events:
        observations.append("ultimo evento visual: " + (latest_event_op or "evento"))

    issues: List[str] = []
    if project_status == "blocked":
        issues.append("runtime-truth marca el proyecto como blocked; el cierre aun no esta limpio")
    if latest_checkpoint == "lace-closure-gate-blocked":
        issues.append("el checkpoint de cierre LACE esta bloqueado")
    if latest_event_op == "session_blocked":
        issues.append("el ultimo evento del runtime reporta session_blocked")
    if lace_pending and not running_tasks:
        issues.append(
            f"hay {len(lace_pending)} tarea(s) LACE pendientes y ningun worker ejecutandolas ahora"
        )
    if failed_tasks:
        issues.append(f"hay {len(failed_tasks)} tarea(s) fallida(s)")
    if blocked_tasks:
        issues.append(f"hay {len(blocked_tasks)} tarea(s) bloqueada(s)")
    if truth.get("stale"):
        issues.append("el runtime parece zombie segun runtime-truth")
    if active_sessions and not running_tasks and pending_tasks:
        issues.append("hay sesion activa en memoria pero la cola no tiene worker running; posible sesion huerfana")

    lines = ["Monitor verde independiente:"]
    question_text = str(question or "").strip()
    if question_text:
        lines.append(f"Pregunta recibida: {question_text}")
    lines.append("")
    if running_tasks:
        current = running_tasks[0]
        lines.append(
            "Ahora mismo el runtime esta ejecutando "
            f"{current.get('id')} ({current.get('title') or 'sin titulo'})."
        )
    elif lace_pending:
        lines.append(
            "La tarea principal ya dejo evidencia, pero la sesion esta detenida en la fase LACE: "
            f"quedan {len(lace_pending)} ciclos pendientes y no veo worker activo ejecutandolos."
        )
    elif pending_tasks:
        lines.append(
            "Hay tareas pendientes listas o esperando dependencias, pero no veo una tarea corriendo en este instante."
        )
    elif project_status == "blocked" or latest_checkpoint == "lace-closure-gate-blocked" or latest_event_op == "session_blocked":
        lines.append("La cola ya no tiene tareas pendientes, pero el cierre del proyecto sigue bloqueado por la compuerta LACE.")
    elif queue_counts.get("completed", 0) and not failed_tasks and not blocked_tasks:
        lines.append("La cola aparece cerrada sin fallos activos.")
    else:
        lines.append("No veo ejecucion activa para este proyecto en este momento.")

    if latest_result:
        files = latest_result.get("files_modified") if isinstance(latest_result.get("files_modified"), list) else []
        validation = "paso" if latest_result.get("validation_passed") else "no paso"
        lines.append(
            f"Ultima evidencia: {latest_result.get('task_id') or 'sin-id'} cerro con validacion {validation}."
        )
        if files:
            lines.append("Archivos tocados: " + ", ".join(str(item) for item in files[:6]) + ("..." if len(files) > 6 else ""))
    if issues:
        lines.append("Riesgo detectado: " + "; ".join(issues) + ".")
    else:
        lines.append("No detecto bloqueo critico con la evidencia disponible.")
    if lace_pending and not running_tasks:
        lines.append(
            "Conclusion: toca reanudar la cola pendiente o liberar la sesion huerfana; no hace falta borrar el proyecto ni crear uno nuevo."
        )
    elif project_status == "blocked" or latest_checkpoint == "lace-closure-gate-blocked" or latest_event_op == "session_blocked":
        lines.append("Conclusion: no hay que relanzar todo desde cero; toca reparar la regla de cierre LACE o revisar por que solo acepta una parte de los ciclos como validos.")
    elif running_tasks:
        lines.append("Conclusion: el runtime esta trabajando; conviene seguir monitoreando eventos y validaciones reales.")

    return {
        "answer": "\n".join(lines),
        "observations": observations,
        "issues": issues,
        "truth": truth,
        "queueCounts": queue_counts,
        "pendingTaskIds": [str(task.get("id") or "") for task in pending_tasks if str(task.get("id") or "")],
        "runningTaskIds": [str(task.get("id") or "") for task in running_tasks if str(task.get("id") or "")],
        "latestEvents": latest_events,
    }


@app.post("/api/projects/<project_id>/runtime-monitor/ask")
def ask_project_runtime_monitor(project_id: str):
    resolved = resolve_editor_project(project_id)
    if resolved is None:
        return jsonify({"ok": False, "error": "project_not_found"}), 404
    payload = request.get_json(silent=True) or {}
    project_slug, project_dir = resolved
    question = str(payload.get("question") or payload.get("prompt") or "").strip()
    response = _build_runtime_monitor_response(project_slug, project_dir, question)
    socketio.emit(
        "agent:visual",
        {
            "op": "runtime_monitor_answer",
            "phase": "monitor-verde",
            "status": "completed",
            "projectSlug": project_slug,
            "message": response["answer"].splitlines()[0] if response.get("answer") else "Monitor verde respondio.",
        },
    )
    return jsonify({"ok": True, "projectId": project_slug, **response})


@app.post("/api/projects/<project_id>/runtime-zombie/release")
def release_project_runtime_zombie(project_id: str):
    resolved = resolve_editor_project(project_id)
    if resolved is None:
        return jsonify({"ok": False, "error": "project_not_found"}), 404
    project_slug, project_dir = resolved
    truth = _build_project_runtime_truth(project_slug, project_dir)
    if not truth.get("canReleaseZombie"):
        return jsonify({"ok": False, "error": "runtime_not_zombie", "truth": truth}), 409

    runtime_dir = project_dir / "runtime"
    queue_path = runtime_dir / "task_queue.json"
    state_path = runtime_dir / "project_state.json"
    queue_payload = load_json_file(queue_path, [])
    queue_tasks = _runtime_truth_queue_tasks(queue_payload)
    state_payload = load_json_file(state_path, {})

    backup_dir = runtime_dir / "backups" / "zombie_release" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir.mkdir(parents=True, exist_ok=True)
    if queue_path.exists():
        (backup_dir / "task_queue.before.json").write_text(queue_path.read_text(encoding="utf-8"), encoding="utf-8")
    if state_path.exists():
        (backup_dir / "project_state.before.json").write_text(state_path.read_text(encoding="utf-8"), encoding="utf-8")

    released_task_ids: List[str] = []
    release_time = utc_now()
    for task in queue_tasks:
        status = str(task.get("status") or "").strip().lower()
        if status in ACTIVE_AGENT_SESSION_STATUSES:
            task["status"] = "pending"
            task["previous_status"] = status
            task["requeued_reason"] = "runtime_truth_zombie_release"
            task["released_at"] = release_time
            if task.get("id"):
                released_task_ids.append(str(task.get("id")))

    if isinstance(queue_payload, dict):
        next_queue_payload = dict(queue_payload)
        next_queue_payload["tasks"] = queue_tasks
    else:
        next_queue_payload = queue_tasks
    runtime_dir.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(next_queue_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checkpoint_key = "runtime-zombie-recovered-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    failure_event = None
    checkpoint_path = None
    try:
        store = StateStore(runtime_dir)
        failure_event = store.append_failure(
            {
                "kind": "runtime_zombie_recovered",
                "project_id": project_slug,
                "released_task_ids": released_task_ids,
                "reason": "No active agent session, no live worker, and stale disk activity.",
            }
        )
        checkpoint_path = store.save_checkpoint(
            checkpoint_key,
            {
                "reason": "runtime_zombie_recovered",
                "project_id": project_slug,
                "released_task_ids": released_task_ids,
                "failure_event": failure_event,
                "backup_dir": str(backup_dir),
            },
        )
    except Exception:
        failure_event = None
        checkpoint_path = None

    if isinstance(state_payload, dict):
        state_payload["blocked_tasks"] = [
            item for item in state_payload.get("blocked_tasks", []) if str(item) not in released_task_ids
        ] if isinstance(state_payload.get("blocked_tasks"), list) else []
        state_payload["failed_tasks"] = [
            item for item in state_payload.get("failed_tasks", []) if str(item) not in released_task_ids
        ] if isinstance(state_payload.get("failed_tasks"), list) else []
        state_payload["status"] = "initialized"
        state_payload["current_task_id"] = None
        state_payload["last_released_zombie_task_ids"] = released_task_ids
        state_payload["last_released_zombie_at"] = release_time
        state_payload["last_released_zombie_reason"] = "No active agent session, no live worker, and stale disk activity."
        if checkpoint_path is not None:
            state_payload["checkpoints"] = _append_unique(state_payload.get("checkpoints", []), checkpoint_key)
        state_payload["updated_at"] = release_time
        state_path.write_text(json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    projects = list_agent_projects_snapshot()
    next_truth = _build_project_runtime_truth(project_slug, project_dir)
    socketio.emit("agent:projects", {"projects": projects})
    socketio.emit(
        "agent:visual",
        {
            "op": "runtime_zombie_released",
            "phase": "runtime-truth",
            "status": "blocked",
            "projectSlug": project_slug,
            "message": f"Supervisor real reencolo tarea zombie con backup: {', '.join(released_task_ids) or 'sin id'}.",
        },
    )
    return jsonify(
        {
            "ok": True,
            "projectId": project_slug,
            "releasedTaskIds": released_task_ids,
            "backupDir": str(backup_dir),
            "checkpointKey": checkpoint_key,
            "checkpointPath": str(checkpoint_path) if checkpoint_path is not None else None,
            "failureEvent": failure_event,
            "truth": next_truth,
            "projects": projects,
        }
    )


SUBAGENT_ARCHETYPES = [
    {
        "id": "S01",
        "name": "Planner",
        "role": "Descompone el prompt en pasos, riesgos y entregables.",
        "color": "#38bdf8",
        "kind": "planning",
    },
    {
        "id": "S02",
        "name": "Frontend",
        "role": "Implementa interfaz, canvas, estilos y experiencia visual.",
        "color": "#ec4899",
        "kind": "frontend",
    },
    {
        "id": "S03",
        "name": "Backend",
        "role": "Ajusta endpoints, runtime, persistencia y contratos.",
        "color": "#a855f7",
        "kind": "backend",
    },
    {
        "id": "S04",
        "name": "QA Browser",
        "role": "Valida navegador real, consola JS, screenshot, WebGL y HUD.",
        "color": "#22c55e",
        "kind": "validation",
    },
    {
        "id": "S05",
        "name": "Observer",
        "role": "Vigila incidentes, integridad, bloqueos y evidencia del mapa.",
        "color": "#f59e0b",
        "kind": "observer",
    },
    {
        "id": "S06",
        "name": "LACE Docs",
        "role": "Documenta ciclos, memoria, decisiones y cierre auditable.",
        "color": "#14b8a6",
        "kind": "documentation",
    },
    {
        "id": "S07",
        "name": "Performance",
        "role": "Revisa estabilidad, tamanos, bucles largos y uso de recursos.",
        "color": "#60a5fa",
        "kind": "performance",
    },
    {
        "id": "S08",
        "name": "Recovery",
        "role": "Prepara rollback, recuperacion y diagnostico cuando algo falla.",
        "color": "#ef4444",
        "kind": "recovery",
    },
]


def _estimate_project_file_count(project_slug: str) -> int:
    normalized_slug = normalize_layer_name(project_slug)
    if not normalized_slug:
        return 0
    project_dir = workspace_project_dir(normalized_slug).resolve()
    try:
        project_dir.relative_to(AGENT_PROJECTS_ROOT.resolve())
    except ValueError:
        return 0
    if not project_dir.exists() or not project_dir.is_dir():
        return 0
    ignored_parts = {".git", "node_modules", ".venv", "venv", "__pycache__", "runtime"}
    count = 0
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignored_parts for part in path.relative_to(project_dir).parts):
            continue
        count += 1
        if count >= 500:
            return count
    return count


def build_subagent_recommendation(payload: Dict[str, Any]) -> Dict[str, Any]:
    requirement = str(payload.get("requirement") or "").strip()
    runtime_mode = normalize_agent_runtime_mode(payload.get("runtimeMode") or payload.get("mode") or None)
    project_slug = normalize_layer_name(str(payload.get("projectSlug") or ""))
    launch_mode = str(payload.get("launchMode") or "").strip().lower() or ("existing" if project_slug else "new")
    file_count = _estimate_project_file_count(project_slug)
    estimate = estimate_complexity(
        requirement,
        runtime_mode=runtime_mode,
        project_file_count=file_count,
        launch_mode=launch_mode,
        project_slug=project_slug,
    )
    recommended = int(estimate.get("recommended_agents") or 1)
    recommended = max(1, min(len(SUBAGENT_ARCHETYPES), recommended))
    roster = [dict(agent, turn=index + 1) for index, agent in enumerate(SUBAGENT_ARCHETYPES[:recommended])]
    reasons = list(estimate.get("reasons") or [])
    if estimate.get("risk_flags"):
        reasons.append("riesgos: " + ", ".join(str(item) for item in estimate.get("risk_flags") or []))

    difficulty_label = str(estimate.get("difficulty_label") or estimate.get("difficulty") or "desconocida")
    cycles = int(estimate.get("recommended_lace_cycles") or 0)
    max_tasks = int(estimate.get("max_tasks") or 0)
    summary = (
        f"Dificultad {difficulty_label}: {recommended} subagente(s), "
        f"{cycles} ciclo(s) LACE y hasta {max_tasks} tarea(s)."
    )
    return {
        "id": f"SUBAGENTS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "runtimeMode": runtime_mode,
        "launchMode": launch_mode,
        "projectSlug": project_slug,
        "fileCount": file_count,
        "promptWordCount": estimate.get("prompt_word_count"),
        "difficulty": estimate.get("difficulty"),
        "difficultyLabel": difficulty_label,
        "complexityScore": estimate.get("score"),
        "recommendedAgents": recommended,
        "recommendedLaceCycles": cycles,
        "recommendedMaxTasks": max_tasks,
        "recommendedTimeoutSeconds": estimate.get("timeout_seconds"),
        "maxAgents": int(estimate.get("max_agents") or 8),
        "turnPolicy": "round_robin_serialized",
        "reasoningPolicy": "public_reasoning_only",
        "summary": summary,
        "reasons": reasons,
        "requiredTools": list(estimate.get("required_tools") or []),
        "complexityEstimate": estimate,
        "roster": roster,
    }


def normalize_subagent_plan(value: Any) -> Dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    roster = value.get("roster") if isinstance(value.get("roster"), list) else []
    clean_roster = []
    for index, item in enumerate(roster[:8], start=1):
        if not isinstance(item, dict):
            continue
        clean_roster.append(
            {
                "id": str(item.get("id") or f"S{index:02d}")[:12],
                "name": str(item.get("name") or f"Subagente {index}")[:40],
                "role": str(item.get("role") or "Apoyo operacional")[:220],
                "kind": str(item.get("kind") or "support")[:40],
                "turn": index,
            }
        )
    if not clean_roster:
        return None
    normalized = {
        "id": str(value.get("id") or f"SUBAGENTS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")[:80],
        "recommendedAgents": len(clean_roster),
        "turnPolicy": str(value.get("turnPolicy") or "round_robin_serialized")[:80],
        "reasoningPolicy": "public_reasoning_only",
        "summary": str(value.get("summary") or f"{len(clean_roster)} subagente(s) asignados.")[:260],
        "roster": clean_roster,
    }
    if isinstance(value.get("complexityEstimate"), dict):
        estimate = value["complexityEstimate"]
        normalized["complexityEstimate"] = estimate
        normalized["difficulty"] = value.get("difficulty") or estimate.get("difficulty")
        normalized["difficultyLabel"] = value.get("difficultyLabel") or estimate.get("difficulty_label")
        normalized["complexityScore"] = value.get("complexityScore") or estimate.get("score")
        normalized["recommendedLaceCycles"] = value.get("recommendedLaceCycles") or estimate.get("recommended_lace_cycles")
        normalized["recommendedMaxTasks"] = value.get("recommendedMaxTasks") or estimate.get("max_tasks")
        normalized["recommendedTimeoutSeconds"] = value.get("recommendedTimeoutSeconds") or estimate.get("timeout_seconds")
        normalized["requiredTools"] = list(value.get("requiredTools") or estimate.get("required_tools") or [])
    return normalized


def attach_subagent_plan_to_requirement(requirement: str, plan: Dict[str, Any] | None) -> str:
    if not plan:
        return requirement
    roster_lines = [
        f"- {agent['id']} {agent['name']} (turno {agent['turn']}): {agent['role']}"
        for agent in plan.get("roster", [])
    ]
    directive = "\n".join(
        [
            "PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:",
            f"Dictamen: {plan.get('summary')}",
            f"Dificultad: {plan.get('difficultyLabel') or plan.get('difficulty') or 'no declarada'} | score: {plan.get('complexityScore') or 'n/a'} | ciclos LACE: {plan.get('recommendedLaceCycles') or 'n/a'} | max tareas: {plan.get('recommendedMaxTasks') or 'n/a'}",
            f"Herramientas requeridas: {', '.join(str(item) for item in plan.get('requiredTools', [])) or 'segun directiva'}",
            f"Politica de turnos: {plan.get('turnPolicy')}",
            "Regla: escribir solo razonamiento publico, acciones, observaciones, evidencia y siguiente paso; no exponer cadena de pensamiento privada.",
            "Subagentes disponibles:",
            *(roster_lines or ["- S01 Apoyo: sin roster detallado"]),
            "El agente principal debe coordinar estos roles, evitar conflictos y reportar en consola eventos publicos por turno.",
        ]
    )
    return f"{requirement.rstrip()}\n\n{directive}\n"


@app.post("/api/agent/subagents/plan")
def plan_agent_subagents():
    payload = request.get_json(silent=True) or {}
    try:
        recommendation = build_subagent_recommendation(payload if isinstance(payload, dict) else {})
    except ValueError as error:
        return jsonify({"ok": False, "error": "invalid_runtime_mode", "message": str(error)}), 400
    socketio.emit(
        "agent:visual",
        {
            "op": "subagent_plan_ready",
            "phase": "orchestration",
            "status": "ready",
            "projectSlug": recommendation.get("projectSlug"),
            "message": recommendation.get("summary"),
            "subagentPlan": recommendation,
        },
    )
    return jsonify({"ok": True, "recommendation": recommendation})


@app.post("/api/agent/projects")
def create_agent_project():
    payload = request.get_json(silent=True) or {}
    project_name = str(payload.get("name") or f"nuevo-proyecto-{datetime.now().strftime('%H%M%S')}")
    ensure_unique = bool(payload.get("ensureUnique"))
    bootstrap = bool(payload.get("bootstrapProject", True))
    project = agent_runtime.create_project(project_name, ensure_unique=ensure_unique, bootstrap=bootstrap)
    projects = list_agent_projects_snapshot()
    socketio.emit("agent:projects", {"projects": projects})
    socketio.start_background_task(sync_runtime_graph, True)
    return jsonify({"ok": True, "project": project, "projects": projects})


@app.post("/api/agent/projects/<project_id>/delete")
def delete_agent_project(project_id: str):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_payload", "message": "El cuerpo debe ser JSON."}), 400

    normalized_slug = normalize_layer_name(project_id)
    if normalized_slug in PROTECTED_AGENT_PROJECTS:
        return jsonify({"ok": False, "error": "protected_project", "message": "Proyecto protegido; no se puede eliminar."}), 403
    if not payload.get("confirmDelete") or str(payload.get("projectSlug") or "") != normalized_slug:
        return jsonify({"ok": False, "error": "delete_confirmation_required", "message": "Confirmacion de eliminacion invalida."}), 400

    password = str(payload.get("password") or "")
    verified, auth_context, auth_error, auth_message, auth_status = verify_current_user_password(str(app.config.get("SECRET_KEY") or "architecture-view-dev"), password)
    if not verified:
        return jsonify({"ok": False, "error": auth_error, "message": auth_message}), auth_status

    project_dir = workspace_project_dir(normalized_slug).resolve()
    try:
        project_dir.relative_to(AGENT_PROJECTS_ROOT.resolve())
    except ValueError:
        return jsonify({"ok": False, "error": "invalid_project"}), 400
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify({"ok": False, "error": "project_not_found"}), 404

    active_statuses = {"queued", "preparing", "starting", "running"}
    active_sessions = []
    for session in agent_runtime.list_sessions():
        try:
            same_project = Path(session.get("projectDir") or "").resolve() == project_dir
        except OSError:
            same_project = False
        if same_project and str(session.get("status") or "").lower() in active_statuses:
            active_sessions.append(session.get("sessionId") or session.get("id") or "active")
    if active_sessions:
        return jsonify({"ok": False, "error": "project_runtime_active", "message": "Deten el runtime del proyecto antes de eliminarlo.", "sessions": active_sessions}), 409

    deleted_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = PROJECT_ROOT / "runtime" / "backups" / "deleted_projects" / deleted_at
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backup_root / normalized_slug
    suffix = 2
    while backup_dir.exists():
        backup_dir = backup_root / f"{normalized_slug}-{suffix}"
        suffix += 1

    shutil.copytree(project_dir, backup_dir)
    manifest = {
        "kind": "agent_project_deleted",
        "deletedAt": datetime.now(timezone.utc).isoformat(),
        "projectSlug": normalized_slug,
        "sourcePath": str(project_dir),
        "backupPath": str(backup_dir),
        "operatorUserId": (auth_context or {}).get("user", {}).get("id"),
        "operatorEmail": (auth_context or {}).get("user", {}).get("email"),
        "reason": "sidebar_project_delete_password_confirmed",
    }
    (backup_dir / ".deleted-project.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    shutil.rmtree(project_dir)

    projects = list_agent_projects_snapshot()
    socketio.emit("agent:projects", {"projects": projects})
    socketio.start_background_task(sync_runtime_graph, True)
    try:
        backup_relative = str(backup_dir.relative_to(PROJECT_ROOT))
    except ValueError:
        backup_relative = str(backup_dir)
    return jsonify({"ok": True, "deleted": manifest, "backupRelativePath": backup_relative, "projects": projects})


@app.post("/api/agent/projects/<project_id>/archive")
def archive_agent_project(project_id: str):
    normalized_slug = normalize_layer_name(project_id)
    if normalized_slug in PROTECTED_AGENT_PROJECTS:
        return jsonify({"ok": False, "error": "protected_project", "message": "Proyecto protegido; no se puede archivar desde la UI."}), 403

    project_dir = workspace_project_dir(normalized_slug).resolve()
    try:
        project_dir.relative_to(AGENT_PROJECTS_ROOT.resolve())
    except ValueError:
        return jsonify({"ok": False, "error": "invalid_project"}), 400
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify({"ok": False, "error": "project_not_found"}), 404

    active_statuses = {"queued", "preparing", "starting", "running"}
    active_sessions = []
    for session in agent_runtime.list_sessions():
        try:
            same_project = Path(session.get("projectDir") or "").resolve() == project_dir
        except OSError:
            same_project = False
        if same_project and str(session.get("status") or "").lower() in active_statuses:
            active_sessions.append(session.get("sessionId") or session.get("id") or "active")
    if active_sessions:
        return jsonify({"ok": False, "error": "project_runtime_active", "message": "Deten el runtime del proyecto antes de archivarlo.", "sessions": active_sessions}), 409

    archived_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = PROJECT_ROOT / "runtime" / "backups" / "archived_projects" / archived_at
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backup_root / normalized_slug
    suffix = 2
    while backup_dir.exists():
        backup_dir = backup_root / f"{normalized_slug}-{suffix}"
        suffix += 1
    shutil.move(str(project_dir), str(backup_dir))

    manifest = {
        "kind": "agent_project_archived",
        "archivedAt": datetime.now(timezone.utc).isoformat(),
        "projectSlug": normalized_slug,
        "sourcePath": str(project_dir),
        "backupPath": str(backup_dir),
        "reason": "sidebar_project_archive",
    }
    (backup_dir / ".archived-project.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    projects = list_agent_projects_snapshot()
    socketio.emit("agent:projects", {"projects": projects})
    socketio.start_background_task(sync_runtime_graph, True)
    try:
        backup_relative = str(backup_dir.relative_to(PROJECT_ROOT))
    except ValueError:
        backup_relative = str(backup_dir)
    return jsonify({"ok": True, "archived": manifest, "backupRelativePath": backup_relative, "projects": projects})


def clear_pending_project_queue(
    project_slug: str,
    statuses: List[str] | None = None,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    normalized_slug = normalize_layer_name(project_slug)
    project_dir = workspace_project_dir(normalized_slug).resolve()
    try:
        project_dir.relative_to(AGENT_PROJECTS_ROOT.resolve())
    except ValueError:
        return {"ok": False, "error": "invalid_project"}
    if not project_dir.exists() or not project_dir.is_dir():
        return {"ok": False, "error": "project_not_found"}

    active_statuses = {"queued", "preparing", "starting", "running"}
    stopped_sessions: List[str] = []
    if force:
        for session in agent_runtime.list_sessions():
            session_id = str(session.get("sessionId") or "")
            if not session_id or session.get("projectSlug") != normalized_slug:
                continue
            if str(session.get("status") or "").strip().lower() not in active_statuses:
                continue
            try:
                agent_runtime.stop_session(session_id)
            except Exception:
                pass
            stopped_sessions.append(session_id)
        if hasattr(agent_runtime, "lock") and hasattr(agent_runtime, "sessions"):
            with agent_runtime.lock:  # type: ignore[attr-defined]
                for session_id in stopped_sessions:
                    session_obj = agent_runtime.sessions.get(session_id)  # type: ignore[attr-defined]
                    if session_obj is None:
                        continue
                    now_value = utc_now()
                    session_obj.stop_requested = True
                    session_obj.status = "stopped"
                    session_obj.returncode = -15
                    session_obj.error_code = "manual_queue_force_clear"
                    session_obj.error_message = "Sesion detenida por limpieza forzada de colas."
                    session_obj.progress_label = "Sesion detenida por limpieza forzada de colas."
                    session_obj.updated_at = now_value
                    session_obj.ended_at = now_value

    lock_state = build_editor_lock_state(normalized_slug, project_dir)
    if lock_state.get("locked") and not force:
        return {"ok": False, "error": "project_locked", "lock": lock_state}

    requested_statuses = {
        str(status or "").strip().lower()
        for status in (statuses or ["pending", "blocked"])
        if str(status or "").strip()
    }
    target_statuses = requested_statuses or {"pending", "blocked"}
    if force:
        target_statuses.update(active_statuses)
        target_statuses.update({"pending", "blocked"})
    runtime_dir = project_dir / "runtime"
    queue_path = runtime_dir / "task_queue.json"
    state_path = runtime_dir / "project_state.json"
    queue_payload = load_json_file(queue_path, [])
    queue_tasks = queue_payload.get("tasks") if isinstance(queue_payload, dict) else queue_payload
    queue_tasks = queue_tasks if isinstance(queue_tasks, list) else []

    removed_tasks = [
        task
        for task in queue_tasks
        if str(task.get("status") or "").strip().lower() in target_statuses
    ]
    removed_ids = [str(task.get("id") or "") for task in removed_tasks if str(task.get("id") or "")]
    removed_id_set = set(removed_ids)
    retained_tasks = [task for task in queue_tasks if str(task.get("id") or "") not in removed_id_set]

    backup_dir = RUNTIME_ROOT / "backups" / "pending_queue_clear" / normalized_slug / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir.mkdir(parents=True, exist_ok=True)
    if queue_path.exists():
        (backup_dir / "task_queue.before.json").write_text(queue_path.read_text(encoding="utf-8"), encoding="utf-8")
    if state_path.exists():
        (backup_dir / "project_state.before.json").write_text(state_path.read_text(encoding="utf-8"), encoding="utf-8")

    if isinstance(queue_payload, dict):
        next_queue_payload = dict(queue_payload)
        next_queue_payload["tasks"] = retained_tasks
    else:
        next_queue_payload = retained_tasks
    runtime_dir.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(next_queue_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    state_payload = load_json_file(state_path, {})
    if isinstance(state_payload, dict):
        state_payload["blocked_tasks"] = [
            item
            for item in state_payload.get("blocked_tasks", [])
            if str(item or "") not in removed_id_set
        ]
        if "pending_control_plane_work" in state_payload:
            state_payload["pending_control_plane_work"] = [
                item
                for item in state_payload.get("pending_control_plane_work", [])
                if str(item or "") not in removed_id_set
            ]
        if state_payload.get("current_task_id") in removed_id_set or force:
            state_payload["current_task_id"] = None
        has_active_queue = any(
            str(task.get("status") or "").strip().lower() in active_statuses
            for task in retained_tasks
        )
        has_pending_or_blocked = any(
            str(task.get("status") or "").strip().lower() in {"pending", "blocked"}
            for task in retained_tasks
        )
        if force and not has_active_queue and not has_pending_or_blocked:
            state_payload["status"] = "stopped"
        elif not has_active_queue and str(state_payload.get("status") or "").strip().lower() in active_statuses:
            state_payload["status"] = "completed"
        state_payload["last_queue_clear_at"] = utc_now()
        state_payload["last_queue_clear_force"] = bool(force)
        state_payload["last_queue_clear_removed_task_ids"] = removed_ids
        state_payload["updated_at"] = utc_now()
        state_path.write_text(json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "projectId": normalized_slug,
        "force": bool(force),
        "stoppedSessions": stopped_sessions,
        "removedCount": len(removed_tasks),
        "removedTaskIds": removed_ids,
        "remainingCount": len(retained_tasks),
        "backupDir": str(backup_dir),
        "lock": build_editor_lock_state(normalized_slug, project_dir),
    }


@app.post("/api/agent/projects/<project_id>/pending-queue/clear")
def clear_agent_project_pending_queue(project_id: str):
    payload = request.get_json(silent=True) or {}
    statuses = payload.get("statuses") if isinstance(payload.get("statuses"), list) else None
    force = bool(payload.get("force"))
    result = clear_pending_project_queue(project_id, statuses=statuses, force=force)
    if result.get("error") == "project_locked":
        return jsonify(result), 423
    if result.get("error") in {"invalid_project", "project_not_found"}:
        return jsonify(result), 404
    projects = list_agent_projects_snapshot()
    result["projects"] = projects
    socketio.emit("agent:projects", {"projects": projects})
    socketio.emit(
        "agent:visual",
        {
            "op": "pending_queue_cleared",
            "phase": "cleanup",
            "status": "completed",
            "projectSlug": result.get("projectId"),
            "message": f"Colas pendientes borradas: {result.get('removedCount', 0)} tarea(s).",
        },
    )

    return jsonify(result)


RETRY_REAL_BROWSER_RULE = """Regla de cierre obligatoria:
No marcar completado solo porque existen archivos. Antes de cerrar debe pasar prueba real de navegador:
- abrir el juego en navegador o sandbox
- comprobar que existe canvas
- comprobar WebGL activo o fallback funcional
- consola JS sin excepciones
- screenshot no negro
- HUD o telemetria actualiza
- si falla, dejar tarea blocked con evidencia, no completed"""


def _task_queue_items(payload: Any) -> List[Dict[str, Any]]:
    tasks = payload.get("tasks") if isinstance(payload, dict) else payload
    if not isinstance(tasks, list):
        return []
    return [task for task in tasks if isinstance(task, dict)]


def _retryable_snapshot_paths(project_slug: str, project_dir: Path) -> List[Path]:
    normalized_slug = normalize_layer_name(project_slug)
    paths: List[Path] = []
    paths.extend((project_dir / "runtime" / "backups").glob("**/task_queue.before.json"))
    paths.extend((RUNTIME_ROOT / "backups" / "pending_queue_clear" / normalized_slug).glob("*/task_queue.before.json"))
    queue_path = project_dir / "runtime" / "task_queue.json"
    if queue_path.exists():
        paths.append(queue_path)
    return sorted({path.resolve() for path in paths if path.exists()}, key=lambda item: item.stat().st_mtime, reverse=True)


def _retryable_task_score(task: Dict[str, Any], source_path: Path) -> int:
    task_id = str(task.get("id") or "")
    status = str(task.get("status") or "").strip().lower()
    title = str(task.get("title") or "").strip().lower()
    goal = str(task.get("goal") or "").strip()
    score = 0
    if task_id.startswith("RUNTIME-"):
        score += 120
    if task_id.startswith("REPAIR-"):
        score -= 60
    if status == "blocked":
        score += 46
    elif status in {"failed", "pending"}:
        score += 40
    elif status == "running":
        score += 34
    if status == "completed":
        score -= 80
    if "reparar punto rojo" in title or "modo reparacion agentica" in goal.lower():
        score -= 35
    if "browser_render_smoke.py" in "\n".join(str(command) for command in task.get("validation_commands", [])):
        score += 15
    return score


def _find_retryable_project_task(project_slug: str, task_id: str | None = None) -> Dict[str, Any] | None:
    normalized_slug = normalize_layer_name(project_slug)
    project_dir = workspace_project_dir(normalized_slug).resolve()
    try:
        project_dir.relative_to(AGENT_PROJECTS_ROOT.resolve())
    except ValueError:
        return None
    if not project_dir.exists() or not project_dir.is_dir():
        return None

    candidates: List[Dict[str, Any]] = []
    for source_path in _retryable_snapshot_paths(normalized_slug, project_dir):
        source_payload = load_json_file(source_path, [])
        for task in _task_queue_items(source_payload):
            current_id = str(task.get("id") or "").strip()
            goal = str(task.get("goal") or "").strip()
            if not current_id or not goal:
                continue
            if task_id and current_id != task_id:
                continue
            source_mtime = source_path.stat().st_mtime
            candidates.append(
                {
                    "task": dict(task),
                    "sourcePath": str(source_path),
                    "sourceMtime": source_mtime,
                    "score": _retryable_task_score(task, source_path),
                }
            )

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item["score"], item["sourceMtime"]), reverse=True)
    selected = candidates[0]
    task = selected["task"]
    goal = str(task.get("goal") or "").strip()
    return {
        "id": str(task.get("id") or ""),
        "title": str(task.get("title") or ""),
        "status": str(task.get("status") or ""),
        "mode": str(task.get("mode") or "build"),
        "goal": goal,
        "goalPreview": goal[:260],
        "expectedFiles": [str(item) for item in task.get("expected_files", []) if str(item).strip()],
        "validationCommands": [str(item) for item in task.get("validation_commands", []) if str(item).strip()],
        "sourcePath": selected["sourcePath"],
        "sourceMtime": selected["sourceMtime"],
        "score": selected["score"],
    }


def _project_display_name(project_dir: Path, fallback_slug: str) -> str:
    metadata = load_json_file(project_dir / ".agent-project.json", {})
    if isinstance(metadata, dict) and str(metadata.get("name") or "").strip():
        return str(metadata.get("name")).strip()
    return fallback_slug


def _build_retry_requirement(project_slug: str, retryable_task: Dict[str, Any]) -> str:
    expected_files = retryable_task.get("expectedFiles") if isinstance(retryable_task.get("expectedFiles"), list) else []
    validation_commands = retryable_task.get("validationCommands") if isinstance(retryable_task.get("validationCommands"), list) else []
    expected_label = "\n".join(f"- {item}" for item in expected_files) or "- usar los archivos del proyecto existente"
    validation_label = "\n".join(f"- {item}" for item in validation_commands) or "- ejecutar validacion real disponible"
    return "\n\n".join(
        [
            "MODO EJECUCION AGENTICA CONTROLADA.",
            f"Proyecto existente: {project_slug}.",
            "No crear proyecto nuevo. No cambiar workspace. No blanquear el proyecto. Trabajar como refactor/continuacion sobre los archivos actuales.",
            f"Retomar la orden recuperada de la tarea {retryable_task.get('id')}. Relanzarla como ejecucion limpia de runtime, no como proyecto nuevo.",
            "Orden original:\n" + str(retryable_task.get("goal") or "").strip(),
            RETRY_REAL_BROWSER_RULE,
            "Entregables esperados:\n" + expected_label,
            "Validacion obligatoria:\n" + validation_label,
        ]
    )


@app.get("/api/agent/projects/<project_id>/retryable-task")
def get_agent_project_retryable_task(project_id: str):
    retryable_task = _find_retryable_project_task(project_id, request.args.get("taskId"))
    if retryable_task is None:
        return jsonify({"ok": False, "error": "retryable_task_not_found"}), 404
    return jsonify({"ok": True, "projectId": normalize_layer_name(project_id), "task": retryable_task})


@app.post("/api/agent/projects/<project_id>/retryable-task/relaunch")
def relaunch_agent_project_retryable_task(project_id: str):
    payload = request.get_json(silent=True) or {}
    project_slug = normalize_layer_name(project_id)
    project_dir = workspace_project_dir(project_slug).resolve()
    try:
        project_dir.relative_to(AGENT_PROJECTS_ROOT.resolve())
    except ValueError:
        return jsonify({"ok": False, "error": "invalid_project"}), 404
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify({"ok": False, "error": "project_not_found"}), 404

    retryable_task = _find_retryable_project_task(project_slug, str(payload.get("taskId") or "").strip() or None)
    if retryable_task is None:
        return jsonify({"ok": False, "error": "retryable_task_not_found"}), 404

    try:
        runtime_mode = normalize_agent_runtime_mode(payload.get("runtimeMode") or retryable_task.get("mode") or None)
    except ValueError as error:
        return jsonify({"ok": False, "error": "invalid_runtime_mode", "message": str(error)}), 400

    cleanup_result = None
    if bool(payload.get("forceClean", True)):
        cleanup_result = clear_pending_project_queue(
            project_slug,
            statuses=["queued", "starting", "running", "pending", "blocked"],
            force=True,
        )
        if cleanup_result.get("ok") is False:
            status_code = 423 if cleanup_result.get("error") == "project_locked" else 400
            return jsonify(cleanup_result), status_code

    requirement = _build_retry_requirement(project_slug, retryable_task)
    subagent_plan = normalize_subagent_plan(payload.get("subagentPlan") or payload.get("subagents"))
    prepared_requirement = attach_subagent_plan_to_requirement(requirement, subagent_plan)
    project_name = _project_display_name(project_dir, project_slug)
    session = agent_runtime.start_session(
        requirement=prepared_requirement,
        project_name=project_name,
        project_slug=project_slug,
        bootstrap=False,
        ensure_new_project=False,
        mode=runtime_mode,
    )
    projects = list_agent_projects_snapshot()
    sync_runtime_graph(save_state=True)
    socketio.emit("agent:projects", {"projects": projects})
    socketio.emit(
        "agent:visual",
        {
            "op": "retryable_task_relaunched",
            "phase": "runtime-retry",
            "status": "running",
            "projectSlug": project_slug,
            "message": f"Orden recuperada relanzada sobre el mismo proyecto: {retryable_task.get('id')}.",
        },
    )
    return jsonify(
        {
            "ok": True,
            "projectId": project_slug,
            "session": session,
            "task": retryable_task,
            "cleanup": cleanup_result,
            "projects": projects,
            "subagentPlan": subagent_plan,
        }
    )


runtime_admin_service = RuntimeAdminService(
    agent_runtime=agent_runtime,
    projects_root_provider=lambda: AGENT_PROJECTS_ROOT,
    observer_memory_file=OBSERVER_MEMORY_FILE,
    observer_timeline_file=OBSERVER_TIMELINE_FILE,
    email_command_root=EMAIL_COMMAND_ROOT,
    save_analysis_state=save_analysis_state,
    create_blank_view_graph=create_blank_view_graph,
    save_graph_state=save_graph_state,
    normalize_graph=normalize_graph,
    observer_plane_provider=lambda: observer_plane,
    socketio=socketio,
)

remove_children = runtime_admin_service.remove_children
remove_existing_files = runtime_admin_service.remove_existing_files
clear_runtime_workspace_state = runtime_admin_service.clear_workspace_state

register_runtime_admin_routes(
    app,
    default_reset_port=DEFAULT_RUNTIME_RESET_PORT,
    default_reset_host=DEFAULT_RUNTIME_RESET_HOST,
    clean_workspace_keyword=CLEAN_WORKSPACE_KEYWORD,
    project_root=PROJECT_ROOT,
    workspace_root=AGENT_WORKSPACE_ROOT,
    runtime_root=RUNTIME_ROOT,
    normalize_runtime_mode=normalize_agent_runtime_mode,
    schedule_runtime_reset=lambda *args, **kwargs: schedule_runtime_reset(*args, **kwargs),
    decidir_y_justificar_blanqueo=lambda *args, **kwargs: decidir_y_justificar_blanqueo(*args, **kwargs),
    record_blanqueo_decision=lambda *args, **kwargs: record_blanqueo_decision(*args, **kwargs),
    create_blanqueo_backup=lambda *args, **kwargs: create_blanqueo_backup(*args, **kwargs),
    apply_selective_blanqueo=lambda *args, **kwargs: apply_selective_blanqueo(*args, **kwargs),
    create_post_blanqueo_recovery=lambda *args, **kwargs: create_post_blanqueo_recovery(*args, **kwargs),
    clear_runtime_workspace_state=lambda: clear_runtime_workspace_state(),
    agent_runtime=agent_runtime,
    socketio=socketio,
)

@app.get("/api/agent/sessions")
def get_agent_sessions():
    return jsonify({"sessions": agent_runtime.list_sessions()})


@app.get("/api/agent/session/<session_id>")
def get_agent_session(session_id: str):
    session = agent_runtime.get_session(session_id)
    if session is None:
        return jsonify({"ok": False, "error": "session_not_found"}), 404
    return jsonify({"ok": True, "session": session})


@app.post("/api/agent/session")
def start_agent_session():
    payload = request.get_json(silent=True) or {}
    requirement = str(payload.get("requirement") or "").strip()
    project_name = str(payload.get("projectName") or payload.get("projectSlug") or "").strip()
    project_slug = str(payload.get("projectSlug") or "").strip()
    ensure_new_project = bool(payload.get("ensureNewProject"))
    bootstrap = bool(payload.get("bootstrapProject", True))
    try:
        runtime_mode = normalize_agent_runtime_mode(payload.get("runtimeMode") or payload.get("mode") or None)
    except ValueError as error:
        return jsonify({"ok": False, "error": "invalid_runtime_mode", "message": str(error)}), 400

    if not requirement:
        return jsonify({"ok": False, "error": "missing_requirement"}), 400

    if not project_name:
        project_name = f"proyecto-{datetime.now().strftime('%H%M%S')}"

    subagent_plan = normalize_subagent_plan(payload.get("subagentPlan") or payload.get("subagents"))
    prepared_requirement = attach_subagent_plan_to_requirement(requirement, subagent_plan)
    session = agent_runtime.start_session(
        requirement=prepared_requirement,
        project_name=project_name,
        project_slug=project_slug or None,
        bootstrap=bootstrap,
        ensure_new_project=ensure_new_project,
        mode=runtime_mode,
    )
    if subagent_plan:
        socketio.emit(
            "agent:visual",
            {
                "op": "subagents_assigned",
                "phase": "orchestration",
                "status": "preparing",
                "projectSlug": session.get("projectSlug") or project_slug,
                "message": f"{subagent_plan.get('recommendedAgents')} subagente(s) asignados a la sesion.",
                "subagentPlan": subagent_plan,
            },
        )
    def refresh_agent_projects_snapshot() -> None:
        try:
            socketio.emit("agent:projects", {"projects": list_agent_projects_snapshot()})
        except Exception:
            app.logger.exception("agent_projects_snapshot_refresh_failed")

    socketio.start_background_task(sync_runtime_graph, True)
    socketio.start_background_task(refresh_agent_projects_snapshot)
    return jsonify({"ok": True, "session": session, "subagentPlan": subagent_plan})


@app.post("/api/agent/session/<session_id>/stop")
def stop_agent_session(session_id: str):
    session = agent_runtime.stop_session(session_id)
    if session is None:
        return jsonify({"ok": False, "error": "session_not_found"}), 404
    return jsonify({"ok": True, "session": session})


@socketio.on("connect")
def handle_connect():
    start_email_command_dispatcher()
    # App.jsx asks for the full graph with architecture:request. Avoid sending
    # multi-MB architecture payloads to every auxiliary socket on handshake.
    emit("agent:projects", {"projects": list_agent_projects_snapshot()})
    emit("reverse:sessions", {"sessions": list_analysis_sessions()})
    emit(
        "agent:observer",
        {
            "op": "observer_status",
            "enabled": observer_plane.enabled,
            "state": observer_plane.context.state,
            "observer": observer_status_payload(),
            "message": "Observer Plane conectado.",
        },
    )
    emit(
        "agent:email_command",
        {
            "op": "email_command_status",
            "source": "email_command_plane",
            "emailStatus": email_command_plane.status(),
            "message": "Email Command Plane conectado.",
        },
    )
    for session in agent_runtime.list_sessions():
        emit("agent:session", session)


@socketio.on("architecture:request")
def handle_architecture_request(_payload=None):
    emit("architecture:update", normalize_graph(load_default_graph()))


@socketio.on("architecture:reset-view")
def handle_architecture_reset_view(_payload=None):
    save_analysis_state({"analyses": []})
    graph = normalize_graph(create_blank_view_graph())
    save_graph_state(graph)
    socketio.emit("reverse:sessions", {"sessions": []})
    socketio.emit("architecture:update", graph)
    return {"ok": True, "graph": graph, "sessions": []}


@socketio.on("architecture:demo-habla")
def handle_architecture_demo_habla(_payload=None):
    save_analysis_state({"analyses": []})
    graph = normalize_graph(create_habla_architecture_demo_graph())
    save_graph_state(graph)
    socketio.emit("reverse:sessions", {"sessions": []})
    socketio.emit("architecture:update", graph)
    return {"ok": True, "graph": graph, "sessions": []}


@socketio.on("reverse:request")
def handle_reverse_request(_payload=None):
    emit("reverse:sessions", {"sessions": list_analysis_sessions()})
    return {"ok": True}


@socketio.on("reverse:analyze")
def handle_reverse_analyze(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    target_path = str(payload.get("targetPath") or "").strip()
    if not target_path:
        return {"ok": False, "error": "missing_target_path"}

    try:
        entry = build_analysis_entry(target_path)
    except FileNotFoundError as error:
        return {"ok": False, "error": "target_not_found", "message": str(error)}
    except ValueError as error:
        return {"ok": False, "error": "analysis_failed", "message": str(error)}
    except OSError as error:
        return {"ok": False, "error": "analysis_io_error", "message": str(error)}

    sessions = upsert_analysis_entry(entry)
    graph = normalize_graph(load_default_graph())
    socketio.emit("architecture:update", graph)
    socketio.emit("reverse:sessions", {"sessions": sessions})
    return {"ok": True, "entry": summarize_analysis_entry(entry), "sessions": sessions}


@socketio.on("reverse:remove")
def handle_reverse_remove(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    analysis_id = str(payload.get("analysisId") or "").strip()
    if not analysis_id:
        return {"ok": False, "error": "missing_analysis_id"}

    sessions = remove_analysis_entry(analysis_id)
    graph = normalize_graph(load_default_graph())
    socketio.emit("architecture:update", graph)
    socketio.emit("reverse:sessions", {"sessions": sessions})
    return {"ok": True, "sessions": sessions}


@socketio.on("reverse:agent-transcribe")
def handle_reverse_agent_transcribe(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    target_path = str(payload.get("targetPath") or "").strip()
    if not target_path:
        return {"ok": False, "error": "missing_target_path"}

    resolved_target = Path(target_path).expanduser().resolve()
    if not resolved_target.exists():
        return {"ok": False, "error": "target_not_found", "message": f"No existe la ruta: {resolved_target}"}

    project_name = f"transcribe-{resolved_target.stem if resolved_target.is_file() else resolved_target.name}"
    project_slug = normalize_layer_name(project_name)

    save_analysis_state({"analyses": []})
    graph = strip_workspace_project(normalize_graph(load_default_graph()), project_slug)
    save_graph_state(graph)
    socketio.emit("reverse:sessions", {"sessions": []})
    socketio.emit("architecture:update", graph)

    requirement = build_agent_transcription_requirement(str(resolved_target))
    session = agent_runtime.start_session(requirement=requirement, project_name=project_name, bootstrap=False)
    sync_runtime_graph(save_state=True)
    observe_with_tool_event(
        "agent_started",
        project_slug=str(session.get("projectSlug") or project_slug or project_name),
        reason="Sesion de proyecto iniciada: Observer entra en modo autonomo de mision.",
        persistent=True,
    )
    projects = list_agent_projects_snapshot()
    socketio.emit("agent:projects", {"projects": projects})
    return {"ok": True, "session": session, "projects": projects, "targetPath": str(resolved_target)}


@socketio.on("architecture:patch")
def handle_architecture_patch(payload):
    graph = normalize_graph(payload if isinstance(payload, dict) else {})
    save_graph_state(graph)
    socketio.emit("architecture:update", graph)


@socketio.on("agent:request")
def handle_agent_request(_payload=None):
    emit("agent:projects", {"projects": list_agent_projects_snapshot()})
    emit("agent:email_command", {"op": "email_command_status", "emailStatus": email_command_plane.status()})
    for session in agent_runtime.list_sessions():
        emit("agent:session", session)
    return {"ok": True}


@socketio.on("email:command:inbound")
def handle_email_command_inbound(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    result = email_command_plane.ingest_email(
        sender=str(payload.get("from") or payload.get("sender") or ""),
        subject=str(payload.get("subject") or ""),
        body=str(payload.get("body") or payload.get("text") or ""),
        message_id=str(payload.get("messageId") or payload.get("message_id") or ""),
        source=str(payload.get("source") or "socket"),
    )
    command = result.get("command") if isinstance(result.get("command"), dict) else None
    if result.get("ok"):
        emit_email_command_event("email_command_received", command, message="Correo ejecutable recibido por socket.")
        socketio.start_background_task(dispatch_next_email_command)
    else:
        emit_email_command_event("email_command_rejected", command, error=result.get("error"), message="Correo rechazado por politica.")
    return {**result, "email": email_command_plane.status()}


@socketio.on("email:command:dispatch")
def handle_email_command_dispatch(_payload=None):
    result = dispatch_next_email_command()
    result["email"] = email_command_plane.status()
    return result


@socketio.on("observer:enabled")
def handle_observer_enabled(payload=None):
    result = apply_observer_enabled_request(payload if isinstance(payload, dict) else {})
    socketio.emit(
        "agent:observer",
        {
            "op": "observer_status",
            "enabled": result.get("enabled"),
            "state": result.get("state"),
            "observer": result.get("observer"),
            "message": result.get("message"),
        },
    )
    return result


@socketio.on("observer:behavior")
def handle_observer_behavior(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    behavior_tree = payload.get("behaviorTree") if isinstance(payload.get("behaviorTree"), dict) else payload
    next_tree = observer_plane.update_behavior_tree(behavior_tree)
    status = observer_status_payload()
    socketio.emit("agent:observer", {"op": "observer_behavior_updated", "observer": status, "behaviorTree": next_tree})
    return {"ok": True, "observer": status}


@socketio.on("observer:action")
def handle_observer_action(payload=None):
    payload = payload if isinstance(payload, dict) else {}
    result = execute_observer_safe_action(str(payload.get("action") or ""), payload.get("payload") if isinstance(payload.get("payload"), dict) else {})
    result["observer"] = observer_status_payload()
    return result


@socketio.on("observer:observe-once")
def handle_observer_observe_once(_payload=None):
    event = observe_with_tool_event("observe_now", reason="Observacion puntual solicitada por socket.", persistent=False)
    return {"ok": True, "event": event, "enabled": observer_plane.enabled, "state": observer_plane.context.state}


@socketio.on("agent:project:create")
def handle_agent_project_create(payload):
    project_name = str((payload or {}).get("name") or f"nuevo-proyecto-{datetime.now().strftime('%H%M%S')}")
    ensure_unique = bool((payload or {}).get("ensureUnique"))
    bootstrap = bool((payload or {}).get("bootstrapProject", True))
    project = agent_runtime.create_project(project_name, ensure_unique=ensure_unique, bootstrap=bootstrap)
    projects = list_agent_projects_snapshot()
    socketio.emit("agent:projects", {"projects": projects})
    socketio.start_background_task(sync_runtime_graph, True)
    return {"ok": True, "project": project, "projects": projects}


@socketio.on("agent:session:start")
def handle_agent_session_start(payload):
    requirement = str((payload or {}).get("requirement") or "").strip()
    project_name = str((payload or {}).get("projectName") or (payload or {}).get("projectSlug") or "").strip()
    project_slug = str((payload or {}).get("projectSlug") or "").strip()
    ensure_new_project = bool((payload or {}).get("ensureNewProject"))
    bootstrap = bool((payload or {}).get("bootstrapProject", True))
    try:
        runtime_mode = normalize_agent_runtime_mode((payload or {}).get("runtimeMode") or (payload or {}).get("mode") or None)
    except ValueError as error:
        return {"ok": False, "error": "invalid_runtime_mode", "message": str(error)}
    if not requirement:
        return {"ok": False, "error": "missing_requirement"}
    if not project_name:
        project_name = f"proyecto-{datetime.now().strftime('%H%M%S')}"

    subagent_plan = normalize_subagent_plan((payload or {}).get("subagentPlan") or (payload or {}).get("subagents"))
    prepared_requirement = attach_subagent_plan_to_requirement(requirement, subagent_plan)
    session = agent_runtime.start_session(
        requirement=prepared_requirement,
        project_name=project_name,
        project_slug=project_slug or None,
        bootstrap=bootstrap,
        ensure_new_project=ensure_new_project,
        mode=runtime_mode,
    )
    if subagent_plan:
        socketio.emit(
            "agent:visual",
            {
                "op": "subagents_assigned",
                "phase": "orchestration",
                "status": "preparing",
                "projectSlug": session.get("projectSlug") or project_slug,
                "message": f"{subagent_plan.get('recommendedAgents')} subagente(s) asignados a la sesion.",
                "subagentPlan": subagent_plan,
            },
        )
    socketio.start_background_task(sync_runtime_graph, True)
    observer_event = observe_with_tool_event(
        "agent_started",
        project_slug=str(session.get("projectSlug") or project_slug or project_name),
        reason="Sesion de proyecto iniciada: Observer entra en modo autonomo de mision.",
        persistent=True,
    )
    projects = list_agent_projects_snapshot()
    socketio.emit("agent:projects", {"projects": projects})
    return {"ok": True, "session": session, "projects": projects, "observerEvent": observer_event}


@socketio.on("agent:session:stop")
def handle_agent_session_stop(payload):
    session_id = str((payload or {}).get("sessionId") or "").strip()
    if not session_id:
        return {"ok": False, "error": "missing_session_id"}
    session = agent_runtime.stop_session(session_id)
    if session is None:
        return {"ok": False, "error": "session_not_found"}
    return {"ok": True, "session": session}


@socketio.on("agent:architecture:rescan")
def handle_agent_architecture_rescan(_payload=None):
    graph = sync_runtime_graph(save_state=True)
    return {"ok": True, "graph": graph}


if __name__ == "__main__":
    socketio.run(
        app,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
        allow_unsafe_werkzeug=True,
    )
