from __future__ import annotations

import os
import re
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List, Tuple

from ir_adapters.common import build_edge, build_symbol_node
from ir_contract import CONTRACT_VERSION, slugify


def _normalize_relative_path(path: str) -> str:
    normalized = str(PurePosixPath(os.path.normpath(path))).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_external_reference(reference: str) -> bool:
    return reference.startswith(("http://", "https://", "//"))


def _is_ignored_reference(reference: str) -> bool:
    return not reference or reference.startswith(("#", "data:", "mailto:", "javascript:"))


def _candidate_paths_for_reference(current_path: str, reference: str) -> List[str]:
    if _is_ignored_reference(reference):
        return []

    normalized_reference = reference.split("?", 1)[0].split("#", 1)[0].strip()
    if not normalized_reference or _is_external_reference(normalized_reference):
        return []

    current = PurePosixPath(current_path)
    current_parent = current.parent
    candidates: List[str] = []

    if normalized_reference.startswith("/"):
        parts = current.parts
        if parts:
            candidates.append(_normalize_relative_path(str(PurePosixPath(parts[0]) / normalized_reference.lstrip("/"))))
    else:
        candidates.append(_normalize_relative_path(str(current_parent / normalized_reference)))

    suffix = PurePosixPath(normalized_reference).suffix.lower()
    if not suffix:
        for extension in (".js", ".jsx", ".ts", ".tsx", ".css", ".html"):
            candidates.append(f"{candidates[0]}{extension}")

    unique: List[str] = []
    seen = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def _lookup_node_by_reference(nodes: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        for key in ("canonicalPath", "path"):
            value = str(node.get(key) or "")
            if value and value not in mapping:
                mapping[value] = node
    return mapping


def _resolve_internal_reference(
    *,
    current_path: str,
    reference: str,
    nodes_by_path: Dict[str, Dict[str, Any]],
) -> Tuple[str | None, Dict[str, Any] | None]:
    for candidate in _candidate_paths_for_reference(current_path, reference):
        target = nodes_by_path.get(candidate)
        if target is not None:
            return candidate, target
    return None, None


class HtmlSemanticParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.script_references: List[Dict[str, Any]] = []
        self.stylesheet_references: List[Dict[str, Any]] = []
        self.asset_references: List[Dict[str, Any]] = []
        self.event_handlers: List[Dict[str, Any]] = []
        self.inline_scripts: List[Dict[str, Any]] = []
        self.inline_styles: List[Dict[str, Any]] = []
        self._active_script: Dict[str, Any] | None = None
        self._active_style: Dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        line, _ = self.getpos()

        for attr_name, attr_value in attr_map.items():
            if attr_name.startswith("on") and attr_value.strip():
                self.event_handlers.append(
                    {
                        "eventName": attr_name[2:],
                        "code": attr_value.strip(),
                        "tag": tag,
                        "line": line,
                    }
                )

        if tag == "script":
            src = attr_map.get("src", "").strip()
            if src:
                self.script_references.append(
                    {
                        "src": src,
                        "type": attr_map.get("type", "").strip().lower(),
                        "line": line,
                    }
                )
            else:
                self._active_script = {
                    "type": attr_map.get("type", "").strip().lower(),
                    "line": line,
                    "code": "",
                }
            return

        if tag == "style":
            self._active_style = {
                "line": line,
                "code": "",
            }
            return

        if tag == "link":
            rel = {part.strip().lower() for part in attr_map.get("rel", "").split()}
            href = attr_map.get("href", "").strip()
            if "stylesheet" in rel and href:
                self.stylesheet_references.append({"href": href, "line": line})
                return

        for attr_name in ("src", "href", "poster"):
            value = attr_map.get(attr_name, "").strip()
            if not value:
                continue
            if tag == "link" and attr_name == "href":
                continue
            if tag == "script" and attr_name == "src":
                continue
            self.asset_references.append(
                {
                    "tag": tag,
                    "attribute": attr_name,
                    "value": value,
                    "line": line,
                }
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._active_script is not None:
            code = self._active_script["code"].strip()
            if code:
                self.inline_scripts.append(self._active_script)
            self._active_script = None
        elif tag == "style" and self._active_style is not None:
            code = self._active_style["code"].strip()
            if code:
                self.inline_styles.append(self._active_style)
            self._active_style = None

    def handle_data(self, data: str) -> None:
        if self._active_script is not None:
            self._active_script["code"] += data
        if self._active_style is not None:
            self._active_style["code"] += data


def _css_reference_matches(code: str) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for match in re.finditer(r"@import\s+(?:url\()?['\"]?([^'\"\)\s]+)", code):
        line = code[: match.start()].count("\n") + 1
        matches.append({"reference": match.group(1), "referenceType": "import", "line": line})
    for match in re.finditer(r"url\(\s*['\"]?([^'\"\)]+)", code):
        value = match.group(1).strip()
        if value.startswith("data:"):
            continue
        line = code[: match.start()].count("\n") + 1
        matches.append({"reference": value, "referenceType": "asset", "line": line})
    return matches


def _external_dependency_node(
    *,
    parent_node: Dict[str, Any],
    parent_id: str,
    line_start: int | None,
    name: str,
    target_url: str,
    position_x: float,
    position_y: float,
) -> Dict[str, Any]:
    node_id = f"{parent_id}::external:{slugify(target_url)}"
    node = build_symbol_node(
        parent_node=parent_node,
        symbol_id=node_id,
        symbol_name=name,
        node_type="external_dependency",
        description=f"Dependencia externa referenciada desde `{parent_node['name']}`.",
        language="external",
        line_start=line_start,
        line_end=line_start,
        parent_id=parent_id,
        position={"x": position_x, "y": position_y},
        metadata={"targetUrl": target_url},
    )
    node["originType"] = "inference"
    node["canonicalPath"] = f"{parent_node['canonicalPath']}::{target_url}"
    node["sourcePath"] = target_url
    return node


def _missing_reference_issue(
    *,
    parent_node: Dict[str, Any],
    reference: str,
    line: int | None,
    message: str,
    evidence: List[str],
) -> Dict[str, Any]:
    return {
        "id": f"issue:htmlcss:{parent_node['id']}:{line or 0}:{slugify(reference)}",
        "issueType": "missing_dependency",
        "severity": "warning",
        "status": "open",
        "projectId": parent_node["projectId"],
        "sceneId": parent_node["sceneId"],
        "nodeId": parent_node["id"],
        "edgeId": "",
        "stepId": "",
        "sourcePath": parent_node["sourcePath"],
        "lineStart": line,
        "lineEnd": line,
        "message": message,
        "evidence": evidence,
        "suggestedAction": "Agrega el asset referido al proyecto o corrige la ruta.",
        "metadata": {"adapter": "html_css", "reference": reference},
    }


def _append_external_reference(
    *,
    parent_node: Dict[str, Any],
    parent_id: str,
    edge_type: str,
    reference: str,
    line: int | None,
    semantic_nodes: List[Dict[str, Any]],
    semantic_edges: List[Dict[str, Any]],
    external_nodes: Dict[str, Dict[str, Any]],
    offset_y: float,
) -> None:
    external_key = f"{parent_id}::{reference}"
    dependency = external_nodes.get(external_key)
    if dependency is None:
        dependency = _external_dependency_node(
            parent_node=parent_node,
            parent_id=parent_id,
            line_start=line,
            name=reference,
            target_url=reference,
            position_x=(parent_node.get("position", {}) or {}).get("x", 0.0) + 270.0,
            position_y=(parent_node.get("position", {}) or {}).get("y", 0.0) + offset_y,
        )
        external_nodes[external_key] = dependency
        semantic_nodes.append(dependency)
        semantic_edges.append(
            build_edge(
                edge_id=f"edge:{parent_id}->{dependency['id']}:contains",
                edge_type="contains",
                source_id=parent_id,
                target_id=dependency["id"],
                project_id=parent_node["projectId"],
                scene_id=parent_node["sceneId"],
                origin_type=parent_node["originType"],
            )
        )

    semantic_edges.append(
        build_edge(
            edge_id=f"edge:{parent_id}->{dependency['id']}:{edge_type}:{line or 0}",
            edge_type=edge_type,
            source_id=parent_id,
            target_id=dependency["id"],
            project_id=parent_node["projectId"],
            scene_id=parent_node["sceneId"],
            origin_type="inference",
            confidence=0.92,
            metadata={"reference": reference},
        )
    )


def _process_css_references(
    *,
    parent_node: Dict[str, Any],
    owner_node: Dict[str, Any],
    base_path: str,
    code: str,
    nodes_by_path: Dict[str, Dict[str, Any]],
    semantic_nodes: List[Dict[str, Any]],
    semantic_edges: List[Dict[str, Any]],
    semantic_issues: List[Dict[str, Any]],
    external_nodes: Dict[str, Dict[str, Any]],
    line_offset: int = 0,
) -> None:
    for match in _css_reference_matches(code):
        reference = str(match["reference"])
        reference_type = str(match["referenceType"])
        line = (int(match["line"]) + line_offset) if isinstance(match.get("line"), int) else None

        if _is_ignored_reference(reference):
            continue

        if _is_external_reference(reference):
            _append_external_reference(
                parent_node=parent_node,
                parent_id=owner_node["id"],
                edge_type="links_to_external",
                reference=reference,
                line=line,
                semantic_nodes=semantic_nodes,
                semantic_edges=semantic_edges,
                external_nodes=external_nodes,
                offset_y=210.0 + len(external_nodes) * 36.0,
            )
            continue

        resolved_path, target_node = _resolve_internal_reference(
            current_path=base_path,
            reference=reference,
            nodes_by_path=nodes_by_path,
        )
        if target_node is not None:
            semantic_edges.append(
                build_edge(
                    edge_id=f"edge:{owner_node['id']}->{target_node['id']}:{reference_type}:{line or 0}",
                    edge_type="imports" if reference_type == "import" else "references",
                    source_id=owner_node["id"],
                    target_id=str(target_node["id"]),
                    project_id=parent_node["projectId"],
                    scene_id=parent_node["sceneId"],
                    origin_type="inference",
                    confidence=0.94,
                    metadata={"reference": reference, "resolvedPath": resolved_path or ""},
                )
            )
            continue

        semantic_issues.append(
            _missing_reference_issue(
                parent_node=parent_node,
                reference=reference,
                line=line,
                message=f"No se pudo resolver la referencia CSS `{reference}`.",
                evidence=[reference_type, base_path],
            )
        )


def build_html_css_semantic_graph(nodes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    semantic_nodes: List[Dict[str, Any]] = []
    semantic_edges: List[Dict[str, Any]] = []
    semantic_issues: List[Dict[str, Any]] = []
    adapters: List[Dict[str, Any]] = []
    nodes_by_path = _lookup_node_by_reference(nodes)
    external_nodes: Dict[str, Dict[str, Any]] = {}

    for parent_node in nodes:
        language = str(parent_node.get("language") or "")
        node_type = str(parent_node.get("nodeType") or "")
        code = str(parent_node.get("code") or "")
        if not code.strip():
            continue

        if language == "html" or node_type == "template":
            parser = HtmlSemanticParser()
            parser.feed(code)
            parser.close()
            file_symbols: List[Dict[str, Any]] = []

            for index, inline_style in enumerate(parser.inline_styles, start=1):
                style_id = f"{parent_node['id']}::style:{index}"
                style_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=style_id,
                    symbol_name=f"inline-style-{index}",
                    node_type="style_sheet",
                    description="Bloque `<style>` embebido en la plantilla HTML.",
                    language="css",
                    line_start=inline_style["line"],
                    line_end=inline_style["line"] + inline_style["code"].count("\n"),
                    parent_id=parent_node["id"],
                    position={
                        "x": (parent_node.get("position", {}) or {}).get("x", 0.0) + 180.0,
                        "y": (parent_node.get("position", {}) or {}).get("y", 0.0) + 70.0 + index * 44.0,
                    },
                    metadata={"code": inline_style["code"]},
                )
                semantic_nodes.append(style_node)
                file_symbols.append(style_node)
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{parent_node['id']}->{style_id}:contains",
                        edge_type="contains",
                        source_id=parent_node["id"],
                        target_id=style_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type=parent_node["originType"],
                    )
                )
                _process_css_references(
                    parent_node=parent_node,
                    owner_node=style_node,
                    base_path=str(parent_node.get("canonicalPath") or parent_node.get("path") or ""),
                    code=str(inline_style["code"]),
                    nodes_by_path=nodes_by_path,
                    semantic_nodes=semantic_nodes,
                    semantic_edges=semantic_edges,
                    semantic_issues=semantic_issues,
                    external_nodes=external_nodes,
                    line_offset=max(int(inline_style["line"]) - 1, 0),
                )

            for index, inline_script in enumerate(parser.inline_scripts, start=1):
                script_id = f"{parent_node['id']}::script:{index}"
                script_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=script_id,
                    symbol_name=f"inline-script-{index}",
                    node_type="script_block",
                    description="Bloque `<script>` embebido en la plantilla HTML.",
                    language="javascript",
                    line_start=inline_script["line"],
                    line_end=inline_script["line"] + inline_script["code"].count("\n"),
                    parent_id=parent_node["id"],
                    position={
                        "x": (parent_node.get("position", {}) or {}).get("x", 0.0) + 180.0,
                        "y": (parent_node.get("position", {}) or {}).get("y", 0.0) + 160.0 + index * 44.0,
                    },
                    metadata={"scriptType": inline_script["type"], "code": inline_script["code"]},
                )
                semantic_nodes.append(script_node)
                file_symbols.append(script_node)
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{parent_node['id']}->{script_id}:contains",
                        edge_type="contains",
                        source_id=parent_node["id"],
                        target_id=script_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type=parent_node["originType"],
                    )
                )

            for index, handler in enumerate(parser.event_handlers, start=1):
                handler_id = f"{parent_node['id']}::event:{slugify(handler['eventName'])}:{index}"
                handler_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=handler_id,
                    symbol_name=f"{handler['eventName']}@{handler['tag']}",
                    node_type="event_handler",
                    description="Handler inline definido como atributo HTML.",
                    language="html",
                    line_start=handler["line"],
                    line_end=handler["line"],
                    parent_id=parent_node["id"],
                    position={
                        "x": (parent_node.get("position", {}) or {}).get("x", 0.0) + 180.0,
                        "y": (parent_node.get("position", {}) or {}).get("y", 0.0) + 250.0 + index * 36.0,
                    },
                    metadata={"eventName": handler["eventName"], "tag": handler["tag"], "code": handler["code"]},
                )
                semantic_nodes.append(handler_node)
                file_symbols.append(handler_node)
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{parent_node['id']}->{handler_id}:contains",
                        edge_type="contains",
                        source_id=parent_node["id"],
                        target_id=handler_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type=parent_node["originType"],
                    )
                )

            current_path = str(parent_node.get("canonicalPath") or parent_node.get("path") or "")
            for script_ref in parser.script_references:
                reference = str(script_ref["src"])
                line = int(script_ref["line"]) if isinstance(script_ref.get("line"), int) else None
                if _is_external_reference(reference):
                    _append_external_reference(
                        parent_node=parent_node,
                        parent_id=parent_node["id"],
                        edge_type="links_to_external",
                        reference=reference,
                        line=line,
                        semantic_nodes=semantic_nodes,
                        semantic_edges=semantic_edges,
                        external_nodes=external_nodes,
                        offset_y=320.0 + len(external_nodes) * 36.0,
                    )
                    continue
                resolved_path, target_node = _resolve_internal_reference(
                    current_path=current_path,
                    reference=reference,
                    nodes_by_path=nodes_by_path,
                )
                if target_node is not None:
                    semantic_edges.append(
                        build_edge(
                            edge_id=f"edge:{parent_node['id']}->{target_node['id']}:imports:{line or 0}",
                            edge_type="imports",
                            source_id=parent_node["id"],
                            target_id=str(target_node["id"]),
                            project_id=parent_node["projectId"],
                            scene_id=parent_node["sceneId"],
                            origin_type="inference",
                            confidence=0.97,
                            metadata={"reference": reference, "resolvedPath": resolved_path or "", "scriptType": script_ref["type"]},
                        )
                    )
                else:
                    semantic_issues.append(
                        _missing_reference_issue(
                            parent_node=parent_node,
                            reference=reference,
                            line=line,
                            message=f"No se pudo resolver el script `{reference}`.",
                            evidence=["script", current_path],
                        )
                    )

            for style_ref in parser.stylesheet_references:
                reference = str(style_ref["href"])
                line = int(style_ref["line"]) if isinstance(style_ref.get("line"), int) else None
                if _is_external_reference(reference):
                    _append_external_reference(
                        parent_node=parent_node,
                        parent_id=parent_node["id"],
                        edge_type="links_to_external",
                        reference=reference,
                        line=line,
                        semantic_nodes=semantic_nodes,
                        semantic_edges=semantic_edges,
                        external_nodes=external_nodes,
                        offset_y=360.0 + len(external_nodes) * 36.0,
                    )
                    continue
                resolved_path, target_node = _resolve_internal_reference(
                    current_path=current_path,
                    reference=reference,
                    nodes_by_path=nodes_by_path,
                )
                if target_node is not None:
                    semantic_edges.append(
                        build_edge(
                            edge_id=f"edge:{parent_node['id']}->{target_node['id']}:imports:style:{line or 0}",
                            edge_type="imports",
                            source_id=parent_node["id"],
                            target_id=str(target_node["id"]),
                            project_id=parent_node["projectId"],
                            scene_id=parent_node["sceneId"],
                            origin_type="inference",
                            confidence=0.97,
                            metadata={"reference": reference, "resolvedPath": resolved_path or ""},
                        )
                    )
                else:
                    semantic_issues.append(
                        _missing_reference_issue(
                            parent_node=parent_node,
                            reference=reference,
                            line=line,
                            message=f"No se pudo resolver la hoja de estilos `{reference}`.",
                            evidence=["link-stylesheet", current_path],
                        )
                    )

            for asset_ref in parser.asset_references:
                reference = str(asset_ref["value"])
                line = int(asset_ref["line"]) if isinstance(asset_ref.get("line"), int) else None
                if _is_ignored_reference(reference):
                    continue
                if _is_external_reference(reference):
                    _append_external_reference(
                        parent_node=parent_node,
                        parent_id=parent_node["id"],
                        edge_type="links_to_external",
                        reference=reference,
                        line=line,
                        semantic_nodes=semantic_nodes,
                        semantic_edges=semantic_edges,
                        external_nodes=external_nodes,
                        offset_y=400.0 + len(external_nodes) * 36.0,
                    )
                    continue
                resolved_path, target_node = _resolve_internal_reference(
                    current_path=current_path,
                    reference=reference,
                    nodes_by_path=nodes_by_path,
                )
                if target_node is not None:
                    semantic_edges.append(
                        build_edge(
                            edge_id=f"edge:{parent_node['id']}->{target_node['id']}:references:{line or 0}",
                            edge_type="references",
                            source_id=parent_node["id"],
                            target_id=str(target_node["id"]),
                            project_id=parent_node["projectId"],
                            scene_id=parent_node["sceneId"],
                            origin_type="inference",
                            confidence=0.92,
                            metadata={"reference": reference, "tag": asset_ref["tag"], "attribute": asset_ref["attribute"]},
                        )
                    )
                else:
                    semantic_issues.append(
                        _missing_reference_issue(
                            parent_node=parent_node,
                            reference=reference,
                            line=line,
                            message=f"No se pudo resolver el asset `{reference}`.",
                            evidence=[asset_ref["tag"], asset_ref["attribute"], current_path],
                        )
                    )

            adapters.append(
                {
                    "language": "html",
                    "parser": "html.parser",
                    "status": "ok",
                    "sourceNodeId": parent_node["id"],
                    "limitations": [
                        "estructura por etiquetas relevantes",
                        "eventos inline y referencias a scripts/styles/assets",
                    ],
                    "nodeCount": len(file_symbols),
                }
            )

        elif language == "css" or node_type == "style_sheet":
            _process_css_references(
                parent_node=parent_node,
                owner_node=parent_node,
                base_path=str(parent_node.get("canonicalPath") or parent_node.get("path") or ""),
                code=code,
                nodes_by_path=nodes_by_path,
                semantic_nodes=semantic_nodes,
                semantic_edges=semantic_edges,
                semantic_issues=semantic_issues,
                external_nodes=external_nodes,
            )
            adapters.append(
                {
                    "language": "css",
                    "parser": "regex",
                    "status": "ok",
                    "sourceNodeId": parent_node["id"],
                    "limitations": [
                        "resolucion de @import y url()",
                        "sin parser CSS completo",
                    ],
                    "nodeCount": 0,
                }
            )

    return {
        "version": CONTRACT_VERSION,
        "nodes": semantic_nodes,
        "edges": semantic_edges,
        "issues": semantic_issues,
        "metadata": {
            "nodeCount": len(semantic_nodes),
            "edgeCount": len(semantic_edges),
            "issueCount": len(semantic_issues),
            "adapterCount": len(adapters),
        },
        "adapters": adapters,
    }
