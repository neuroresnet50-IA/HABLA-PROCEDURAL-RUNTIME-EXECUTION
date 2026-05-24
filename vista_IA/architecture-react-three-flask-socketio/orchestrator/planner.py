"""Deterministic project planner for Sprint 2.

The planner intentionally stays simple: it turns a large objective into small
contract-valid tasks without pretending to execute or validate them.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

try:
    from .contracts import ALLOWED_MODES, ContractError, validate_task, validate_task_queue
except ImportError:  # pragma: no cover - supports direct script execution during bootstraps.
    from contracts import ALLOWED_MODES, ContractError, validate_task, validate_task_queue  # type: ignore


DEFAULT_TIMEOUT_SECONDS = {
    "smoke": 300,
    "build": 900,
    "medium": 1800,
    "long-run": 3600,
}

_BULLET_PATTERN = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$")
_PATH_PATTERN = re.compile(
    r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_.-]+)?|"
    r"(?:[A-Za-z0-9_.-]+/)+|"
    r"[A-Za-z0-9_.-]+\.(?:py|json|jsonl|md|txt|js|jsx|ts|tsx|css|html|yml|yaml|toml)"
)
_PATH_ONLY_PATTERN = re.compile(
    r"^(?:(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]*(?:\.[A-Za-z0-9_.-]+)?|"
    r"[A-Za-z0-9_.-]+\.(?:py|json|jsonl|md|txt|js|jsx|ts|tsx|css|html|yml|yaml|toml))$"
)
_IGNORED_SECTION_TERMS = (
    "restriccion",
    "restricciones",
    "validacion",
    "validaciones",
    "criterio",
    "criterios",
    "al final",
    "riesgo",
    "riesgos",
    "prohibido",
)
_DELIVERABLE_SECTION_TERMS = ("entregable", "entregables", "alcance exacto")
_WORK_SECTION_TERMS = (
    "objetivo",
    "requisito",
    "requisitos",
    "trabajo",
    "implementacion",
    "correccion",
    "correcciones",
)
_NEGATIVE_STARTS = (
    "no ",
    "prohibido",
    "evitar ",
    "sin ",
    "no crear",
    "no tocar",
    "no trabajar",
    "no implementar",
)
_META_STARTS = (
    "bug en ",
    "bugs corregidos",
    "archivos tocados",
    "validaciones ejecutadas",
    "riesgos reales",
    "que falta",
    "debes dejar evidencia",
)
_VALIDATION_STARTS = (
    "validar",
    "verificar",
    "asegurar",
    "el planner ",
    "task_queue.py ordena",
    "una tarea dependiente",
    "la cola se puede",
    "la cola sigue",
    "existe ",
)
_WORK_STARTS = (
    "crear",
    "construir",
    "implementar",
    "corregir",
    "modificar",
    "refactorizar",
    "escribir",
    "agregar",
    "inicializar",
    "actualizar",
    "preparar",
    "cargar",
    "guardar",
    "ordenar",
    "detectar",
    "seleccionar",
    "exponer",
    "producir",
    "asignar",
    "recibir",
    "usar",
)

MULTI_MODULE_REQUIRED_FILES = [
    "frontend/index.html",
    "frontend/styles.css",
    "frontend/app.js",
    "shared/crm_schema.json",
    "shared/erp_schema.json",
    "shared/analytics_schema.json",
    "src/crm.js",
    "src/erp.js",
    "src/analytics.js",
    "tests/crm_smoke.test.js",
    "tests/erp_smoke.test.js",
    "tests/analytics_smoke.test.js",
    "tests/integration_smoke.test.js",
    "docs/architecture.md",
    "docs/usage.md",
]

_MULTI_MODULE_SCOPE_MARKERS = (
    "multi-modulo",
    "multi modulo",
    "multimodulo",
    "multi-module",
    "multi module",
    "multi-modular",
    "multi modular",
)
_MODULE_MARKERS = {
    "crm": ("crm", "cliente", "clientes", "customer", "customers"),
    "erp": ("erp", "inventario", "facturacion", "finanzas", "compras", "ordenes"),
    "analytics": ("analytics", "analitica", "analitico", "metricas", "reportes", "dashboard", "bi"),
    "integration": ("integration", "integracion", "integraciones", "e2e", "end-to-end", "end to end"),
    "docs/architecture": ("docs/architecture", "docs/architecture.md", "arquitectura", "architecture"),
}
_PYTHON_SCRIPT_SCOPE_MARKERS = (
    "script",
    "script python",
    "archivo python",
    "fichero python",
)
_SINGLE_FILE_SCOPE_MARKERS = (
    "solo",
    "solamente",
    "unico",
    "unica",
    "un solo",
    "una sola",
    "no mas de",
    "maximo",
)
_STATIC_WEB_APP_MARKERS = (
    "juego",
    "game",
    "pong",
    "canvas",
    "web",
    "frontend",
    "html",
    "navegador",
    "browser",
)
_STATIC_WEB_APP_FILES = ["frontend/index.html", "frontend/styles.css", "frontend/app.js"]
_INTERNAL_EXPECTED_EXACT_PATHS = frozenset({".agent-project.json", "agent-project.json"})
_TKINTER_APP_MARKERS = ("tkinter", "ui tkinter", "interfaz tkinter")
_SUM_APP_MARKERS = ("suma", "sumar", "sume", "sumador", "sumadora")
_RANDOM_MARKERS = ("random", "ramdom", "aleatorio", "aleatoria")


def plan_project(
    objective: str,
    *,
    mode: str = "build",
    max_tasks: int = 8,
    sequential: bool = True,
    task_id_prefix: str = "TASK",
    timeout_seconds: int | None = None,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """Create a small, valid initial task plan from a project objective."""

    if mode not in ALLOWED_MODES:
        raise ContractError(f"mode must be one of: {', '.join(sorted(ALLOWED_MODES))}")
    if not isinstance(objective, str) or not objective.strip():
        raise ContractError("objective must be a non-empty string")
    if max_tasks < 1:
        raise ContractError("max_tasks must be greater than 0")
    if max_retries < 0:
        raise ContractError("max_retries must be greater than or equal to 0")

    selected_timeout = timeout_seconds if timeout_seconds is not None else DEFAULT_TIMEOUT_SECONDS[mode]
    if selected_timeout < 1:
        raise ContractError("timeout_seconds must be greater than 0")
    explicit_python_tasks = _plan_explicit_python_script_tasks(
        objective,
        mode=mode,
        sequential=sequential,
        task_id_prefix=task_id_prefix,
        timeout_seconds=selected_timeout,
        max_retries=max_retries,
    )
    if explicit_python_tasks:
        return validate_plan_scope(objective, explicit_python_tasks)

    tkinter_tasks = _plan_tkinter_app_tasks(
        objective,
        mode=mode,
        sequential=sequential,
        task_id_prefix=task_id_prefix,
        timeout_seconds=selected_timeout,
        max_retries=max_retries,
    )
    if tkinter_tasks:
        return validate_plan_scope(objective, tkinter_tasks)

    static_web_tasks = _plan_static_web_app_tasks(
        objective,
        mode=mode,
        sequential=sequential,
        task_id_prefix=task_id_prefix,
        timeout_seconds=selected_timeout,
        max_retries=max_retries,
    )
    if static_web_tasks:
        return validate_plan_scope(objective, static_web_tasks)

    if mode == "long-run":
        blueprint_tasks = _plan_product_blueprint_tasks(
            objective,
            mode=mode,
            max_tasks=max_tasks,
            sequential=sequential,
            task_id_prefix=task_id_prefix,
            timeout_seconds=selected_timeout,
            max_retries=max_retries,
        )
        if blueprint_tasks:
            return validate_plan_scope(objective, blueprint_tasks)

    work_items = _extract_work_items(objective, max_tasks=max_tasks)

    tasks: list[dict[str, Any]] = []
    for index, work_item in enumerate(work_items, start=1):
        task_id = f"{task_id_prefix}-{index:03d}"
        expected_files = _infer_expected_files(work_item, task_id)
        task = {
            "id": task_id,
            "title": _make_title(work_item, index),
            "goal": work_item,
            "status": "pending",
            "priority": (len(work_items) - index + 1) * 10,
            "dependencies": [f"{task_id_prefix}-{index - 1:03d}"] if sequential and index > 1 else [],
            "expected_files": expected_files,
            "validation_commands": [_expected_files_validation_command(expected_files)],
            "timeout_seconds": selected_timeout,
            "max_retries": max_retries,
            "mode": mode,
            "checkpoint_key": f"{task_id.lower()}-checkpoint",
        }
        tasks.append(validate_task(task))

    return validate_plan_scope(objective, tasks)


def validate_plan_scope(objective: str, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate task contracts plus explicit project scope promises."""

    validated_tasks = validate_task_queue(tasks)
    if _requires_multi_module_scope(objective):
        missing = _missing_expected_files(validated_tasks, MULTI_MODULE_REQUIRED_FILES)
        if missing:
            raise ContractError(
                "multi-module scope gate failed; missing expected files: " + ", ".join(missing)
            )
    return validated_tasks


def _plan_product_blueprint_tasks(
    objective: str,
    *,
    mode: str,
    max_tasks: int,
    sequential: bool,
    task_id_prefix: str,
    timeout_seconds: int,
    max_retries: int,
) -> list[dict[str, Any]]:
    blueprint = _product_blueprint(objective)
    if not blueprint:
        return []

    selected = blueprint if _requires_multi_module_scope(objective) else blueprint[:max_tasks]
    tasks: list[dict[str, Any]] = []
    for index, item in enumerate(selected, start=1):
        task_id = f"{task_id_prefix}-{index:03d}"
        dependencies = [f"{task_id_prefix}-{index - 1:03d}"] if sequential and index > 1 else []
        task = {
            "id": task_id,
            "title": item["title"],
            "goal": item["goal"],
            "status": "pending",
            "priority": (len(selected) - index + 1) * 10,
            "dependencies": dependencies,
            "expected_files": item["expected_files"],
            "validation_commands": [_expected_files_validation_command(item["expected_files"])],
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
            "mode": mode,
            "checkpoint_key": f"{task_id.lower()}-checkpoint",
        }
        tasks.append(validate_task(task))
    return tasks


def _plan_explicit_python_script_tasks(
    objective: str,
    *,
    mode: str,
    sequential: bool,
    task_id_prefix: str,
    timeout_seconds: int,
    max_retries: int,
) -> list[dict[str, Any]]:
    python_files = _explicit_python_script_files(objective)
    if not python_files:
        return []

    task_id = f"{task_id_prefix}-001"
    validation_commands = [
        _expected_files_validation_command(python_files),
        _python_compile_validation_command(python_files),
    ]
    task = {
        "id": task_id,
        "title": "Implement explicit Python script",
        "goal": _compact_whitespace(objective),
        "status": "pending",
        "priority": 10,
        "dependencies": [] if sequential else [],
        "expected_files": python_files,
        "validation_commands": validation_commands,
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "mode": mode,
        "checkpoint_key": f"{task_id.lower()}-checkpoint",
    }
    return [validate_task(task)]


def _plan_static_web_app_tasks(
    objective: str,
    *,
    mode: str,
    sequential: bool,
    task_id_prefix: str,
    timeout_seconds: int,
    max_retries: int,
) -> list[dict[str, Any]]:
    if _requires_multi_module_scope(objective):
        return []
    normalized = _normalize_text(objective)
    if not normalized or not any(marker in normalized for marker in _STATIC_WEB_APP_MARKERS):
        return []

    task_id = f"{task_id_prefix}-001"
    task = {
        "id": task_id,
        "title": "Build runnable static web app",
        "goal": _compact_whitespace(objective),
        "status": "pending",
        "priority": 10,
        "dependencies": [] if sequential else [],
        "expected_files": list(_STATIC_WEB_APP_FILES),
        "validation_commands": [_expected_files_validation_command(_STATIC_WEB_APP_FILES)],
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "mode": mode,
        "checkpoint_key": f"{task_id.lower()}-checkpoint",
    }
    return [validate_task(task)]


def _plan_tkinter_app_tasks(
    objective: str,
    *,
    mode: str,
    sequential: bool,
    task_id_prefix: str,
    timeout_seconds: int,
    max_retries: int,
) -> list[dict[str, Any]]:
    normalized = _normalize_text(objective)
    if not normalized or not any(marker in normalized for marker in _TKINTER_APP_MARKERS):
        return []

    task_id = f"{task_id_prefix}-001"
    expected_files = [_tkinter_app_expected_file(normalized)]
    validation_commands = [
        _expected_files_validation_command(expected_files),
        _python_compile_validation_command(expected_files),
    ]
    line_limit = _line_limit_from_objective(normalized)
    if line_limit is not None:
        validation_commands.append(_line_count_validation_command(expected_files, line_limit))
    task = {
        "id": task_id,
        "title": "Build Tkinter Python app",
        "goal": _compact_whitespace(objective),
        "status": "pending",
        "priority": 10,
        "dependencies": [] if sequential else [],
        "expected_files": expected_files,
        "validation_commands": validation_commands,
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "mode": mode,
        "checkpoint_key": f"{task_id.lower()}-checkpoint",
    }
    return [validate_task(task)]


def _tkinter_app_expected_file(normalized_objective: str) -> str:
    if any(marker in normalized_objective for marker in _SUM_APP_MARKERS):
        if any(marker in normalized_objective for marker in _RANDOM_MARKERS):
            return "src/suma_random_tkinter.py"
        return "src/suma_tkinter.py"
    return "src/tkinter_app.py"


def _explicit_python_script_files(objective: str) -> list[str]:
    if _requires_multi_module_scope(objective):
        return []
    normalized = _normalize_text(objective)
    if not normalized:
        return []
    has_script_scope = any(marker in normalized for marker in _PYTHON_SCRIPT_SCOPE_MARKERS)
    has_single_file_scope = any(marker in normalized for marker in _SINGLE_FILE_SCOPE_MARKERS)
    if not (has_script_scope and has_single_file_scope):
        return []
    python_files = _positive_python_paths(objective)
    return python_files


def _positive_python_paths(objective: str) -> list[str]:
    paths: list[str] = []
    for match in _PATH_PATTERN.finditer(objective):
        path = match.group(0).rstrip(".,:;")
        if path.endswith(".py") and not _has_negative_path_context(objective, match.start()):
            paths.append(path)
    return _dedupe_preserving_order(paths)


def _has_negative_path_context(objective: str, path_start: int) -> bool:
    prefix = objective[max(0, path_start - 120):path_start]
    clause = re.split(r"[\n;]|(?<=[.!?])\s+", prefix)[-1]
    normalized = _normalize_text(clause)
    if normalized.startswith(_NEGATIVE_STARTS):
        return True
    negative_markers = (
        "no crees",
        "no crear",
        "no cree",
        "no generes",
        "no generar",
        "no implementes",
        "no implementar",
        "sin crear",
        "sin generar",
        "sin implementar",
    )
    return any(marker in normalized for marker in negative_markers)


def _product_blueprint(objective: str) -> list[dict[str, Any]]:
    normalized = _normalize_text(objective)
    if not normalized.strip():
        return []
    if _requires_multi_module_scope(objective):
        return _multi_module_blueprint()
    is_crm = any(marker in normalized for marker in ("crm", "cliente", "clientes", "customer", "customers"))
    product_name = "CRM" if is_crm else "project"
    return [
        {
            "title": f"Define {product_name} scope and project shell",
            "goal": f"Create the initial {product_name} project scope, README, and implementation notes.",
            "expected_files": ["README.md", "docs/project_scope.md"],
        },
        {
            "title": f"Build {product_name} frontend shell",
            "goal": f"Create the visible {product_name} application shell with HTML and CSS.",
            "expected_files": ["frontend/index.html", "frontend/styles.css"],
        },
        {
            "title": f"Implement {product_name} interaction layer",
            "goal": f"Create interactive {product_name} behavior and shared data schema.",
            "expected_files": ["frontend/app.js", "shared/crm_schema.json" if is_crm else "shared/project_schema.json"],
        },
        {
            "title": f"Implement {product_name} domain module",
            "goal": f"Create reusable domain logic for the {product_name} workflow.",
            "expected_files": ["src/crm.js" if is_crm else "src/project.js"],
        },
        {
            "title": f"Add {product_name} validation tests",
            "goal": f"Create a small validation test or smoke check for the {product_name} workflow.",
            "expected_files": ["tests/crm_smoke.test.js" if is_crm else "tests/project_smoke.test.js"],
        },
        {
            "title": f"Document {product_name} usage",
            "goal": f"Document how to run, inspect, and extend the {product_name} project.",
            "expected_files": ["docs/usage.md"],
        },
    ]


def _multi_module_blueprint() -> list[dict[str, Any]]:
    return [
        {
            "title": "Build multi-module frontend shell",
            "goal": "Create the shared frontend shell for CRM, ERP, and analytics workflows.",
            "expected_files": ["frontend/index.html", "frontend/styles.css"],
        },
        {
            "title": "Implement multi-module frontend controller",
            "goal": "Wire the frontend controller across CRM, ERP, analytics, and integration state.",
            "expected_files": ["frontend/app.js"],
        },
        {
            "title": "Implement CRM domain module",
            "goal": "Create CRM schema, domain logic, and a smoke test for customer workflows.",
            "expected_files": ["shared/crm_schema.json", "src/crm.js", "tests/crm_smoke.test.js"],
        },
        {
            "title": "Implement ERP domain module",
            "goal": "Create ERP schema, domain logic, and a smoke test for operational workflows.",
            "expected_files": ["shared/erp_schema.json", "src/erp.js", "tests/erp_smoke.test.js"],
        },
        {
            "title": "Implement analytics domain module",
            "goal": "Create analytics schema, domain logic, and a smoke test for reporting workflows.",
            "expected_files": [
                "shared/analytics_schema.json",
                "src/analytics.js",
                "tests/analytics_smoke.test.js",
            ],
        },
        {
            "title": "Add cross-module integration validation",
            "goal": "Validate CRM, ERP, and analytics contracts together through an integration smoke test.",
            "expected_files": ["tests/integration_smoke.test.js"],
        },
        {
            "title": "Document multi-module architecture and usage",
            "goal": "Document the architecture, module boundaries, integration flow, and usage.",
            "expected_files": ["docs/architecture.md", "docs/usage.md"],
        },
    ]


def create_task(
    *,
    task_id: str,
    title: str,
    goal: str,
    priority: int,
    dependencies: list[str] | None = None,
    expected_files: list[str] | None = None,
    validation_commands: list[str] | None = None,
    timeout_seconds: int | None = None,
    max_retries: int = 3,
    mode: str = "build",
    checkpoint_key: str | None = None,
) -> dict[str, Any]:
    """Build one contract-valid task for callers that already know the scope."""

    if mode not in ALLOWED_MODES:
        raise ContractError(f"mode must be one of: {', '.join(sorted(ALLOWED_MODES))}")
    selected_timeout = timeout_seconds if timeout_seconds is not None else DEFAULT_TIMEOUT_SECONDS[mode]
    if selected_timeout < 1:
        raise ContractError("timeout_seconds must be greater than 0")

    files = expected_files or [f"runtime/artifacts/{task_id}.json"]
    task = {
        "id": task_id,
        "title": title,
        "goal": goal,
        "status": "pending",
        "priority": priority,
        "dependencies": dependencies or [],
        "expected_files": files,
        "validation_commands": validation_commands or [_expected_files_validation_command(files)],
        "timeout_seconds": selected_timeout,
        "max_retries": max_retries,
        "mode": mode,
        "checkpoint_key": checkpoint_key,
    }
    return validate_task(task)


def _extract_work_items(objective: str, *, max_tasks: int) -> list[str]:
    bullet_candidates = _extract_bullet_candidates(objective)
    if bullet_candidates:
        work_items = [_normalize_work_item(item) for item in bullet_candidates if _is_real_work_item(item)]
        work_items = _dedupe_preserving_order(work_items)
        if not work_items:
            raise ContractError("objective does not contain executable work items")
        return _limit_items(work_items, max_tasks)

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", objective) if part.strip()]
    if len(paragraphs) > 1:
        return _limit_items(paragraphs, max_tasks)

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", objective) if part.strip()]
    if len(sentences) > 1:
        return _limit_items(sentences, max_tasks)

    return [_compact_whitespace(objective)]


def _extract_bullet_candidates(objective: str) -> list[str]:
    items: list[str] = []
    section_kind = "general"
    for line in objective.splitlines():
        match = _BULLET_PATTERN.match(line)
        if match:
            if section_kind != "ignored":
                items.append(_compact_whitespace(match.group(1)))
            continue

        heading = _section_kind_from_heading(line)
        if heading is not None:
            section_kind = heading
    return _dedupe_preserving_order(items)


def _section_kind_from_heading(line: str) -> str | None:
    raw = _compact_whitespace(line.strip())
    stripped = _compact_whitespace(raw.strip("#: "))
    if not raw or not stripped:
        return None
    normalized = _normalize_text(stripped)
    if not _looks_like_heading(raw):
        return None
    if any(term in normalized for term in _IGNORED_SECTION_TERMS):
        return "ignored"
    if any(term in normalized for term in _DELIVERABLE_SECTION_TERMS):
        return "deliverable"
    if any(term in normalized for term in _WORK_SECTION_TERMS):
        return "work"
    return "general"


def _looks_like_heading(value: str) -> bool:
    if value.endswith(":") or value.startswith("#"):
        return True
    letters = [character for character in value if character.isalpha()]
    if letters and sum(character.isupper() for character in letters) / len(letters) > 0.7:
        return True
    return bool(re.match(r"^\d+\.\s+[A-ZÁÉÍÓÚÑ]", value))


def _is_real_work_item(item: str) -> bool:
    normalized = _normalize_text(item)
    if not normalized:
        return False
    if normalized.startswith(_NEGATIVE_STARTS):
        return False
    if normalized.startswith(_META_STARTS):
        return False
    if normalized.startswith(_VALIDATION_STARTS):
        return False
    if any(term in normalized for term in ("validacion minima", "criterio de aceptacion")):
        return False
    if _is_path_only_item(item):
        return True
    if normalized.startswith(_WORK_STARTS):
        return True
    return bool(_PATH_PATTERN.search(item) and any(verb in normalized for verb in _WORK_STARTS))


def _normalize_work_item(item: str) -> str:
    clean_item = _compact_whitespace(item)
    if _is_path_only_item(clean_item):
        if clean_item.endswith("/"):
            return f"Crear estructura {clean_item}"
        return f"Implementar {clean_item}"
    return clean_item


def _is_path_only_item(item: str) -> bool:
    return bool(_PATH_ONLY_PATTERN.fullmatch(item.strip()))


def _limit_items(items: list[str], max_tasks: int) -> list[str]:
    clean_items = [_compact_whitespace(item) for item in items if item.strip()]
    if len(clean_items) <= max_tasks:
        return clean_items

    grouped: list[str] = []
    group_count = min(max_tasks, len(clean_items))
    iterator = iter(clean_items)
    for group_index in range(group_count):
        group_size = (len(clean_items) - group_index + group_count - 1) // group_count
        grouped.append("; ".join(next(iterator) for _ in range(group_size)))
    return grouped


def _infer_expected_files(work_item: str, task_id: str) -> list[str]:
    paths = _sanitize_expected_file_paths(_PATH_PATTERN.findall(work_item))
    if paths:
        return paths
    return [f"runtime/artifacts/{task_id.lower()}.json"]


def _requires_multi_module_scope(objective: str) -> bool:
    normalized = _normalize_text(objective)
    if not normalized:
        return False
    requested_modules = {
        module
        for module, markers in _MODULE_MARKERS.items()
        if any(_contains_marker(normalized, marker) for marker in markers)
    }
    has_multi_marker = any(marker in normalized for marker in _MULTI_MODULE_SCOPE_MARKERS)
    requested_core_modules = {"crm", "erp", "analytics"}.issubset(requested_modules)
    return requested_core_modules or (has_multi_marker and len(requested_modules) >= 2)


def _missing_expected_files(tasks: list[dict[str, Any]], required_files: list[str]) -> list[str]:
    planned_files = {
        str(path)
        for task in tasks
        for path in task.get("expected_files", [])
        if str(path)
    }
    return [path for path in required_files if path not in planned_files]


def _contains_marker(normalized_text: str, marker: str) -> bool:
    normalized_marker = _normalize_text(marker)
    if not normalized_marker:
        return False
    if re.search(r"[a-z0-9]", normalized_marker):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized_marker)}(?![a-z0-9])", normalized_text))
    return normalized_marker in normalized_text


def _expected_files_validation_command(expected_files: list[str]) -> str:
    return (
        "python3 -B -c "
        + repr(
            "from pathlib import Path; "
            f"missing=[p for p in {expected_files!r} if not Path(p).is_file()]; "
            "assert not missing, missing"
        )
    )


def _python_compile_validation_command(python_files: list[str]) -> str:
    return "python3 -m py_compile " + " ".join(python_files)


def _line_count_validation_command(files: list[str], max_lines: int) -> str:
    return (
        "python3 -B -c "
        + repr(
            "from pathlib import Path; "
            f"too_long=[p for p in {files!r} if len(Path(p).read_text(encoding='utf-8').splitlines()) > {max_lines}]; "
            "assert not too_long, too_long"
        )
    )


def _line_limit_from_objective(normalized_objective: str) -> int | None:
    patterns = (
        r"no mas de\s+(\d+)\s+lineas?",
        r"maximo\s+(\d+)\s+lineas?",
        r"menos de\s+(\d+)\s+lineas?",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized_objective)
        if match:
            return int(match.group(1))
    return None


def _make_title(work_item: str, index: int) -> str:
    words = _compact_whitespace(work_item).split()
    title = " ".join(words[:8]).rstrip(".,;:")
    return title or f"Tarea {index}"


def _compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_text(value: str) -> str:
    without_accents = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(character for character in without_accents if not unicodedata.combining(character))
    return _compact_whitespace(ascii_text).lower()


def _dedupe_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _sanitize_expected_file_paths(paths: list[str]) -> list[str]:
    sanitized: list[str] = []
    for raw_path in paths:
        path = str(Path(raw_path.replace("\\", "/").strip()).as_posix())
        if not path or path.endswith("/"):
            continue
        if path.startswith("/") or ".." in Path(path).parts:
            continue
        if path == "workspace/projects" or path.startswith("workspace/projects/"):
            continue
        if _is_internal_expected_file_path(path):
            continue
        if not Path(path).suffix:
            continue
        sanitized.append(path)
    return _dedupe_preserving_order(sanitized)


def _is_internal_expected_file_path(path: str) -> bool:
    normalized = str(Path(str(path or ".")).as_posix())
    if normalized in _INTERNAL_EXPECTED_EXACT_PATHS:
        return True
    return normalized.startswith(".vista/")
