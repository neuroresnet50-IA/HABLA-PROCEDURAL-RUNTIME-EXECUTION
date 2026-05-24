from typing import Any, Dict, List
from cyberlace.core.models import GuardDecision
from cyberlace.utils.patterns import find_sensitive, redact_sensitive


class ToolGuard:
    DANGEROUS_TOOLS = {"shell", "exec", "subprocess", "filesystem_write", "delete_file", "send_email", "post_social", "external_request"}
    EXTERNAL_TOOLS = {"send_email", "post_social", "external_request", "browser_post", "webhook"}

    def inspect_call(self, agent_id: str, tool_name: str, tool_args: Dict[str, Any], task_context: Dict[str, Any] | None = None) -> GuardDecision:
        task_context = task_context or {}
        args_text = str(tool_args or {})
        evidence: List[Dict[str, Any]] = []
        risk = 0

        if tool_name in self.DANGEROUS_TOOLS:
            evidence.append({"type": "dangerous_tool", "tool_name": tool_name})
            risk += 30

        sensitive_hits = find_sensitive(args_text)
        if sensitive_hits:
            evidence.extend({"type": "sensitive_data_in_tool_args", **h} for h in sensitive_hits)
            risk += min(50, 15 * len(sensitive_hits))

        if tool_name in self.EXTERNAL_TOOLS and sensitive_hits:
            evidence.append({"type": "external_exfiltration_risk", "tool_name": tool_name})
            risk += 35

        if task_context.get("requires_human_approval") and tool_name in self.DANGEROUS_TOOLS:
            evidence.append({"type": "human_approval_required"})
            risk += 20

        action = "ALLOW"
        allowed = True
        modified = tool_args

        if risk >= 80:
            action = "BLOCK"
            allowed = False
        elif risk >= 60:
            action = "REQUIRE_APPROVAL"
            allowed = False
        elif sensitive_hits:
            action = "SANITIZE_ARGS"
            redacted_text, _ = redact_sensitive(args_text)
            modified = {"_sanitized_args_repr": redacted_text}

        return GuardDecision(
            allowed=allowed,
            action=action,
            risk_score=min(100, risk),
            severity="CRITICAL" if risk >= 76 else "HIGH" if risk >= 51 else "MEDIUM" if risk >= 21 else "LOW",
            category="tool_call",
            reason="Tool permitida" if allowed else f"Tool {tool_name} bloqueada o requiere aprobación",
            modified_payload=modified,
            evidence=evidence,
            confidence=0.86 if evidence else 0.64,
        )
