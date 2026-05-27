from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Sequence

IGNORED_PARTS = {".git", ".pytest_cache", ".ruff_cache", ".runtime", "build", "coverage", "node_modules", "dist", "__pycache__", ".venv"}
IGNORED_FILES = {"package-lock.json", ".agent-project.json", "editor_state.json", "reverse_engineering_state.json"}
MAX_NODE_CODE_BYTES = 250_000
IGNORED_WORKSPACE_PROJECT_PARTS = {"runtime", ".vista"}
SUPPORTED_SUFFIXES = {".py", ".jsx", ".js", ".ts", ".tsx", ".css", ".html", ".json", ".txt", ".md", ".cpp", ".cc", ".cxx", ".h", ".hpp"}
JS_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
STYLE_SUFFIXES = {".css"}
CONFIG_FILES = {"package.json", "requirements.txt"}
FLOW_TYPES = {"start", "end", "process", "decision", "io"}
DEFAULT_LAYER_COLORS = {
    "frontend": "#a855f7",
    "backend": "#f97316",
    "data": "#fb7185",
    "microservice": "#14b8a6",
    "shared": "#38bdf8",
    "docs": "#eab308",
    "style": "#d946ef",
    "config": "#f59e0b",
    "script": "#ec4899",
}
CUSTOM_LAYER_COLORS = ["#60a5fa", "#22c55e", "#f43f5e", "#f59e0b", "#14b8a6", "#a855f7", "#fb7185"]


def graph_code_payload(content: str) -> tuple[str, bool]:
    encoded = content.encode("utf-8")
    if len(encoded) <= MAX_NODE_CODE_BYTES:
        return content, False
    preview = encoded[:MAX_NODE_CODE_BYTES].decode("utf-8", errors="ignore")
    return f"{preview}\n\n[... graph code preview truncated: {len(encoded)} bytes total ...]", True


def build_project_graph(project_root: Path) -> Dict[str, Any]:
    files = discover_source_files(project_root)
    known_paths = {to_posix(path.relative_to(project_root)) for path in files}
    nodes = []
    imports_by_path: Dict[str, List[str]] = {}

    for file_path in files:
        relative_path = to_posix(file_path.relative_to(project_root))
        try:
            content = file_path.read_text(encoding="utf-8")
            file_size = file_path.stat().st_size
            source_path = str(file_path.resolve())
        except (FileNotFoundError, OSError):
            continue
        code_payload, code_truncated = graph_code_payload(content)
        statements = extract_real_statements(relative_path, content)
        algorithm = build_real_algorithm(relative_path, content, statements)
        imports = extract_internal_references(relative_path, content, known_paths)

        imports_by_path[relative_path] = imports
        nodes.append(
            {
                "id": node_id_for_path(relative_path),
                "name": file_path.name,
                "path": relative_path,
                "sourcePath": source_path,
                "layer": infer_layer(relative_path),
                "layerLabel": layer_label_for_path(relative_path),
                "status": infer_status(relative_path),
                "size": format_size(file_size),
                "lines": count_lines(content),
                "description": describe_file(relative_path, statements),
                "imports": imports,
                "dependents": [],
                "color": default_color_for_layer(infer_layer(relative_path)),
                "code": code_payload,
                "codeTruncated": code_truncated,
                "codeLanguage": detect_code_language(relative_path),
                "algorithm": algorithm,
            }
        )

    node_id_by_path = {node["path"]: node["id"] for node in nodes}
    dependents_by_path = {node["path"]: [] for node in nodes}

    for source_path, import_paths in imports_by_path.items():
        for target_path in import_paths:
            dependents_by_path.setdefault(target_path, []).append(source_path)

    for node in nodes:
        node["dependents"] = dependents_by_path.get(node["path"], [])

    edges = []
    seen_edges = set()
    for source_path, import_paths in imports_by_path.items():
        source_node = next((node for node in nodes if node["path"] == source_path), None)
        if not source_node:
            continue

        for target_path in import_paths:
            source_id = node_id_by_path[source_path]
            target_id = node_id_by_path[target_path]
            edge_key = (source_id, target_id)
            if edge_key in seen_edges or source_id == target_id:
                continue
            seen_edges.add(edge_key)

            target_node = next((node for node in nodes if node["path"] == target_path), None)
            edges.append(
                {
                    "id": f"edge-{source_id}-{target_id}",
                    "from": source_id,
                    "to": target_id,
                    "type": infer_edge_type(source_node, target_node),
                    "label": infer_edge_label(source_node, target_node),
                    "dashed": False,
                }
            )

    return {
        "metadata": {
            "projectName": project_root.name,
            "sessionId": "repo-live-scan",
            "source": "real_project_scan",
            "note": "Mapa generado desde los archivos reales del repositorio. Cada algoritmo usa lineas reales del codigo.",
        },
        "nodes": nodes,
        "edges": edges,
    }


def discover_source_files(project_root: Path) -> List[Path]:
    files: List[Path] = []
    for root_name in ("backend", "frontend", "microservice-js", "workspace/projects"):
        root = project_root / root_name
        if not root.exists():
            continue

        try:
            iterator = root.rglob("*")
            for file_path in iterator:
                try:
                    if not file_path.is_file():
                        continue
                except (FileNotFoundError, OSError):
                    continue

                if any(part in IGNORED_PARTS for part in file_path.parts):
                    continue

                if is_workspace_runtime_internal_file(project_root, file_path):
                    continue

                if file_path.name in IGNORED_FILES or file_path.suffix not in SUPPORTED_SUFFIXES:
                    continue

                files.append(file_path)
        except (FileNotFoundError, OSError):
            continue

    return sorted(files, key=lambda path: to_posix(path.relative_to(project_root)))


def is_workspace_runtime_internal_file(project_root: Path, file_path: Path) -> bool:
    try:
        parts = file_path.relative_to(project_root).parts
    except ValueError:
        return False
    if len(parts) < 4 or parts[0] != "workspace" or parts[1] != "projects":
        return False
    project_relative_parts = parts[3:]
    return bool(project_relative_parts and project_relative_parts[0] in IGNORED_WORKSPACE_PROJECT_PARTS)


def extract_internal_references(current_path: str, content: str, known_paths: set[str]) -> List[str]:
    references = []

    if current_path == "backend/app.py" and "backend/requirements.txt" in known_paths:
        references.append("backend/requirements.txt")

    if current_path.endswith(tuple(JS_SUFFIXES)):
        for specifier in extract_js_imports(content):
            resolved = resolve_import_specifier(current_path, specifier, known_paths)
            if resolved:
                references.append(resolved)

        if "frontend/package.json" in known_paths and uses_frontend_dependencies(content):
            references.append("frontend/package.json")

        if current_path.startswith("microservice-js/") and "microservice-js/package.json" in known_paths:
            references.append("microservice-js/package.json")

        if "backend/app.py" in known_paths and references_backend_runtime(content):
            references.append("backend/app.py")

    if current_path.endswith(".html"):
        for specifier in extract_html_references(content):
            resolved = resolve_import_specifier(current_path, specifier, known_paths)
            if resolved:
                references.append(resolved)

    if current_path.endswith(".py"):
        references.extend(extract_python_import_references(current_path, content, known_paths))

    if current_path.endswith(".css"):
        for specifier in re.findall(r'@import\s+["\']([^"\']+)["\']', content):
            resolved = resolve_import_specifier(current_path, specifier, known_paths)
            if resolved:
                references.append(resolved)

    unique = []
    seen = set()
    for reference in references:
        if reference in seen or reference == current_path:
            continue
        seen.add(reference)
        unique.append(reference)
    return unique


def extract_js_imports(content: str) -> List[str]:
    matches = re.findall(r'import\s+(?:[^;]*?\s+from\s+)?["\']([^"\']+)["\']', content)
    return [match for match in matches if match]


def extract_html_references(content: str) -> List[str]:
    matches = re.findall(r'(?:src|href)=["\']([^"\']+)["\']', content)
    return [match for match in matches if match]


def extract_python_import_references(current_path: str, content: str, known_paths: set[str]) -> List[str]:
    try:
        module = ast.parse(content)
    except SyntaxError:
        return []

    references: List[str] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = resolve_python_module_reference(current_path, alias.name, known_paths, level=0)
                if resolved:
                    references.append(resolved)
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if module_name:
                resolved = resolve_python_module_reference(current_path, module_name, known_paths, level=node.level)
                if resolved:
                    references.append(resolved)
            elif node.level > 0:
                for alias in node.names:
                    resolved = resolve_python_module_reference(current_path, alias.name, known_paths, level=node.level)
                    if resolved:
                        references.append(resolved)

    return references


def uses_frontend_dependencies(content: str) -> bool:
    return any(package in content for package in ('from "react"', 'from "react-dom"', 'from "three"', 'from "socket.io-client"'))


def references_backend_runtime(content: str) -> bool:
    return (
        "SOCKET_URL" in content
        or "socket.io-client" in content
        or "localhost:5000" in content
        or "/api/architecture" in content
    )


def resolve_import_specifier(current_path: str, specifier: str, known_paths: set[str]) -> str | None:
    normalized = specifier.strip()
    if not normalized:
        return None

    current_parent = PurePosixPath(current_path).parent
    if normalized.startswith("/"):
        if current_path.startswith("frontend/"):
            candidate = to_posix(PurePosixPath("frontend") / normalized.lstrip("/"))
            if candidate in known_paths:
                return candidate
        return None

    if normalized.startswith("."):
        joined = normalize_posix_path(str(current_parent / normalized))
        for candidate in expand_candidate_paths(joined):
            if candidate in known_paths:
                return candidate
        return None

    return None


def expand_candidate_paths(path: str) -> List[str]:
    suffix = PurePosixPath(path).suffix
    candidates = [path]

    if not suffix:
        for extension in (".js", ".jsx", ".ts", ".tsx", ".css", ".json", ".html"):
            candidates.append(f"{path}{extension}")
        for index_name in ("index.js", "index.jsx", "index.ts", "index.tsx"):
            candidates.append(f"{path}/{index_name}")

    return candidates


def resolve_python_module_reference(current_path: str, module_name: str, known_paths: set[str], level: int = 0) -> str | None:
    normalized_module = str(module_name or "").strip()
    current_parent = PurePosixPath(current_path).parent
    candidates: List[str] = []

    if level > 0:
        relative_parent = current_parent
        for _ in range(max(level - 1, 0)):
            relative_parent = relative_parent.parent
        joined_parts = list(relative_parent.parts)
        if normalized_module:
            joined_parts.extend(normalized_module.split("."))
        if joined_parts:
            joined_path = normalize_posix_path("/".join(joined_parts))
            candidates.extend(expand_python_module_candidates(joined_path))

    if normalized_module:
        direct_parts = normalized_module.split(".")
        direct_path = normalize_posix_path("/".join(direct_parts))
        candidates.extend(expand_python_module_candidates(direct_path))

        for ancestor in [current_parent, *current_parent.parents]:
            if str(ancestor) in {".", ""}:
                continue
            joined_path = normalize_posix_path(str(ancestor / PurePosixPath(*direct_parts)))
            candidates.extend(expand_python_module_candidates(joined_path))

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate in known_paths:
            return candidate
    return None


def expand_python_module_candidates(path: str) -> List[str]:
    normalized = normalize_posix_path(path)
    return [
        f"{normalized}.py",
        f"{normalized}/__init__.py",
    ]


def extract_real_statements(relative_path: str, content: str) -> List[Dict[str, Any]]:
    suffix = PurePosixPath(relative_path).suffix

    if suffix == ".py":
        return extract_python_statements(content)
    if suffix in JS_SUFFIXES:
        return extract_js_statements(content)
    if suffix in STYLE_SUFFIXES:
        return extract_css_statements(content)
    if suffix == ".html":
        return extract_html_statements(content)
    if suffix == ".json":
        return extract_json_statements(content)
    if suffix == ".txt":
        return extract_text_statements(content)
    if suffix == ".md":
        return extract_text_statements(content)
    if suffix in {".cpp", ".cc", ".cxx", ".h", ".hpp"}:
        return fallback_text_statements(content)

    return []


def extract_python_statements(content: str) -> List[Dict[str, Any]]:
    try:
        module = ast.parse(content)
    except SyntaxError:
        return fallback_text_statements(content)

    statements: List[Dict[str, Any]] = []
    for node in module.body:
        statements.extend(flatten_python_node(node, content))

    return select_key_statements(statements, max_items=8)


def flatten_python_node(node: ast.AST, content: str) -> List[Dict[str, Any]]:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [python_statement(node, content, "io", priority=3)]

    if isinstance(node, ast.Try):
        statements = []
        for child in node.body[:1]:
            statements.extend(flatten_python_node(child, content))
        for handler in node.handlers[:1]:
            for child in handler.body[:1]:
                statements.extend(flatten_python_node(child, content))
        return statements

    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        statement = python_statement(node, content, "process", priority=4)
        if statement["text"].count("{") > 3 or len(statement["text"]) > 100:
            return []
        return [statement]

    if isinstance(node, ast.FunctionDef):
        decorators = [source_segment(decorator, content) for decorator in node.decorator_list]
        signature = f"def {node.name}(...):"
        if decorators:
            signature = f"{decorators[0]} {signature}"
        statements = [
            {
                "line": node.lineno,
                "text": signature,
                "type": "process",
                "priority": 12 if decorators else 8,
            }
        ]
        first_child = first_python_child(node.body)
        if first_child is not None:
            child_statement = python_statement(first_child, content, infer_python_step_type(first_child), priority=6)
            if len(child_statement["text"]) <= 90:
                statements.append(child_statement)
        return statements

    if isinstance(node, ast.If):
        statements = [python_statement(node, content, "decision", priority=11, force_text=f"if {source_segment(node.test, content)}:")]
        first_body = first_python_child(node.body)
        if first_body is not None:
            statements.append(python_statement(first_body, content, infer_python_step_type(first_body), priority=7))
        first_else = first_python_child(node.orelse)
        if first_else is not None:
            statements.append(python_statement(first_else, content, infer_python_step_type(first_else), priority=7))
        return statements

    if isinstance(node, ast.Expr):
        return [python_statement(node, content, infer_python_step_type(node), priority=6)]

    return [python_statement(node, content, infer_python_step_type(node), priority=5)]


def first_python_child(nodes: Sequence[ast.stmt]) -> ast.stmt | None:
    for node in nodes:
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str):
            continue
        return node
    return None


def infer_python_step_type(node: ast.AST) -> str:
    text = source_segment(node, "")
    if isinstance(node, ast.If):
        return "decision"
    if isinstance(node, (ast.Return, ast.Yield)):
        return "io"
    if isinstance(node, ast.Expr):
        call = getattr(node, "value", None)
        if isinstance(call, ast.Call):
            callee = source_segment(call.func, "")
            if any(token in callee for token in ("emit", "jsonify", "run", "request")):
                return "io"
    if any(token in text for token in ("emit(", "jsonify(", "socketio.run", "request", "return ")):
        return "io"
    return "process"


def python_statement(node: ast.AST, content: str, step_type: str, priority: int, force_text: str | None = None) -> Dict[str, Any]:
    text = force_text or source_segment(node, content)
    return {
        "line": getattr(node, "lineno", 1),
        "text": compact_code(text),
        "type": step_type if step_type in FLOW_TYPES else "process",
        "priority": priority,
    }


def source_segment(node: ast.AST, content: str) -> str:
    if content:
        segment = ast.get_source_segment(content, node)
        if segment:
            return segment
    if isinstance(node, ast.Attribute):
        return f"{source_segment(node.value, content)}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    return node.__class__.__name__


def extract_js_statements(content: str) -> List[Dict[str, Any]]:
    scope, line_offset = extract_default_export_scope(content)
    statements: List[Dict[str, Any]] = []

    for index, raw_line in enumerate(scope.splitlines(), start=1):
        line_no = line_offset + index
        compact = compact_code(raw_line)
        if not compact or compact in {"{", "}", ");", ")", "]", "];"}:
            continue
        if compact.startswith("//") or compact.startswith("*"):
            continue

        step_type = infer_js_step_type(compact)
        priority = score_js_line(compact)
        if priority <= 0:
            continue

        statements.append(
            {
                "line": line_no,
                "text": compact,
                "type": step_type,
                "priority": priority,
            }
        )

    return select_key_statements(statements, max_items=8)


def extract_default_export_scope(content: str) -> tuple[str, int]:
    match = re.search(r"export\s+default\s+function\b[^{]*\{", content)
    if not match:
        return content, 0

    start_index = content.find("{", match.start())
    end_index = find_matching_brace(content, start_index)
    if end_index <= start_index:
        return content, 0

    body = content[start_index + 1 : end_index]
    line_offset = content[: start_index + 1].count("\n")
    return body, line_offset


def find_matching_brace(content: str, start_index: int) -> int:
    depth = 0
    in_string = False
    quote = ""
    escaped = False

    for index in range(start_index, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                in_string = False
            continue

        if char in {'"', "'", "`"}:
            in_string = True
            quote = char
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index

    return len(content) - 1


def infer_js_step_type(line: str) -> str:
    if re.match(r"^(if|else if|switch|for|while)\b", line):
        return "decision"
    if any(token in line for token in ("socket.", "io(", "emit(", "render(", "appendChild(", "emit(")):
        return "io"
    if line.startswith("return"):
        return "io"
    return "process"


def score_js_line(line: str) -> int:
    if line.startswith("const [") or "useState(" in line:
        return 9
    if "useEffect" in line or "useMemo" in line:
        return 12
    if "socket.on" in line or "socket.emit" in line or "io(" in line:
        return 13
    if line.startswith("if ") or line.startswith("if(") or line.startswith("if ("):
        return 11
    if line.startswith("for ") or line.startswith("for(") or ".map(" in line:
        return 8
    if any(token in line for token in ("new THREE.", "renderer.", "scene.", "controls.", "requestAnimationFrame")):
        return 10
    if line.startswith("return"):
        return 11
    if line.startswith("const ") or line.startswith("let ") or line.startswith("function "):
        return 6
    if line.startswith("<") or line.startswith("</"):
        return 0
    return 4


def extract_css_statements(content: str) -> List[Dict[str, Any]]:
    statements = []
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        if stripped.endswith("{") or stripped.startswith("@media"):
            statements.append({"line": line_no, "text": compact_code(stripped), "type": "process", "priority": 8})
        elif stripped.startswith("--"):
            statements.append({"line": line_no, "text": compact_code(stripped), "type": "process", "priority": 5})
    return select_key_statements(statements, max_items=8)


def extract_html_statements(content: str) -> List[Dict[str, Any]]:
    statements = []
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("<!doctype"):
            continue
        if stripped.startswith("<"):
            priority = 10 if "script" in stripped or 'id="root"' in stripped else 6
            step_type = "io" if "script" in stripped else "process"
            statements.append({"line": line_no, "text": compact_code(stripped), "type": step_type, "priority": priority})
    return select_key_statements(statements, max_items=8)


def extract_json_statements(content: str) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return fallback_text_statements(content)

    statements = []
    if isinstance(payload, dict):
        if not payload:
            statements.append(
                {
                    "line": 1,
                    "text": "{}",
                    "type": "process",
                    "priority": 8,
                }
            )
        for index, (key, value) in enumerate(payload.items(), start=1):
            summary = summarize_json_value(value)
            statements.append(
                {
                    "line": index,
                    "text": compact_code(f'"{key}": {summary}'),
                    "type": "process",
                    "priority": 10 if key in {"scripts", "dependencies", "name"} else 6,
                }
            )
    elif isinstance(payload, list):
        if not payload:
            statements.append(
                {
                    "line": 1,
                    "text": "[0 items]",
                    "type": "process",
                    "priority": 8,
                }
            )
        for index, value in enumerate(payload[:8], start=1):
            statements.append(
                {
                    "line": index,
                    "text": compact_code(f"[{index - 1}] {summarize_json_value(value)}"),
                    "type": "process",
                    "priority": 8,
                }
            )
    else:
        statements.append(
            {
                "line": 1,
                "text": compact_code(summarize_json_value(payload)),
                "type": "process",
                "priority": 8,
            }
        )
    return select_key_statements(statements, max_items=8)


def summarize_json_value(value: Any) -> str:
    if isinstance(value, dict):
        return "{" + ", ".join(list(value.keys())[:4]) + ("..." if len(value) > 4 else "") + "}"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return json.dumps(value, ensure_ascii=True)


def extract_text_statements(content: str) -> List[Dict[str, Any]]:
    statements = []
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        statements.append({"line": line_no, "text": stripped, "type": "io", "priority": 8})
    return select_key_statements(statements, max_items=8)


def fallback_text_statements(content: str) -> List[Dict[str, Any]]:
    statements = []
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        compact = compact_code(raw_line)
        if not compact:
            continue
        statements.append({"line": line_no, "text": compact, "type": "process", "priority": 4})
    return select_key_statements(statements, max_items=8)


def select_key_statements(statements: List[Dict[str, Any]], max_items: int) -> List[Dict[str, Any]]:
    cleaned = []
    seen = set()
    for statement in statements:
        text = statement["text"]
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(statement)

    if len(cleaned) <= max_items:
        return cleaned

    ranked = sorted(cleaned, key=lambda item: (-item["priority"], item["line"]))
    selected_lines = sorted(item["line"] for item in ranked[:max_items])
    return [item for item in cleaned if item["line"] in selected_lines]


class FlowGraphBuilder:
    def __init__(self, language: str, title: str) -> None:
        self.language = language
        self.title = title
        self.steps: List[Dict[str, Any]] = [{"id": "start", "type": "start", "label": "Inicio", "x": 300, "y": 46, "line": 0}]
        self.edges: List[Dict[str, Any]] = []
        self.step_count = 0

    def add_step(self, step_type: str, label: str, line: int, x: float, y: float, code: str | None = None) -> str:
        self.step_count += 1
        step_id = f"step-{self.step_count}"
        self.steps.append(
            {
                "id": step_id,
                "type": step_type if step_type in FLOW_TYPES else "process",
                "label": wrap_code_label(label),
                "x": round(x, 2),
                "y": round(y, 2),
                "line": int(line or 0),
                "code": compact_code(code or label),
                "codeLanguage": self.language,
                "color": None,
            }
        )
        return step_id

    def add_edge(self, source_id: str, target_id: str, label: str = "") -> None:
        if not source_id or not target_id or source_id == target_id:
            return

        edge = {"from": source_id, "to": target_id}
        if label:
            edge["label"] = label
        self.edges.append(edge)

    def connect(self, pending_links: List[Dict[str, Any]], target_id: str) -> None:
        for link in pending_links:
            self.add_edge(str(link.get("id") or ""), target_id, str(link.get("label") or ""))

    def finalize(self, pending_links: List[Dict[str, Any]], end_y: float) -> Dict[str, Any]:
        self.steps.append({"id": "end", "type": "end", "label": "Fin", "x": 300, "y": round(end_y, 2), "line": 0})
        self.connect(pending_links or [{"id": "start", "label": ""}], "end")
        return {
            "title": self.title,
            "source": "real_source",
            "steps": self.steps,
            "edges": self.edges,
        }


def build_real_algorithm(relative_path: str, content: str, statements: List[Dict[str, Any]]) -> Dict[str, Any]:
    suffix = PurePosixPath(relative_path).suffix.lower()

    if suffix == ".py":
        algorithm = build_python_algorithm(relative_path, content)
        if algorithm:
            return algorithm
    if suffix in JS_SUFFIXES:
        algorithm = build_js_algorithm(relative_path, content)
        if algorithm:
            return algorithm
    return build_algorithm(relative_path, statements)


def build_python_algorithm(relative_path: str, content: str) -> Dict[str, Any] | None:
    try:
        module = ast.parse(content)
    except SyntaxError:
        return None

    entry = select_python_entry(module)
    entry_body = entry.get("body") if isinstance(entry, dict) else None
    if not isinstance(entry_body, list):
        return None

    builder = FlowGraphBuilder("python", f"Algoritmo real de {PurePosixPath(relative_path).name}")
    pending_links = [{"id": "start", "label": ""}]
    current_y = 156.0

    entry_label = str(entry.get("label") or "").strip()
    entry_line = int(entry.get("line") or 0)
    if entry_label:
        entry_step_id = builder.add_step("process", entry_label, entry_line, 300, current_y, entry_label)
        builder.connect(pending_links, entry_step_id)
        pending_links = [{"id": entry_step_id, "label": ""}]
        current_y += 120

    pending_links, current_y = walk_python_sequence(
        builder,
        entry_body,
        content,
        pending_links,
        300,
        current_y,
        340,
    )
    return builder.finalize(pending_links, max(current_y, 280))


def select_python_entry(module: ast.Module) -> Dict[str, Any]:
    functions = [node for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    entry_guard = next((node for node in module.body if is_python_main_guard(node)), None)
    if isinstance(entry_guard, ast.If):
        called_name = first_called_name(entry_guard.body)
        target = next((node for node in functions if node.name == called_name), None)
        if target is not None:
            return {
                "label": format_python_function_signature(target),
                "line": target.lineno,
                "body": list(target.body),
            }
        return {
            "label": "if __name__ == '__main__':",
            "line": entry_guard.lineno,
            "body": list(entry_guard.body),
        }

    preferred_names = {"main", "run", "bootstrap", "start", "init_app", "create_app", "handle_request", "serve", "build_app"}
    ranked_functions = sorted(
        functions,
        key=lambda node: (
            0 if node.name in preferred_names else 1,
            0 if node.decorator_list else 1,
            node.lineno,
        ),
    )
    if ranked_functions:
        target = ranked_functions[0]
        return {
            "label": format_python_function_signature(target),
            "line": target.lineno,
            "body": list(target.body),
        }

    body = [node for node in module.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
    return {
        "label": "",
        "line": 1,
        "body": body or list(module.body),
    }


def is_python_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    return (
        isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def first_called_name(nodes: Sequence[ast.stmt]) -> str | None:
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                return called_name_from_ast(child.func)
    return None


def called_name_from_ast(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def format_python_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}(...)"


def walk_python_sequence(
    builder: FlowGraphBuilder,
    statements: Sequence[ast.stmt],
    content: str,
    pending_links: List[Dict[str, Any]],
    center_x: float,
    current_y: float,
    lane_width: float,
) -> tuple[List[Dict[str, Any]], float]:
    active_links = pending_links
    next_y = current_y

    for node in statements:
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str):
            continue

        if isinstance(node, ast.If):
            label = compact_code(f"if {source_segment(node.test, content)}:")
            decision_id = builder.add_step("decision", label, node.lineno, center_x, next_y, label)
            builder.connect(active_links, decision_id)

            branch_y = next_y + 152
            branch_width = max(170, lane_width * 0.68)
            true_links, true_y = walk_python_sequence(
                builder,
                node.body,
                content,
                [{"id": decision_id, "label": "Si"}],
                center_x - branch_width / 2,
                branch_y,
                branch_width,
            )
            if node.orelse:
                false_links, false_y = walk_python_sequence(
                    builder,
                    node.orelse,
                    content,
                    [{"id": decision_id, "label": "No"}],
                    center_x + branch_width / 2,
                    branch_y,
                    branch_width,
                )
            else:
                false_links = [{"id": decision_id, "label": "No"}]
                false_y = branch_y

            active_links = true_links + false_links
            next_y = max(true_y, false_y) + 132
            continue

        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            if isinstance(node, ast.While):
                label = compact_code(f"while {source_segment(node.test, content)}:")
            else:
                label = compact_code(f"for {source_segment(node.target, content)} in {source_segment(node.iter, content)}:")

            loop_id = builder.add_step("decision", label, node.lineno, center_x, next_y, label)
            builder.connect(active_links, loop_id)
            body_y = next_y + 152
            body_links, body_end_y = walk_python_sequence(
                builder,
                node.body,
                content,
                [{"id": loop_id, "label": "Itera"}],
                center_x - max(120, lane_width * 0.18),
                body_y,
                max(170, lane_width * 0.72),
            )
            for link in body_links:
                builder.add_edge(str(link.get("id") or ""), loop_id, str(link.get("label") or "Repite"))

            active_links = [{"id": loop_id, "label": "Sale"}]
            next_y = body_end_y + 132
            continue

        if isinstance(node, ast.Try):
            try_label = "try"
            try_id = builder.add_step("process", try_label, node.lineno, center_x, next_y, try_label)
            builder.connect(active_links, try_id)
            branch_y = next_y + 146
            body_links, body_y = walk_python_sequence(
                builder,
                node.body,
                content,
                [{"id": try_id, "label": "Ok"}],
                center_x - max(100, lane_width * 0.18),
                branch_y,
                lane_width,
            )
            except_links: List[Dict[str, Any]] = []
            except_y = branch_y
            for handler_index, handler in enumerate(node.handlers, start=1):
                handler_label = compact_code(f"except {source_segment(handler.type, content) if handler.type else 'Exception'}:")
                catch_id = builder.add_step("process", handler_label, handler.lineno, center_x + max(120, lane_width * 0.22), branch_y + (handler_index - 1) * 118, handler_label)
                builder.add_edge(try_id, catch_id, "Error")
                handler_links, handler_end_y = walk_python_sequence(
                    builder,
                    handler.body,
                    content,
                    [{"id": catch_id, "label": "Maneja"}],
                    center_x + max(180, lane_width * 0.32),
                    branch_y + handler_index * 118,
                    lane_width,
                )
                except_links.extend(handler_links)
                except_y = max(except_y, handler_end_y)

            active_links = body_links + except_links
            if node.finalbody:
                active_links, final_y = walk_python_sequence(
                    builder,
                    node.finalbody,
                    content,
                    active_links,
                    center_x,
                    max(body_y, except_y) + 124,
                    lane_width,
                )
                next_y = final_y + 114
            else:
                next_y = max(body_y, except_y) + 124
            continue

        step_type = infer_python_step_type(node)
        text = format_python_flow_label(node, content)
        step_id = builder.add_step(step_type, text, getattr(node, "lineno", 1), center_x, next_y, source_segment(node, content))
        builder.connect(active_links, step_id)
        active_links = [{"id": step_id, "label": ""}]
        next_y += 118 if step_type == "decision" else 106

    return active_links, next_y


def format_python_flow_label(node: ast.AST, content: str) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return format_python_function_signature(node)
    if isinstance(node, ast.Return):
        return compact_code(f"return {source_segment(node.value, content) if node.value else ''}".strip())
    if isinstance(node, ast.Assign):
        return compact_code(source_segment(node, content))
    if isinstance(node, ast.AnnAssign):
        return compact_code(source_segment(node, content))
    if isinstance(node, ast.AugAssign):
        return compact_code(source_segment(node, content))
    return compact_code(source_segment(node, content))


def build_js_algorithm(relative_path: str, content: str) -> Dict[str, Any] | None:
    scope, line_offset, label = select_js_entry_scope(content)
    if not scope.strip():
        return None

    flow_lines = extract_js_flow_lines(scope, line_offset)
    if not flow_lines:
        return None

    builder = FlowGraphBuilder(detect_code_language(relative_path), f"Algoritmo real de {PurePosixPath(relative_path).name}")
    pending_links = [{"id": "start", "label": ""}]
    current_y = 156.0

    if label:
        entry_step_id = builder.add_step("process", label, max(line_offset, 1), 300, current_y, label)
        builder.connect(pending_links, entry_step_id)
        pending_links = [{"id": entry_step_id, "label": ""}]
        current_y += 120

    pending_links, current_y, _ = walk_js_block(
        builder,
        flow_lines,
        0,
        0,
        pending_links,
        300,
        current_y,
        340,
    )
    return builder.finalize(pending_links, max(current_y, 280))


def select_js_entry_scope(content: str) -> tuple[str, int, str]:
    export_match = re.search(r"export\s+default\s+function\s+([A-Za-z0-9_]*)?[^{]*\{", content)
    if export_match:
        function_name = export_match.group(1) or "default"
        start_index = content.find("{", export_match.start())
        end_index = find_matching_brace(content, start_index)
        body = content[start_index + 1 : end_index]
        line_offset = content[: start_index + 1].count("\n")
        return body, line_offset, f"export default function {function_name}(...)"

    preferred_name_priority = {
        "main": 0,
        "run": 0,
        "bootstrap": 0,
        "start": 0,
        "init": 0,
        "initialize": 0,
        "initializeApp": 0,
        "mount": 1,
        "setup": 1,
        "App": 2,
        "render": 4,
    }
    named_matches = []
    for pattern in (
        r"((?:async\s+)?function\s+([A-Za-z_$][\w$]*)\b[^{]*\{)",
        r"((?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>\s*\{)",
    ):
        for match in re.finditer(pattern, content):
            name = match.group(2) or "entry"
            start_index = content.find("{", match.start())
            end_index = find_matching_brace(content, start_index)
            invocation_count = len(re.findall(rf"\b(?:void\s+)?{re.escape(name)}\s*\(", content))
            named_matches.append(
                {
                    "name": name,
                    "start": start_index,
                    "end": end_index,
                    "score": (
                        preferred_name_priority.get(name, 3),
                        0 if re.search(r"(init|start|bootstrap|mount|setup)", name, re.IGNORECASE) else 1,
                        0 if re.search(r"(load|handle|save|bind|render)", name, re.IGNORECASE) else 1,
                        0 if invocation_count > 1 else 1,
                        match.start(),
                    ),
                }
            )

    if named_matches:
        target = sorted(named_matches, key=lambda item: item["score"])[0]
        body = content[target["start"] + 1 : target["end"]]
        line_offset = content[: target["start"] + 1].count("\n")
        return body, line_offset, f"{target['name']}(...)"

    scope, line_offset = extract_default_export_scope(content)
    return scope, line_offset, ""


def extract_js_flow_lines(scope: str, line_offset: int) -> List[Dict[str, Any]]:
    depths = js_depths_by_line(scope)
    flow_lines: List[Dict[str, Any]] = []

    for index, raw_line in enumerate(scope.splitlines(), start=1):
        stripped = compact_code(raw_line)
        if not stripped or stripped in {"{", "}", ");", ")", "]", "];"}:
            continue
        if stripped.startswith(("//", "*", "/*")) or stripped.startswith("<") or stripped.startswith("</"):
            continue

        kind = classify_js_flow_line(stripped)
        if kind is None:
            continue

        flow_lines.append(
            {
                "line": line_offset + index,
                "text": stripped,
                "type": infer_js_step_type(stripped),
                "kind": kind,
                "depth": depths[index - 1] if index - 1 < len(depths) else 0,
                "opensBlock": "{" in raw_line,
            }
        )

    return flow_lines


def js_depths_by_line(content: str) -> List[int]:
    depths: List[int] = []
    depth = 0
    in_string = False
    quote = ""
    escaped = False
    in_block_comment = False

    for raw_line in content.splitlines():
        depths.append(max(depth, 0))
        index = 0
        while index < len(raw_line):
            char = raw_line[index]
            next_char = raw_line[index + 1] if index + 1 < len(raw_line) else ""

            if in_block_comment:
                if char == "*" and next_char == "/":
                    in_block_comment = False
                    index += 2
                    continue
                index += 1
                continue

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    in_string = False
                index += 1
                continue

            if char == "/" and next_char == "/":
                break
            if char == "/" and next_char == "*":
                in_block_comment = True
                index += 2
                continue
            if char in {'"', "'", "`"}:
                in_string = True
                quote = char
                index += 1
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth = max(0, depth - 1)
            index += 1

    return depths


def classify_js_flow_line(line: str) -> str | None:
    if re.match(r"^if\s*\(", line):
        return "if"
    if re.match(r"^else\s+if\s*\(", line):
        return "else_if"
    if re.match(r"^else\b", line):
        return "else"
    if re.match(r"^(for|while)\s*\(", line):
        return "loop"
    if re.match(r"^return\b", line):
        return "return"
    if re.match(r"^(const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>", line):
        return "function"
    if re.match(r"^(?:async\s+)?function\s+[A-Za-z_$][\w$]*\s*\(", line):
        return "function"
    if any(token in line for token in ("fetch(", "socket.", "emit(", "addEventListener(", "appendChild(", "render(", "setState(", "dispatch(")):
        return "io"
    if line.startswith(("const ", "let ", "var ", "await ", "document.", "window.")):
        return "process"
    return None


def walk_js_block(
    builder: FlowGraphBuilder,
    flow_lines: Sequence[Dict[str, Any]],
    start_index: int,
    depth: int,
    pending_links: List[Dict[str, Any]],
    center_x: float,
    current_y: float,
    lane_width: float,
) -> tuple[List[Dict[str, Any]], float, int]:
    active_links = pending_links
    next_y = current_y
    index = start_index

    while index < len(flow_lines):
        line = flow_lines[index]
        line_depth = int(line.get("depth") or 0)
        kind = str(line.get("kind") or "")

        if line_depth < depth:
            break
        if line_depth > depth:
            index += 1
            continue
        if kind in {"else", "else_if"} and index != start_index:
            break

        if kind in {"if", "else_if"}:
            decision_id = builder.add_step("decision", str(line.get("text") or ""), int(line.get("line") or 0), center_x, next_y, str(line.get("text") or ""))
            builder.connect(active_links, decision_id)

            branch_y = next_y + 152
            branch_width = max(170, lane_width * 0.68)
            true_links, true_y, next_index = walk_js_block(
                builder,
                flow_lines,
                index + 1,
                depth + 1,
                [{"id": decision_id, "label": "Si"}],
                center_x - branch_width / 2,
                branch_y,
                branch_width,
            ) if line.get("opensBlock") else ([{"id": decision_id, "label": "Si"}], branch_y, index + 1)

            false_links: List[Dict[str, Any]] = [{"id": decision_id, "label": "No"}]
            false_y = branch_y
            index = next_index
            if index < len(flow_lines):
                next_line = flow_lines[index]
                next_kind = str(next_line.get("kind") or "")
                next_depth = int(next_line.get("depth") or 0)
                if next_depth == depth and next_kind in {"else", "else_if"}:
                    false_center_x = center_x + branch_width / 2
                    if next_kind == "else_if":
                        false_links, false_y, index = walk_js_block(
                            builder,
                            flow_lines,
                            index,
                            depth,
                            [{"id": decision_id, "label": "No"}],
                            false_center_x,
                            branch_y,
                            branch_width,
                        )
                    else:
                        false_links, false_y, index = walk_js_block(
                            builder,
                            flow_lines,
                            index + 1,
                            depth + 1,
                            [{"id": decision_id, "label": "No"}],
                            false_center_x,
                            branch_y,
                            branch_width,
                        ) if next_line.get("opensBlock") else ([{"id": decision_id, "label": "No"}], branch_y, index + 1)

            active_links = true_links + false_links
            next_y = max(true_y, false_y) + 132
            continue

        if kind == "loop":
            loop_id = builder.add_step("decision", str(line.get("text") or ""), int(line.get("line") or 0), center_x, next_y, str(line.get("text") or ""))
            builder.connect(active_links, loop_id)
            body_y = next_y + 152
            body_links, body_end_y, index = walk_js_block(
                builder,
                flow_lines,
                index + 1,
                depth + 1,
                [{"id": loop_id, "label": "Itera"}],
                center_x - max(120, lane_width * 0.18),
                body_y,
                max(170, lane_width * 0.72),
            ) if line.get("opensBlock") else ([{"id": loop_id, "label": "Itera"}], body_y, index + 1)
            for link in body_links:
                builder.add_edge(str(link.get("id") or ""), loop_id, str(link.get("label") or "Repite"))
            active_links = [{"id": loop_id, "label": "Sale"}]
            next_y = body_end_y + 132
            continue

        step_id = builder.add_step(
            str(line.get("type") or "process"),
            str(line.get("text") or ""),
            int(line.get("line") or 0),
            center_x,
            next_y,
            str(line.get("text") or ""),
        )
        builder.connect(active_links, step_id)
        active_links = [{"id": step_id, "label": ""}]
        next_y += 118 if line.get("type") == "decision" else 106
        index += 1

    return active_links, next_y, index


def build_algorithm(relative_path: str, statements: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not statements:
        statements = [{"line": 1, "text": relative_path, "type": "process", "priority": 1}]

    language = detect_code_language(relative_path)
    steps = [{"id": "start", "type": "start", "label": "Inicio", "x": 300, "y": 46}]
    edges = []
    y = 156
    previous_id = "start"

    for index, statement in enumerate(statements, start=1):
        step_id = f"step-{index}"
        steps.append(
            {
                "id": step_id,
                "type": statement["type"] if statement["type"] in FLOW_TYPES else "process",
                "label": wrap_code_label(f"L{statement['line']} {statement['text']}"),
                "x": 300,
                "y": y,
                "line": int(statement["line"]),
                "code": statement["text"],
                "codeLanguage": language,
                "color": None,
            }
        )
        edges.append({"from": previous_id, "to": step_id})
        previous_id = step_id
        y += 118 if statement["type"] == "decision" else 106

    steps.append({"id": "end", "type": "end", "label": "Fin", "x": 300, "y": y, "line": 0})
    edges.append({"from": previous_id, "to": "end"})

    return {
        "title": f"Algoritmo real de {PurePosixPath(relative_path).name}",
        "source": "real_source",
        "steps": steps,
        "edges": edges,
    }


def wrap_code_label(text: str, max_chars: int = 24, max_lines: int = 4) -> str:
    words = text.split()
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

    consumed = len(" ".join(lines).split())
    if consumed < len(words) and lines:
        lines[-1] = f"{lines[-1]}..."

    return "\n".join(lines[:max_lines])


def compact_code(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def format_size(byte_count: int) -> str:
    if byte_count < 1024:
        return f"{byte_count} B"
    return f"{byte_count / 1024:.1f} KB"


def count_lines(content: str) -> int:
    return len(content.splitlines())


def infer_layer(relative_path: str) -> str:
    file_name = PurePosixPath(relative_path).name
    suffix = PurePosixPath(relative_path).suffix
    workspace_project = workspace_project_slug(relative_path)

    if file_name in CONFIG_FILES:
        return "config"
    if suffix in STYLE_SUFFIXES:
        return "style"
    if suffix == ".md" or "/docs/" in relative_path:
        return "docs"
    if relative_path.startswith("backend/data/") or "/backend/data/" in relative_path:
        return "data"
    if workspace_project:
        return workspace_project
    if relative_path.startswith("microservice-js/"):
        return "microservice"
    if relative_path.startswith("backend/"):
        return "backend"
    if relative_path.startswith("frontend/"):
        return "frontend"
    return "script"


def infer_status(relative_path: str) -> str:
    file_name = PurePosixPath(relative_path).name
    if file_name in {"app.py", "App.jsx", "ArchitectureCanvas.jsx", "AlgorithmFlow.jsx"}:
        return "modified"
    if file_name in CONFIG_FILES:
        return "generated"
    return "generated"


def detect_code_language(relative_path: str) -> str:
    suffix = PurePosixPath(relative_path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".css": "css",
        ".html": "html",
        ".json": "json",
        ".txt": "text",
        ".md": "markdown",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "cpp",
        ".hpp": "cpp",
    }.get(suffix, "text")


def layer_label_for_path(relative_path: str) -> str:
    workspace_project = workspace_project_slug(relative_path)
    if workspace_project:
        return workspace_project.replace("-", " ").title()

    layer = infer_layer(relative_path)
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


def default_color_for_layer(layer: str) -> str:
    if layer in DEFAULT_LAYER_COLORS:
        return DEFAULT_LAYER_COLORS[layer]
    palette_index = sum(ord(char) for char in layer) % len(CUSTOM_LAYER_COLORS)
    return CUSTOM_LAYER_COLORS[palette_index]


def describe_file(relative_path: str, statements: List[Dict[str, Any]]) -> str:
    suffix = PurePosixPath(relative_path).suffix
    step_count = len(statements)
    if suffix == ".py":
        return f"Archivo Python con {step_count} pasos extraidos del codigo real del servidor."
    if suffix in JS_SUFFIXES:
        return f"Modulo JavaScript/React con {step_count} pasos tomados del componente o flujo real."
    if suffix == ".css":
        return f"Hoja de estilos con {step_count} reglas o bloques reales relevantes."
    if suffix == ".html":
        return f"Documento HTML con {step_count} elementos clave del flujo de carga."
    if suffix == ".json":
        return f"Configuracion JSON con {step_count} claves reales del proyecto."
    if suffix == ".md":
        return f"Documento Markdown con {step_count} fragmentos reales usados para explicar la arquitectura."
    return f"Archivo real del proyecto con {step_count} fragmentos relevantes."


def infer_edge_type(source_node: Dict[str, Any], target_node: Dict[str, Any] | None) -> str:
    if not target_node:
        return "uses"
    if source_node["layer"] in {"frontend", "microservice"} and target_node["layer"] == "backend":
        return "socket"
    if source_node["layer"] == "backend" and target_node["layer"] == "microservice":
        return "socket"
    if source_node["layer"] not in DEFAULT_LAYER_COLORS and target_node["layer"] == "backend":
        return "socket"
    if source_node["layer"] == "backend" and target_node["layer"] not in DEFAULT_LAYER_COLORS:
        return "socket"
    if source_node["layer"] == "config" or target_node["layer"] == "config":
        return "import"
    if source_node["layer"] == "style" or target_node["layer"] == "style":
        return "reference"
    return "uses"


def infer_edge_label(source_node: Dict[str, Any], target_node: Dict[str, Any] | None) -> str:
    if not target_node:
        return "usa"
    if source_node["layer"] == "frontend" and target_node["layer"] == "backend":
        return "consume backend"
    if source_node["layer"] == "microservice" and target_node["layer"] == "backend":
        return "sincroniza ecosistema"
    if source_node["layer"] == "backend" and target_node["layer"] == "microservice":
        return "publica pulso"
    if source_node["layer"] not in DEFAULT_LAYER_COLORS and target_node["layer"] == "backend":
        return "conecta servicio"
    if source_node["layer"] == "backend" and target_node["layer"] not in DEFAULT_LAYER_COLORS:
        return "orquesta proyecto"
    if source_node["layer"] == "config":
        return "define runtime"
    if target_node["layer"] == "config":
        return "requiere config"
    if target_node["layer"] == "style":
        return "aplica estilo"
    return "importa"


def workspace_project_slug(relative_path: str) -> str | None:
    path = PurePosixPath(relative_path)
    parts = path.parts
    if len(parts) >= 3 and parts[0] == "workspace" and parts[1] == "projects":
        return re.sub(r"[^a-z0-9]+", "-", parts[2].lower()).strip("-") or parts[2].lower()
    return None


def node_id_for_path(relative_path: str) -> str:
    return normalize_posix_path(relative_path).replace("/", "__").replace(".", "_")


def normalize_posix_path(value: str) -> str:
    return to_posix(PurePosixPath(os.path.normpath(value)))


def to_posix(path: os.PathLike[str] | PurePosixPath | str) -> str:
    return str(path).replace("\\", "/")
