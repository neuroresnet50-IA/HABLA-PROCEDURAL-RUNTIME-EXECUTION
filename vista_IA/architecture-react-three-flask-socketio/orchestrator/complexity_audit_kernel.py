"""Adaptive complexity audit kernel for HABLA/LACE budgets.

This module is deterministic, auditable, and intentionally conservative. It is
not a model replacement. It converts prompt shape, repository evidence, runtime
risk, required validation, historical failures, and uncertainty into an
operational budget for workers and LACE.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_VERSION = "complexity-audit-kernel-v1"
POLICY_DEFAULT_CEILING = 10
SAFE_FALLBACK_MIN = 1
SAFE_FALLBACK_TARGET = 2
SAFE_FALLBACK_MAX = 3

DIFFICULTY_BUDGETS: dict[str, dict[str, Any]] = {
    "facil": {
        "label": "Facil",
        "estimated_minutes": 15,
        "recommended_agents": 1,
        "max_agents": 2,
        "lace_min_cycles": 0,
        "lace_target_cycles": 1,
        "lace_max_cycles": 2,
        "early_exit_allowed": True,
    },
    "medio": {
        "label": "Medio",
        "estimated_minutes": 45,
        "recommended_agents": 3,
        "max_agents": 4,
        "lace_min_cycles": 2,
        "lace_target_cycles": 3,
        "lace_max_cycles": 4,
        "early_exit_allowed": True,
    },
    "dificil": {
        "label": "Dificil",
        "estimated_minutes": 120,
        "recommended_agents": 5,
        "max_agents": 6,
        "lace_min_cycles": 3,
        "lace_target_cycles": 5,
        "lace_max_cycles": 7,
        "early_exit_allowed": True,
    },
    "extradificil": {
        "label": "Extradificil",
        "estimated_minutes": 240,
        "recommended_agents": 8,
        "max_agents": 8,
        "lace_min_cycles": 5,
        "lace_target_cycles": 8,
        "lace_max_cycles": 10,
        "early_exit_allowed": True,
        "early_exit_mode": "conditional",
    },
}

EXCLUDED_PROJECT_PARTS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "runtime",
    "venv",
    ".venv",
}

PROMPT_MARKERS = {
    "frontend": ("frontend", "react", "ui", "interfaz", "modal", "browser", "canvas"),
    "backend": ("backend", "api", "flask", "server", "endpoint"),
    "database": ("database", "base de datos", "postgres", "sql", "orm"),
    "auth": ("auth", "login", "autentic", "password", "token"),
    "runtime": ("runtime", "control plane", "cola", "task_queue", "checkpoint", "worker"),
    "lace": ("lace", "automejora", "closure gate", "ciclo"),
    "scanner": ("scanner", "integrity", "findings", "forense", "evidencia"),
    "sandbox": ("sandbox", "preview", "healthcheck", "servidor vivo"),
    "three_d": ("3d", "three", "webgl", "shader", "mario"),
    "tests": ("test", "pytest", "unittest", "e2e", "validacion"),
    "refactor": ("refactor", "arquitectura", "multiarchivo", "transversal"),
}

RISK_PATH_PARTS = {
    "backend/agent_runtime.py": 30,
    "orchestrator/validator.py": 24,
    "orchestrator/recovery.py": 22,
    "orchestrator/task_queue.py": 22,
    "orchestrator/executor.py": 20,
    "workers/codex_worker.py": 22,
    "backend/app.py": 18,
}

HISTORY_MARKERS = (
    "bwrap",
    "bubblewrap",
    "workspace-write",
    "paused_infrastructure_failures",
    "worker_smoke_failed",
    "expected_file_missing",
    "lace_closure_blocked",
    "runtime_zombie_recovered",
    "project_locked",
    "cyberlace",
    "timeout",
)


def audit_complexity(
    prompt: str,
    *,
    project_root: str | Path | None = None,
    task: dict[str, Any] | None = None,
    runtime_mode: str = "build",
    launch_mode: str = "new",
    project_slug: str = "",
    project_file_count: int | None = None,
    legacy_estimate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a seven-layer operational complexity audit."""

    project_path = Path(project_root).resolve() if project_root is not None else None
    prompt_layer = score_prompt_layer(prompt)
    project_layer = score_project_layer(project_path, project_file_count=project_file_count)
    risk_layer = score_operational_risk_layer(prompt, project_path, task=task)
    blast_layer = score_blast_radius_layer(prompt, task=task)
    evidence_layer = score_evidence_layer(prompt, task=task)
    history_layer = score_history_layer(project_path)
    uncertainty_layer = score_uncertainty_layer(prompt, project_path, task=task)

    layer_scores = {
        "prompt": prompt_layer["score"],
        "project": project_layer["score"],
        "operational_risk": risk_layer["score"],
        "blast_radius": blast_layer["score"],
        "evidence": evidence_layer["score"],
        "history": history_layer["score"],
        "uncertainty": uncertainty_layer["score"],
    }
    score = round(
        layer_scores["prompt"] * 0.18
        + layer_scores["project"] * 0.14
        + layer_scores["operational_risk"] * 0.22
        + layer_scores["blast_radius"] * 0.16
        + layer_scores["evidence"] * 0.12
        + layer_scores["history"] * 0.10
        + layer_scores["uncertainty"] * 0.08
    )
    score = max(0, min(100, int(score)))
    if runtime_mode == "smoke":
        score = min(score, 20)
    elif runtime_mode == "medium":
        score = max(score, 35)
    elif runtime_mode == "long-run":
        score = max(score, 55)

    difficulty = difficulty_for_score(score)
    if isinstance(legacy_estimate, dict) and legacy_estimate.get("difficulty"):
        legacy_difficulty = normalize_difficulty(str(legacy_estimate.get("difficulty")))
        if legacy_difficulty and difficulty_rank(legacy_difficulty) > difficulty_rank(difficulty):
            # Legacy estimator remains a risk signal, but it cannot force LACE to 10 by itself.
            difficulty = legacy_difficulty
            score = max(score, int(legacy_estimate.get("score") or score))

    budget = dict(DIFFICULTY_BUDGETS[difficulty])
    if runtime_mode == "smoke":
        budget.update({"lace_min_cycles": 0, "lace_target_cycles": 0, "lace_max_cycles": 0, "early_exit_allowed": True})

    tools = sorted(set(prompt_layer["required_tools"]) | set(project_layer["required_tools"]) | set(risk_layer["required_tools"]) | set(evidence_layer["required_tools"]))
    risk_flags = sorted(set(prompt_layer["risk_flags"]) | set(project_layer["risk_flags"]) | set(risk_layer["risk_flags"]) | set(history_layer["risk_flags"]) | set(uncertainty_layer["risk_flags"]))
    reasoning = []
    for layer in (prompt_layer, project_layer, risk_layer, blast_layer, evidence_layer, history_layer, uncertainty_layer):
        reasoning.extend(layer["reasons"][:4])

    confidence = confidence_for_audit(reasoning, uncertainty_layer["score"], history_layer["score"], project_layer["observed"])
    return {
        "schema_version": 1,
        "audit_version": AUDIT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runtime_mode": runtime_mode,
        "launch_mode": str(launch_mode or "new"),
        "project_slug": str(project_slug or (project_path.name if project_path else "")),
        "difficulty": difficulty,
        "difficulty_label": budget["label"],
        "complexity_score": score,
        "confidence": confidence,
        "estimated_minutes": budget["estimated_minutes"],
        "recommended_agents": budget["recommended_agents"],
        "max_agents": budget["max_agents"],
        "lace_min_cycles": budget["lace_min_cycles"],
        "lace_target_cycles": budget["lace_target_cycles"],
        "lace_max_cycles": budget["lace_max_cycles"],
        "early_exit_allowed": bool(budget.get("early_exit_allowed", True)),
        "early_exit_mode": budget.get("early_exit_mode", "allowed"),
        "required_tools": tools or ["pytest"],
        "risk_flags": risk_flags,
        "reasoning": reasoning[:18],
        "layer_scores": layer_scores,
        "layers": {
            "prompt": prompt_layer,
            "project": project_layer,
            "operational_risk": risk_layer,
            "blast_radius": blast_layer,
            "evidence": evidence_layer,
            "history": history_layer,
            "uncertainty": uncertainty_layer,
        },
    }


def score_prompt_layer(prompt: str) -> dict[str, Any]:
    text = normalize_text(prompt)
    words = re.findall(r"\w+", text)
    score = 4 if len(words) <= 25 else 18 if len(words) <= 120 else 38 if len(words) <= 260 else 62
    reasons = [f"prompt palabras={len(words)}"]
    tools: set[str] = set()
    flags: set[str] = set()
    marker_hits = []
    for label, markers in PROMPT_MARKERS.items():
        if contains_any(text, markers):
            marker_hits.append(label)
            if label in {"scanner", "sandbox", "tests"}:
                tools.add("sandbox" if label == "sandbox" else "scanner" if label == "scanner" else "pytest")
            if label in {"runtime", "lace", "auth", "database", "three_d"}:
                flags.add(label)
    score += min(36, len(marker_hits) * 6)
    if marker_hits:
        reasons.append("capas detectadas en prompt: " + ", ".join(marker_hits[:8]))
    deliverable_count = len(re.findall(r"\b(crear|reparar|implementar|validar|agregar|conectar|probar|integrar)\b", text))
    if deliverable_count > 2:
        score += min(16, deliverable_count * 2)
        reasons.append(f"multiples acciones solicitadas={deliverable_count}")
    return layer(score, reasons, tools, flags)


def score_project_layer(project_root: Path | None, *, project_file_count: int | None = None) -> dict[str, Any]:
    observed = bool(project_root and project_root.exists())
    count = max(0, int(project_file_count or 0))
    reasons: list[str] = []
    tools: set[str] = set()
    flags: set[str] = set()
    if observed and project_root is not None:
        files = list(iter_project_files(project_root, limit=600))
        count = max(count, len(files))
        names = {path.name for path in files}
        parts = {part for path in files for part in path.parts}
        if "package.json" in names or "frontend" in parts:
            tools.add("sandbox")
            flags.add("frontend")
            reasons.append("frontend/package detectado")
        if "backend" in parts or "app.py" in names:
            tools.add("pytest")
            flags.add("backend")
            reasons.append("backend/python detectado")
        if "orchestrator" in parts or "workers" in parts or "runtime" in parts:
            flags.add("agentic_runtime")
            reasons.append("runtime agentico detectado")
        if "LACE.md" in names:
            flags.add("lace_policy")
            reasons.append("LACE.md presente")
    else:
        reasons.append("proyecto no inspeccionado")
        flags.add("project_unknown")
    score = 4 if count <= 5 else 18 if count <= 40 else 36 if count <= 120 else 58 if count <= 300 else 78
    reasons.insert(0, f"archivos materiales estimados={count}")
    return {**layer(score, reasons, tools, flags), "observed": observed, "file_count": count}


def score_operational_risk_layer(prompt: str, project_root: Path | None, *, task: dict[str, Any] | None = None) -> dict[str, Any]:
    text = normalize_text(prompt)
    score = 0
    reasons: list[str] = []
    tools: set[str] = set()
    flags: set[str] = set()
    for marker in ("runtime", "control plane", "task_queue", "validator", "recovery", "worker", "codex", "cyberlace", "lace"):
        if marker in text:
            score += 10
            flags.add(marker.replace(" ", "_"))
    expected = [str(item) for item in (task or {}).get("expected_files") or []]
    candidates = expected
    for relative, weight in RISK_PATH_PARTS.items():
        if relative in text or relative in candidates:
            score += weight
            flags.add("critical_runtime_file")
            reasons.append(f"archivo critico: {relative}")
    if any(item.startswith("runtime/") for item in expected):
        score += 30
        flags.add("runtime_state")
    if contains_any(text, ("auth", "login", "postgres", "token", "secret", "seguridad")):
        score += 18
        flags.add("security_or_auth")
    if flags:
        tools.update({"integrity", "findings"})
        reasons.append("riesgo operativo: " + ", ".join(sorted(flags)[:8]))
    return layer(score, reasons or ["riesgo operativo bajo"], tools, flags)


def score_blast_radius_layer(prompt: str, *, task: dict[str, Any] | None = None) -> dict[str, Any]:
    text = normalize_text(prompt)
    expected = [str(item) for item in (task or {}).get("expected_files") or []]
    touched_dirs = {Path(item).parts[0] for item in expected if Path(item).parts}
    score = 6
    reasons = [f"expected_files={len(expected)}"]
    flags: set[str] = set()
    if len(expected) == 1:
        score = 10
    elif len(expected) <= 4:
        score = 24
    elif len(expected) <= 10:
        score = 42
    elif len(expected) > 10:
        score = 62
    if len(touched_dirs) >= 3:
        score += 16
        flags.add("multi_layer")
        reasons.append("multiples directorios: " + ", ".join(sorted(touched_dirs)))
    if contains_any(text, ("arquitectura", "transversal", "sistema completo", "end to end", "todo")):
        score += 22
        flags.add("architecture_wide")
    return layer(score, reasons, set(), flags)


def score_evidence_layer(prompt: str, *, task: dict[str, Any] | None = None) -> dict[str, Any]:
    text = normalize_text(prompt)
    commands = [str(item) for item in (task or {}).get("validation_commands") or []]
    score = 8 + min(30, len(commands) * 8)
    tools: set[str] = set()
    flags: set[str] = set()
    reasons = [f"validation_commands={len(commands)}"]
    evidence_markers = {
        "pytest": ("pytest", "unittest", "test"),
        "scanner": ("scanner", "lupa"),
        "integrity": ("integrity", "integridad"),
        "sandbox": ("sandbox", "healthcheck", "browser smoke"),
        "findings": ("findings", "observer"),
    }
    joined = text + " " + " ".join(commands).lower()
    for tool, markers in evidence_markers.items():
        if contains_any(joined, markers):
            tools.add(tool)
            flags.add(f"requires_{tool}")
            score += 10
    if tools:
        reasons.append("evidencia requerida: " + ", ".join(sorted(tools)))
    return layer(score, reasons, tools, flags)


def score_history_layer(project_root: Path | None) -> dict[str, Any]:
    reasons: list[str] = []
    flags: set[str] = set()
    if project_root is None:
        return layer(12, ["historial no disponible"], set(), {"history_unknown"})
    runtime = project_root / "runtime"
    haystack = ""
    for relative in ("failures.jsonl", "task_history.jsonl"):
        path = runtime / relative
        if path.exists():
            try:
                haystack += "\n" + "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-120:])
            except OSError:
                pass
    text = normalize_text(haystack)
    hits = [marker for marker in HISTORY_MARKERS if marker in text]
    score = min(80, len(hits) * 9)
    if hits:
        flags.update(hits[:8])
        reasons.append("fallos historicos: " + ", ".join(hits[:8]))
    else:
        reasons.append("sin fallos historicos relevantes")
    return layer(score, reasons, set(), flags)


def score_uncertainty_layer(prompt: str, project_root: Path | None, *, task: dict[str, Any] | None = None) -> dict[str, Any]:
    text = normalize_text(prompt)
    score = 0
    reasons: list[str] = []
    flags: set[str] = set()
    if not text.strip():
        score += 60
        flags.add("empty_prompt")
    if contains_any(text, ("algo", "lo que sea", "todo", "varias cosas", "mejoralo", "arreglalo")):
        score += 24
        flags.add("ambiguous_prompt")
    if project_root is None or not project_root.exists():
        score += 24
        flags.add("project_not_observed")
    if task is not None and not task.get("expected_files"):
        score += 20
        flags.add("expected_files_missing")
    if flags:
        reasons.append("incertidumbre: " + ", ".join(sorted(flags)))
    else:
        reasons.append("incertidumbre baja")
    return layer(score, reasons, set(), flags)


def map_score_to_lace_budget(score: int, *, runtime_mode: str = "build", policy_ceiling: int = POLICY_DEFAULT_CEILING) -> dict[str, Any]:
    if runtime_mode == "smoke":
        difficulty = "facil"
        budget = {**DIFFICULTY_BUDGETS[difficulty], "lace_min_cycles": 0, "lace_target_cycles": 0, "lace_max_cycles": 0}
    else:
        difficulty = difficulty_for_score(score)
        budget = dict(DIFFICULTY_BUDGETS[difficulty])
    return clamp_lace_budget(
        {
            "difficulty": difficulty,
            "min_cycles": budget["lace_min_cycles"],
            "target_cycles": budget["lace_target_cycles"],
            "max_cycles": budget["lace_max_cycles"],
            "early_exit_allowed": bool(budget.get("early_exit_allowed", True)),
            "quality_threshold": 85,
            "source": AUDIT_VERSION,
            "policy_ceiling": policy_ceiling,
        },
        policy_ceiling=policy_ceiling,
    )


def resolve_lace_budget_from_sources(
    *,
    runtime_mode: str,
    explicit_config: dict[str, Any] | None = None,
    complexity_audit: dict[str, Any] | None = None,
    complexity_estimate: dict[str, Any] | None = None,
    lace_log_text: str = "",
    lace_policy_text: str = "",
) -> dict[str, Any]:
    """Resolve LACE min/target/max with policy as ceiling, not hard requirement."""

    if runtime_mode == "smoke":
        return clamp_lace_budget({"min_cycles": 0, "target_cycles": 0, "max_cycles": 0, "source": "smoke_mode", "early_exit_allowed": True})

    policy_ceiling = extract_lace_policy_ceiling(lace_policy_text) or POLICY_DEFAULT_CEILING
    explicit = normalize_explicit_budget(explicit_config, policy_ceiling=policy_ceiling)
    if explicit is not None:
        return explicit

    audit_budget = budget_from_audit(complexity_audit, policy_ceiling=policy_ceiling)
    if audit_budget is not None:
        return audit_budget

    estimate_budget = budget_from_estimate(complexity_estimate, policy_ceiling=policy_ceiling)
    if estimate_budget is not None:
        active = extract_lace_log_active_cycles(lace_log_text)
        if active and active <= estimate_budget["max_cycles"]:
            estimate_budget["target_cycles"] = max(estimate_budget["min_cycles"], min(active, estimate_budget["max_cycles"]))
            estimate_budget["source"] += "+lace_log_active"
        return estimate_budget

    return clamp_lace_budget(
        {
            "min_cycles": SAFE_FALLBACK_MIN,
            "target_cycles": SAFE_FALLBACK_TARGET,
            "max_cycles": min(policy_ceiling, SAFE_FALLBACK_MAX),
            "source": "safe_fallback",
            "confidence": 35,
            "early_exit_allowed": True,
            "policy_ceiling": policy_ceiling,
        },
        policy_ceiling=policy_ceiling,
    )


def budget_from_audit(audit: dict[str, Any] | None, *, policy_ceiling: int) -> dict[str, Any] | None:
    if not isinstance(audit, dict):
        return None
    if isinstance(audit.get("complexity_audit"), dict):
        audit = audit["complexity_audit"]
    max_cycles = int_value(audit.get("lace_max_cycles"))
    target = int_value(audit.get("lace_target_cycles"))
    minimum = int_value(audit.get("lace_min_cycles"))
    if max_cycles is None and target is None:
        return None
    return clamp_lace_budget(
        {
            "difficulty": normalize_difficulty(str(audit.get("difficulty") or "")) or audit.get("difficulty"),
            "min_cycles": minimum if minimum is not None else 1,
            "target_cycles": target if target is not None else max_cycles,
            "max_cycles": max_cycles if max_cycles is not None else target,
            "early_exit_allowed": audit.get("early_exit_allowed") is not False,
            "quality_threshold": int_value(audit.get("quality_threshold")) or 85,
            "confidence": int_value(audit.get("confidence")) or 40,
            "source": str(audit.get("audit_version") or AUDIT_VERSION),
            "policy_ceiling": policy_ceiling,
        },
        policy_ceiling=policy_ceiling,
    )


def budget_from_estimate(estimate: dict[str, Any] | None, *, policy_ceiling: int) -> dict[str, Any] | None:
    if not isinstance(estimate, dict) or not estimate:
        return None
    if isinstance(estimate.get("complexity_audit"), dict):
        return budget_from_audit(estimate.get("complexity_audit"), policy_ceiling=policy_ceiling)
    difficulty = normalize_difficulty(str(estimate.get("difficulty") or estimate.get("difficulty_label") or "")) or "medio"
    recommended = int_value(estimate.get("recommended_lace_cycles")) or int_value(estimate.get("lace_required_cycles"))
    preset = DIFFICULTY_BUDGETS.get(difficulty, DIFFICULTY_BUDGETS["medio"])
    max_cycles = recommended if recommended is not None else int(preset["lace_max_cycles"])
    if difficulty == "facil":
        minimum, target = 0, min(1, max_cycles)
        max_cycles = min(max_cycles, 2)
    elif difficulty == "medio":
        minimum, target = 2, min(3, max_cycles)
        max_cycles = min(max_cycles, 4)
    elif difficulty == "dificil":
        minimum, target = 3, min(5, max_cycles)
        max_cycles = min(max(max_cycles, target), 7)
    else:
        minimum, target = 5, min(8, max_cycles)
        max_cycles = min(max(max_cycles, target), 10)
    return clamp_lace_budget(
        {
            "difficulty": difficulty,
            "min_cycles": minimum,
            "target_cycles": target,
            "max_cycles": max_cycles,
            "early_exit_allowed": True,
            "quality_threshold": 85,
            "confidence": int_value(estimate.get("confidence")) or 40,
            "source": "complexity_estimate",
            "policy_ceiling": policy_ceiling,
        },
        policy_ceiling=policy_ceiling,
    )


def normalize_explicit_budget(config: dict[str, Any] | None, *, policy_ceiling: int) -> dict[str, Any] | None:
    if not isinstance(config, dict):
        return None
    explicit = int_value(config.get("lace_required_cycles")) or int_value(config.get("required_cycles"))
    if explicit is not None and explicit > 0:
        return clamp_lace_budget(
            {
                "min_cycles": explicit,
                "target_cycles": explicit,
                "max_cycles": explicit,
                "early_exit_allowed": config.get("early_exit_allowed") is not False,
                "quality_threshold": int_value(config.get("quality_threshold")) or 85,
                "source": "explicit_config",
                "policy_ceiling": policy_ceiling,
            },
            policy_ceiling=policy_ceiling,
        )
    keys = ("lace_min_cycles", "lace_target_cycles", "lace_max_cycles")
    if any(key in config for key in keys):
        return clamp_lace_budget(
            {
                "min_cycles": int_value(config.get("lace_min_cycles")) or 0,
                "target_cycles": int_value(config.get("lace_target_cycles")) or int_value(config.get("lace_max_cycles")) or 0,
                "max_cycles": int_value(config.get("lace_max_cycles")) or int_value(config.get("lace_target_cycles")) or 0,
                "early_exit_allowed": config.get("early_exit_allowed") is not False,
                "quality_threshold": int_value(config.get("quality_threshold")) or 85,
                "source": "explicit_config_budget",
                "policy_ceiling": policy_ceiling,
            },
            policy_ceiling=policy_ceiling,
        )
    return None


def clamp_lace_budget(budget: dict[str, Any], *, policy_ceiling: int = POLICY_DEFAULT_CEILING) -> dict[str, Any]:
    ceiling = max(0, min(POLICY_DEFAULT_CEILING, int(policy_ceiling or POLICY_DEFAULT_CEILING)))
    minimum = max(0, int(budget.get("min_cycles") or 0))
    target = max(minimum, int(budget.get("target_cycles") or minimum))
    maximum = max(target, int(budget.get("max_cycles") or target))
    maximum = min(maximum, ceiling)
    target = min(target, maximum)
    minimum = min(minimum, target)
    return {
        **budget,
        "min_cycles": minimum,
        "target_cycles": target,
        "max_cycles": maximum,
        "policy_ceiling": ceiling,
        "policy_ceiling_applied": maximum == ceiling and ceiling < int(budget.get("max_cycles") or maximum),
        "early_exit_allowed": budget.get("early_exit_allowed") is not False,
        "quality_threshold": int(budget.get("quality_threshold") or 85),
    }


def extract_lace_policy_ceiling(text: str) -> int:
    if not text:
        return POLICY_DEFAULT_CEILING
    patterns = (
        r"max(?:imo)?[_\s-]*lace[_\s-]*cycles\s*[:=]\s*(\d+)",
        r"max(?:imo)?\s+(\d+)\s+ciclos",
        r"ciclos\s+1\s+al\s+(\d+)",
        r"(\d+)\s+ciclos\s+obligatorios",
        r"completar\s+(\d+)\s+ciclos",
    )
    for pattern in patterns:
        match = re.search(pattern, normalize_text(text), flags=re.IGNORECASE)
        if match:
            value = int(match.group(1))
            return max(0, min(POLICY_DEFAULT_CEILING, value))
    return POLICY_DEFAULT_CEILING


def extract_lace_log_active_cycles(text: str) -> int | None:
    match = re.search(r"regla activa:\s*(\d+)\s+ciclos", normalize_text(text), flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def difficulty_for_score(score: int) -> str:
    if score <= 20:
        return "facil"
    if score <= 45:
        return "medio"
    if score <= 70:
        return "dificil"
    return "extradificil"


def difficulty_rank(value: str) -> int:
    return {"facil": 1, "medio": 2, "dificil": 3, "extradificil": 4}.get(value, 0)


def normalize_difficulty(value: str) -> str | None:
    text = normalize_text(value).replace(" ", "")
    mapping = {"facil": "facil", "medio": "medio", "dificil": "dificil", "extradificil": "extradificil", "extra": "extradificil"}
    return mapping.get(text)


def confidence_for_audit(reasons: list[str], uncertainty_score: int, history_score: int, project_observed: bool) -> int:
    confidence = 92
    if not project_observed:
        confidence -= 18
    if uncertainty_score > 40:
        confidence -= 18
    elif uncertainty_score > 20:
        confidence -= 8
    if history_score > 50:
        confidence -= 8
    if len(reasons) < 5:
        confidence -= 8
    return max(35, min(95, confidence))


def iter_project_files(root: Path, *, limit: int) -> list[Path]:
    files: list[Path] = []
    try:
        iterator = root.rglob("*")
        for path in iterator:
            if len(files) >= limit:
                break
            if any(part in EXCLUDED_PROJECT_PARTS for part in path.parts):
                continue
            if path.is_file():
                try:
                    files.append(path.relative_to(root))
                except ValueError:
                    files.append(path)
    except OSError:
        return files
    return files


def layer(score: int, reasons: list[str], tools: set[str], flags: set[str]) -> dict[str, Any]:
    return {
        "score": max(0, min(100, int(score))),
        "reasons": reasons,
        "required_tools": sorted(tools),
        "risk_flags": sorted(flags),
    }


def contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
