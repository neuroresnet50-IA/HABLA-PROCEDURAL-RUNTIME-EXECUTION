from typing import Any, Dict, List
from cyberlace.core.models import GuardDecision
from cyberlace.utils.patterns import find_sensitive


class PromptGuard:
    INJECTION_PATTERNS = [
        "ignore previous instructions",
        "ignora las instrucciones",
        "olvida tus reglas",
        "system prompt",
        "muestra tu prompt",
        "jailbreak",
        "developer message",
        "desactiva tus reglas",
        "bypass",
        "act as dan",
        "reveal hidden",
        "instrucciones ocultas",
    ]

    def inspect(self, prompt: str, context: Dict[str, Any] | None = None) -> GuardDecision:
        context = context or {}
        prompt_l = (prompt or "").lower()
        evidence: List[Dict[str, Any]] = []
        risk = 0
        category = "normal"

        for pattern in self.INJECTION_PATTERNS:
            if pattern in prompt_l:
                evidence.append({"type": "prompt_pattern", "pattern": pattern})
                risk += 25
                category = "prompt_injection"

        sensitive_hits = find_sensitive(prompt or "")
        if sensitive_hits:
            evidence.extend({"type": "sensitive_in_prompt", **h} for h in sensitive_hits)
            risk += min(35, 10 * len(sensitive_hits))
            category = "sensitive_data_in_prompt"

        if "tool" in prompt_l and ("delete" in prompt_l or "borrar" in prompt_l or "enviar" in prompt_l):
            evidence.append({"type": "dangerous_tool_intent"})
            risk += 20

        risk = min(100, risk)
        allowed = risk < 80
        action = "ALLOW" if allowed else "BLOCK"

        return GuardDecision(
            allowed=allowed,
            action=action,
            risk_score=risk,
            severity="CRITICAL" if risk >= 76 else "HIGH" if risk >= 51 else "MEDIUM" if risk >= 21 else "LOW",
            category=category,
            reason="Prompt aceptado" if allowed else "Prompt bloqueado por riesgo cognitivo alto",
            modified_payload=prompt,
            evidence=evidence,
            confidence=0.80 if evidence else 0.60,
        )
