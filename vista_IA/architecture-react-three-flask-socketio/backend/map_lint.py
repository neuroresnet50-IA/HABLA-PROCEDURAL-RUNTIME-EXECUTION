from __future__ import annotations

import ast
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List

from project_graph import extract_html_references, extract_js_imports, normalize_posix_path, resolve_import_specifier, to_posix

IGNORED_PARTS = {"node_modules", "dist", "__pycache__", ".venv", ".vista"}
WORKSPACE_PREFIXES = {("workspace", "projects"), ("analysis", "projects")}
PROJECT_CONTENT_FOLDERS = {"src", "backend", "frontend", "shared", "tests", "docs", "algorithms", "assets"}
CONCEPTUAL_DOC_SUFFIXES = {".md"}
CONCEPTUAL_ROOT_FILES = {"readme.md"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_path_parts(relative_path: str) -> tuple[str, str, List[str]] | None:
    path = PurePosixPath(normalize_posix_path(relative_path))
    parts = list(path.parts)
    if len(parts) < 3 or tuple(parts[:2]) not in WORKSPACE_PREFIXES:
        return None
    return parts[0], parts[2], parts[3:]


def workspace_scene_segments(relative_path: str) -> List[str]:
    resolved = workspace_path_parts(relative_path)
    if resolved is None:
        return []

    _, _, remainder = resolved
    segments: List[str] = []
    for index, part in enumerate(remainder):
        if part in PROJECT_CONTENT_FOLDERS:
            break
        if index == len(remainder) - 1:
            break
        segments.append(part)
    return segments


def workspace_scene_key_for_path(relative_path: str) -> str | None:
    resolved = workspace_path_parts(relative_path)
    if resolved is None:
        return None

    _, project_slug, _ = resolved
    segments = workspace_scene_segments(relative_path)
    if not segments:
        return project_slug
    return "/".join([project_slug, *segments])


def workspace_scene_label(scene_key: str | None) -> str:
    if not scene_key:
        return "Mapa completo"
    return " / ".join(segment.replace("-", " ").title() for segment in scene_key.split("/"))


def workspace_scene_root_for_path(relative_path: str) -> str | None:
    resolved = workspace_path_parts(relative_path)
    if resolved is None:
        return None

    prefix_kind, project_slug, _ = resolved
    segments = workspace_scene_segments(relative_path)
    root_parts = [prefix_kind, "projects", project_slug, *segments]
    return normalize_posix_path("/".join(root_parts))


def infer_expected_layer(relative_path: str) -> str | None:
    normalized = normalize_posix_path(relative_path)
    suffix = PurePosixPath(normalized).suffix.lower()

    if normalized.endswith("/backend/data/tasks.json") or "/backend/data/" in normalized:
        return "data"
    if "/docs/" in normalized or suffix == ".md":
        return "docs"
    if suffix == ".css":
        return "style"
    if "/shared/" in normalized:
        return "shared"
    if "/frontend/" in normalized:
        return "frontend"
    if "/backend/" in normalized:
        return "backend"
    return None


def extract_fetch_targets(content: str) -> List[str]:
    return [match for match in re.findall(r'fetch\(\s*["\']([^"\']+)["\']', content or "") if match]


def resolve_project_root_reference(current_path: str, specifier: str, known_paths: set[str]) -> str | None:
    normalized = str(specifier or "").strip()
    if not normalized.startswith("/"):
        return None

    scene_root = workspace_scene_root_for_path(current_path)
    if not scene_root:
        return None

    if normalized.startswith(("/shared/", "/frontend/", "/assets/", "/backend/")):
        candidate = normalize_posix_path(f"{scene_root}/{normalized.lstrip('/')}")
        if candidate in known_paths:
            return candidate
    return None


def edge_exists(nodes_by_path: Dict[str, Dict[str, Any]], edge_pairs: set[tuple[str, str]], source_path: str, target_path: str) -> bool:
    source_node = nodes_by_path.get(source_path)
    target_node = nodes_by_path.get(target_path)
    if not source_node or not target_node:
        return False
    return (str(source_node.get("id")), str(target_node.get("id"))) in edge_pairs


def nearest_step_id(steps: List[Dict[str, Any]], line: int | None) -> str | None:
    if not steps or not line:
        return None

    candidates = [
        step for step in steps
        if isinstance(step.get("line"), int) and int(step.get("line") or 0) > 0 and str(step.get("id") or "") not in {"start", "end"}
    ]
    if not candidates:
        return None

    nearest = min(candidates, key=lambda step: abs(int(step.get("line") or 0) - int(line)))
    return str(nearest.get("id") or "") or None


def top_level_python_functions(module: ast.Module) -> List[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def python_call_names(module: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(module):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                names.add(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                names.add(child.func.attr)
    return names


def should_skip_python_orphan(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.name.startswith("_") or node.name in {"main", "run", "start", "bootstrap", "create_app"}:
        return True
    for decorator in node.decorator_list:
        decorator_text = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
        if any(token in decorator_text for token in ("route", "socketio.on", "app.", "bp.", "property")):
            return True
    return False


def extract_js_local_functions(content: str) -> List[Dict[str, Any]]:
    functions: List[Dict[str, Any]] = []
    patterns = (
        r"^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
        r"^(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
        r"^(?:export\s+)?let\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
    )
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("//", "*", "/*")):
            continue
        for pattern in patterns:
            match = re.match(pattern, stripped)
            if match:
                functions.append(
                    {
                        "name": match.group(1),
                        "line": line_no,
                        "exported": stripped.startswith("export "),
                    }
                )
                break
    return functions


def validate_algorithm_wiring(
    steps: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    add_finding,
    *,
    relative_path: str,
    scene_key: str,
) -> None:
    if not steps:
        return

    step_ids = {str(step.get("id") or "") for step in steps if step.get("id")}
    outgoing: Dict[str, List[Dict[str, Any]]] = {step_id: [] for step_id in step_ids}
    incoming: Dict[str, List[Dict[str, Any]]] = {step_id: [] for step_id in step_ids}

    for edge in edges:
        source_id = str(edge.get("from") or "")
        target_id = str(edge.get("to") or "")
        if source_id not in step_ids or target_id not in step_ids:
            add_finding(
                "error",
                "algorithm_broken_edge",
                "El diagrama interno contiene una flecha hacia un bloque inexistente.",
                relative_path=relative_path,
                scene_key=scene_key,
                hint="Corrige el origen o destino de la flecha interna para mantener el cableado del flujo.",
                evidence={"edge": edge},
                step_id=source_id or None,
            )
            continue
        outgoing[source_id].append(edge)
        incoming[target_id].append(edge)

    reachable = set()
    stack = ["start"] if "start" in step_ids else []
    while stack:
        current = stack.pop()
        if current in reachable:
            continue
        reachable.add(current)
        for edge in outgoing.get(current, []):
            target_id = str(edge.get("to") or "")
            if target_id and target_id not in reachable:
                stack.append(target_id)

    for step in steps:
        step_id = str(step.get("id") or "")
        step_type = str(step.get("type") or "")
        line = int(step.get("line") or 0) or None
        if step_id not in reachable and step_id not in {"start"}:
            add_finding(
                "error",
                "algorithm_unreachable_step",
                "Hay un bloque interno que nunca recibe flujo desde el inicio del algoritmo.",
                relative_path=relative_path,
                scene_key=scene_key,
                hint="Conecta este bloque al flujo principal o eliminalo si quedo aislado.",
                line=line,
                step_id=step_id,
            )
        if step_type == "decision" and len(outgoing.get(step_id, [])) < 2:
            add_finding(
                "warning",
                "algorithm_missing_branch",
                "La decision no tiene ambas ramas conectadas y el flujo puede quedar ambiguo.",
                relative_path=relative_path,
                scene_key=scene_key,
                hint="Agrega al menos una salida afirmativa y otra negativa desde este bloque de decision.",
                line=line,
                step_id=step_id,
            )
        if step_type not in {"end", "decision"} and step_id not in {"start"} and not outgoing.get(step_id):
            add_finding(
                "warning",
                "algorithm_dead_end",
                "El bloque interno termina sin salida y puede haber un corte en el harness del algoritmo.",
                relative_path=relative_path,
                scene_key=scene_key,
                hint="Conecta este bloque con el siguiente paso logico o con el fin del flujo.",
                line=line,
                step_id=step_id,
            )


def lint_graph(
    graph: Dict[str, Any],
    project_root: Path,
    scene_filter: str | None = None,
    *,
    include_workspace_doc_scan: bool = True,
) -> Dict[str, Any]:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    nodes_by_path = {normalize_posix_path(str(node.get("path") or "")): node for node in nodes if node.get("path")}
    known_paths = set(nodes_by_path)
    edge_pairs = {(str(edge.get("from") or ""), str(edge.get("to") or "")) for edge in edges if edge.get("from") and edge.get("to")}
    findings: List[Dict[str, Any]] = []

    def in_scope(relative_path: str | None, scene_key: str | None = None) -> bool:
        if not scene_filter:
            return True
        if scene_key is None and relative_path:
            scene_key = workspace_scene_key_for_path(relative_path)
        return scene_key == scene_filter

    def add_finding(
        severity: str,
        code: str,
        message: str,
        *,
        relative_path: str | None = None,
        scene_key: str | None = None,
        hint: str | None = None,
        evidence: Dict[str, Any] | None = None,
        line: int | None = None,
        step_id: str | None = None,
    ) -> None:
        normalized_path = normalize_posix_path(relative_path) if relative_path else None
        if not in_scope(normalized_path, scene_key):
            return
        node = nodes_by_path.get(normalized_path or "")
        algorithm = node.get("algorithm") if isinstance(node, dict) and isinstance(node.get("algorithm"), dict) else {}
        steps = algorithm.get("steps") if isinstance(algorithm.get("steps"), list) else []
        derived_step_id = step_id or nearest_step_id(steps, line)
        finding = {
            "severity": severity,
            "code": code,
            "message": message,
            "path": normalized_path,
            "scene": scene_key or (workspace_scene_key_for_path(normalized_path) if normalized_path else None),
            "hint": hint or "",
            "evidence": evidence or {},
            "line": line,
            "stepId": derived_step_id,
            "nodeId": str(node.get("id") or "") if isinstance(node, dict) else "",
        }
        findings.append(finding)

    for node in nodes:
        relative_path = normalize_posix_path(str(node.get("path") or ""))
        suffix = PurePosixPath(relative_path).suffix.lower()
        scene_key = str(node.get("workspaceScene") or workspace_scene_key_for_path(relative_path) or "")
        expected_scene = workspace_scene_key_for_path(relative_path)
        if expected_scene and scene_key and expected_scene != scene_key:
            add_finding(
                "warning",
                "scene_mismatch",
                "El nodo pertenece a otra escena segun su path y puede contaminar el mapa conceptual.",
                relative_path=relative_path,
                scene_key=scene_key,
                hint="Recalcula workspaceScene usando la ruta real del archivo antes de persistir el nodo.",
                evidence={"expectedScene": expected_scene, "actualScene": scene_key},
            )

        origin = node.get("sceneOrigin") if isinstance(node.get("sceneOrigin"), dict) else None
        position = node.get("position") if isinstance(node.get("position"), dict) else None
        if origin and position:
            origin_x = origin.get("x")
            origin_y = origin.get("y")
            position_x = position.get("x")
            position_y = position.get("y")
            if isinstance(origin_x, (int, float)) and isinstance(origin_y, (int, float)) and isinstance(position_x, (int, float)) and isinstance(position_y, (int, float)):
                if position_x < origin_x or position_y < origin_y:
                    add_finding(
                        "error",
                        "scene_local_coordinates",
                        "El nodo conserva coordenadas locales y puede montarse encima de otra escena.",
                        relative_path=relative_path,
                        scene_key=scene_key,
                        hint="Traduce la posicion local sumando sceneOrigin antes de guardar el nodo sincronizado.",
                        evidence={"sceneOrigin": origin, "position": position},
                    )

        expected_layer = infer_expected_layer(relative_path)
        actual_layer = str(node.get("layer") or "")
        if expected_layer == "data" and actual_layer != "data":
            add_finding(
                "warning",
                "layer_storage_mismatch",
                "El archivo de persistencia esta mezclado con la capa backend en vez de una capa de datos.",
                relative_path=relative_path,
                scene_key=scene_key,
                hint="Clasifica backend/data como layer data para separar logica ejecutable de estado persistido.",
                evidence={"expectedLayer": "data", "actualLayer": actual_layer},
            )
        if expected_layer == "docs" and actual_layer != "docs":
            add_finding(
                "warning",
                "layer_docs_mismatch",
                "La documentacion del proyecto no esta etiquetada como docs dentro del mapa.",
                relative_path=relative_path,
                scene_key=scene_key,
                hint="Usa la capa docs para archivos .md y contenido dentro de /docs/.",
                evidence={"expectedLayer": "docs", "actualLayer": actual_layer},
            )

        algorithm = node.get("algorithm") if isinstance(node.get("algorithm"), dict) else {}
        steps = algorithm.get("steps") if isinstance(algorithm.get("steps"), list) else []
        edges_in_algorithm = algorithm.get("edges") if isinstance(algorithm.get("edges"), list) else []
        code = str(node.get("code") or "")
        validate_algorithm_wiring(
            steps,
            edges_in_algorithm,
            add_finding,
            relative_path=relative_path,
            scene_key=scene_key,
        )
        if expected_layer == "data" and code.strip() in {"[]", "{}", ""}:
            if any(relative_path in str(step.get("code") or "") for step in steps):
                add_finding(
                    "info",
                    "passive_data_pseudo_flow",
                    "El almacenamiento vacio se esta dibujando como algoritmo de proceso en vez de estado pasivo.",
                    relative_path=relative_path,
                    scene_key=scene_key,
                    hint="Renderiza nodos de datos vacios como snapshot o estado, no como flujo ejecutable.",
                )

        if suffix == ".py":
            try:
                module = ast.parse(code)
            except SyntaxError as error:
                add_finding(
                    "error",
                    "python_syntax_error",
                    "El archivo Python tiene un error de sintaxis o indentacion y no puede cablearse completo.",
                    relative_path=relative_path,
                    scene_key=scene_key,
                    hint="Corrige la sintaxis para que el analizador pueda reconstruir el flujo completo.",
                    evidence={"detail": error.msg},
                    line=error.lineno,
                )
            else:
                called_names = python_call_names(module)
                for function in top_level_python_functions(module):
                    if should_skip_python_orphan(function):
                        continue
                    if function.name not in called_names:
                        add_finding(
                            "warning",
                            "python_orphan_function",
                            "Hay una funcion definida que no parece ser llamada por ningun flujo del modulo.",
                            relative_path=relative_path,
                            scene_key=scene_key,
                            hint="Conectala desde el flujo principal, exportala de forma explicita o elimina el codigo muerto.",
                            evidence={"function": function.name},
                            line=function.lineno,
                        )
                for child in ast.walk(module):
                    if isinstance(child, ast.ImportFrom) and child.level > 0:
                        import_path = relative_path
                        base = PurePosixPath(import_path).parent
                        parent_parts = list(base.parts)
                        if child.level > 1:
                            parent_parts = parent_parts[: max(0, len(parent_parts) - (child.level - 1))]
                        module_parts = list(parent_parts)
                        if child.module:
                            module_parts.extend(child.module.split("."))
                        resolved_base = "/".join(module_parts)
                        candidate_paths = [f"{resolved_base}.py", f"{resolved_base}/__init__.py"]
                        if not any(candidate in known_paths for candidate in candidate_paths):
                            add_finding(
                                "error",
                                "python_relative_import_missing",
                                "Hay una importacion relativa de Python que no resuelve a ningun archivo real del proyecto.",
                                relative_path=relative_path,
                                scene_key=scene_key,
                                hint="Revisa el paquete objetivo o corrige la ruta relativa del import.",
                                evidence={"module": child.module or "", "level": child.level},
                                line=child.lineno,
                            )

        if suffix in {".js", ".jsx", ".ts", ".tsx"}:
            open_braces = code.count("{")
            close_braces = code.count("}")
            if open_braces != close_braces:
                add_finding(
                    "warning",
                    "js_brace_mismatch",
                    "El archivo JS/TS tiene llaves desbalanceadas y la lectura del flujo puede quedar rota.",
                    relative_path=relative_path,
                    scene_key=scene_key,
                    hint="Revisa bloques if/else, loops o funciones que no cierran correctamente.",
                    evidence={"openBraces": open_braces, "closeBraces": close_braces},
                )
            for function in extract_js_local_functions(code):
                if function["exported"] or str(function["name"]).startswith(("use", "App")):
                    continue
                occurrences = len(re.findall(rf"\b{re.escape(str(function['name']))}\b", code))
                if occurrences <= 1:
                    add_finding(
                        "warning",
                        "js_orphan_function",
                        "Hay una funcion local declarada que no parece participar en el cableado del modulo.",
                        relative_path=relative_path,
                        scene_key=scene_key,
                        hint="Invocala desde el flujo real, pasala como callback visible o elimina el codigo muerto.",
                        evidence={"function": function["name"]},
                        line=int(function["line"]),
                    )

    workspace_root = project_root / "workspace" / "projects"
    if include_workspace_doc_scan and workspace_root.exists():
        for file_path in workspace_root.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in IGNORED_PARTS for part in file_path.parts):
                continue
            suffix = file_path.suffix.lower()
            file_name = file_path.name.lower()
            if suffix not in CONCEPTUAL_DOC_SUFFIXES and file_name not in CONCEPTUAL_ROOT_FILES:
                continue
            relative_path = to_posix(file_path.relative_to(project_root))
            scene_key = workspace_scene_key_for_path(relative_path)
            if relative_path not in nodes_by_path:
                add_finding(
                    "warning",
                    "missing_conceptual_node",
                    "El archivo existe en disco pero no aparece en el mapa conceptual.",
                    relative_path=relative_path,
                    scene_key=scene_key,
                    hint="Incluye markdown en el escaner o preserva nodos de documentacion al mezclar el estado guardado con el rescan.",
                )

    for relative_path, node in nodes_by_path.items():
        scene_key = str(node.get("workspaceScene") or workspace_scene_key_for_path(relative_path) or "")
        suffix = PurePosixPath(relative_path).suffix.lower()
        content = str(node.get("code") or "")

        if suffix == ".html":
            for specifier in extract_html_references(content):
                resolved = resolve_import_specifier(relative_path, specifier, known_paths) or resolve_project_root_reference(relative_path, specifier, known_paths)
                if (specifier.startswith(".") or specifier.startswith("/")) and not resolved:
                    add_finding(
                        "error",
                        "unresolved_html_reference",
                        "La vista HTML referencia un recurso local que no existe o no puede resolverse.",
                        relative_path=relative_path,
                        scene_key=scene_key,
                        hint="Corrige la ruta del script, stylesheet o recurso enlazado.",
                        evidence={"specifier": specifier},
                    )
                if resolved and not edge_exists(nodes_by_path, edge_pairs, relative_path, resolved):
                    add_finding(
                        "warning",
                        "missing_html_dependency_edge",
                        "La vista HTML referencia un recurso real que no esta conectado en el mapa.",
                        relative_path=relative_path,
                        scene_key=scene_key,
                        hint="Crea una flecha entre el HTML y el recurso referenciado para que la carga sea trazable.",
                        evidence={"targetPath": resolved, "specifier": specifier},
                    )

        if suffix in {".js", ".jsx", ".ts", ".tsx"}:
            for specifier in extract_js_imports(content):
                resolved = resolve_import_specifier(relative_path, specifier, known_paths) or resolve_project_root_reference(relative_path, specifier, known_paths)
                if (specifier.startswith(".") or specifier.startswith("/")) and not resolved:
                    add_finding(
                        "error",
                        "unresolved_module_import",
                        "El modulo importa un archivo local que no existe o no puede resolverse.",
                        relative_path=relative_path,
                        scene_key=scene_key,
                        hint="Corrige el import o crea el archivo faltante para cerrar el cableado.",
                        evidence={"specifier": specifier},
                    )
                if resolved and not edge_exists(nodes_by_path, edge_pairs, relative_path, resolved):
                    add_finding(
                        "warning",
                        "missing_module_edge",
                        "El modulo importa o referencia un archivo real que no esta conectado en el mapa.",
                        relative_path=relative_path,
                        scene_key=scene_key,
                        hint="Agrega una flecha usa/importa para reflejar la dependencia real del modulo.",
                        evidence={"targetPath": resolved, "specifier": specifier},
                    )

            fetch_targets = extract_fetch_targets(content)
            backend_paths = [
                path
                for path, target_node in nodes_by_path.items()
                if str(target_node.get("workspaceScene") or "") == scene_key and str(target_node.get("layer") or "") == "backend"
            ]
            if any(target.startswith("/") and not target.startswith(("/shared/", "/assets/", "/frontend/")) for target in fetch_targets):
                if backend_paths and not any(edge_exists(nodes_by_path, edge_pairs, relative_path, backend_path) for backend_path in backend_paths):
                    add_finding(
                        "warning",
                        "missing_http_backend_edge",
                        "El frontend usa rutas HTTP pero no tiene una flecha hacia el backend de su escena.",
                        relative_path=relative_path,
                        scene_key=scene_key,
                        hint="Conecta el cliente con el servicio backend que responde esas rutas.",
                    )

            for target in fetch_targets:
                resolved = resolve_project_root_reference(relative_path, target, known_paths)
                if resolved and not edge_exists(nodes_by_path, edge_pairs, relative_path, resolved):
                    add_finding(
                        "warning",
                        "missing_fetch_resource_edge",
                        "El cliente hace fetch a un recurso interno pero el mapa no muestra esa dependencia.",
                        relative_path=relative_path,
                        scene_key=scene_key,
                        hint="Agrega una flecha desde el cliente hacia el recurso compartido o estatico que consulta.",
                        evidence={"targetPath": resolved, "fetchTarget": target},
                    )

        if suffix == ".py" and "/backend/" in relative_path:
            if "task_schema.json" in content:
                scene_root = workspace_scene_root_for_path(relative_path)
                if scene_root:
                    target_path = normalize_posix_path(f"{scene_root}/shared/task_schema.json")
                    if target_path in known_paths and not edge_exists(nodes_by_path, edge_pairs, relative_path, target_path):
                        add_finding(
                            "warning",
                            "missing_backend_schema_edge",
                            "El backend usa el schema compartido pero esa dependencia no aparece conectada.",
                            relative_path=relative_path,
                            scene_key=scene_key,
                            hint="Conecta el backend con el schema compartido para reflejar la validacion real.",
                            evidence={"targetPath": target_path},
                        )
            if "tasks.json" in content:
                scene_root = workspace_scene_root_for_path(relative_path)
                if scene_root:
                    target_path = normalize_posix_path(f"{scene_root}/backend/data/tasks.json")
                    if target_path in known_paths and not edge_exists(nodes_by_path, edge_pairs, relative_path, target_path):
                        add_finding(
                            "warning",
                            "missing_backend_storage_edge",
                            "El backend persiste tareas en disco pero el mapa no muestra la dependencia de storage.",
                            relative_path=relative_path,
                            scene_key=scene_key,
                            hint="Conecta el servicio backend con su archivo o capa de persistencia.",
                            evidence={"targetPath": target_path},
                        )

    severity_order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda item: (severity_order.get(str(item.get("severity")), 9), str(item.get("path") or ""), str(item.get("code") or "")))

    summary = {"error": 0, "warning": 0, "info": 0, "total": len(findings)}
    for finding in findings:
        severity = str(finding.get("severity") or "info")
        if severity not in summary:
            summary[severity] = 0
        summary[severity] += 1

    return {
        "generatedAt": utc_now(),
        "scope": {
            "scene": scene_filter or "",
            "label": workspace_scene_label(scene_filter),
        },
        "summary": summary,
        "findings": findings,
    }
