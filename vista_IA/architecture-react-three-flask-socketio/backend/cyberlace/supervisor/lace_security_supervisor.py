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

        if any(d.action in {"BLOCK", "QUARANTINE"} for d in decisions) and mode == "enforce":
            base.allowed = False
            if base.action not in {"QUARANTINE", "BLOCK"}:
                base.action = "BLOCK"

        base.reason = " ".join(reason_parts)
        return base
