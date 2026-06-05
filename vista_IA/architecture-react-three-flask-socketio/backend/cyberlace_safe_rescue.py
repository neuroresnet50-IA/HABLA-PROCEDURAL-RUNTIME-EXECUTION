"""CyberLACE safety rescue helpers for blocked natural-language prompts.

The rescue flow never authorizes the blocked prompt. It explains the block in
human language, proposes a safer prompt, and records whether the human accepted
that safe rewrite.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

try:
    from cyberlace_integration import cyberlace_paths
except ImportError:  # pragma: no cover - package import path during unittest.
    from backend.cyberlace_integration import cyberlace_paths

_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd|token|secret|api[_-]?key|authorization)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)\b(?:sk|ghp|github_pat|xox[baprs])-?[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
]

_SAFE_DEFAULT_PROMPT = (
    "Continuar el proyecto con una version segura del requerimiento: conservar "
    "la intencion funcional permitida, excluir secretos, credenciales, bypasses "
    "de seguridad y acciones destructivas, y ejecutar solo cambios verificables "
    "dentro del workspace autorizado."
)

_CONFIRMATIONS = {
    "CONTINUAR_SEGURO",
    "SAFE_REWRITE",
    "HUMAN_REVIEW",
    "EDIT_SAFE_PROMPT",
    "AUTONOMOUS_SAFE_REWRITE",
}

_DEFAULT_LOCAL_RESCUE_PIN = "7319"


def _configured_rescue_pin() -> str:
    return str(os.environ.get("CYBERLACE_RESCUE_PIN") or os.environ.get("VISTA_SECURITY_PIN") or _DEFAULT_LOCAL_RESCUE_PIN).strip()


def _validate_rescue_pin(value: str) -> bool:
    configured = _configured_rescue_pin()
    if not configured:
        return False
    return hmac.compare_digest(str(value or "").strip(), configured)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_json_safe(dict(payload)), ensure_ascii=False, sort_keys=True) + "\n")


def _evidence_path() -> Path:
    return Path(cyberlace_paths()["evidence"]) / "cyberlace_safe_rewrites.jsonl"


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _redact_text(value: str, limit: int = 520) -> str:
    value = str(value or "")
    value = value.replace("\n", " ").strip()
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    if len(value) > limit:
        return value[:limit].rstrip() + "..."
    return value


def _safe_list(value: Any, limit: int = 6) -> List[str]:
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value[:limit]:
        if isinstance(item, Mapping):
            reason = item.get("reason") or item.get("message") or item.get("path") or item.get("type")
            result.append(_redact_text(str(reason or item), limit=160))
        else:
            result.append(_redact_text(str(item), limit=160))
    return result


def _normalize_decision(decision: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(decision, Mapping):
        return {}
    return dict(decision)


def _extract_safe_alternative(decision: Mapping[str, Any]) -> Dict[str, Any]:
    for key in ("safeAlternative", "safe_alternative", "rewrite", "safeRewrite"):
        value = decision.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    return {}


def _extract_evidence(decision: Mapping[str, Any]) -> List[str]:
    evidence = _safe_list(decision.get("evidence"))
    evidence.extend(_safe_list(decision.get("blockedPaths")))
    evidence.extend(_safe_list(decision.get("matches")))
    return evidence[:8]


def _blocked_reason_kind(decision: Mapping[str, Any], prompt: str) -> str:
    joined = " ".join(
        str(decision.get(key) or "")
        for key in ("reason", "runtimeAction", "action", "deniedAction", "blockedCategory")
    ).lower()
    joined = f"{joined} {prompt.lower()}"
    if any(token in joined for token in ("secret", "token", "password", "credential", "exfil")):
        return "secrets_or_exfiltration"
    if any(token in joined for token in ("bypass", "disable safety", "sin seguridad", "quarantine")):
        return "policy_bypass_or_ambiguous_control"
    if any(token in joined for token in ("delete", "destroy", "rm -rf", "wipe", "blanquear")):
        return "destructive_or_high_impact"
    return "ambiguous_or_high_risk_language"


def _human_explanation(kind: str, action: str) -> Dict[str, str]:
    reasons = {
        "secrets_or_exfiltration": (
            "CyberLACE detecto lenguaje compatible con secretos, credenciales o salida de datos sensibles. "
            "Por politica, el texto original no se entrega al worker ni se reintenta automaticamente."
        ),
        "policy_bypass_or_ambiguous_control": (
            "CyberLACE detecto una peticion que puede interpretarse como bypass de controles, cuarentena o reglas de seguridad. "
            "Eso no significa que el proyecto termino; significa que la intencion debe reformularse como una tarea segura."
        ),
        "destructive_or_high_impact": (
            "CyberLACE detecto una accion destructiva o de alto impacto. Antes de continuar, el sistema necesita una version segura, trazable y verificable."
        ),
        "ambiguous_or_high_risk_language": (
            "CyberLACE detecto lenguaje ambiguo o demasiado determinista para una accion sensible. La tarea queda pausada hasta usar una version segura del prompt."
        ),
    }
    action_label = str(action or "QUARANTINE").upper()
    return {
        "title": "Mensaje de CyberLACE",
        "intro": (
            "No te alarmes: CyberLACE es el nucleo runtime de seguridad y acaba de proteger el proceso. "
            "El bloqueo no significa que el trabajo se perdio ni que no podamos continuar."
        ),
        "why": reasons.get(kind, reasons["ambiguous_or_high_risk_language"]),
        "nextStep": (
            "Puedes escribir tu PIN de contexto y oprimir el boton verde Continuar con prompt seguro. "
            "CyberLACE mantendra bloqueado el texto original, creara P_safe sin partes sensibles "
            "y el runtime continuara con evidencia auditable."
        ),
        "actionSummary": f"Decision aplicada: {action_label}. Worker original denegado; ruta segura disponible solo con confirmacion humana.",
    }


def _safe_prompt_has_cyberlace_contract(safe_prompt: str) -> bool:
    normalized = str(safe_prompt or "").lower()
    required_markers = (
        "[prompt seguro generado por cyberlace]",
        "no ejecutar el prompt original bloqueado",
        "reglas de continuacion segura",
    )
    return all(marker in normalized for marker in required_markers)


def _acceptance_is_autonomous_safe_rewrite(acceptance_type: str, confirmation: str, safe_prompt: str) -> bool:
    acceptance = str(acceptance_type or "").strip().lower()
    confirm = str(confirmation or "").strip().upper()
    return (
        acceptance == "autonomous_safe_rewrite"
        and confirm in {"SAFE_REWRITE", "AUTONOMOUS_SAFE_REWRITE", "CONTINUAR_SEGURO"}
        and _safe_prompt_has_cyberlace_contract(safe_prompt)
    )


def _build_safe_prompt(decision: Mapping[str, Any], project_slug: str, source_session_id: str) -> str:
    safe_alt = _extract_safe_alternative(decision)
    candidate = (
        safe_alt.get("suggestedRequirement")
        or safe_alt.get("safePrompt")
        or safe_alt.get("prompt")
        or decision.get("safePrompt")
        or decision.get("rewritePrompt")
    )
    body = _redact_text(str(candidate or _SAFE_DEFAULT_PROMPT), limit=1600)
    project_line = f"Proyecto: {project_slug}" if project_slug else "Proyecto: actual"
    session_line = f"Sesion origen: {source_session_id}" if source_session_id else "Sesion origen: runtime actual"
    return "\n".join(
        [
            "[PROMPT SEGURO GENERADO POR CYBERLACE]",
            project_line,
            session_line,
            "",
            body,
            "",
            "Reglas de continuacion segura:",
            "- No ejecutar el prompt original bloqueado.",
            "- No incluir secretos, credenciales, bypasses ni acciones destructivas no verificadas.",
            "- Mantener cambios dentro del workspace autorizado.",
            "- Validar por filesystem y registrar evidencia antes de completed=true.",
        ]
    )


def build_cyberlace_rescue(
    *,
    decision: Optional[Mapping[str, Any]],
    prompt: str,
    project_slug: str = "",
    source_session_id: str = "",
    user_id: str = "local-human",
) -> Dict[str, Any]:
    """Build and persist a safe rewrite proposal for a blocked CyberLACE prompt."""

    normalized = _normalize_decision(decision)
    prompt = str(prompt or "")
    action = normalized.get("runtimeAction") or normalized.get("action") or "QUARANTINE"
    kind = _blocked_reason_kind(normalized, prompt)
    safe_prompt = _build_safe_prompt(normalized, project_slug, source_session_id)
    rescue_id = f"CYBERLACE-RESCUE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    record = {
        "recordType": "cyberlace_safe_rewrite_proposed",
        "timestamp": _utc_now(),
        "rescueId": rescue_id,
        "projectSlug": project_slug,
        "sourceSessionId": source_session_id,
        "userId": user_id,
        "runtimeAction": action,
        "riskScore": normalized.get("riskScore"),
        "reasonKind": kind,
        "reason": _redact_text(str(normalized.get("reason") or ""), limit=320),
        "originalPromptHash": _hash_text(prompt),
        "originalPromptPreview": _redact_text(prompt),
        "safePromptHash": _hash_text(safe_prompt),
        "hardBlockStillEnforced": True,
        "requiresHumanConfirmation": True,
        "confirmationCode": "CONTINUAR_SEGURO",
        "pinRequired": True,
        "authMethod": "cyberlace_context_pin",
        "redactedEvidence": _extract_evidence(normalized),
    }
    _append_jsonl(_evidence_path(), record)
    human_message = _human_explanation(kind, str(action))
    return {
        "ok": True,
        **record,
        "humanMessage": human_message,
        "safePrompt": safe_prompt,
        "safeAlternative": {
            "rescueId": rescue_id,
            "label": "Continuar con prompt seguro",
            "suggestedRequirement": safe_prompt,
            "safePrompt": safe_prompt,
            "requiresHumanConfirmation": True,
            "confirmationCode": "CONTINUAR_SEGURO",
            "pinRequired": True,
            "authMethod": "cyberlace_context_pin",
            "hardBlockStillEnforced": True,
            "originalPromptHash": record["originalPromptHash"],
            "originalPromptPreview": record["originalPromptPreview"],
        },
        "safeNextSteps": [
            "Continuar con prompt seguro",
            "Editar prompt seguro antes de lanzar",
            "Pedir revision humana si el bloqueo no es claro",
        ],
    }


def record_cyberlace_rescue_acceptance(
    *,
    rescue_id: str,
    safe_prompt: str,
    project_slug: str = "",
    source_session_id: str = "",
    user_id: str = "local-human",
    confirmation: str = "",
    acceptance_type: str = "continue_safe",
    rescue_pin: str = "",
) -> Dict[str, Any]:
    """Persist human acceptance of P_safe. The blocked source prompt remains blocked."""

    confirmation = str(confirmation or "").strip().upper()
    safe_prompt = str(safe_prompt or "").strip()
    if confirmation not in _CONFIRMATIONS:
        result = {
            "ok": False,
            "status": "blocked",
            "reason": "human_confirmation_required",
            "message": "Para continuar se requiere confirmar CONTINUAR_SEGURO sobre P_safe. El prompt original sigue bloqueado.",
            "hardBlockStillEnforced": True,
        }
        _append_jsonl(_evidence_path(), {"recordType": "cyberlace_safe_rewrite_rejected", "timestamp": _utc_now(), **result})
        return result
    if not safe_prompt:
        result = {
            "ok": False,
            "status": "blocked",
            "reason": "safe_prompt_empty",
            "message": "No hay P_safe para ejecutar. El prompt original sigue bloqueado.",
            "hardBlockStillEnforced": True,
        }
        _append_jsonl(_evidence_path(), {"recordType": "cyberlace_safe_rewrite_rejected", "timestamp": _utc_now(), **result})
        return result
    autonomous_safe_rewrite = _acceptance_is_autonomous_safe_rewrite(acceptance_type, confirmation, safe_prompt)
    if not autonomous_safe_rewrite:
        if not str(rescue_pin or "").strip():
            result = {
                "ok": False,
                "status": "blocked",
                "reason": "context_pin_required",
                "message": "CyberLACE requiere PIN de contexto para continuar con P_safe. El prompt original sigue bloqueado.",
                "hardBlockStillEnforced": True,
                "pinAuthenticated": False,
                "authMethod": "cyberlace_context_pin",
            }
            _append_jsonl(_evidence_path(), {"recordType": "cyberlace_safe_rewrite_rejected", "timestamp": _utc_now(), **result})
            return result
        if not _validate_rescue_pin(rescue_pin):
            result = {
                "ok": False,
                "status": "blocked",
                "reason": "context_pin_invalid",
                "message": "PIN de contexto invalido. CyberLACE no continuara con P_safe y el prompt original sigue bloqueado.",
                "hardBlockStillEnforced": True,
                "pinAuthenticated": False,
                "authMethod": "cyberlace_context_pin",
            }
            _append_jsonl(_evidence_path(), {"recordType": "cyberlace_safe_rewrite_rejected", "timestamp": _utc_now(), **result})
            return result

    auth_method = "cyberlace_autonomous_safe_rewrite" if autonomous_safe_rewrite else "cyberlace_context_pin"
    record = {
        "recordType": "cyberlace_safe_rewrite_accepted",
        "timestamp": _utc_now(),
        "rescueId": rescue_id or f"CYBERLACE-RESCUE-{uuid.uuid4().hex[:8]}",
        "projectSlug": project_slug,
        "sourceSessionId": source_session_id,
        "userId": user_id,
        "acceptanceType": acceptance_type,
        "safePromptHash": _hash_text(safe_prompt),
        "safePrompt": safe_prompt,
        "hardBlockStillEnforced": True,
        "confirmation": confirmation,
        "pinAuthenticated": not autonomous_safe_rewrite,
        "autonomousSafeRewrite": autonomous_safe_rewrite,
        "authMethod": auth_method,
    }
    _append_jsonl(_evidence_path(), record)
    return {
        "ok": True,
        "status": "accepted",
        "message": (
            "P_safe confirmado por politica autonoma segura. El prompt original sigue bloqueado y solo se ejecuta la version segura."
            if autonomous_safe_rewrite
            else "P_safe confirmado con PIN de contexto. El prompt original sigue bloqueado y solo se puede ejecutar la version segura."
        ),
        "hardBlockStillEnforced": True,
        "pinAuthenticated": not autonomous_safe_rewrite,
        "autonomousSafeRewrite": autonomous_safe_rewrite,
        "authMethod": auth_method,
        **record,
    }
