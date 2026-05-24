"""Deterministic complexity estimator for the orchestration control plane.

The estimator is intentionally evidence-based and cheap to run. It does not
pretend to be a model. It converts request shape, project size, runtime hints,
and risk markers into one auditable budget used by LACE, workers, tasks, and
subagent planning.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

MIN_LACE_CYCLES = 2
MAX_LACE_CYCLES = 10
MAX_SUBAGENTS = 8

RUNTIME_MODE_HINT_SCORE = {
    "smoke": 0,
    "build": 8,
    "medium": 20,
    "long-run": 30,
}

RUNTIME_MODE_SCORE_FLOOR = {
    "medium": 50,
    "long-run": 75,
}

DIFFICULTY_PRESETS: dict[str, dict[str, int | str]] = {
    "facil": {
        "label": "Facil",
        "min_score": 0,
        "max_score": 24,
        "recommended_agents": 1,
        "recommended_lace_cycles": 2,
        "bootstrap_tasks": 1,
        "max_tasks": 3,
        "timeout_seconds": 600,
        "recovery_budget": 2,
        "max_retries": 2,
    },
    "medio": {
        "label": "Medio",
        "min_score": 25,
        "max_score": 49,
        "recommended_agents": 2,
        "recommended_lace_cycles": 3,
        "bootstrap_tasks": 4,
        "max_tasks": 8,
        "timeout_seconds": 900,
        "recovery_budget": 5,
        "max_retries": 3,
    },
    "dificil": {
        "label": "Dificil",
        "min_score": 50,
        "max_score": 74,
        "recommended_agents": 4,
        "recommended_lace_cycles": 5,
        "bootstrap_tasks": 6,
        "max_tasks": 18,
        "timeout_seconds": 1800,
        "recovery_budget": 8,
        "max_retries": 3,
    },
    "extradificil": {
        "label": "Extradificil",
        "min_score": 75,
        "max_score": 100,
        "recommended_agents": 6,
        "recommended_lace_cycles": 8,
        "bootstrap_tasks": 8,
        "max_tasks": 40,
        "timeout_seconds": 3600,
        "recovery_budget": 12,
        "max_retries": 4,
    },
}

_SIMPLE_MARKERS = (
    "bug puntual",
    "cambio puntual",
    "parche minimo",
    "solo",
    "solamente",
    "un archivo",
    "una funcion",
    "sin refactor",
    "no refactor",
    "no crear proyecto nuevo",
    "no cambiar arquitectura",
)
_RUNTIME_RISK_MARKERS = (
    "runtime",
    "cola",
    "checkpoint",
    "blocked",
    "bloqueado",
    "zombie",
    "recuperacion",
    "persistido",
    "estado",
)
_AUDIT_MARKERS = (
    "lace",
    "scanner",
    "integrity",
    "integridad",
    "auditoria",
    "forense",
    "evidencia",
    "checkpoint",
    "observer",
    "findings",
)
_VISUAL_MARKERS = (
    "frontend",
    "ui",
    "interfaz",
    "web",
    "browser",
    "navegador",
    "canvas",
    "screenshot",
    "modal",
)
_BACKEND_MARKERS = ("backend", "api", "flask", "server", "servidor", "endpoint")
_DATA_MARKERS = ("database", "base de datos", "postgres", "mysql", "sqlite", "sql", "orm")
_REALTIME_MARKERS = ("socket", "websocket", "realtime", "tiempo real", "stream")
_3D_MARKERS = ("3d", "three", "three.js", "webgl", "shader")
_SECURITY_MARKERS = ("auth", "login", "seguridad", "security", "permisos", "tokens", "oauth")
_VALIDATION_MARKERS = ("test", "tests", "pytest", "prueba", "validacion", "e2e", "end to end", "punta a punta")
_AMBIGUOUS_BIG_MARKERS = (
    "sistema completo",
    "plataforma",
    "todo",
    "end to end",
    "punta a punta",
    "autonomo",
    "orquestador",
)


def estimate_complexity(
    requirement: str,
    *,
    runtime_mode: str = "build",
    project_file_count: int = 0,
    launch_mode: str = "new",
    project_slug: str = "",
) -> dict[str, Any]:
    """Return one auditable complexity and budget decision.

    `runtime_mode` is a human hint, not the only source of truth. The prompt,
    project size, technical layers, and risk markers can raise or lower the
    final difficulty.
    """

    normalized_mode = _normalize_runtime_mode(runtime_mode)
    normalized_text = _normalize_text(requirement)
    word_count = _word_count(normalized_text)
    file_count = max(0, int(project_file_count or 0))
    score = RUNTIME_MODE_HINT_SCORE.get(normalized_mode, RUNTIME_MODE_HINT_SCORE["build"])
    reasons: list[str] = [f"modo runtime solicitado: {normalized_mode}"]
    risk_flags: list[str] = []
    required_tools: set[str] = set()

    if word_count <= 30:
        reasons.append(f"prompt corto: {word_count} palabras")
    elif word_count <= 120:
        score += 6
        reasons.append(f"prompt medio: {word_count} palabras")
    elif word_count <= 260:
        score += 12
        reasons.append(f"prompt largo: {word_count} palabras")
    else:
        score += 18
        reasons.append(f"prompt muy largo: {word_count} palabras")
        risk_flags.append("prompt_extenso")

    if file_count:
        reasons.append(f"archivos estimados del proyecto: {file_count}")
    if file_count > 40:
        score += 6
    if file_count > 120:
        score += 10
        risk_flags.append("proyecto_mediano_existente")
    if file_count > 300:
        score += 16
        risk_flags.append("proyecto_grande_existente")

    has_simple_markers = _contains_any(normalized_text, _SIMPLE_MARKERS)
    if has_simple_markers:
        score -= 10
        reasons.append("marcadores de trabajo puntual/minimo")
    if _contains_any(normalized_text, _RUNTIME_RISK_MARKERS):
        score += 10
        reasons.append("toca runtime/estado persistido")
        risk_flags.append("estado_persistido")
    if _contains_any(normalized_text, _AUDIT_MARKERS):
        score += 10
        required_tools.update({"scanner", "integrity", "findings"})
        reasons.append("requiere evidencia auditable")
    if _contains_any(normalized_text, _VALIDATION_MARKERS):
        score += 5
        required_tools.add("pytest")
        reasons.append("declara pruebas o validacion")

    layer_count = 0
    if _contains_any(normalized_text, _VISUAL_MARKERS):
        layer_count += 1
        score += 7
        required_tools.update({"scanner", "sandbox"})
        reasons.append("incluye capa visual/frontend")
    if _contains_any(normalized_text, _BACKEND_MARKERS):
        layer_count += 1
        score += 7
        required_tools.add("pytest")
        reasons.append("incluye backend/API")
    if _contains_any(normalized_text, _DATA_MARKERS):
        layer_count += 1
        score += 8
        risk_flags.append("datos_o_base_de_datos")
        reasons.append("incluye datos/base de datos")
    if _contains_any(normalized_text, _REALTIME_MARKERS):
        layer_count += 1
        score += 8
        risk_flags.append("realtime")
        reasons.append("incluye tiempo real/socket")
    if _contains_any(normalized_text, _3D_MARKERS):
        layer_count += 1
        score += 12
        required_tools.update({"scanner", "sandbox"})
        risk_flags.append("visual_3d")
        reasons.append("incluye 3D/WebGL")
    if _contains_any(normalized_text, _SECURITY_MARKERS):
        layer_count += 1
        score += 8
        risk_flags.append("seguridad")
        reasons.append("incluye seguridad/autenticacion")

    if layer_count >= 2:
        score += layer_count * 4
        reasons.append(f"multiples capas tecnicas: {layer_count}")
    if _contains_any(normalized_text, _AMBIGUOUS_BIG_MARKERS):
        score += 8
        reasons.append("alcance amplio o end-to-end")

    if normalized_mode == "smoke":
        score = min(score, 24)
        required_tools = {tool for tool in required_tools if tool in {"pytest"}}
        reasons.append("modo smoke limita presupuesto")
    elif not has_simple_markers:
        mode_floor = RUNTIME_MODE_SCORE_FLOOR.get(normalized_mode)
        if mode_floor is not None and score < mode_floor:
            score = mode_floor
            reasons.append(f"modo {normalized_mode} fija piso de complejidad {mode_floor}")

    score = max(0, min(100, score))
    difficulty = _difficulty_for_score(score)
    preset = dict(DIFFICULTY_PRESETS[difficulty])
    budget = _budget_for_score(score, difficulty, preset)
    if not required_tools:
        required_tools.add("pytest" if difficulty in {"facil", "medio"} else "scanner")
    if difficulty in {"dificil", "extradificil"}:
        required_tools.update({"scanner", "integrity"})
    if difficulty == "extradificil":
        required_tools.update({"sandbox", "findings"})

    confidence = _confidence(score, reasons, risk_flags, normalized_text)
    return {
        "schema_version": 1,
        "estimate_type": "project_complexity_budget",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runtime_mode": normalized_mode,
        "launch_mode": str(launch_mode or "new"),
        "project_slug": str(project_slug or ""),
        "project_file_count": file_count,
        "prompt_word_count": word_count,
        "score": score,
        "difficulty": difficulty,
        "difficulty_label": str(preset["label"]),
        "min_lace_cycles": MIN_LACE_CYCLES,
        "max_lace_cycles": MAX_LACE_CYCLES,
        "recommended_lace_cycles": budget["recommended_lace_cycles"],
        "recommended_agents": budget["recommended_agents"],
        "max_agents": MAX_SUBAGENTS,
        "bootstrap_tasks": budget["bootstrap_tasks"],
        "max_tasks": budget["max_tasks"],
        "timeout_seconds": budget["timeout_seconds"],
        "recovery_budget": budget["recovery_budget"],
        "max_retries": budget["max_retries"],
        "required_tools": sorted(required_tools),
        "risk_flags": sorted(set(risk_flags)),
        "reasons": reasons,
        "confidence": confidence,
    }


def _budget_for_score(score: int, difficulty: str, preset: dict[str, int | str]) -> dict[str, int]:
    budget = {
        "recommended_agents": int(preset["recommended_agents"]),
        "recommended_lace_cycles": int(preset["recommended_lace_cycles"]),
        "bootstrap_tasks": int(preset["bootstrap_tasks"]),
        "max_tasks": int(preset["max_tasks"]),
        "timeout_seconds": int(preset["timeout_seconds"]),
        "recovery_budget": int(preset["recovery_budget"]),
        "max_retries": int(preset["max_retries"]),
    }
    if difficulty == "medio" and score >= 38:
        budget["recommended_agents"] = 3
        budget["recommended_lace_cycles"] = 4
        budget["max_tasks"] = 10
        budget["timeout_seconds"] = 1200
    elif difficulty == "dificil":
        step = min(2, max(0, (score - 50) // 10))
        budget["recommended_agents"] = 4 + step
        budget["recommended_lace_cycles"] = 5 + step
        budget["max_tasks"] = 18 + step * 4
    elif difficulty == "extradificil":
        step = min(2, max(0, (score - 75) // 10))
        budget["recommended_agents"] = 6 + step
        budget["recommended_lace_cycles"] = 8 + step
        budget["timeout_seconds"] = 3600 + step * 900
        budget["max_tasks"] = 32 + step * 4
    budget["recommended_agents"] = max(1, min(MAX_SUBAGENTS, budget["recommended_agents"]))
    budget["recommended_lace_cycles"] = max(MIN_LACE_CYCLES, min(MAX_LACE_CYCLES, budget["recommended_lace_cycles"]))
    return budget


def _difficulty_for_score(score: int) -> str:
    if score <= 24:
        return "facil"
    if score <= 49:
        return "medio"
    if score <= 74:
        return "dificil"
    return "extradificil"


def _confidence(score: int, reasons: list[str], risk_flags: list[str], normalized_text: str) -> int:
    confidence = 88
    if not normalized_text.strip():
        confidence -= 35
    if len(reasons) < 3:
        confidence -= 8
    if "prompt_extenso" in risk_flags:
        confidence -= 5
    if any(marker in normalized_text for marker in ("etc", "lo que sea", "algo", "varias cosas")):
        confidence -= 12
    if score in {24, 25, 49, 50, 74, 75}:
        confidence -= 5
    return max(40, min(95, confidence))


def _normalize_runtime_mode(value: str | None) -> str:
    mode = str(value or "build").strip().lower()
    return mode if mode in RUNTIME_MODE_HINT_SCORE else "build"


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(_contains_marker(text, marker) for marker in markers)


def _contains_marker(text: str, marker: str) -> bool:
    normalized_marker = _normalize_text(marker).strip()
    if not normalized_marker:
        return False
    parts = [re.escape(part) for part in normalized_marker.split()]
    pattern = r"(?<!\w)" + r"\s+".join(parts) + r"(?!\w)"
    return re.search(pattern, text) is not None


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))
