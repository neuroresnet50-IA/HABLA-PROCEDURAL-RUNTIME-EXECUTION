from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Dict


CONTRACT_VERSION = "1.0"

NODE_TYPES = {
    "project",
    "package",
    "directory",
    "module",
    "file",
    "class",
    "function",
    "method",
    "entry_point",
    "route",
    "event_handler",
    "worker",
    "process",
    "service",
    "api_endpoint",
    "queue",
    "data_store",
    "external_dependency",
    "template",
    "style_sheet",
    "script_block",
    "config_asset",
    "control_flow_step",
    "decision_step",
    "io_step",
    "loop_step",
    "start_step",
    "end_step",
    "virtual_group",
    "analysis_anchor",
}

EDGE_TYPES = {
    "contains",
    "defines",
    "declares",
    "references",
    "imports",
    "depends_on",
    "links_to_external",
    "calls",
    "starts",
    "spawns",
    "handles",
    "emits",
    "routes_to",
    "renders",
    "reads_from",
    "writes_to",
    "shares_schema",
    "syncs_to",
    "flows_to",
    "branch_true",
    "branch_false",
    "loops_to",
    "returns_to",
    "flags_issue",
    "blocks_execution",
}

ISSUE_TYPES = {
    "syntax_error",
    "indentation_error",
    "parse_failure",
    "type_resolution_failure",
    "unresolved_import",
    "missing_dependency",
    "broken_external_reference",
    "orphan_function",
    "orphan_handler",
    "orphan_route",
    "broken_call_edge",
    "broken_event_wiring",
    "broken_data_flow",
    "missing_entrypoint",
    "unreachable_code",
    "dead_branch",
    "missing_branch",
    "missing_loop_back_edge",
    "incomplete_control_flow",
    "inference_gap",
    "confidence_low",
    "runtime_contract_gap",
}

EVENT_TYPES = {
    "session_start",
    "phase",
    "heartbeat",
    "session_complete",
    "session_failed",
    "session_stopped",
    "upsert_node",
    "upsert_edge",
    "focus_node",
    "upsert_flow_step",
    "upsert_flow_edge",
    "sync_file",
    "report_issue",
    "audit_summary",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".txt": "text",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
}

EDGE_TYPE_MAP = {
    "import": "imports",
    "imports": "imports",
    "uses": "depends_on",
    "socket": "emits",
    "reference": "references",
    "flow": "flows_to",
}

ISSUE_TYPE_MAP = {
    "python_syntax_error": "syntax_error",
    "python_relative_import_missing": "unresolved_import",
    "unresolved_module_import": "unresolved_import",
    "unresolved_html_reference": "broken_external_reference",
    "python_orphan_function": "orphan_function",
    "js_orphan_function": "orphan_function",
    "algorithm_unreachable_step": "unreachable_code",
    "algorithm_missing_branch": "missing_branch",
    "algorithm_dead_end": "incomplete_control_flow",
    "algorithm_broken_edge": "broken_call_edge",
    "missing_module_edge": "inference_gap",
    "missing_html_dependency_edge": "inference_gap",
    "scene_mismatch": "runtime_contract_gap",
    "scene_local_coordinates": "runtime_contract_gap",
    "layer_storage_mismatch": "inference_gap",
    "layer_docs_mismatch": "inference_gap",
    "passive_data_pseudo_flow": "inference_gap",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-") or "graph"


def project_id_for_slug(slug: str) -> str:
    return f"project:{slugify(slug)}"


def scene_id_for_key(scene_key: str) -> str:
    return f"scene:{slugify(scene_key) if '/' not in scene_key else scene_key}"


def scene_label_from_key(scene_key: str) -> str:
    return " / ".join(part.replace("-", " ").title() for part in str(scene_key or "main").split("/"))


def normalize_severity(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"info", "warning", "error", "critical"}:
        return normalized
    return "warning"


def normalize_issue_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"open", "confirmed", "ignored", "resolved"}:
        return normalized
    return "open"


def detect_language_from_node(node: Dict[str, Any]) -> str:
    explicit = str(node.get("language") or node.get("codeLanguage") or "").strip().lower()
    if explicit and explicit != "text":
        return explicit
    suffix = PurePosixPath(str(node.get("path") or "")).suffix.lower()
    return LANGUAGE_BY_SUFFIX.get(suffix, "text")
