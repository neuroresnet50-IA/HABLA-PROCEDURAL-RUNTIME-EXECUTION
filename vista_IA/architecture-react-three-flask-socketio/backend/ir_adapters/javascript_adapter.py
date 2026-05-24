from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ir_adapters.common import build_edge, build_symbol_node, position_offset
from ir_contract import CONTRACT_VERSION, slugify


JAVASCRIPT_LANGUAGES = {"javascript", "jsx", "typescript", "tsx"}
TOP_LEVEL_FUNCTION_PATTERNS = (
    r"^(?:export\s+default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
    r"^(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
    r"^(?:export\s+)?let\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
    r"^(?:export\s+)?var\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
)
ROUTE_PATTERN = re.compile(
    r"\b(?:app|router|server)\.(get|post|put|patch|delete|all|use)\(\s*([\"'`])([^\"'`]+)\2(?:\s*,\s*([A-Za-z_$][\w$]*))?"
)
EVENT_PATTERN = re.compile(
    r"\b([A-Za-z_$][\w$.]*)\.(on|addEventListener)\(\s*([\"'`])([^\"'`]+)\3(?:\s*,\s*([A-Za-z_$][\w$]*))?"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_PATH = Path(__file__).resolve().with_name("js_semantic_bridge.mjs")
DEFAULT_NODE_CANDIDATES = (
    Path("/home/neurodriver/Downloads/node-v24.14.1-linux-x64/bin/node"),
    Path.home() / "Downloads/node-v24.14.1-linux-x64/bin/node",
)
AST_BRIDGE_TIMEOUT_SECONDS = float(os.environ.get("NEURO_LACE_JS_AST_BRIDGE_TIMEOUT_SECONDS", "4"))
AST_BRIDGE_MAX_NODES = int(os.environ.get("NEURO_LACE_JS_AST_BRIDGE_MAX_NODES", "40"))
AST_BRIDGE_MAX_BYTES = int(os.environ.get("NEURO_LACE_JS_AST_BRIDGE_MAX_BYTES", "250000"))


def _empty_result() -> Dict[str, Any]:
    return {
        "version": CONTRACT_VERSION,
        "nodes": [],
        "edges": [],
        "issues": [],
        "metadata": {
            "nodeCount": 0,
            "edgeCount": 0,
            "issueCount": 0,
            "adapterCount": 0,
        },
        "adapters": [],
    }


def _collect_relevant_nodes(nodes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    relevant_nodes: List[Dict[str, Any]] = []
    for node in nodes:
        if str(node.get("language") or "") not in JAVASCRIPT_LANGUAGES:
            continue
        if str(node.get("nodeType") or "") not in {"module", "file"}:
            continue
        relevant_nodes.append(node)
    return relevant_nodes


def _candidate_node_binaries() -> List[Path]:
    candidates: List[Path] = []
    raw_node = str(os.environ.get("NODE_BIN") or "").strip()
    if raw_node:
        candidates.append(Path(raw_node))

    raw_node_dir = str(os.environ.get("NODE_BIN_DIR") or "").strip()
    if raw_node_dir:
        candidates.append(Path(raw_node_dir) / "node")

    discovered = shutil.which("node")
    if discovered:
        candidates.append(Path(discovered))

    candidates.extend(DEFAULT_NODE_CANDIDATES)

    unique_candidates: List[Path] = []
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def _resolve_node_binary() -> Path | None:
    for candidate in _candidate_node_binaries():
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _run_ast_bridge(nodes: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    total_code_bytes = sum(len(str(node.get("code") or "").encode("utf-8")) for node in nodes)
    if len(nodes) > AST_BRIDGE_MAX_NODES or total_code_bytes > AST_BRIDGE_MAX_BYTES:
        return None

    node_binary = _resolve_node_binary()
    if node_binary is None or not BRIDGE_PATH.is_file():
        return None

    payload = {
        "contractVersion": CONTRACT_VERSION,
        "nodes": nodes,
    }

    try:
        completed = subprocess.run(
            [str(node_binary), str(BRIDGE_PATH)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=str(REPO_ROOT),
            timeout=AST_BRIDGE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0 or not str(completed.stdout or "").strip():
        return None

    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    if not isinstance(parsed.get("nodes"), list):
        return None
    if not isinstance(parsed.get("edges"), list):
        return None
    if not isinstance(parsed.get("issues"), list):
        return None
    if not isinstance(parsed.get("adapters"), list):
        return None

    metadata = parsed.get("metadata") or {}
    parsed["version"] = CONTRACT_VERSION
    parsed["metadata"] = {
        "nodeCount": int(metadata.get("nodeCount") or len(parsed["nodes"])),
        "edgeCount": int(metadata.get("edgeCount") or len(parsed["edges"])),
        "issueCount": int(metadata.get("issueCount") or len(parsed["issues"])),
        "adapterCount": int(metadata.get("adapterCount") or len(parsed["adapters"])),
    }
    return parsed


def _sanitize_line(raw_line: str) -> str:
    sanitized = re.sub(r"`(?:\\.|[^`])*`", "``", raw_line)
    sanitized = re.sub(r'"(?:\\.|[^"\\])*"', '""', sanitized)
    sanitized = re.sub(r"'(?:\\.|[^'\\])*'", "''", sanitized)
    sanitized = re.sub(r"//.*", "", sanitized)
    return sanitized


def _brace_delta(raw_line: str) -> int:
    sanitized = _sanitize_line(raw_line)
    return sanitized.count("{") - sanitized.count("}")


def _build_regex_fallback(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    semantic_nodes: List[Dict[str, Any]] = []
    semantic_edges: List[Dict[str, Any]] = []
    adapters: List[Dict[str, Any]] = []

    for parent_node in nodes:
        code = str(parent_node.get("code") or "")
        if not code.strip():
            continue

        symbols_by_name: Dict[str, str] = {}
        file_symbols: List[Dict[str, Any]] = []
        class_stack: List[Dict[str, Any]] = []
        pending_links: List[Dict[str, Any]] = []
        depth = 0
        language = str(parent_node.get("language") or "javascript")

        for line_no, raw_line in enumerate(code.splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*")):
                depth = max(depth + _brace_delta(raw_line), 0)
                continue

            current_parent_id = parent_node["id"]
            current_class_name = ""
            if class_stack:
                current_parent_id = class_stack[-1]["id"]
                current_class_name = class_stack[-1]["name"]

            if not class_stack and depth == 0:
                for pattern in TOP_LEVEL_FUNCTION_PATTERNS:
                    match = re.match(pattern, stripped)
                    if not match:
                        continue
                    function_name = match.group(1)
                    function_id = f"{parent_node['id']}::function:{function_name}"
                    function_node = build_symbol_node(
                        parent_node=parent_node,
                        symbol_id=function_id,
                        symbol_name=function_name,
                        node_type="function",
                        description=f"Funcion top-level `{function_name}` extraida del modulo JS/TS.",
                        language=language,
                        line_start=line_no,
                        line_end=line_no,
                        parent_id=parent_node["id"],
                        entry_point=function_name in {"main", "run", "bootstrap", "start", "initializeApp", "App"},
                        position=position_offset(parent_node.get("position"), 90.0, 90.0 + len(file_symbols) * 54.0),
                    )
                    semantic_nodes.append(function_node)
                    file_symbols.append(function_node)
                    symbols_by_name[function_name] = function_id
                    semantic_edges.append(
                        build_edge(
                            edge_id=f"edge:{parent_node['id']}->{function_id}:contains",
                            edge_type="contains",
                            source_id=parent_node["id"],
                            target_id=function_id,
                            project_id=parent_node["projectId"],
                            scene_id=parent_node["sceneId"],
                            origin_type=parent_node["originType"],
                        )
                    )
                    break

                class_match = re.match(r"^(?:export\s+default\s+)?class\s+([A-Za-z_$][\w$]*)\b", stripped)
                if class_match:
                    class_name = class_match.group(1)
                    class_id = f"{parent_node['id']}::class:{class_name}"
                    class_node = build_symbol_node(
                        parent_node=parent_node,
                        symbol_id=class_id,
                        symbol_name=class_name,
                        node_type="class",
                        description=f"Clase `{class_name}` extraida del modulo JS/TS.",
                        language=language,
                        line_start=line_no,
                        line_end=line_no,
                        parent_id=parent_node["id"],
                        position=position_offset(parent_node.get("position"), 90.0, 90.0 + len(file_symbols) * 54.0),
                    )
                    semantic_nodes.append(class_node)
                    file_symbols.append(class_node)
                    symbols_by_name[class_name] = class_id
                    semantic_edges.append(
                        build_edge(
                            edge_id=f"edge:{parent_node['id']}->{class_id}:contains",
                            edge_type="contains",
                            source_id=parent_node["id"],
                            target_id=class_id,
                            project_id=parent_node["projectId"],
                            scene_id=parent_node["sceneId"],
                            origin_type=parent_node["originType"],
                        )
                    )
                    class_stack.append({"id": class_id, "name": class_name, "depth": depth + max(_brace_delta(raw_line), 1)})

            elif class_stack and depth == class_stack[-1]["depth"]:
                method_match = re.match(r"^(?:async\s+)?([A-Za-z_$][\w$]*)\s*\(", stripped)
                if method_match and method_match.group(1) not in {"if", "for", "while", "switch", "catch"}:
                    method_name = method_match.group(1)
                    method_id = f"{class_stack[-1]['id']}::method:{method_name}"
                    symbol_name = f"{current_class_name}.{method_name}"
                    method_node = build_symbol_node(
                        parent_node=parent_node,
                        symbol_id=method_id,
                        symbol_name=symbol_name,
                        node_type="method",
                        description=f"Metodo `{method_name}` de la clase `{current_class_name}`.",
                        language=language,
                        line_start=line_no,
                        line_end=line_no,
                        parent_id=current_parent_id,
                        position=position_offset(parent_node.get("position"), 210.0, 90.0 + len(file_symbols) * 42.0),
                    )
                    semantic_nodes.append(method_node)
                    file_symbols.append(method_node)
                    symbols_by_name[method_name] = method_id
                    symbols_by_name[symbol_name] = method_id
                    semantic_edges.append(
                        build_edge(
                            edge_id=f"edge:{current_parent_id}->{method_id}:defines",
                            edge_type="defines",
                            source_id=current_parent_id,
                            target_id=method_id,
                            project_id=parent_node["projectId"],
                            scene_id=parent_node["sceneId"],
                            origin_type=parent_node["originType"],
                        )
                    )

            route_match = ROUTE_PATTERN.search(stripped)
            if route_match:
                method = route_match.group(1).upper()
                path = route_match.group(3)
                handler_name = str(route_match.group(4) or "")
                route_id = f"{parent_node['id']}::route:{slugify(f'{method}-{path}')}-{line_no}"
                route_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=route_id,
                    symbol_name=f"{method} {path}",
                    node_type="route",
                    description="Ruta HTTP inferida desde el modulo JS/TS.",
                    language=language,
                    line_start=line_no,
                    line_end=line_no,
                    parent_id=parent_node["id"],
                    position=position_offset(parent_node.get("position"), 240.0, 90.0 + len(file_symbols) * 36.0),
                    metadata={"methods": [method], "path": path, "handlerName": handler_name},
                )
                semantic_nodes.append(route_node)
                file_symbols.append(route_node)
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{parent_node['id']}->{route_id}:contains",
                        edge_type="contains",
                        source_id=parent_node["id"],
                        target_id=route_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type=parent_node["originType"],
                    )
                )
                if handler_name:
                    pending_links.append(
                        {
                            "roleId": route_id,
                            "edgeType": "routes_to",
                            "handlerName": handler_name,
                            "metadata": {"handlerName": handler_name, "methods": [method], "path": path},
                        }
                    )

            event_match = EVENT_PATTERN.search(stripped)
            if event_match:
                emitter_name = event_match.group(1)
                event_name = event_match.group(4)
                handler_name = str(event_match.group(5) or "")
                event_id = f"{parent_node['id']}::event:{slugify(event_name)}-{line_no}"
                event_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=event_id,
                    symbol_name=event_name,
                    node_type="event_handler",
                    description="Handler de evento inferido desde el modulo JS/TS.",
                    language=language,
                    line_start=line_no,
                    line_end=line_no,
                    parent_id=parent_node["id"],
                    position=position_offset(parent_node.get("position"), 240.0, 126.0 + len(file_symbols) * 36.0),
                    metadata={"eventName": event_name, "handlerName": handler_name, "emitter": emitter_name},
                )
                semantic_nodes.append(event_node)
                file_symbols.append(event_node)
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{parent_node['id']}->{event_id}:contains",
                        edge_type="contains",
                        source_id=parent_node["id"],
                        target_id=event_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type=parent_node["originType"],
                    )
                )
                if handler_name:
                    pending_links.append(
                        {
                            "roleId": event_id,
                            "edgeType": "handles",
                            "handlerName": handler_name,
                            "metadata": {"handlerName": handler_name, "eventName": event_name, "emitter": emitter_name},
                        }
                    )

            depth = max(depth + _brace_delta(raw_line), 0)
            while class_stack and depth < class_stack[-1]["depth"]:
                class_stack.pop()

        for link in pending_links:
            handler_id = symbols_by_name.get(str(link["handlerName"]))
            if not handler_id:
                continue
            semantic_edges.append(
                build_edge(
                    edge_id=f"edge:{link['roleId']}->{handler_id}:{link['edgeType']}",
                    edge_type=str(link["edgeType"]),
                    source_id=str(link["roleId"]),
                    target_id=handler_id,
                    project_id=parent_node["projectId"],
                    scene_id=parent_node["sceneId"],
                    origin_type="inference",
                    confidence=0.9,
                    metadata=link["metadata"],
                )
            )

        adapters.append(
            {
                "language": language,
                "parser": "regex+brace-scan",
                "status": "fallback",
                "sourceNodeId": parent_node["id"],
                "limitations": [
                    "deteccion top-level y clases simples",
                    "rutas y eventos por heuristica",
                    "sin AST real por falta de bridge o node",
                ],
                "nodeCount": len(file_symbols),
            }
        )

    return {
        "version": CONTRACT_VERSION,
        "nodes": semantic_nodes,
        "edges": semantic_edges,
        "issues": [],
        "metadata": {
            "nodeCount": len(semantic_nodes),
            "edgeCount": len(semantic_edges),
            "issueCount": 0,
            "adapterCount": len(adapters),
        },
        "adapters": adapters,
    }


def build_javascript_semantic_graph(nodes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    relevant_nodes = _collect_relevant_nodes(nodes)
    if not relevant_nodes:
        return _empty_result()

    bridge_result = _run_ast_bridge(relevant_nodes)
    if bridge_result is not None:
        return bridge_result

    return _build_regex_fallback(relevant_nodes)
