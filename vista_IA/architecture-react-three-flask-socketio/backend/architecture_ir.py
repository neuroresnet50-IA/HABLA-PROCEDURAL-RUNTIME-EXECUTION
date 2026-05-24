from __future__ import annotations

from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List

from ir_adapters.registry import build_semantic_graph
from ir_contract import (
    CONTRACT_VERSION,
    EDGE_TYPES,
    EDGE_TYPE_MAP,
    ISSUE_TYPES,
    ISSUE_TYPE_MAP,
    detect_language_from_node,
    normalize_issue_status,
    normalize_severity,
    project_id_for_slug,
    scene_id_for_key,
    scene_label_from_key,
    slugify,
    utc_now,
)


def infer_node_type(node: Dict[str, Any]) -> str:
    if bool(node.get("virtualNode")):
        return "virtual_group"

    path = str(node.get("path") or "")
    suffix = PurePosixPath(path).suffix.lower()
    layer = str(node.get("layer") or "").strip().lower()
    name = str(node.get("name") or PurePosixPath(path).name or "").strip().lower()

    if layer == "data":
        return "data_store"
    if suffix in {".py", ".js", ".jsx", ".ts", ".tsx"}:
        return "module"
    if suffix == ".html":
        return "template"
    if suffix == ".css":
        return "style_sheet"
    if name in {"package.json", "requirements.txt"} or suffix in {".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"}:
        return "config_asset"
    return "file"


def infer_origin_type(node: Dict[str, Any]) -> str:
    path = str(node.get("path") or "")
    if bool(node.get("virtualNode")):
        return "virtual"
    if str(node.get("analysisId") or "").strip() or path.startswith("analysis/projects/"):
        return "analysis"
    if path.startswith("workspace/projects/"):
        return "agent"
    return "physical"


def infer_entry_point(node: Dict[str, Any]) -> bool:
    name = str(node.get("name") or PurePosixPath(str(node.get("path") or "")).name or "").strip().lower()
    return name in {
        "main.py",
        "app.py",
        "server.py",
        "main.js",
        "main.jsx",
        "main.ts",
        "main.tsx",
        "server.js",
        "server.ts",
        "index.html",
    }


def infer_graph_slug(graph: Dict[str, Any], project_root: Path) -> str:
    metadata = graph.get("metadata") if isinstance(graph.get("metadata"), dict) else {}
    explicit = metadata.get("projectSlug") or metadata.get("projectName")
    if explicit:
        return slugify(explicit)

    workspace_projects = sorted(
        {
            str(node.get("workspaceProject") or "").strip()
            for node in graph.get("nodes") or []
            if str(node.get("workspaceProject") or "").strip()
        }
    )
    if len(workspace_projects) == 1:
        return slugify(workspace_projects[0])
    return slugify(project_root.name)


def infer_project_origin(graph: Dict[str, Any]) -> str:
    nodes = graph.get("nodes") or []
    if nodes and all(str(node.get("path") or "").startswith("analysis/projects/") for node in nodes if node.get("path")):
        return "analysis"
    if any(str(node.get("path") or "").startswith("workspace/projects/") for node in nodes if node.get("path")):
        return "workspace"
    return "workspace"


def build_project_descriptor(graph: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    metadata = graph.get("metadata") if isinstance(graph.get("metadata"), dict) else {}
    slug = infer_graph_slug(graph, project_root)
    project_id = project_id_for_slug(slug)
    created_at = str(metadata.get("createdAt") or metadata.get("updatedAt") or utc_now())
    updated_at = str(metadata.get("updatedAt") or utc_now())
    language_hints = sorted(
        {
            detect_language_from_node(node)
            for node in graph.get("nodes") or []
            if detect_language_from_node(node) not in {"", "text", "markdown"}
        }
    )
    return {
        "id": project_id,
        "name": str(metadata.get("projectName") or project_root.name),
        "slug": slug,
        "rootPath": str(project_root),
        "originType": infer_project_origin(graph),
        "sourceLanguageHints": language_hints,
        "createdAt": created_at,
        "updatedAt": updated_at,
    }


def infer_scene_key(node: Dict[str, Any], fallback_slug: str) -> str:
    explicit = str(node.get("workspaceScene") or "").strip()
    if explicit:
        return explicit

    path = str(node.get("path") or "").strip()
    if path.startswith("analysis/projects/"):
        parts = PurePosixPath(path).parts
        if len(parts) >= 3:
            return parts[2]
    if path.startswith("workspace/projects/"):
        parts = PurePosixPath(path).parts
        if len(parts) >= 3:
            return parts[2]
    return fallback_slug


def infer_scene_mode(node: Dict[str, Any]) -> str:
    path = str(node.get("path") or "")
    if str(node.get("analysisId") or "").strip() or path.startswith("analysis/projects/") or bool(node.get("readOnly")):
        return "analysis"
    return "workspace"


def infer_scene_origin(node: Dict[str, Any]) -> Dict[str, float]:
    scene_origin = node.get("sceneOrigin") if isinstance(node.get("sceneOrigin"), dict) else None
    if scene_origin is not None:
        x = scene_origin.get("x")
        y = scene_origin.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return {"x": float(x), "y": float(y)}
    return {"x": 0.0, "y": 0.0}


def canonicalize_nodes(nodes: Iterable[Dict[str, Any]], project: Dict[str, Any]) -> List[Dict[str, Any]]:
    canonical_nodes: List[Dict[str, Any]] = []
    for node in nodes:
        current = deepcopy(node)
        current["nodeType"] = infer_node_type(current)
        current["projectId"] = project["id"]
        current["sceneId"] = scene_id_for_key(infer_scene_key(current, project["slug"]))
        current["canonicalPath"] = str(current.get("canonicalPath") or current.get("path") or "")
        current["sourcePath"] = str(current.get("sourcePath") or current.get("canonicalPath") or current.get("path") or "")
        current["language"] = detect_language_from_node(current)
        current["originType"] = infer_origin_type(current)
        current["parentId"] = current.get("parentId")
        current["entryPoint"] = bool(current.get("entryPoint")) or infer_entry_point(current)
        current["readOnly"] = bool(current.get("readOnly"))
        current["metadata"] = deepcopy(current.get("metadata") or {})
        canonical_nodes.append(current)
    return canonical_nodes


def scene_id_lookup(nodes: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for node in nodes:
        path = str(node.get("path") or "")
        node_id = str(node.get("id") or "")
        if path:
            mapping[path] = str(node.get("sceneId") or "")
        if node_id:
            mapping[node_id] = str(node.get("sceneId") or "")
    return mapping


def origin_type_lookup(nodes: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for node in nodes:
        node_id = str(node.get("id") or "")
        if node_id:
            mapping[node_id] = str(node.get("originType") or "physical")
    return mapping


def canonicalize_edges(edges: Iterable[Dict[str, Any]], project: Dict[str, Any], nodes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scene_lookup = scene_id_lookup(nodes)
    origin_lookup = origin_type_lookup(nodes)
    canonical_edges: List[Dict[str, Any]] = []
    for edge in edges:
        current = deepcopy(edge)
        source = str(current.get("from") or "")
        target = str(current.get("to") or "")
        raw_edge_type = str(current.get("edgeType") or current.get("type") or "depends_on").strip().lower()
        edge_type = EDGE_TYPE_MAP.get(raw_edge_type, raw_edge_type if raw_edge_type in EDGE_TYPES else "depends_on")
        current["edgeType"] = edge_type
        current["projectId"] = project["id"]
        current["sceneId"] = str(current.get("sceneId") or scene_lookup.get(source) or scene_lookup.get(target) or scene_id_for_key(project["slug"]))
        current["originType"] = str(
            current.get("originType")
            or origin_lookup.get(source)
            or origin_lookup.get(target)
            or "physical"
        )
        try:
            current["confidence"] = float(current.get("confidence") if current.get("confidence") is not None else 1.0)
        except (TypeError, ValueError):
            current["confidence"] = 1.0
        current["metadata"] = deepcopy(current.get("metadata") or {})
        canonical_edges.append(current)
    return canonical_edges


def build_scenes(nodes: Iterable[Dict[str, Any]], project: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenes_by_id: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        scene_id = str(node.get("sceneId") or "")
        if not scene_id:
            continue
        scene_key = scene_id.removeprefix("scene:")
        if scene_id in scenes_by_id:
            continue
        scenes_by_id[scene_id] = {
            "id": scene_id,
            "projectId": project["id"],
            "key": scene_key,
            "label": str(node.get("workspaceSceneLabel") or scene_label_from_key(scene_key)),
            "origin": infer_scene_origin(node),
            "mode": infer_scene_mode(node),
            "readOnly": bool(node.get("readOnly")) or infer_scene_mode(node) == "analysis",
        }
    return sorted(scenes_by_id.values(), key=lambda item: item["key"])


def canonicalize_findings_as_issues(
    findings: Iterable[Dict[str, Any]],
    *,
    project: Dict[str, Any],
    nodes: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    nodes_by_id = {str(node.get("id") or ""): node for node in nodes}
    nodes_by_path = {str(node.get("path") or ""): node for node in nodes if node.get("path")}
    canonical_issues: List[Dict[str, Any]] = []

    for index, finding in enumerate(findings):
        current = deepcopy(finding)
        node_id = str(current.get("nodeId") or "")
        node = nodes_by_id.get(node_id)
        if node is None:
            node = nodes_by_path.get(str(current.get("path") or ""))

        issue_code = str(current.get("issueType") or current.get("code") or "").strip().lower()
        issue_type = ISSUE_TYPE_MAP.get(issue_code, issue_code if issue_code in ISSUE_TYPES else "inference_gap")
        line = current.get("line")
        if isinstance(line, (int, float)):
            line_start = int(line)
            line_end = int(line)
        else:
            line_start = None
            line_end = None

        raw_evidence = current.get("evidence")
        if isinstance(raw_evidence, list):
            evidence = [str(item) for item in raw_evidence if str(item).strip()]
        elif raw_evidence:
            evidence = [str(raw_evidence)]
        else:
            evidence = []

        canonical_issues.append(
            {
                "id": str(current.get("id") or f"issue:{slugify(issue_code or index)}-{index + 1}"),
                "issueType": issue_type,
                "severity": normalize_severity(current.get("severity")),
                "status": normalize_issue_status(current.get("status")),
                "projectId": project["id"],
                "sceneId": str(current.get("sceneId") or (node.get("sceneId") if isinstance(node, dict) else "") or scene_id_for_key(project["slug"])),
                "nodeId": str(current.get("nodeId") or (node.get("id") if isinstance(node, dict) else "") or ""),
                "edgeId": str(current.get("edgeId") or ""),
                "stepId": str(current.get("stepId") or ""),
                "sourcePath": str(current.get("sourcePath") or current.get("path") or (node.get("sourcePath") if isinstance(node, dict) else "") or ""),
                "lineStart": line_start,
                "lineEnd": line_end,
                "message": str(current.get("message") or issue_code or "Issue detectado"),
                "evidence": evidence,
                "suggestedAction": str(current.get("hint") or current.get("suggestedAction") or ""),
                "metadata": deepcopy(current.get("metadata") or {}),
            }
        )

    return canonical_issues


def canonicalize_sessions(
    *,
    project: Dict[str, Any],
    analysis_sessions: Iterable[Dict[str, Any]] | None = None,
    agent_sessions: Iterable[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    canonical_sessions: List[Dict[str, Any]] = []

    for session in analysis_sessions or []:
        current = deepcopy(session)
        canonical_sessions.append(
            {
                "id": str(current.get("id") or ""),
                "sessionType": "analysis",
                "projectId": project["id"],
                "state": "completed",
                "createdAt": str(current.get("createdAt") or utc_now()),
                "startedAt": str(current.get("createdAt") or utc_now()),
                "endedAt": str(current.get("createdAt") or utc_now()),
                "firstVisualEventAt": None,
                "lastHeartbeatAt": None,
                "summary": str(current.get("label") or current.get("targetPath") or "Analisis cargado"),
                "metadata": {
                    "mode": str(current.get("mode") or "analysis"),
                    "targetPath": str(current.get("targetPath") or ""),
                    "primaryNodeId": str(current.get("primaryNodeId") or ""),
                },
            }
        )

    for session in agent_sessions or []:
        current = deepcopy(session)
        canonical_sessions.append(
            {
                "id": str(current.get("sessionId") or current.get("id") or ""),
                "sessionType": "agent",
                "projectId": project["id"],
                "state": str(current.get("status") or current.get("state") or "queued"),
                "createdAt": str(current.get("createdAt") or utc_now()),
                "startedAt": str(current.get("startedAt") or ""),
                "endedAt": str(current.get("endedAt") or ""),
                "firstVisualEventAt": current.get("firstVisualEventAt"),
                "lastHeartbeatAt": current.get("lastHeartbeatAt"),
                "summary": str(current.get("progressLabel") or current.get("errorMessage") or ""),
                "metadata": {
                    "projectSlug": str(current.get("projectSlug") or ""),
                    "progressPercent": int(current.get("progressPercent") or 0),
                    "command": deepcopy(current.get("command") or []),
                    "errorCode": str(current.get("errorCode") or ""),
                },
            }
        )

    return canonical_sessions


def merge_issue_lists(*issue_groups: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen_issue_ids = set()

    for issue_group in issue_groups:
        for issue in issue_group or []:
            issue_id = str(issue.get("id") or "")
            if issue_id and issue_id in seen_issue_ids:
                continue
            if issue_id:
                seen_issue_ids.add(issue_id)
            merged.append(deepcopy(issue))

    return merged


def build_architecture_ir(
    graph: Dict[str, Any],
    *,
    project_root: Path,
    analysis_sessions: Iterable[Dict[str, Any]] | None = None,
    agent_sessions: Iterable[Dict[str, Any]] | None = None,
    issues: Iterable[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    metadata = deepcopy(graph.get("metadata") or {})
    project = build_project_descriptor(graph, project_root)
    canonical_nodes = canonicalize_nodes(graph.get("nodes") or [], project)
    canonical_edges = canonicalize_edges(graph.get("edges") or [], project, canonical_nodes)
    canonical_issues = canonicalize_findings_as_issues(issues or [], project=project, nodes=canonical_nodes)
    canonical_sessions = canonicalize_sessions(
        project=project,
        analysis_sessions=analysis_sessions,
        agent_sessions=agent_sessions,
    )
    scenes = build_scenes(canonical_nodes, project)
    semantic_graph = build_semantic_graph(canonical_nodes)
    root_issues = merge_issue_lists(canonical_issues, semantic_graph.get("issues") or [])

    return {
        "version": CONTRACT_VERSION,
        "project": project,
        "nodes": canonical_nodes,
        "edges": canonical_edges,
        "issues": root_issues,
        "sessions": canonical_sessions,
        "scenes": scenes,
        "semanticGraph": semantic_graph,
        "metadata": {
            **metadata,
            "contractVersion": CONTRACT_VERSION,
            "nodeCount": len(canonical_nodes),
            "edgeCount": len(canonical_edges),
            "issueCount": len(root_issues),
            "sessionCount": len(canonical_sessions),
            "sceneCount": len(scenes),
            "semanticNodeCount": int(semantic_graph["metadata"]["nodeCount"]),
            "semanticEdgeCount": int(semantic_graph["metadata"]["edgeCount"]),
            "updatedAt": str(metadata.get("updatedAt") or utc_now()),
        },
    }
