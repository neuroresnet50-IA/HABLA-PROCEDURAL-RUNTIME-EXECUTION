from pathlib import Path
import re
from typing import Dict, List, Tuple, Any
import yaml


DEFAULT_PATTERNS = {
    "api_key": {"regex": r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}", "domain": "credential"},
    "password": {"regex": r"(?i)(password|passwd|contraseña|clave)\s*[:=]\s*['\"]?[^\s,'\"]{4,}", "domain": "credential"},
    "pin": {"regex": r"(?i)\b(pin)\b\s*[:=]?\s*\d{4,6}\b", "domain": "financial"},
    "cvv": {"regex": r"(?i)\b(cvv|cvc)\b\s*[:=]?\s*\d{3,4}\b", "domain": "financial"},
    "credit_card_like": {"regex": r"\b(?:\d[ -]*?){13,19}\b", "domain": "financial"},
    "bank_account": {"regex": r"(?i)(cuenta bancaria|account number|número de cuenta|numero de cuenta)\s*[:=]?\s*\d{6,20}", "domain": "financial"},
    "private_key": {"regex": r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "domain": "credential"},
    "email": {"regex": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "domain": "private"},
}


def load_patterns(path: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
    if path and Path(path).exists():
        with Path(path).open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("patterns", DEFAULT_PATTERNS)
    return DEFAULT_PATTERNS


def find_sensitive(text: str, patterns: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    patterns = patterns or DEFAULT_PATTERNS
    hits = []
    text = text or ""
    for name, item in patterns.items():
        regex = item["regex"]
        for match in re.finditer(regex, text):
            hits.append({
                "pattern": name,
                "domain": item.get("domain", "private"),
                "start": match.start(),
                "end": match.end(),
                "sample": text[match.start():match.end()][:80],
            })
    return hits


def redact_sensitive(text: str, patterns: Dict[str, Dict[str, Any]] | None = None) -> Tuple[str, List[Dict[str, Any]]]:
    patterns = patterns or DEFAULT_PATTERNS
    hits = find_sensitive(text, patterns)
    redacted = text or ""
    for hit in sorted(hits, key=lambda x: x["start"], reverse=True):
        label = f"[REDACTED_{hit['domain'].upper()}]"
        redacted = redacted[:hit["start"]] + label + redacted[hit["end"]:]
    return redacted, hits
