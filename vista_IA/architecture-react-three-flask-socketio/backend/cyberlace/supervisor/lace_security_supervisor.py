from typing import List, Dict, Any
from cyberlace.core.models import GuardDecision
from cyberlace.core.semantic_firewall import SemanticFirewall


class LACESecuritySupervisor:
    def __init__(self):
        self.firewall = SemanticFirewall()

    def supervise(self, decisions: List[GuardDecision], mode: str = "monitor") -> GuardDecision:
        base = self.firewall.decide(decisions, mode=mode)
        reason_parts = [base.reason]

        critical = [d for d in decisions if d.risk_score >= 76]
        if critical:
            reason_parts.append(f"LACE detectó {len(critical)} señales críticas.")
            base.confidence = min(0.98, max(base.confidence, 0.90))

        if mode == "enforce":
            redact_candidates = [d for d in decisions if d.action in {"REDACT", "SANITIZE_ARGS"} and d.modified_payload is not None]
            if redact_candidates and base.allowed and base.action in {"ALLOW", "MONITOR"}:
                selected = redact_candidates[0]
                base.action = "REDACT"
                base.allowed = True
                base.modified_payload = selected.modified_payload
                reason_parts.append("Payload sensible redactado por guard especializado.")

            if any(d.action in {"REQUIRE_APPROVAL", "HUMAN_REVIEW"} for d in decisions) and base.action not in {"BLOCK", "QUARANTINE"}:
                base.allowed = False
                base.action = "HUMAN_REVIEW"
                reason_parts.append("Guard especializado requiere revision humana.")

            if any(d.action in {"BLOCK", "QUARANTINE"} for d in decisions):
                base.allowed = False
                if base.action not in {"QUARANTINE", "BLOCK"}:
                    base.action = "BLOCK"

        base.reason = " ".join(reason_parts)
        return base
