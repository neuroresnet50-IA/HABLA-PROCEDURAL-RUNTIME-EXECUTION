from typing import Any, Dict, List
from cyberlace.core.models import GuardDecision
from cyberlace.utils.patterns import find_sensitive, redact_sensitive


class OutputGuard:
    def inspect_output(self, output: str, context: Dict[str, Any] | None = None) -> GuardDecision:
        context = context or {}
        hits = find_sensitive(output or "")
        evidence: List[Dict[str, Any]] = [{"type": "sensitive_output", **h} for h in hits]
        risk = min(100, 25 * len(hits))
        redacted, _ = redact_sensitive(output or "")

        action = "ALLOW"
        allowed = True
        modified = output

        if hits:
            action = "REDACT"
            modified = redacted

        if risk >= 90:
            action = "BLOCK"
            allowed = False
            modified = None

        return GuardDecision(
            allowed=allowed,
            action=action,
            risk_score=risk,
            severity="CRITICAL" if risk >= 76 else "HIGH" if risk >= 51 else "MEDIUM" if risk >= 21 else "LOW",
            category="output_validation",
            reason="Salida validada" if not hits else "Salida contenía datos sensibles y fue redactada",
            modified_payload=modified,
            evidence=evidence,
            confidence=0.90 if evidence else 0.60,
        )
