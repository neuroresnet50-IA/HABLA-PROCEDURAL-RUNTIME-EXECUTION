from __future__ import annotations

import ast
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List

from project_graph import (
    IGNORED_FILES,
    IGNORED_PARTS,
    JS_SUFFIXES,
    SUPPORTED_SUFFIXES,
    STYLE_SUFFIXES,
    build_real_algorithm,
    count_lines,
    describe_file,
    detect_code_language,
    extract_html_references,
    extract_js_imports,
    extract_real_statements,
    extract_python_import_references,
    format_size,
    infer_edge_label,
    infer_edge_type,
    layer_label_for_path,
    node_id_for_path,
    normalize_posix_path,
    to_posix,
)

ANALYSIS_PATH_PREFIX = "analysis/projects"
ANALYSIS_CONTENT_FOLDERS = {"src", "backend", "frontend", "shared", "tests", "docs", "algorithms", "assets", "data"}
MAX_FILE_ANALYSIS = 80
MAX_DIRECTORY_ANALYSIS = 240


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-") or "analysis"


def build_analysis_entry(target_path: str) -> Dict[str, Any]:
    resolved_target = Path(target_path).expanduser().resolve()
    if not resolved_target.exists():
        raise FileNotFoundError(f"No existe la ruta: {resolved_target}")

    mode = "directory" if resolved_target.is_dir() else "file"
    digest = hashlib.sha1(str(resolved_target).encode("utf-8")).hexdigest()[:8]
    base_name = resolved_target.name if resolved_target.is_dir() else resolved_target.stem
    analysis_id = f"reverse-{slugify(base_name)}-{digest}"
    files = discover_analysis_files(resolved_target, mode)
    graph = build_analysis_graph(resolved_target, files, analysis_id, mode)
    primary_node_id = find_primary_node_id(graph, resolved_target)

    return {
        "id": analysis_id,
        "label": resolved_target.name or str(resolved_target),
        "targetPath": str(resolved_target),
        "mode": mode,
        "createdAt": utc_now(),
        "primaryNodeId": primary_node_id,
        "summary": {
            "nodes": len(graph.get("nodes") or []),
            "edges": len(graph.get("edges") or []),
        },
        "graph": graph,
    }


def discover_analysis_files(target_path: Path, mode: str) -> List[Path]:
    if mode == "directory":
        return discover_directory_files(target_path)
    return discover_file_scope(target_path)


def discover_directory_files(target_dir: Path) -> List[Path]:
    files: List[Path] = []
    for file_path in target_dir.rglob("*"):
        if len(files) >= MAX_DIRECTORY_ANALYSIS:
            break
        if not file_path.is_file():
            continue
        if any(part in IGNORED_PARTS for part in file_path.parts):
            continue
        if file_path.name in IGNORED_FILES or file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        files.append(file_path.resolve())
    return sorted(files, key=lambda item: str(item))


def discover_file_scope(target_file: Path) -> List[Path]:
    root_dir = infer_file_scope_root(target_file)
    discovered: List[Path] = []
    seen = set()
    queue = [target_file.resolve()]

    while queue and len(discovered) < MAX_FILE_ANALYSIS:
        current_path = queue.pop(0)
        if current_path in seen:
            continue
        seen.add(current_path)

        if not current_path.is_file():
            continue
        if current_path.suffix.lower() not in SUPPORTED_SUFFIXES or current_path.name in IGNORED_FILES:
            continue
        if any(part in IGNORED_PARTS for part in current_path.parts):
            continue

        discovered.append(current_path)
        for dependency in resolve_local_dependencies(current_path, root_dir):
            if dependency not in seen:
                queue.append(dependency)

    return sorted(discovered, key=lambda item: str(item))


def infer_file_scope_root(target_file: Path) -> Path:
    target_file = target_file.resolve()
    current_dir = target_file.parent

    while (current_dir / "__init__.py").exists() and current_dir.parent != current_dir:
        current_dir = current_dir.parent

    for marker in ("pyproject.toml", "setup.py", "requirements.txt", ".git", "README.md"):
        if (current_dir / marker).exists():
            return current_dir

    return current_dir


def resolve_local_dependencies(current_file: Path, root_dir: Path) -> List[Path]:
    try:
        content = current_file.read_text(encoding="utf-8")
    except OSError:
        return []

    suffix = current_file.suffix.lower()
    dependencies: List[Path] = []

    if suffix in JS_SUFFIXES:
        for specifier in extract_js_imports(content):
            resolved = resolve_local_specifier_actual(current_file, root_dir, specifier)
            if resolved:
                dependencies.append(resolved)
    if suffix == ".html":
        for specifier in extract_html_references(content):
            resolved = resolve_local_specifier_actual(current_file, root_dir, specifier)
            if resolved:
                dependencies.append(resolved)
    if suffix in STYLE_SUFFIXES:
        for specifier in re.findall(r'@import\s+["\']([^"\']+)["\']', content):
            resolved = resolve_local_specifier_actual(current_file, root_dir, specifier)
            if resolved:
                dependencies.append(resolved)
    if suffix == ".py":
        dependencies.extend(resolve_local_python_dependencies(current_file, root_dir, content))

    unique = []
    seen = set()
    for dependency in dependencies:
        resolved_dependency = dependency.resolve()
        if resolved_dependency in seen:
            continue
        seen.add(resolved_dependency)
        unique.append(resolved_dependency)
    return unique


def resolve_local_specifier_actual(current_file: Path, root_dir: Path, specifier: str) -> Path | None:
    normalized = str(specifier or "").strip()
    if not normalized or not normalized.startswith((".", "/")):
        return None

    candidates: List[Path] = []
    if normalized.startswith("/"):
        joined = root_dir / normalized.lstrip("/")
        candidates.extend(expand_actual_candidates(joined))
    else:
        joined = (current_file.parent / normalized).resolve()
        candidates.extend(expand_actual_candidates(joined))

    for candidate in candidates:
        if candidate.is_file() and is_within_root(candidate, root_dir):
            return candidate.resolve()
    return None


def resolve_local_python_dependencies(current_file: Path, root_dir: Path, content: str) -> List[Path]:
    try:
        module = ast.parse(content)
    except SyntaxError:
        return []

    references: List[Path] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = resolve_python_module_actual(current_file, root_dir, alias.name, level=0)
                if resolved:
                    references.append(resolved)
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if module_name:
                resolved = resolve_python_module_actual(current_file, root_dir, module_name, level=node.level)
                if resolved:
                    references.append(resolved)
            elif node.level > 0:
                for alias in node.names:
                    resolved = resolve_python_module_actual(current_file, root_dir, alias.name, level=node.level)
                    if resolved:
                        references.append(resolved)
    return references


def resolve_python_module_actual(current_file: Path, root_dir: Path, module_name: str, level: int = 0) -> Path | None:
    normalized_module = str(module_name or "").strip()
    candidates: List[Path] = []

    if level > 0:
        relative_parent = current_file.parent.resolve()
        for _ in range(max(level - 1, 0)):
            relative_parent = relative_parent.parent
        parts = normalized_module.split(".") if normalized_module else []
        base = relative_parent.joinpath(*parts) if parts else relative_parent
        candidates.extend(expand_python_actual_candidates(base))

    if normalized_module:
        parts = normalized_module.split(".")
        candidates.extend(expand_python_actual_candidates(root_dir.joinpath(*parts)))
        for ancestor in directories_within_root(current_file.parent.resolve(), root_dir):
            candidates.extend(expand_python_actual_candidates(ancestor.joinpath(*parts)))

    for candidate in candidates:
        if candidate.is_file() and is_within_root(candidate, root_dir):
            return candidate.resolve()
    return None


def directories_within_root(start_dir: Path, root_dir: Path) -> Iterable[Path]:
    current = start_dir.resolve()
    root = root_dir.resolve()
    while True:
        if is_within_root(current, root):
            yield current
        if current == root or current == current.parent:
            break
        current = current.parent


def expand_actual_candidates(base_path: Path) -> List[Path]:
    if base_path.suffix:
        return [base_path]

    candidates = [base_path]
    for extension in (".js", ".jsx", ".ts", ".tsx", ".css", ".json", ".html", ".py", ".md", ".txt", ".cpp", ".cc", ".cxx", ".h", ".hpp"):
        candidates.append(Path(f"{base_path}{extension}"))
    for index_name in ("index.js", "index.jsx", "index.ts", "index.tsx"):
        candidates.append(base_path / index_name)
    return candidates


def expand_python_actual_candidates(base_path: Path) -> List[Path]:
    return [
        Path(f"{base_path}.py"),
        base_path / "__init__.py",
    ]


def is_within_root(candidate: Path, root_dir: Path) -> bool:
    try:
        candidate.resolve().relative_to(root_dir.resolve())
        return True
    except ValueError:
        return False


def build_analysis_graph(target_path: Path, files: List[Path], analysis_id: str, mode: str) -> Dict[str, Any]:
    if not files:
        raise ValueError("No se encontraron archivos analizables para esta ruta.")

    root_dir = target_path.resolve() if target_path.is_dir() else infer_file_scope_root(target_path)
    virtual_by_actual = {
        file_path.resolve(): virtual_analysis_path(analysis_id, relative_analysis_path(file_path.resolve(), root_dir, mode))
        for file_path in files
    }
    actual_by_virtual = {virtual_path: actual_path for actual_path, virtual_path in virtual_by_actual.items()}

    imports_by_virtual: Dict[str, List[str]] = {}
    nodes: List[Dict[str, Any]] = []

    for actual_path, virtual_path in virtual_by_actual.items():
        content = actual_path.read_text(encoding="utf-8")
        relative_source = relative_analysis_path(actual_path, root_dir, mode)
        relative_source_normalized = normalize_posix_path(relative_source)
        statements = extract_real_statements(virtual_path, content)
        algorithm = build_real_algorithm(virtual_path, content, statements)
        imports = build_analysis_imports(actual_path, root_dir, virtual_by_actual, content)
        imports_by_virtual[virtual_path] = imports

        layer = infer_analysis_layer(relative_source_normalized)
        layer_label = layer_label_for_analysis(layer)
        nodes.append(
            {
                "id": node_id_for_path(virtual_path),
                "name": actual_path.name,
                "path": virtual_path,
                "sourcePath": str(actual_path),
                "layer": layer,
                "layerLabel": layer_label,
                "status": "generated",
                "size": format_size(actual_path.stat().st_size),
                "lines": count_lines(content),
                "description": describe_file(relative_source_normalized, statements),
                "imports": imports,
                "dependents": [],
                "color": default_color_for_analysis(layer),
                "code": content,
                "codeLanguage": detect_code_language(virtual_path),
                "algorithm": algorithm,
                "readOnly": True,
                "analysisId": analysis_id,
                "analysisLabel": target_path.name or str(target_path),
                "workspaceProject": analysis_id,
                "workspaceScene": analysis_id,
                "workspaceSceneLabel": f"Analisis · {target_path.name or analysis_id}",
            }
        )

    dependents_by_virtual = {node["path"]: [] for node in nodes}
    for source_virtual, import_virtuals in imports_by_virtual.items():
        for target_virtual in import_virtuals:
            dependents_by_virtual.setdefault(target_virtual, []).append(source_virtual)

    node_by_virtual = {node["path"]: node for node in nodes}
    for node in nodes:
        node["dependents"] = dependents_by_virtual.get(node["path"], [])

    edges = []
    seen_edges = set()
    for source_virtual, import_virtuals in imports_by_virtual.items():
        source_node = node_by_virtual.get(source_virtual)
        if not source_node:
            continue
        for target_virtual in import_virtuals:
            target_node = node_by_virtual.get(target_virtual)
            if not target_node:
                continue
            edge_key = (source_node["id"], target_node["id"])
            if edge_key in seen_edges or source_node["id"] == target_node["id"]:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "id": f"edge-{source_node['id']}-{target_node['id']}",
                    "from": source_node["id"],
                    "to": target_node["id"],
                    "type": infer_edge_type(source_node, target_node),
                    "label": infer_edge_label(source_node, target_node),
                    "dashed": False,
                }
            )

    return {
        "metadata": {
            "projectName": f"Analisis · {target_path.name or analysis_id}",
            "sessionId": analysis_id,
            "source": "reverse_engineering",
            "mode": mode,
            "targetPath": str(target_path.resolve()),
            "generatedCount": len(nodes),
            "connectionCount": len(edges),
            "isolatedCount": len([node for node in nodes if not node["imports"] and not node["dependents"]]),
            "updatedAt": utc_now(),
            "note": "Escena generada por ingenieria inversa desde una ruta local cargada por el programador.",
        },
        "nodes": nodes,
        "edges": edges,
    }


def build_analysis_imports(
    actual_path: Path,
    root_dir: Path,
    virtual_by_actual: Dict[Path, str],
    content: str,
) -> List[str]:
    discovered_virtuals: List[str] = []
    suffix = actual_path.suffix.lower()

    if suffix in JS_SUFFIXES:
        for specifier in extract_js_imports(content):
            resolved = resolve_local_specifier_actual(actual_path, root_dir, specifier)
            if resolved and resolved in virtual_by_actual:
                discovered_virtuals.append(virtual_by_actual[resolved])
    if suffix == ".html":
        for specifier in extract_html_references(content):
            resolved = resolve_local_specifier_actual(actual_path, root_dir, specifier)
            if resolved and resolved in virtual_by_actual:
                discovered_virtuals.append(virtual_by_actual[resolved])
    if suffix in STYLE_SUFFIXES:
        for specifier in re.findall(r'@import\s+["\']([^"\']+)["\']', content):
            resolved = resolve_local_specifier_actual(actual_path, root_dir, specifier)
            if resolved and resolved in virtual_by_actual:
                discovered_virtuals.append(virtual_by_actual[resolved])
    if suffix == ".py":
        for resolved in resolve_local_python_dependencies(actual_path, root_dir, content):
            if resolved in virtual_by_actual:
                discovered_virtuals.append(virtual_by_actual[resolved])

    unique = []
    seen = set()
    for path in discovered_virtuals:
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def relative_analysis_path(actual_path: Path, root_dir: Path, mode: str) -> str:
    try:
        return to_posix(actual_path.resolve().relative_to(root_dir.resolve()))
    except ValueError:
        return to_posix(actual_path.name)


def virtual_analysis_path(analysis_id: str, relative_path: str) -> str:
    return normalize_posix_path(f"{ANALYSIS_PATH_PREFIX}/{slugify(analysis_id)}/{relative_path}")


def infer_analysis_layer(relative_path: str) -> str:
    normalized = normalize_posix_path(relative_path)
    suffix = PurePosixPath(normalized).suffix.lower()
    parts = PurePosixPath(normalized).parts

    if suffix == ".md" or "docs" in parts:
        return "docs"
    if suffix in STYLE_SUFFIXES:
        return "style"
    if "backend" in parts:
        if "data" in parts:
            return "data"
        return "backend"
    if "frontend" in parts:
        return "frontend"
    if "shared" in parts:
        return "shared"
    if "microservice" in normalized or "service" in parts:
        return "microservice"
    if PurePosixPath(normalized).name in {"package.json", "requirements.txt", "pyproject.toml", "tsconfig.json"}:
        return "config"
    return "script"


def layer_label_for_analysis(layer: str) -> str:
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


def default_color_for_analysis(layer: str) -> str:
    from project_graph import default_color_for_layer

    return default_color_for_layer(layer)


def find_primary_node_id(graph: Dict[str, Any], target_path: Path) -> str:
    resolved_target = str(target_path.resolve())
    nodes = graph.get("nodes") if isinstance(graph, dict) else []
    if not isinstance(nodes, list):
        return ""

    for node in nodes:
        if str(node.get("sourcePath") or "") == resolved_target:
            return str(node.get("id") or "")

    return str(nodes[0].get("id") or "") if nodes else ""
