from __future__ import annotations

import ast
from typing import Any, Dict, Iterable, List

from ir_adapters.common import build_edge, build_symbol_node, line_window, position_offset
from ir_contract import CONTRACT_VERSION, slugify


HTTP_DECORATOR_METHODS = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "patch": "PATCH",
    "delete": "DELETE",
    "options": "OPTIONS",
    "head": "HEAD",
}


def _attribute_chain_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _attribute_chain_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _literal_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _string_list_literal(node: ast.AST) -> List[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [_literal_text(item) for item in node.elts]
        return [value for value in values if value]
    value = _literal_text(node)
    return [value] if value else []


def _decorator_target_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _decorator_target_name(node.func)
    return _attribute_chain_name(node)


def _called_symbol_names(node: ast.AST) -> List[str]:
    called: List[str] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name):
            called.append(func.id)
            continue
        if isinstance(func, ast.Attribute):
            dotted = _attribute_chain_name(func)
            if dotted:
                called.append(dotted)
    return called


def _call_specs(node: ast.AST) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        callee_name = _attribute_chain_name(child.func)
        if not callee_name:
            continue
        specs.append(
            {
                "callee": callee_name,
                "lineStart": getattr(child, "lineno", None),
                "lineEnd": getattr(child, "end_lineno", getattr(child, "lineno", None)),
            }
        )
    return specs


def _import_binding_for_call(callee_name: str, import_bindings: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | None:
    parts = [part for part in str(callee_name or "").split(".") if part]
    if not parts:
        return None

    root_name = parts[0]
    binding = import_bindings.get(root_name)
    if not binding:
        return None

    tail_parts = parts[1:]
    binding_kind = str(binding.get("kind") or "")

    if binding_kind == "module":
        module_parts = [part for part in str(binding.get("moduleName") or "").split(".") if part]
        if not module_parts:
            return None
        if not bool(binding.get("aliased")) and len(module_parts) > 1:
            remainder = module_parts[1:]
            if tail_parts[: len(remainder)] == remainder:
                tail_parts = tail_parts[len(remainder) :]
        if not tail_parts:
            return None
        target_module_parts = [*module_parts, *tail_parts[:-1]]
        return {
            "moduleName": ".".join(target_module_parts),
            "importedName": tail_parts[-1],
            "localName": root_name,
            "specifier": str(binding.get("moduleName") or ""),
            "level": int(binding.get("level") or 0),
            "bindingKind": binding_kind,
        }

    if binding_kind == "from":
        module_name = str(binding.get("moduleName") or "")
        imported_name = str(binding.get("importedName") or "")
        if not module_name or not imported_name:
            return None
        if not tail_parts:
            return {
                "moduleName": module_name,
                "importedName": imported_name,
                "localName": root_name,
                "specifier": f"{module_name}.{imported_name}" if module_name else imported_name,
                "level": int(binding.get("level") or 0),
                "bindingKind": binding_kind,
            }
        if not (imported_name[:1].isupper() and any(character.islower() for character in imported_name)):
            return None
        return {
            "moduleName": module_name,
            "importedName": imported_name,
            "localName": root_name,
            "specifier": f"{module_name}.{imported_name}" if module_name else imported_name,
            "level": int(binding.get("level") or 0),
            "bindingKind": binding_kind,
            "memberName": tail_parts[-1],
            "memberChain": tail_parts,
        }

    return None


def _route_specs(node: ast.FunctionDef | ast.AsyncFunctionDef) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for decorator in node.decorator_list:
        decorator_name = _decorator_target_name(decorator)
        terminal = decorator_name.split(".")[-1].lower()
        methods: List[str] = []
        path = ""

        if terminal in HTTP_DECORATOR_METHODS and isinstance(decorator, ast.Call):
            methods = [HTTP_DECORATOR_METHODS[terminal]]
            if decorator.args:
                path = str(_literal_text(decorator.args[0]) or "")
        elif terminal == "route" and isinstance(decorator, ast.Call):
            if decorator.args:
                path = str(_literal_text(decorator.args[0]) or "")
            for keyword in decorator.keywords:
                if keyword.arg == "methods":
                    methods = [value.upper() for value in _string_list_literal(keyword.value)]
                    break
            if not methods:
                methods = ["GET"]

        if methods or path:
            specs.append(
                {
                    "decorator": decorator_name,
                    "methods": methods or ["GET"],
                    "path": path or "",
                }
            )
    return specs


def _event_specs(node: ast.FunctionDef | ast.AsyncFunctionDef) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for decorator in node.decorator_list:
        decorator_name = _decorator_target_name(decorator)
        terminal = decorator_name.split(".")[-1].lower()
        event_name = ""

        if terminal == "on" and isinstance(decorator, ast.Call) and decorator.args:
            event_name = str(_literal_text(decorator.args[0]) or "")
        elif terminal == "event":
            event_name = node.name
        elif terminal == "on_event" and isinstance(decorator, ast.Call) and decorator.args:
            event_name = str(_literal_text(decorator.args[0]) or "")

        if event_name:
            specs.append(
                {
                    "decorator": decorator_name,
                    "eventName": event_name,
                }
            )
    return specs


def build_python_semantic_graph(nodes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    semantic_nodes: List[Dict[str, Any]] = []
    semantic_edges: List[Dict[str, Any]] = []
    semantic_issues: List[Dict[str, Any]] = []
    adapters: List[Dict[str, Any]] = []

    for parent_node in nodes:
        if str(parent_node.get("language") or "") != "python":
            continue
        if str(parent_node.get("nodeType") or "") not in {"module", "file"}:
            continue

        code = str(parent_node.get("code") or "")
        if not code.strip():
            continue

        try:
            module = ast.parse(code)
        except SyntaxError:
            semantic_issues.append(
                {
                    "id": f"issue:semantic:python:{parent_node['id']}",
                    "issueType": "parse_failure",
                    "severity": "error",
                    "status": "open",
                    "projectId": parent_node["projectId"],
                    "sceneId": parent_node["sceneId"],
                    "nodeId": parent_node["id"],
                    "edgeId": "",
                    "stepId": "",
                    "sourcePath": parent_node["sourcePath"],
                    "lineStart": None,
                    "lineEnd": None,
                    "message": "El adaptador semantico Python no pudo parsear el archivo.",
                    "evidence": ["ast.parse"],
                    "suggestedAction": "Corrige la sintaxis del modulo para habilitar la extraccion canonica.",
                    "metadata": {"adapter": "python", "sourceNodeId": parent_node["id"]},
                }
            )
            adapters.append(
                {
                    "language": "python",
                    "parser": "ast:python",
                    "status": "parse_failed",
                    "sourceNodeId": parent_node["id"],
                    "limitations": ["syntax_error"],
                }
            )
            continue

        symbols_by_name: Dict[str, str] = {}
        methods_by_class: Dict[str, Dict[str, str]] = {}
        class_ids: Dict[str, str] = {}
        file_symbols: List[Dict[str, Any]] = []
        deferred_calls: List[Dict[str, Any]] = []
        import_records: List[Dict[str, Any]] = []
        import_bindings: Dict[str, Dict[str, Any]] = {}

        def append_role_nodes(
            *,
            owner_name: str,
            owner_node: ast.FunctionDef | ast.AsyncFunctionDef,
            handler_id: str,
            parent_id: str,
            anchor_position: Dict[str, float] | None,
        ) -> None:
            line_start, line_end = line_window(owner_node)
            route_specs = _route_specs(owner_node)
            event_specs = _event_specs(owner_node)

            for route_index, route_spec in enumerate(route_specs):
                methods = route_spec["methods"]
                path = route_spec["path"]
                route_label = f"{'/'.join(methods)} {path}".strip()
                route_id = f"{handler_id}::route:{slugify(route_label or owner_name)}:{route_index + 1}"
                route_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=route_id,
                    symbol_name=route_label or f"route:{owner_name}",
                    node_type="route",
                    description=f"Ruta HTTP inferida desde `{owner_name}`.",
                    language="python",
                    line_start=line_start,
                    line_end=line_end,
                    parent_id=parent_id,
                    position=position_offset(anchor_position, 180.0, route_index * 48.0) if anchor_position else None,
                    metadata={
                        "methods": methods,
                        "path": path,
                        "handlerNodeId": handler_id,
                        "decorator": route_spec["decorator"],
                    },
                )
                semantic_nodes.append(route_node)
                file_symbols.append(route_node)
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{parent_id}->{route_id}:contains",
                        edge_type="contains",
                        source_id=parent_id,
                        target_id=route_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type=parent_node["originType"],
                    )
                )
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{route_id}->{handler_id}:routes_to",
                        edge_type="routes_to",
                        source_id=route_id,
                        target_id=handler_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type="inference",
                        confidence=0.95,
                        metadata={"methods": methods, "path": path},
                    )
                )

            for event_index, event_spec in enumerate(event_specs):
                event_name = str(event_spec["eventName"] or owner_name)
                event_id = f"{handler_id}::event:{slugify(event_name)}:{event_index + 1}"
                event_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=event_id,
                    symbol_name=event_name,
                    node_type="event_handler",
                    description=f"Handler de evento inferido desde `{owner_name}`.",
                    language="python",
                    line_start=line_start,
                    line_end=line_end,
                    parent_id=parent_id,
                    position=position_offset(anchor_position, 180.0, 96.0 + event_index * 48.0) if anchor_position else None,
                    metadata={
                        "eventName": event_name,
                        "handlerNodeId": handler_id,
                        "decorator": event_spec["decorator"],
                    },
                )
                semantic_nodes.append(event_node)
                file_symbols.append(event_node)
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{parent_id}->{event_id}:contains",
                        edge_type="contains",
                        source_id=parent_id,
                        target_id=event_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type=parent_node["originType"],
                    )
                )
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{event_id}->{handler_id}:handles",
                        edge_type="handles",
                        source_id=event_id,
                        target_id=handler_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type="inference",
                        confidence=0.95,
                        metadata={"eventName": event_name},
                    )
                )

        for child in module.body:
            if isinstance(child, ast.Import):
                for alias in child.names:
                    local_name = str(alias.asname or alias.name.split(".", 1)[0] or "").strip()
                    module_name = str(alias.name or "").strip()
                    if not local_name or not module_name:
                        continue
                    binding = {
                        "kind": "module",
                        "moduleName": module_name,
                        "localName": local_name,
                        "importedName": "*",
                        "level": 0,
                        "aliased": bool(alias.asname),
                    }
                    import_bindings[local_name] = binding
                    import_records.append(
                        {
                            "kind": "module",
                            "moduleName": module_name,
                            "localName": local_name,
                            "importedName": "*",
                            "level": 0,
                            "lineStart": getattr(child, "lineno", None),
                        }
                    )
            elif isinstance(child, ast.ImportFrom):
                module_name = str(child.module or "").strip()
                level = int(child.level or 0)
                for alias in child.names:
                    if alias.name == "*":
                        continue
                    local_name = str(alias.asname or alias.name or "").strip()
                    imported_name = str(alias.name or "").strip()
                    if not local_name or not imported_name:
                        continue
                    binding = {
                        "kind": "from",
                        "moduleName": module_name,
                        "localName": local_name,
                        "importedName": imported_name,
                        "level": level,
                        "aliased": bool(alias.asname),
                    }
                    import_bindings[local_name] = binding
                    import_records.append(
                        {
                            "kind": "from",
                            "moduleName": module_name,
                            "localName": local_name,
                            "importedName": imported_name,
                            "level": level,
                            "lineStart": getattr(child, "lineno", None),
                        }
                    )

        for body_index, child in enumerate(module.body):
            base_position = position_offset(parent_node.get("position"), 90.0, 90.0 + body_index * 72.0)

            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                line_start, line_end = line_window(child)
                symbol_id = f"{parent_node['id']}::function:{child.name}"
                symbol_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=symbol_id,
                    symbol_name=child.name,
                    node_type="function",
                    description=f"Funcion top-level `{child.name}` extraida del modulo Python.",
                    language="python",
                    line_start=line_start,
                    line_end=line_end,
                    parent_id=parent_node["id"],
                    entry_point=child.name == "main",
                    position=base_position,
                    metadata={
                        "exportNames": [child.name],
                        "exported": True,
                        "defaultExport": False,
                    },
                )
                semantic_nodes.append(symbol_node)
                file_symbols.append(symbol_node)
                symbols_by_name[child.name] = symbol_id
                semantic_edges.append(
                    build_edge(
                        edge_id=f"edge:{parent_node['id']}->{symbol_id}:contains",
                        edge_type="contains",
                        source_id=parent_node["id"],
                        target_id=symbol_id,
                        project_id=parent_node["projectId"],
                        scene_id=parent_node["sceneId"],
                        origin_type=parent_node["originType"],
                    )
                )
                continue

            if isinstance(child, ast.ClassDef):
                class_line_start, class_line_end = line_window(child)
                class_id = f"{parent_node['id']}::class:{child.name}"
                class_node = build_symbol_node(
                    parent_node=parent_node,
                    symbol_id=class_id,
                    symbol_name=child.name,
                    node_type="class",
                    description=f"Clase `{child.name}` extraida del modulo Python.",
                    language="python",
                    line_start=class_line_start,
                    line_end=class_line_end,
                    parent_id=parent_node["id"],
                    position=base_position,
                    metadata={
                        "exportNames": [child.name],
                        "exported": True,
                        "defaultExport": False,
                    },
                )
                semantic_nodes.append(class_node)
                file_symbols.append(class_node)
                symbols_by_name[child.name] = class_id
                methods_by_class[child.name] = {}
                class_ids[child.name] = class_id
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

                method_index = 0
                for method in child.body:
                    if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    method_line_start, method_line_end = line_window(method)
                    method_id = f"{class_id}::method:{method.name}"
                    method_node = build_symbol_node(
                        parent_node=parent_node,
                        symbol_id=method_id,
                        symbol_name=f"{child.name}.{method.name}",
                        node_type="method",
                        description=f"Metodo `{method.name}` de la clase `{child.name}`.",
                        language="python",
                        line_start=method_line_start,
                        line_end=method_line_end,
                        parent_id=class_id,
                        entry_point=method.name == "__call__",
                        position=position_offset(base_position, 120.0, method_index * 54.0),
                    )
                    semantic_nodes.append(method_node)
                    file_symbols.append(method_node)
                    methods_by_class[child.name][method.name] = method_id
                    semantic_edges.append(
                        build_edge(
                            edge_id=f"edge:{class_id}->{method_id}:defines",
                            edge_type="defines",
                            source_id=class_id,
                            target_id=method_id,
                            project_id=parent_node["projectId"],
                            scene_id=parent_node["sceneId"],
                            origin_type=parent_node["originType"],
                        )
                    )
                    method_index += 1

        for body_index, child in enumerate(module.body):
            base_position = position_offset(parent_node.get("position"), 90.0, 90.0 + body_index * 72.0)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                handler_id = symbols_by_name.get(child.name)
                if handler_id:
                    append_role_nodes(
                        owner_name=child.name,
                        owner_node=child,
                        handler_id=handler_id,
                        parent_id=parent_node["id"],
                        anchor_position=base_position,
                    )
                continue

            if isinstance(child, ast.ClassDef):
                class_id = class_ids.get(child.name)
                for method_index, method in enumerate(child.body):
                    if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    handler_id = methods_by_class.get(child.name, {}).get(method.name)
                    if not handler_id or not class_id:
                        continue
                    append_role_nodes(
                        owner_name=f"{child.name}.{method.name}",
                        owner_node=method,
                        handler_id=handler_id,
                        parent_id=class_id,
                        anchor_position=position_offset(base_position, 120.0, method_index * 54.0),
                    )

        for child in module.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                source_id = symbols_by_name.get(child.name)
                if not source_id:
                    continue
                for call_spec in _call_specs(child):
                    callee_name = str(call_spec["callee"] or "")
                    target_id = symbols_by_name.get(callee_name)
                    if not target_id or target_id == source_id:
                        imported_binding = _import_binding_for_call(callee_name, import_bindings)
                        if imported_binding:
                            deferred_calls.append(
                                {
                                    "edgeType": "calls",
                                    "sourceId": source_id,
                                    "sourceNodeId": parent_node["id"],
                                    "moduleName": imported_binding["moduleName"],
                                    "importedName": imported_binding["importedName"],
                                    "localName": imported_binding["localName"],
                                    "specifier": imported_binding["specifier"],
                                    "level": imported_binding["level"],
                                    "bindingKind": imported_binding["bindingKind"],
                                    "memberName": imported_binding.get("memberName"),
                                    "memberChain": imported_binding.get("memberChain"),
                                    "lineStart": call_spec["lineStart"],
                                    "metadata": {"callee": callee_name},
                                }
                            )
                        continue
                    semantic_edges.append(
                        build_edge(
                            edge_id=f"edge:{source_id}->{target_id}:calls",
                            edge_type="calls",
                            source_id=source_id,
                            target_id=target_id,
                            project_id=parent_node["projectId"],
                            scene_id=parent_node["sceneId"],
                            origin_type=parent_node["originType"],
                            confidence=0.9,
                            metadata={"callee": callee_name},
                        )
                    )
                continue

            if isinstance(child, ast.ClassDef):
                class_name = child.name
                for method in child.body:
                    if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    source_id = methods_by_class.get(class_name, {}).get(method.name)
                    if not source_id:
                        continue
                    for call_spec in _call_specs(method):
                        callee_name = str(call_spec["callee"] or "")
                        target_id = None
                        if callee_name.startswith("self."):
                            target_id = methods_by_class.get(class_name, {}).get(callee_name.split(".", 1)[1])
                        if target_id is None:
                            target_id = symbols_by_name.get(callee_name)
                        if not target_id or target_id == source_id:
                            imported_binding = _import_binding_for_call(callee_name, import_bindings)
                            if imported_binding:
                                deferred_calls.append(
                                    {
                                        "edgeType": "calls",
                                        "sourceId": source_id,
                                        "sourceNodeId": parent_node["id"],
                                        "moduleName": imported_binding["moduleName"],
                                        "importedName": imported_binding["importedName"],
                                        "localName": imported_binding["localName"],
                                        "specifier": imported_binding["specifier"],
                                        "level": imported_binding["level"],
                                        "bindingKind": imported_binding["bindingKind"],
                                        "memberName": imported_binding.get("memberName"),
                                        "memberChain": imported_binding.get("memberChain"),
                                        "lineStart": call_spec["lineStart"],
                                        "metadata": {"callee": callee_name},
                                    }
                                )
                            continue
                        semantic_edges.append(
                            build_edge(
                                edge_id=f"edge:{source_id}->{target_id}:calls",
                                edge_type="calls",
                                source_id=source_id,
                                target_id=target_id,
                                project_id=parent_node["projectId"],
                                scene_id=parent_node["sceneId"],
                                origin_type=parent_node["originType"],
                                confidence=0.88 if callee_name.startswith("self.") else 0.9,
                                metadata={"callee": callee_name},
                            )
                        )

        adapters.append(
            {
                "language": "python",
                "parser": "ast:python",
                "status": "ok",
                "sourceNodeId": parent_node["id"],
                "limitations": [
                    "solo simbolos top-level y metodos de clase",
                    "resolucion inter-modulo limitada a imports de funciones, clases o submodulos locales",
                ],
                "nodeCount": len(file_symbols),
                "imports": import_records,
                "deferredCalls": deferred_calls,
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
