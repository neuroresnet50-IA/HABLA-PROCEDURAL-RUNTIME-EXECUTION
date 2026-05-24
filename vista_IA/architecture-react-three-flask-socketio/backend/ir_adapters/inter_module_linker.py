from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List

from ir_adapters.common import build_edge
from project_graph import resolve_import_specifier, resolve_python_module_reference


def _is_local_specifier(specifier: Any) -> bool:
    normalized = str(specifier or "").strip()
    return normalized.startswith((".", "/"))


def _module_known_paths(nodes: Iterable[Dict[str, Any]]) -> set[str]:
    known_paths: set[str] = set()
    for node in nodes:
        for key in ("canonicalPath", "path"):
            value = str(node.get(key) or "").strip()
            if value:
                known_paths.add(value)
    return known_paths


def _module_lookup(nodes: Iterable[Dict[str, Any]]) -> tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    path_to_id: Dict[str, str] = {}
    for node in nodes:
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        by_id[node_id] = node
        for key in ("canonicalPath", "path"):
            value = str(node.get(key) or "").strip()
            if value:
                path_to_id[value] = node_id
    return by_id, path_to_id


def _semantic_node_lookup(nodes: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(node.get("id") or ""): node for node in nodes if str(node.get("id") or "")}


def _children_by_parent(nodes: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    children: Dict[str, List[Dict[str, Any]]] = {}
    for node in nodes:
        parent_id = str(node.get("parentId") or "")
        if not parent_id:
            continue
        children.setdefault(parent_id, []).append(node)
    return children


def _python_internal_roots(nodes: Iterable[Dict[str, Any]]) -> set[str]:
    roots: set[str] = set()
    for node in nodes:
        if str(node.get("language") or "").strip().lower() != "python":
            continue
        raw_path = str(node.get("canonicalPath") or node.get("path") or "").strip()
        if not raw_path.endswith(".py"):
            continue
        path = PurePosixPath(raw_path)
        if path.stem and path.stem != "__init__":
            roots.add(path.stem)
        if path.name == "__init__.py" and path.parent.name:
            roots.add(path.parent.name)
    return roots


def _build_export_index(nodes: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    exports_by_module: Dict[str, Dict[str, str]] = {}
    for node in nodes:
        metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        source_node_id = str(metadata.get("sourceNodeId") or "")
        if not source_node_id:
            continue
        export_names = list(metadata.get("exportNames") or [])
        if bool(metadata.get("defaultExport")) and "default" not in export_names:
            export_names.append("default")
        if not export_names:
            continue
        module_exports = exports_by_module.setdefault(source_node_id, {})
        for export_name in export_names:
            normalized = str(export_name or "").strip()
            if normalized and normalized not in module_exports:
                module_exports[normalized] = str(node.get("id") or "")
    return exports_by_module


def _build_issue(
    *,
    source_module: Dict[str, Any],
    source_id: str,
    issue_type: str,
    line_start: int | None,
    message: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "id": f"issue:semantic:{source_module['id']}:{issue_type}:{source_id}:{line_start or 0}",
        "issueType": issue_type,
        "severity": "warning",
        "status": "open",
        "projectId": source_module["projectId"],
        "sceneId": source_module["sceneId"],
        "nodeId": source_id,
        "edgeId": "",
        "stepId": "",
        "sourcePath": str(source_module.get("sourcePath") or source_module.get("canonicalPath") or ""),
        "lineStart": line_start,
        "lineEnd": line_start,
        "message": message,
        "evidence": [str(metadata.get("specifier") or ""), str(metadata.get("importedName") or "")],
        "suggestedAction": "Asegura que el modulo exporte ese simbolo o corrige el import local.",
        "metadata": {
            "adapter": "inter_module_linker",
            **deepcopy(metadata),
        },
    }


def _should_validate_python_import(deferred: Dict[str, Any], internal_roots: set[str]) -> bool:
    level = int(deferred.get("level") or 0)
    if level > 0:
        return True
    module_name = str(deferred.get("moduleName") or "").strip()
    if not module_name:
        return False
    top_level = module_name.split(".", 1)[0]
    return top_level in internal_roots


def _resolve_target_module_id(
    source_module: Dict[str, Any],
    deferred: Dict[str, Any],
    known_paths: set[str],
    path_to_id: Dict[str, str],
) -> str | None:
    current_path = str(source_module.get("canonicalPath") or source_module.get("path") or "")
    if not current_path:
        return None

    language = str(deferred.get("language") or source_module.get("language") or "").strip().lower()
    if language == "python":
        module_name = str(deferred.get("moduleName") or "").strip()
        level = int(deferred.get("level") or 0)
        if not module_name and level <= 0:
            return None
        target_path = resolve_python_module_reference(current_path, module_name, known_paths, level=level)
        return path_to_id.get(target_path) if target_path else None

    specifier = str(deferred.get("specifier") or "").strip()
    if not _is_local_specifier(specifier):
        return None
    target_path = resolve_import_specifier(current_path, specifier, known_paths)
    return path_to_id.get(target_path) if target_path else None


def _resolve_target_symbol_id(
    *,
    target_module_id: str,
    deferred: Dict[str, Any],
    exports_by_module: Dict[str, Dict[str, str]],
    semantic_nodes_by_id: Dict[str, Dict[str, Any]],
    children_by_parent: Dict[str, List[Dict[str, Any]]],
) -> str | None:
    imported_name = str(deferred.get("importedName") or "").strip()
    if not imported_name or imported_name == "*":
        return None

    target_exports = exports_by_module.get(target_module_id) or {}
    target_symbol_id = target_exports.get(imported_name)
    if not target_symbol_id:
        return None

    member_name = str(deferred.get("memberName") or "").strip()
    if not member_name:
        return target_symbol_id

    target_symbol = semantic_nodes_by_id.get(target_symbol_id) or {}
    if str(target_symbol.get("nodeType") or "") != "class":
        return None

    for child in children_by_parent.get(target_symbol_id, []):
        metadata = child.get("metadata") if isinstance(child.get("metadata"), dict) else {}
        binding_name = str(metadata.get("bindingName") or "")
        child_name = str(child.get("name") or "")
        if binding_name == member_name or child_name.endswith(f".{member_name}"):
            return str(child.get("id") or "")
    return None


def link_inter_module_semantics(
    canonical_nodes: Iterable[Dict[str, Any]],
    semantic_graph: Dict[str, Any],
) -> Dict[str, Any]:
    linked_graph = {
        "version": str(semantic_graph.get("version") or "1.0"),
        "nodes": list(semantic_graph.get("nodes") or []),
        "edges": list(semantic_graph.get("edges") or []),
        "issues": list(semantic_graph.get("issues") or []),
        "metadata": deepcopy(semantic_graph.get("metadata") or {}),
        "adapters": list(semantic_graph.get("adapters") or []),
    }

    if not linked_graph["adapters"]:
        return linked_graph

    module_nodes_by_id, module_path_to_id = _module_lookup(canonical_nodes)
    semantic_nodes_by_id = _semantic_node_lookup(linked_graph["nodes"])
    semantic_children_by_parent = _children_by_parent(linked_graph["nodes"])
    known_paths = _module_known_paths(canonical_nodes)
    exports_by_module = _build_export_index(linked_graph["nodes"])
    python_internal_roots = _python_internal_roots(canonical_nodes)

    seen_edge_ids = {str(edge.get("id") or "") for edge in linked_graph["edges"]}
    seen_issue_ids = {str(issue.get("id") or "") for issue in linked_graph["issues"]}

    def append_issue(issue: Dict[str, Any]) -> None:
        issue_id = str(issue.get("id") or "")
        if issue_id and issue_id not in seen_issue_ids:
            seen_issue_ids.add(issue_id)
            linked_graph["issues"].append(issue)

    def append_edge(edge: Dict[str, Any]) -> None:
        edge_id = str(edge.get("id") or "")
        if edge_id and edge_id not in seen_edge_ids:
            seen_edge_ids.add(edge_id)
            linked_graph["edges"].append(edge)

    for adapter in linked_graph["adapters"]:
        parser_name = str(adapter.get("parser") or "")
        language = str(adapter.get("language") or "").strip().lower()
        supports_linking = parser_name.startswith("rolldown-ast") or language == "python"
        if not supports_linking:
            continue

        source_module_id = str(adapter.get("sourceNodeId") or "")
        source_module = module_nodes_by_id.get(source_module_id)
        if not source_module:
            continue

        deferred_groups = (
            adapter.get("deferredCalls") or [],
            adapter.get("deferredRoleLinks") or [],
            adapter.get("deferredRenders") or [],
        )

        for imported in adapter.get("imports") or []:
            imported_record = dict(imported)
            imported_record["language"] = language
            if language == "python":
                if not _should_validate_python_import(imported_record, python_internal_roots):
                    continue
            else:
                specifier = str(imported_record.get("specifier") or "").strip()
                if not _is_local_specifier(specifier):
                    continue

            target_module_id = _resolve_target_module_id(source_module, imported_record, known_paths, module_path_to_id)
            if target_module_id:
                continue

            import_label = str(imported_record.get("specifier") or imported_record.get("moduleName") or "").strip()
            append_issue(
                _build_issue(
                    source_module=source_module,
                    source_id=source_module_id,
                    issue_type="unresolved_import",
                    line_start=int(imported_record.get("lineStart")) if imported_record.get("lineStart") is not None else None,
                    message=f"No se pudo resolver el modulo importado `{import_label}`.",
                    metadata={
                        "specifier": str(imported_record.get("specifier") or ""),
                        "moduleName": str(imported_record.get("moduleName") or ""),
                        "importedName": str(imported_record.get("importedName") or ""),
                        "level": imported_record.get("level"),
                        "sourceModuleId": source_module_id,
                    },
                )
            )

        for deferred_group in deferred_groups:
            for deferred in deferred_group:
                deferred["language"] = language
                if language != "python":
                    specifier = str(deferred.get("specifier") or "").strip()
                    if not _is_local_specifier(specifier):
                        continue
                target_module_id = _resolve_target_module_id(source_module, deferred, known_paths, module_path_to_id)
                if not target_module_id:
                    if language != "python" or _should_validate_python_import(deferred, python_internal_roots):
                        import_label = str(deferred.get("specifier") or deferred.get("moduleName") or "").strip()
                        append_issue(
                            _build_issue(
                                source_module=source_module,
                                source_id=str(deferred.get("sourceId") or source_module_id),
                                issue_type="unresolved_import",
                                line_start=int(deferred.get("lineStart")) if deferred.get("lineStart") is not None else None,
                                message=f"No se pudo resolver el modulo importado `{import_label}`.",
                                metadata={
                                    "specifier": str(deferred.get("specifier") or ""),
                                    "moduleName": str(deferred.get("moduleName") or ""),
                                    "importedName": str(deferred.get("importedName") or ""),
                                    "level": deferred.get("level"),
                                    "edgeType": str(deferred.get("edgeType") or ""),
                                    "sourceModuleId": source_module_id,
                                },
                            )
                        )
                    continue

                imported_name = str(deferred.get("importedName") or "").strip()
                if not imported_name or imported_name == "*":
                    continue

                target_symbol_id = _resolve_target_symbol_id(
                    target_module_id=target_module_id,
                    deferred=deferred,
                    exports_by_module=exports_by_module,
                    semantic_nodes_by_id=semantic_nodes_by_id,
                    children_by_parent=semantic_children_by_parent,
                )
                if not target_symbol_id:
                    append_issue(
                        _build_issue(
                            source_module=source_module,
                            source_id=str(deferred.get("sourceId") or source_module_id),
                            issue_type="type_resolution_failure",
                            line_start=int(deferred.get("lineStart")) if deferred.get("lineStart") is not None else None,
                            message=f"No se pudo resolver el simbolo importado `{imported_name}` desde `{str(deferred.get('specifier') or deferred.get('moduleName') or '')}`.",
                            metadata={
                                "specifier": str(deferred.get("specifier") or ""),
                                "importedName": imported_name,
                                "moduleName": str(deferred.get("moduleName") or ""),
                                "memberName": str(deferred.get("memberName") or ""),
                                "level": deferred.get("level"),
                                "targetModuleId": target_module_id,
                                "sourceModuleId": source_module_id,
                                "edgeType": str(deferred.get("edgeType") or ""),
                            },
                        )
                    )
                    continue

                source_id = str(deferred.get("sourceId") or "")
                source_scene = str(
                    (semantic_nodes_by_id.get(source_id) or {}).get("sceneId")
                    or source_module.get("sceneId")
                    or ""
                )
                source_origin = str(
                    (semantic_nodes_by_id.get(source_id) or {}).get("originType")
                    or source_module.get("originType")
                    or "inference"
                )
                edge_type = str(deferred.get("edgeType") or "depends_on")
                line_start = int(deferred.get("lineStart")) if deferred.get("lineStart") is not None else 0
                append_edge(
                    build_edge(
                        edge_id=f"edge:{source_id}->{target_symbol_id}:{edge_type}:inter-module:{line_start}",
                        edge_type=edge_type,
                        source_id=source_id,
                        target_id=target_symbol_id,
                        project_id=source_module["projectId"],
                        scene_id=source_scene,
                        origin_type=source_origin,
                        confidence=0.9,
                        metadata={
                            **deepcopy(deferred.get("metadata") or {}),
                            "interModule": True,
                            "specifier": str(deferred.get("specifier") or ""),
                            "importedName": imported_name,
                            "moduleName": deferred.get("moduleName"),
                            "memberName": deferred.get("memberName"),
                            "level": deferred.get("level"),
                            "sourceModuleId": source_module_id,
                            "targetModuleId": target_module_id,
                        },
                    )
                )

    linked_graph["metadata"] = {
        **linked_graph["metadata"],
        "nodeCount": len(linked_graph["nodes"]),
        "edgeCount": len(linked_graph["edges"]),
        "issueCount": len(linked_graph["issues"]),
    }
    return linked_graph
