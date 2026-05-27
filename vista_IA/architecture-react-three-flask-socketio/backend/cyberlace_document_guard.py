"""Hard-stop document scanner for CyberLACE runtime launches.

This guard is intentionally stricter than CyberLACE monitor mode: if a runtime
is about to process local documents that contain credentials or high-risk
financial secrets, Codex must not be launched. Evidence is sanitized so the
secret value is never persisted.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from cyberlace.utils.patterns import find_sensitive
except ImportError:  # pragma: no cover - package import path during unittest.
    from backend.cyberlace.utils.patterns import find_sensitive

MAX_DOCUMENT_SCAN_BYTES = 2_000_000
MAX_REFERENCED_DOCUMENTS = 64
MAX_WORKSPACE_DOCUMENTS = 1_000
MAX_TOTAL_WORKSPACE_SCAN_BYTES = 10_000_000
BLOCK_PATTERNS = {"api_key", "password", "pin", "cvv", "bank_account", "private_key"}
TEXT_SUFFIXES = {
    ".txt", ".md", ".json", ".jsonl", ".yaml", ".yml", ".env", ".ini", ".cfg",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".csv", ".xml",
}
SENSITIVE_TEXT_FILENAMES = {
    ".env", ".npmrc", ".pypirc", ".netrc",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "credentials", "secrets", "secret", "passwords",
}
WORKSPACE_EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".next", ".cache",
    "dist", "build", "coverage", "runtime",
}
TRUSTED_RUNTIME_CONTROL_FILES = {
    "project_state.json",
    "task_queue.json",
    "task_history.jsonl",
    "failures.jsonl",
    "complexity_estimate.json",
}
TRUSTED_RUNTIME_CONTROL_DIRS = {"artifacts", "checkpoints", "directives", "logs"}
PATH_TOKEN_RE = re.compile(
    r"(?<![:A-Za-z0-9])(?P<path>(?:~|[A-Za-z]:)?(?:(?:\.{0,2}/|/)|(?:[A-Za-z0-9_.@+=-]+/))(?:[^\s`'\"<>|;&]+))"
)
SENSITIVE_FILENAME_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.@+=/-])(?P<path>\.env|\.npmrc|\.pypirc|\.netrc|id_rsa|id_dsa|id_ecdsa|id_ed25519|credentials(?:\.[A-Za-z0-9_.-]+)?|secrets(?:\.[A-Za-z0-9_.-]+)?|passwords(?:\.[A-Za-z0-9_.-]+)?)(?![A-Za-z0-9_.@+=/-])",
    re.IGNORECASE,
)
FINANCIAL_CONTEXT_RE = re.compile(r"(?i)\b(card|tarjeta|credit|credito|cr[e\u00e9]dito|cvv|cvc|pin|bank|banco|cuenta)\b")
SECRET_ANCHOR_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:api|token|secret|password|passwd|pwd|credential|"
    r"credencial|key|llave|smtp|imap|mail|correo|github|ghp|pat|openai|"
    r"codex|aws|stripe|paypal|bank|banco|cvv|cvc)(?![A-Za-z0-9])"
)
FRAGMENTED_SECRET_NAME_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:openai|codex|github|ghp|pat|smtp|imap|mail|"
    r"correo|aws|api|token|secret|password|passwd|pwd|key|credential|credencial)"
    r"[A-Za-z0-9_-]{0,64}(?:part|parte|fragment|piece|segment|chunk|alpha|"
    r"beta|gamma|delta|prefix|suffix|middle)(?:[_-]?[A-Za-z0-9]+)?(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])(?:part|parte|fragment|piece|segment|chunk|alpha|beta|"
    r"gamma|delta|prefix|suffix|middle)(?:[_-]?[A-Za-z0-9]+)?[A-Za-z0-9_-]{0,32}"
    r"(?:token|secret|password|passwd|pwd|key|credential|credencial|pat|smtp|api)"
    r"(?![A-Za-z0-9])"
)
REASSEMBLY_CONTEXT_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:reassembl(?:e|y|ing)?|reconstru(?:ir|ccion|"
    r"cci[o\u00f3]n|ct)|rebuild|join|unir|concatenar|base64|decode|"
    r"decodificar|split|dividid[oa]|fragment(?:o|ed|ado)?|pieza|piece|"
    r"segment(?:o)?)(?![A-Za-z0-9])"
)
PAYMENT_DATA_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:tarjeta|targeta|card|credit|credito|cr[e\u00e9]dito|"
    r"debit|debito|d[e\u00e9]bito|pan|cvv|cvc|pin|payment|pago|pagos|"
    r"cliente|clientes)(?![A-Za-z0-9])"
)
PAYMENT_SECRET_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:cvv|cvc|pan|pin|full[_ -]?card|tarjeta[_ -]?completa|"
    r"targeta[_ -]?completa|numero[_ -]?de[_ -]?tarjeta|n[u\u00fa]mero[_ -]?de[_ -]?tarjeta|"
    r"token[_ -]?de[_ -]?seguridad|security[_ -]?token|card[_ -]?number)(?![A-Za-z0-9])"
)
UNSAFE_PAYMENT_ACTION_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:copiar|copy|clonar|duplicar|exportar|extraer|"
    r"enviar|send|email|mandar|subir|upload|guardar|almacenar|store|"
    r"recolectar|capturar|descargar|download|listar|imprimir|compartir)(?![A-Za-z0-9])"
)
UNSAFE_PAYMENT_CHANNEL_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:correo|email|e-mail|gmail|smtp|api|endpoint|webhook|"
    r"nube|cloud|drive|dropbox|slack|telegram|whatsapp|csv|excel|archivo)(?![A-Za-z0-9])"
)
PAYMENT_NEGATION_RE = re.compile(
    r"(?i)(?:\b(?:sin|no|nunca|never|without|evitar|prohibir|prohibido|ni)\b[\s\w,;:-]{0,48})$"
)
EXTERNAL_ACCOUNT_TARGET_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:correo|email|e-mail|gmail|outlook|imap|smtp|mailbox|"
    r"buz[oó]n|mensajes|adjuntos|attachments|inbox)(?![A-Za-z0-9])"
)
UNSAFE_EXTERNAL_LOGIN_ACTION_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:entra|entrar|accede|acceder|login|loggear|loguear|"
    r"iniciar[_ -]?sesi[oó]n|sign[_ -]?in|revisa|revisar|lee|leer|extrae|extraer|"
    r"descarga|descargar|download|scrape|importa|importar)(?![A-Za-z0-9])"
)
EXTERNAL_LOGIN_NEGATION_RE = re.compile(
    r"(?i)(?:\b(?:sin|no|nunca|never|without|evitar|prohibir|prohibido|ni)\b[\s\w,;:-]{0,48})$"
)
PROMPT_INJECTION_CONTROL_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:ignora|ignore|olvida|bypass|desactiva|deshabilita|"
    r"disable|override|sobrescribe|salta|omite|no[_ -]?obedezcas|"
    r"do[_ -]?not[_ -]?follow|jailbreak)(?![A-Za-z0-9])"
)
PROMPT_INJECTION_GUARD_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:cyberlace|guard|seguridad|security|policy|"
    r"pol[ií]tica|safety|sistema|system|instrucciones|instructions|developer|"
    r"runtime)(?![A-Za-z0-9])"
)
PROMPT_INJECTION_HARM_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:exfiltra|exfiltrar|exfiltrate|filtra|leak|"
    r"extrae|extract|sube|upload|env[ií]a|send|secretos?|secrets?|tokens?|"
    r"credenciales|credentials|passwords?|contrase[nñ]as|api[_ -]?keys?|llaves?)(?![A-Za-z0-9])"
)
OBFUSCATED_SECRET_CONTEXT_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:base64|b64|hex|rot13|decode|decodifica|"
    r"decodificar|normaliza|normalizar|encoded|codificado|ofuscado|ofuscaci[oó]n)(?![A-Za-z0-9])"
)
BASE64_BLOB_RE = re.compile(
    r"(?<![A-Za-z0-9+/=_-])(?P<blob>[A-Za-z0-9+/]{24,}={0,2})(?![A-Za-z0-9+/=_-])"
)
HEX_BLOB_RE = re.compile(
    r"(?<![A-Fa-f0-9])(?P<blob>(?:[A-Fa-f0-9]{2}){16,})(?![A-Fa-f0-9])"
)
ROT13_LINE_RE = re.compile(
    r"(?im)^\s*(?:rot13|payload[_ -]?rot13|encoded[_ -]?rot13|codificado[_ -]?rot13)\s*[:=]\s*(?P<blob>[^\r\n]{12,})\s*$"
)

def _safe_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return repr(value)


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def _has_financial_context(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 80): min(len(text), end + 80)]
    return bool(FINANCIAL_CONTEXT_RE.search(window))


def _should_block_hit(hit: Dict[str, Any], text: str) -> bool:
    pattern = str(hit.get("pattern") or "")
    if pattern in BLOCK_PATTERNS:
        return True
    if pattern == "credit_card_like":
        return _has_financial_context(text, int(hit.get("start") or 0), int(hit.get("end") or 0))
    return False


def _sanitize_hit(hit: Dict[str, Any], text: str, *, source: str, path: str | None = None) -> Dict[str, Any]:
    start = int(hit.get("start") or 0)
    return {
        "type": "sensitive_document_content",
        "source": source,
        "path": path,
        "pattern": str(hit.get("pattern") or "unknown"),
        "domain": str(hit.get("domain") or "private"),
        "line": _line_for_offset(text, start),
        "sample": "[REDACTED]",
    }


def _structural_secret_anchor(text: str, match: re.Match[str]) -> bool:
    window = text[max(0, match.start() - 32): min(len(text), match.end() + 32)].lower()
    return any(name in window for name in (
        "checkpoint_key",
        "directive_source_hash",
        "source_hash",
        "schema_version",
    ))


def _nearby_reassembly_context(text: str, anchor: re.Match[str], *, window: int = 160) -> re.Match[str] | None:
    start = max(0, anchor.start() - window)
    end = min(len(text), anchor.end() + window)
    return REASSEMBLY_CONTEXT_RE.search(text[start:end])


def _fragmented_secret_findings(text: str, *, source: str, path: str | None = None) -> List[Dict[str, Any]]:
    """Detect secret material split across names/instructions without storing values."""

    body = text or ""
    if not body.strip() or not SECRET_ANCHOR_RE.search(body):
        return []
    match = FRAGMENTED_SECRET_NAME_RE.search(body)
    if not match:
        for anchor in SECRET_ANCHOR_RE.finditer(body):
            if _structural_secret_anchor(body, anchor):
                continue
            reassembly = _nearby_reassembly_context(body, anchor)
            if reassembly:
                match = anchor if anchor.start() <= reassembly.start() else reassembly
                break
    if not match:
        return []
    return [{
        "type": "fragmented_sensitive_material",
        "source": source,
        "path": path,
        "pattern": "fragmented_secret_reassembly",
        "domain": "private",
        "line": _line_for_offset(body, match.start()),
        "sample": "[REDACTED]",
    }]


def _payment_action_is_negated(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 64):match.start()]
    return bool(PAYMENT_NEGATION_RE.search(prefix))


def _first_unnegated_payment_action(text: str) -> re.Match[str] | None:
    for match in UNSAFE_PAYMENT_ACTION_RE.finditer(text or ""):
        if not _payment_action_is_negated(text or "", match):
            return match
    return None


def _unsafe_payment_intent_findings(text: str, *, source: str, path: str | None = None) -> List[Dict[str, Any]]:
    """Block unsafe operational handling of payment data without blocking safe design talk."""

    body = text or ""
    if not body.strip() or not PAYMENT_DATA_RE.search(body):
        return []
    action = _first_unnegated_payment_action(body)
    secret = PAYMENT_SECRET_RE.search(body)
    channel = UNSAFE_PAYMENT_CHANNEL_RE.search(body)
    if not action or not (secret or channel):
        return []
    marker = action
    return [{
        "type": "unsafe_payment_data_handling_intent",
        "source": source,
        "path": path,
        "pattern": "payment_data_copy_store_or_send",
        "domain": "payment_security",
        "line": _line_for_offset(body, marker.start()),
        "sample": "[REDACTED]",
    }]


def _external_login_action_is_negated(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 64):match.start()]
    return bool(EXTERNAL_LOGIN_NEGATION_RE.search(prefix))


def _first_unnegated_external_login_action(text: str) -> re.Match[str] | None:
    for match in UNSAFE_EXTERNAL_LOGIN_ACTION_RE.finditer(text or ""):
        if not _external_login_action_is_negated(text or "", match):
            return match
    return None


def _unsafe_external_login_intent_findings(text: str, *, source: str, path: str | None = None) -> List[Dict[str, Any]]:
    """Block attempts to log into external accounts or extract mailbox content."""

    body = text or ""
    if not body.strip() or not EXTERNAL_ACCOUNT_TARGET_RE.search(body):
        return []
    action = _first_unnegated_external_login_action(body)
    if not action:
        return []
    return [{
        "type": "external_account_login_attempt",
        "source": source,
        "path": path,
        "pattern": "external_login_or_mailbox_extraction",
        "domain": "account_security",
        "line": _line_for_offset(body, action.start()),
        "sample": "[REDACTED]",
    }]


def _persisted_prompt_injection_findings(text: str, *, source: str, path: str | None = None) -> List[Dict[str, Any]]:
    """Block persisted instructions that try to override safety and exfiltrate data."""

    body = text or ""
    if not body.strip():
        return []
    control = PROMPT_INJECTION_CONTROL_RE.search(body)
    guard = PROMPT_INJECTION_GUARD_RE.search(body)
    harm = PROMPT_INJECTION_HARM_RE.search(body)
    if not (control and guard and harm):
        return []
    marker = min((control, guard, harm), key=lambda item: item.start())
    return [{
        "type": "persisted_prompt_injection_instruction",
        "source": source,
        "path": path,
        "pattern": "safety_bypass_and_exfiltration_instruction",
        "domain": "agent_security",
        "line": _line_for_offset(body, marker.start()),
        "sample": "[REDACTED]",
    }]


def _decoded_text_from_bytes(raw: bytes) -> str | None:
    try:
        decoded = raw.decode("utf-8", errors="ignore")
    except Exception:
        return None
    if len(decoded.strip()) < 8:
        return None
    printable = sum(1 for char in decoded if char.isprintable() or char in "\r\n\t")
    if printable / max(len(decoded), 1) < 0.75:
        return None
    return decoded


def _obfuscated_secret_result(
    decoded: str | None,
    *,
    encoding: str,
    source: str,
    path: str | None,
    line: int,
) -> List[Dict[str, Any]]:
    if not decoded:
        return []
    findings: List[Dict[str, Any]] = []
    for hit in find_sensitive(decoded):
        if _should_block_hit(hit, decoded):
            findings.append({
                "type": "obfuscated_sensitive_material",
                "source": source,
                "path": path,
                "pattern": f"{encoding}_{hit.get('pattern') or 'secret'}",
                "encoding": encoding,
                "domain": str(hit.get("domain") or "private"),
                "line": line,
                "sample": "[REDACTED]",
            })
    if findings:
        return findings
    decoded_has_secret_anchor = SECRET_ANCHOR_RE.search(decoded)
    decoded_has_reassembly = REASSEMBLY_CONTEXT_RE.search(decoded)
    if decoded_has_secret_anchor and decoded_has_reassembly:
        findings.append({
            "type": "obfuscated_sensitive_material",
            "source": source,
            "path": path,
            "pattern": f"{encoding}_secret_reassembly",
            "encoding": encoding,
            "domain": "private",
            "line": line,
            "sample": "[REDACTED]",
        })
    return findings


def _try_base64_decode(blob: str) -> str | None:
    candidate = blob.strip()
    padding = "=" * ((4 - len(candidate) % 4) % 4)
    try:
        raw = base64.b64decode(candidate + padding, validate=True)
    except (binascii.Error, ValueError):
        return None
    return _decoded_text_from_bytes(raw)


def _try_hex_decode(blob: str) -> str | None:
    try:
        raw = bytes.fromhex(blob.strip())
    except ValueError:
        return None
    return _decoded_text_from_bytes(raw)


def _obfuscated_secret_findings(text: str, *, source: str, path: str | None = None) -> List[Dict[str, Any]]:
    """Detect secrets hidden behind base64/hex/rot13 without persisting decoded values."""

    body = text or ""
    if not body.strip() or not OBFUSCATED_SECRET_CONTEXT_RE.search(body):
        return []
    findings: List[Dict[str, Any]] = []
    for match in BASE64_BLOB_RE.finditer(body):
        decoded = _try_base64_decode(match.group("blob"))
        findings.extend(_obfuscated_secret_result(
            decoded,
            encoding="base64",
            source=source,
            path=path,
            line=_line_for_offset(body, match.start()),
        ))
    for match in HEX_BLOB_RE.finditer(body):
        decoded = _try_hex_decode(match.group("blob"))
        findings.extend(_obfuscated_secret_result(
            decoded,
            encoding="hex",
            source=source,
            path=path,
            line=_line_for_offset(body, match.start()),
        ))
    for match in ROT13_LINE_RE.finditer(body):
        decoded = codecs.decode(match.group("blob"), "rot_13")
        findings.extend(_obfuscated_secret_result(
            decoded,
            encoding="rot13",
            source=source,
            path=path,
            line=_line_for_offset(body, match.start()),
        ))
    return findings


def _has_obfuscated_secret_block(findings: List[Dict[str, Any]]) -> bool:
    return any(item.get("type") == "obfuscated_sensitive_material" for item in findings)


def _has_payment_intent_block(findings: List[Dict[str, Any]]) -> bool:
    return any(item.get("type") == "unsafe_payment_data_handling_intent" for item in findings)


def _has_external_login_intent_block(findings: List[Dict[str, Any]]) -> bool:
    return any(item.get("type") == "external_account_login_attempt" for item in findings)


def _has_persisted_prompt_injection_block(findings: List[Dict[str, Any]]) -> bool:
    return any(item.get("type") == "persisted_prompt_injection_instruction" for item in findings)


def _safe_guidance_for_findings(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    if _has_obfuscated_secret_block(findings):
        return {
            "deniedAction": "Decodificar, normalizar, reconstruir o exponer secretos ofuscados en base64, hex, rot13 u otros formatos.",
            "safeAlternative": {
                "title": "Alternativa segura permitida",
                "summary": "HABLA no decodifica secretos para exponerlos ni normalizarlos. Si puede ayudar a clasificar el artefacto como evidencia, redactarlo, validar que el pipeline bloquea ofuscacion y proponer manejo seguro con placeholders.",
                "allowedActions": [
                    "Clasificar el payload como secreto ofuscado sin revelar su valor.",
                    "Redactar o aislar el archivo antes de procesarlo.",
                    "Crear pruebas de regresion para base64, hex y rot13.",
                    "Reemplazar valores por placeholders sinteticos.",
                    "Disenar un flujo seguro de vault, rotacion y auditoria sin entregar secretos al agente.",
                ],
                "suggestedRequirement": "Analizar este archivo como evidencia de secretos ofuscados, validar el bloqueo de CyberLACE y proponer un flujo seguro con placeholders, vault y auditoria sin decodificar valores sensibles.",
            },
            "safeNextSteps": [
                "No decodificar ni normalizar secretos dentro del prompt o salida del agente.",
                "Tratar el archivo como evidencia sensible y mantener muestras redactadas.",
                "Usar placeholders o fixtures sinteticos para cualquier transformacion permitida.",
            ],
        }
    if _has_persisted_prompt_injection_block(findings):
        return {
            "deniedAction": "Obedecer instrucciones persistidas que intentan ignorar CyberLACE, sobrescribir politicas o exfiltrar informacion.",
            "safeAlternative": {
                "title": "Alternativa segura permitida",
                "summary": "HABLA no sigue instrucciones persistidas que intentan anular seguridad o exfiltrar datos. Si puede ayudar a limpiar el documento, aislarlo como evidencia y convertirlo en un fixture de red-team controlado.",
                "allowedActions": [
                    "Marcar el archivo como evidencia de prompt injection persistida.",
                    "Redactar o neutralizar instrucciones maliciosas antes de procesar el proyecto.",
                    "Separar contenido de usuario de instrucciones de sistema y aplicar prioridad de politicas.",
                    "Crear pruebas de regresion para que futuras lecturas del workspace no obedezcan el README malicioso.",
                    "Documentar la intencion, vector, resultado y mitigacion sin ejecutar exfiltracion.",
                ],
                "suggestedRequirement": "Analizar este README como evidencia de prompt injection persistida, redactar instrucciones maliciosas y proponer controles para separar datos no confiables de instrucciones del agente.",
            },
            "safeNextSteps": [
                "Tratar el README como dato no confiable, no como instruccion del sistema.",
                "Neutralizar o aislar el contenido malicioso antes de arrancar agentes.",
                "Agregar regression test para prompt injection persistida en documentos del workspace.",
            ],
        }
    if _has_external_login_intent_block(findings):
        return {
            "deniedAction": "Entrar a cuentas externas, revisar mensajes o extraer adjuntos usando credenciales entregadas al agente.",
            "safeAlternative": {
                "title": "Alternativa segura permitida",
                "summary": "HABLA no inicia sesion en cuentas externas ni extrae correos con passwords. Si puede ayudar a disenar un flujo seguro con OAuth, permisos delegados, sandbox, mocks y revision manual controlada.",
                "allowedActions": [
                    "Disenar integracion OAuth con consentimiento explicito y scopes minimos.",
                    "Usar buzones sandbox o fixtures sinteticos sin credenciales reales.",
                    "Definir un flujo donde el usuario exporta adjuntos manualmente y HABLA procesa solo archivos ya sanitizados.",
                    "Crear validadores de arquitectura, auditoria, rotacion de secretos y almacenamiento en vault.",
                    "Generar plantillas de configuracion con placeholders, nunca con passwords ni tokens.",
                ],
                "suggestedRequirement": "Disenar una integracion segura de correo con OAuth, scopes minimos, sandbox de pruebas, auditoria y procesamiento de adjuntos sanitizados sin entregar passwords al agente.",
            },
            "safeNextSteps": [
                "Retirar passwords, tokens y credenciales del prompt o archivos.",
                "Usar OAuth/sandbox/mocks en vez de login con password.",
                "Procesar solo adjuntos exportados manualmente y sanitizados.",
            ],
        }
    if _has_payment_intent_block(findings):
        return {
            "deniedAction": "Copiar, recolectar, almacenar o enviar PAN/CVV/PIN/tokens de pago por correo, archivos, APIs o canales inseguros.",
            "safeAlternative": {
                "title": "Alternativa segura permitida",
                "summary": "HABLA no ayuda a copiar ni enviar datos de tarjetas/CVV. Si puede ayudar a disenar una arquitectura de pagos donde la aplicacion nunca vea ni almacene CVV, use tokenizacion y envie solo recibos o ultimos 4 digitos.",
                "allowedActions": [
                    "Disenar un flujo PCI-style con tokenizacion de proveedor de pagos.",
                    "Usar enlaces seguros o checkout hospedado por el procesador de pagos.",
                    "Mostrar y enviar solo recibos, IDs de transaccion y ultimos 4 digitos.",
                    "Definir auditoria, cifrado de metadatos y controles de acceso sin manejar PAN/CVV completo.",
                    "Crear validaciones de arquitectura segura y pruebas con datos sinteticos.",
                ],
                "suggestedRequirement": "Disenar una arquitectura segura de pagos con tokenizacion, checkout hospedado, recibos, auditoria y sin almacenar ni enviar PAN/CVV/PIN/tokens por canales inseguros.",
            },
            "safeNextSteps": [
                "Reformular la tarea hacia tokenizacion y proveedor de pagos.",
                "Eliminar cualquier solicitud de copiar, almacenar o enviar PAN/CVV/PIN.",
                "Trabajar solo con datos sinteticos, ultimos 4 digitos y recibos.",
            ],
        }
    return {
        "deniedAction": "Procesar, reconstruir, exponer o transportar informacion sensible detectada por CyberLACE.",
        "safeAlternative": {
            "title": "Alternativa segura permitida",
            "summary": "HABLA puede ayudar a redactar, tokenizar, simular o redisenar el flujo para que los secretos no entren al modelo ni salgan del entorno seguro.",
            "allowedActions": [
                "Usar placeholders o fixtures sinteticos.",
                "Redactar evidencia sensible antes de procesarla.",
                "Disenar controles de acceso, auditoria y rutas seguras.",
                "Convertir la tarea en una validacion de arquitectura segura.",
            ],
            "suggestedRequirement": "Redisenar la tarea para usar datos sinteticos o redactados y validar una arquitectura segura sin procesar secretos reales.",
        },
        "safeNextSteps": [
            "Retirar documentos o valores sensibles del alcance.",
            "Usar datos sinteticos o redactados.",
            "Solicitar una revision de arquitectura segura.",
        ],
    }


def _inspect_text(text: str, *, source: str, path: str | None = None) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for hit in find_sensitive(text or ""):
        if _should_block_hit(hit, text or ""):
            findings.append(_sanitize_hit(hit, text or "", source=source, path=path))
    findings.extend(_fragmented_secret_findings(text or "", source=source, path=path))
    findings.extend(_unsafe_payment_intent_findings(text or "", source=source, path=path))
    findings.extend(_unsafe_external_login_intent_findings(text or "", source=source, path=path))
    findings.extend(_persisted_prompt_injection_findings(text or "", source=source, path=path))
    findings.extend(_obfuscated_secret_findings(text or "", source=source, path=path))
    return findings


def _walk_values(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _walk_values(item)
        return
    yield str(value)


def _extract_path_tokens(text: str) -> List[str]:
    tokens: List[str] = []
    for pattern in (PATH_TOKEN_RE, SENSITIVE_FILENAME_TOKEN_RE):
        for match in pattern.finditer(text or ""):
            token = match.group("path").strip().strip("`'\"()[]{}<>.,;:")
            if not token or "://" in token:
                continue
            if token not in tokens:
                tokens.append(token)
    return tokens


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_display_path(path: Path, *, repo: Path, project_root: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        try:
            return path.relative_to(project_root).as_posix()
        except ValueError:
            return path.name


def _is_generated_runtime_control_reference(path: Path, roots: List[Path], *, source: str) -> bool:
    if source not in {"task", "directive"}:
        return False
    for root in roots:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        parts = relative.parts
        for index, part in enumerate(parts[:-1]):
            if part != "runtime":
                continue
            next_part = parts[index + 1]
            if index + 2 == len(parts) and next_part in TRUSTED_RUNTIME_CONTROL_FILES:
                return True
            if next_part in TRUSTED_RUNTIME_CONTROL_DIRS:
                return True
    return False


def _external_reference_finding(token: str, *, source: str) -> Dict[str, Any]:
    raw_name = Path(token.replace("~", "")).name or "external"
    return {
        "type": "external_document_reference_denied",
        "source": source,
        "path": f"external:{raw_name}",
        "pattern": "external_path",
        "domain": "filesystem",
        "line": 1,
        "sample": "[REDACTED]",
    }


def _scan_limit_finding(*, reason: str, path: str | None = None) -> Dict[str, Any]:
    return {
        "type": "workspace_scan_incomplete",
        "source": "workspace_preflight",
        "path": path,
        "pattern": reason,
        "domain": "filesystem",
        "line": 1,
        "sample": "[REDACTED]",
    }


def _is_text_document(path: Path) -> bool:
    name = path.name.lower()
    return name in SENSITIVE_TEXT_FILENAMES or path.suffix.lower() in TEXT_SUFFIXES


def _read_text_document(path: Path) -> str | None:
    if not _is_text_document(path):
        return None
    try:
        if path.stat().st_size > MAX_DOCUMENT_SCAN_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _inspect_document(path: Path, *, source: str, display_path: str) -> tuple[List[Dict[str, Any]], Dict[str, Any] | None]:
    if not _is_text_document(path):
        return [], None
    try:
        size = path.stat().st_size
    except OSError:
        return [_scan_limit_finding(reason="document_stat_failed", path=display_path)], None
    if size > MAX_DOCUMENT_SCAN_BYTES:
        return [_scan_limit_finding(reason="document_too_large", path=display_path)], {
            "path": display_path,
            "bytes": size,
            "blockedFindings": 1,
            "skipped": True,
            "reason": "document_too_large",
        }
    text = _read_text_document(path)
    if text is None:
        return [_scan_limit_finding(reason="document_read_failed", path=display_path)], None
    doc_findings = _inspect_text(text, source=source, path=display_path)
    return doc_findings, {
        "path": display_path,
        "bytes": size,
        "blockedFindings": len(doc_findings),
    }


def _resolve_referenced_path(token: str, roots: List[Path]) -> Path | None:
    raw = token.strip().strip("`'\"()[]{}<>.,;:")
    if not raw or "://" in raw:
        return None
    candidate = Path(raw).expanduser()
    resolved_roots = [root.resolve() for root in roots]
    candidates: List[Path]
    if candidate.is_absolute():
        candidates = [candidate]
    else:
        candidates = [root / candidate for root in resolved_roots]
    for item in candidates:
        try:
            resolved = item.resolve()
        except OSError:
            continue
        if not any(_is_relative_to(resolved, root) for root in resolved_roots):
            continue
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _path_escapes_roots(path: Path, roots: List[Path]) -> bool:
    return not any(_is_relative_to(path, root) for root in roots)


def _meaningful_external_absolute_path(token: str) -> bool:
    raw = token.strip()
    if raw.startswith("~/") or raw.startswith("../") or bool(re.match(r"^[A-Za-z]:[\\/]", raw)):
        return True
    if not raw.startswith("/"):
        return False
    normalized = raw.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    name = parts[-1].lower() if parts else ""
    has_sensitive_name = name in SENSITIVE_TEXT_FILENAMES or name.startswith("id_")
    has_suffix = bool(Path(normalized).suffix)
    if normalized.startswith(("/home/", "/Users/")):
        return len(parts) >= 4 or has_sensitive_name or has_suffix
    if normalized.startswith("/root/"):
        return len(parts) >= 3 or has_sensitive_name or has_suffix
    if normalized.startswith("/etc/"):
        return len(parts) >= 2
    if normalized.startswith(("/var/", "/tmp/", "/mnt/", "/media/", "/opt/", "/srv/")):
        return len(parts) >= 3 or has_sensitive_name or has_suffix
    return len(parts) >= 2 and has_suffix


def _looks_like_external_path(token: str) -> bool:
    return _meaningful_external_absolute_path(token)


def _collect_paths_for_text(text: str, roots: List[Path], *, source: str) -> tuple[List[Path], List[Dict[str, Any]]]:
    resolved: List[Path] = []
    denied: List[Dict[str, Any]] = []
    seen: set[str] = set()
    resolved_roots = [root.resolve() for root in roots]
    for token in _extract_path_tokens(text):
        raw = token.strip().strip("`'\"()[]{}<>.,;:")
        candidate = Path(raw).expanduser()
        if candidate.is_absolute():
            if not _meaningful_external_absolute_path(raw):
                continue
            try:
                absolute_candidate = candidate.resolve()
            except OSError:
                absolute_candidate = candidate
            if _path_escapes_roots(absolute_candidate, resolved_roots):
                denied.append(_external_reference_finding(raw, source=source))
                continue
        elif _looks_like_external_path(raw):
            denied.append(_external_reference_finding(raw, source=source))
            continue
        path = _resolve_referenced_path(raw, roots)
        if path is None:
            continue
        if _is_generated_runtime_control_reference(path, resolved_roots, source=source):
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(path)
        if len(resolved) >= MAX_REFERENCED_DOCUMENTS:
            denied.append(_scan_limit_finding(reason="referenced_document_limit_exceeded"))
            return resolved, denied
    return resolved, denied


def _workspace_document_paths(project_root: Path) -> Iterable[Path]:
    if not project_root.exists() or not project_root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [
            dirname for dirname in dirnames
            if dirname not in WORKSPACE_EXCLUDED_DIRS and not dirname.endswith(".egg-info")
        ]
        for filename in filenames:
            path = Path(dirpath) / filename
            if _is_text_document(path):
                yield path


def _inspect_workspace_documents(
    project_root: Path,
    *,
    repo: Path,
    already_scanned: set[str],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    scanned_documents: List[Dict[str, Any]] = []
    scanned_count = 0
    scanned_bytes = 0
    incomplete_reason: str | None = None

    for path in _workspace_document_paths(project_root):
        try:
            resolved = path.resolve()
        except OSError:
            continue
        key = str(resolved)
        if key in already_scanned:
            continue
        display_path = _safe_display_path(resolved, repo=repo, project_root=project_root)
        try:
            size = resolved.stat().st_size
        except OSError:
            findings.append(_scan_limit_finding(reason="document_stat_failed", path=display_path))
            continue
        if scanned_count >= MAX_WORKSPACE_DOCUMENTS:
            incomplete_reason = "workspace_document_limit_exceeded"
            break
        if scanned_bytes + size > MAX_TOTAL_WORKSPACE_SCAN_BYTES:
            incomplete_reason = "workspace_byte_limit_exceeded"
            break
        doc_findings, info = _inspect_document(resolved, source="workspace_document", display_path=display_path)
        scanned_count += 1
        scanned_bytes += min(size, MAX_DOCUMENT_SCAN_BYTES)
        findings.extend(doc_findings)
        if info and (doc_findings or len(scanned_documents) < 120):
            scanned_documents.append(info)

    if incomplete_reason:
        findings.append(_scan_limit_finding(reason=incomplete_reason, path=project_root.name))

    return findings, scanned_documents, {
        "documents": scanned_count,
        "bytes": scanned_bytes,
        "incomplete": bool(incomplete_reason),
        "incompleteReason": incomplete_reason,
    }


def inspect_runtime_document_inputs(
    *,
    requirement: str,
    project_dir: str | Path,
    repo_root: str | Path,
    task: Dict[str, Any] | None = None,
    directive: Dict[str, Any] | None = None,
    session_id: str | None = None,
    project_slug: str | None = None,
    scan_workspace: bool = True,
) -> Dict[str, Any]:
    """Inspect prompt/task/directive text, referenced documents, and workspace docs.

    Returns a sanitized CyberLACE-style decision. ``blocked=True`` is a hard stop
    and must be enforced regardless of global CyberLACE monitor/enforce mode.
    """

    project_root = Path(project_dir).resolve()
    repo = Path(repo_root).resolve()
    roots = [project_root, repo]
    text_sources: List[tuple[str, str]] = [("requirement", str(requirement or ""))]
    if task:
        text_sources.append(("task", _safe_string(task)))
    if directive:
        rendered = str(directive.get("rendered_instruction") or "") if isinstance(directive, dict) else ""
        text_sources.append(("directive", rendered or _safe_string(directive)))

    findings: List[Dict[str, Any]] = []
    for source, text in text_sources:
        findings.extend(_inspect_text(text, source=source))

    referenced_paths: List[Path] = []
    seen_paths: set[str] = set()
    for source, text in text_sources:
        paths, denied = _collect_paths_for_text(text, roots, source=source)
        findings.extend(denied)
        for path in paths:
            key = str(path)
            if key not in seen_paths:
                seen_paths.add(key)
                referenced_paths.append(path)

    scanned_documents: List[Dict[str, Any]] = []
    already_scanned: set[str] = set()
    for path in referenced_paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        display_path = _safe_display_path(resolved, repo=repo, project_root=project_root)
        doc_findings, info = _inspect_document(resolved, source="referenced_document", display_path=display_path)
        already_scanned.add(str(resolved))
        findings.extend(doc_findings)
        if info:
            scanned_documents.append(info)

    workspace_summary = {"documents": 0, "bytes": 0, "incomplete": False, "incompleteReason": None}
    if scan_workspace:
        workspace_findings, workspace_scanned, workspace_summary = _inspect_workspace_documents(
            project_root,
            repo=repo,
            already_scanned=already_scanned,
        )
        findings.extend(workspace_findings)
        scanned_documents.extend(workspace_scanned)

    blocked = bool(findings)
    evidence_documents = [
        item for item in scanned_documents
        if item.get("blockedFindings") or item.get("skipped") or item.get("reason")
    ][:24]
    safe_guidance = _safe_guidance_for_findings(findings) if blocked else {}
    obfuscated_block = _has_obfuscated_secret_block(findings)
    prompt_injection_block = _has_persisted_prompt_injection_block(findings)
    login_block = _has_external_login_intent_block(findings)
    payment_block = _has_payment_intent_block(findings)
    reason = (
        "CyberLACE blocked obfuscated secret material: encoded payloads decoded to sensitive credentials and must not be normalized or exposed."
        if obfuscated_block
        else "CyberLACE blocked persisted prompt injection: workspace content attempted to override safety policy and exfiltrate information."
        if prompt_injection_block
        else "CyberLACE blocked external account login intent: agents must not use provided passwords to enter mailboxes, review messages, or extract attachments."
        if login_block
        else "CyberLACE blocked unsafe payment-data handling intent: copying, collecting, storing or sending card/CVV/PIN/token data is denied. A safe tokenized payment architecture can be designed instead."
        if payment_block
        else "CyberLACE hard gate blocked local document processing: sensitive credentials, financial secrets, unsafe external path references, or unscannable workspace documents were found."
        if blocked
        else "CyberLACE hard gate found no blocking sensitive document content."
    )
    return {
        "ok": True,
        "recordType": "decision",
        "mode": "hard-gate",
        "stage": "document-preflight",
        "agentId": "cyberlace-document-guard",
        "sessionId": session_id,
        "projectSlug": project_slug,
        "action": "QUARANTINE" if blocked else "ALLOW",
        "runtimeAction": "QUARANTINE" if blocked else "ALLOW",
        "allowed": not blocked,
        "blocked": blocked,
        "blocksRuntime": blocked,
        "requiresHumanReview": False,
        "redactsPayload": False,
        "riskScore": 100.0 if blocked else 0.0,
        "severity": "CRITICAL" if blocked else "LOW",
        "reason": reason,
        "message": (
            "PELIGRO: secreto ofuscado detectado. HABLA puede ayudar a clasificar y redactar la evidencia sin decodificar ni exponer valores."
            if obfuscated_block
            else "PELIGRO: prompt injection persistida negada. HABLA puede ayudar a aislar, redactar y convertir el documento en evidencia segura."
            if prompt_injection_block
            else "PELIGRO: intento de login externo negado. HABLA puede ayudar con una alternativa segura basada en OAuth, sandbox, mocks y adjuntos sanitizados."
            if login_block
            else "PELIGRO: accion financiera insegura negada. HABLA puede ayudar con una alternativa segura basada en tokenizacion, recibos y arquitectura PCI-style."
            if payment_block
            else "PELIGRO: potencial informacion insegura. La accion fue negada y no se lanzara Codex."
            if blocked
            else "Documentos verificados."
        ),
        "deniedAction": safe_guidance.get("deniedAction"),
        "safeAlternative": safe_guidance.get("safeAlternative"),
        "safeNextSteps": safe_guidance.get("safeNextSteps") or [],
        "evidence": findings[:24],
        "blockedPaths": sorted({str(item.get("path")) for item in findings if item.get("path")}),
        "scannedDocuments": evidence_documents,
        "scannedDocumentCount": len(scanned_documents),
        "workspaceScan": workspace_summary,
    }
