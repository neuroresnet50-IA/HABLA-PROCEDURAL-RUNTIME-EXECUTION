from __future__ import annotations

import ast
from copy import deepcopy
from typing import Any, Dict, Iterable, List

from ir_contract import CONTRACT_VERSION, EDGE_TYPES, NODE_TYPES


def position_offset(position: Any, dx: float, dy: float) -> Dict[str, float] | None:
    if not isinstance(position, dict):
        return None
    x = position.get("x")
    y = position.get("y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    return {"x": float(x) + dx, "y": float(y) + dy}


def line_window(node: ast.AST) -> tuple[int | None, int | None]:
    line_start = getattr(node, "lineno", None)
    line_end = getattr(node, "end_lineno", line_start)
    return line_start, line_end


def build_symbol_node(
    *,
    parent_node: Dict[str, Any],
    symbol_id: str,
    symbol_name: str,
    node_type: str,
    description: str,
    language: str,
    line_start: int | None,
    line_end: int | None,
    parent_id: str | None,
    entry_point: bool = False,
    position: Dict[str, float] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    canonical_path = f"{parent_node['canonicalPath']}::{symbol_name}"
    return {
        "id": symbol_id,
        "nodeType": node_type if node_type in NODE_TYPES else "function",
        "name": symbol_name,
        "projectId": parent_node["projectId"],
        "sceneId": parent_node["sceneId"],
        "canonicalPath": canonical_path,
        "sourcePath": parent_node["sourcePath"],
        "language": language,
        "layer": parent_node["layer"],
        "originType": parent_node["originType"],
        "parentId": parent_id,
        "entryPoint": entry_point,
        "readOnly": bool(parent_node.get("readOnly")),
        "position": position,
        "description": description,
        "metadata": {
            "lineStart": line_start,
            "lineEnd": line_end,
            "symbolName": symbol_name,
            "symbolKind": node_type,
            "sourceNodeId": parent_node["id"],
            **deepcopy(metadata or {}),
        },
    }


def build_edge(
    *,
    edge_id: str,
    edge_type: str,
    source_id: str,
    target_id: str,
    project_id: str,
    scene_id: str,
    origin_type: str,
    confidence: float = 1.0,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "id": edge_id,
        "edgeType": edge_type if edge_type in EDGE_TYPES else "references",
        "from": source_id,
        "to": target_id,
        "projectId": project_id,
        "sceneId": scene_id,
        "originType": origin_type,
        "label": edge_type,
        "confidence": confidence,
        "metadata": deepcopy(metadata or {}),
    }


def merge_adapter_results(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    merged_nodes: List[Dict[str, Any]] = []
    merged_edges: List[Dict[str, Any]] = []
    merged_issues: List[Dict[str, Any]] = []
    adapters: List[Dict[str, Any]] = []
    seen_node_ids = set()
    seen_edge_ids = set()
    seen_issue_ids = set()

    for result in results:
        for node in result.get("nodes") or []:
            node_id = str(node.get("id") or "")
            if not node_id or node_id in seen_node_ids:
                continue
            seen_node_ids.add(node_id)
            merged_nodes.append(node)
        for edge in result.get("edges") or []:
            edge_id = str(edge.get("id") or "")
            if not edge_id or edge_id in seen_edge_ids:
                continue
            seen_edge_ids.add(edge_id)
            merged_edges.append(edge)
        for issue in result.get("issues") or []:
            issue_id = str(issue.get("id") or "")
            if not issue_id or issue_id in seen_issue_ids:
                continue
            seen_issue_ids.add(issue_id)
            merged_issues.append(issue)
        adapters.extend(result.get("adapters") or [])

    return {
        "version": CONTRACT_VERSION,
        "nodes": merged_nodes,
        "edges": merged_edges,
        "issues": merged_issues,
        "metadata": {
            "nodeCount": len(merged_nodes),
            "edgeCount": len(merged_edges),
            "issueCount": len(merged_issues),
            "adapterCount": len(adapters),
        },
        "adapters": adapters,
    }
