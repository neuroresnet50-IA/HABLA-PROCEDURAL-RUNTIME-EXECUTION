from typing import Any, Dict, List
from cyberlace.core.models import GuardDecision
from cyberlace.utils.patterns import find_sensitive, redact_sensitive


class MemoryGuard:
    DOMAIN_KEYWORDS = {
        "financial": ["cuenta bancaria", "pin", "cvv", "tarjeta", "banco", "bank", "card"],
        "credential": ["password", "api_key", "token", "secret", "clave", "private key"],
        "private": ["correo", "email", "teléfono", "telefono", "address", "dirección"],
        "technical": ["código", "python", "api", "servidor", "modelo", "dataset"],
        "project": ["proyecto", "arquitectura", "roadmap", "plan"],
        "public": ["idea", "post", "blog", "publicación"],
    }

    def classify_domain(self, text: str) -> str:
        t = (text or "").lower()
        hits = find_sensitive(t)
        if hits:
            domains = {h["domain"] for h in hits}
            if "credential" in domains:
                return "credential"
            if "financial" in domains:
                return "financial"
            if "private" in domains:
                return "private"

        for domain, words in self.DOMAIN_KEYWORDS.items():
            if any(w in t for w in words):
                return domain
        return "public"

    def inspect_read(self, memory_text: str, task_context: Dict[str, Any] | None = None) -> GuardDecision:
        task_context = task_context or {}
        task_domain = task_context.get("task_domain", "general")
        memory_domain = self.classify_domain(memory_text)
        sensitive_hits = find_sensitive(memory_text or "")
        evidence: List[Dict[str, Any]] = []
        risk = 0

        if sensitive_hits:
            evidence.extend({"type": "sensitive_memory", **h} for h in sensitive_hits)
            risk += min(60, 20 * len(sensitive_hits))

        mismatch = memory_domain in {"financial", "credential", "restricted"} and task_domain not in {
            "finance", "security", "credential_management"
        }
        if mismatch:
            evidence.append({
                "type": "context_domain_mismatch",
                "task_domain": task_domain,
                "memory_domain": memory_domain,
            })
            risk += 45

        redacted, redaction_hits = redact_sensitive(memory_text or "")
        action = "ALLOW"
        allowed = True
        modified = memory_text

        if risk >= 80:
            action = "BLOCK"
            allowed = False
            modified = None
        elif sensitive_hits:
            action = "REDACT"
            modified = redacted

        return GuardDecision(
            allowed=allowed,
            action=action,
            risk_score=min(100, risk),
            severity="CRITICAL" if risk >= 76 else "HIGH" if risk >= 51 else "MEDIUM" if risk >= 21 else "LOW",
            category="memory_access",
            reason="Memoria permitida" if allowed else "Memoria bloqueada por dominio sensible incompatible",
            modified_payload=modified,
            evidence=evidence,
            confidence=0.88 if evidence else 0.65,
        )
