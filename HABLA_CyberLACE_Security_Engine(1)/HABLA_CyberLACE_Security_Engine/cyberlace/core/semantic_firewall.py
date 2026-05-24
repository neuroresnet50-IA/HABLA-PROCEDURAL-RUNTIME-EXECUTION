from typing import Dict, Any, List
from cyberlace.core.models import GuardDecision


class SemanticFirewall:
    def decide(self, decisions: List[GuardDecision], mode: str = "monitor") -> GuardDecision:
        if not decisions:
            return GuardDecision(
                allowed=True,
                action="ALLOW",
                risk_score=0,
                severity="LOW",
                reason="Sin señales de riesgo",
                category="semantic_firewall",
            )

        max_risk = max(d.risk_score for d in decisions)
        evidence = []
        categories = []
        for d in decisions:
            evidence.extend(d.evidence)
            categories.append(d.category)

        if mode == "off":
            return GuardDecision(True, "ALLOW", 0, "LOW", "CyberLACE apagado", "semantic_firewall")

        if mode == "monitor":
            return GuardDecision(
                allowed=True,
                action="MONITOR",
                risk_score=max_risk,
                severity=self._severity(max_risk),
                reason="Modo monitor: se registra riesgo sin bloquear",
                category="semantic_firewall",
                evidence=evidence,
            )

        if max_risk >= 90:
            action, allowed = "QUARANTINE", False
        elif max_risk >= 80:
            action, allowed = "BLOCK", False
        elif max_risk >= 60:
            action, allowed = "HUMAN_REVIEW", False
        elif max_risk >= 35:
            action, allowed = "MONITOR", True
        else:
            action, allowed = "ALLOW", True

        return GuardDecision(
            allowed=allowed,
            action=action,
            risk_score=max_risk,
            severity=self._severity(max_risk),
            reason=f"Decisión semántica basada en riesgo {max_risk}",
            category="semantic_firewall",
            evidence=evidence,
            confidence=max(d.confidence for d in decisions),
        )

    def _severity(self, risk: float) -> str:
        if risk >= 76:
            return "CRITICAL"
        if risk >= 51:
            return "HIGH"
        if risk >= 21:
            return "MEDIUM"
        return "LOW"
