"""Bridge between the existing runtime security policy and CyberLACE decisions."""

from __future__ import annotations

from typing import Any, Dict


ALLOW_ACTIONS = {"ALLOW", "MONITOR"}
REDACT_ACTIONS = {"REDACT", "SANITIZE_ARGS"}
HUMAN_REVIEW_ACTIONS = {"HUMAN_REVIEW", "REQUIRE_APPROVAL"}
BLOCK_ACTIONS = {"BLOCK", "QUARANTINE"}


def map_security_policy_to_cyberlace(policy: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Expose command-policy metadata as CyberLACE cognitive context."""

    policy = policy if isinstance(policy, dict) else {}
    categories = policy.get("risk_categories") if isinstance(policy.get("risk_categories"), dict) else {}
    return {
        "source": "orchestrator.security_policy",
        "defaultDecision": policy.get("default_decision"),
        "riskCategories": {
            str(name): {
                "decision": value.get("decision"),
                "riskLevel": value.get("risk_level"),
                "activated": value.get("activated", True),
            }
            for name, value in categories.items()
            if isinstance(value, dict)
        },
        "allowPrefixes": policy.get("allow_prefixes", []),
        "askPrefixes": policy.get("ask_prefixes", []),
        "denyPrefixes": policy.get("deny_prefixes", []),
    }


def normalize_cyberlace_action(action: Any) -> str:
    normalized = str(action or "ALLOW").strip().upper() or "ALLOW"
    if normalized == "REQUIRE_APPROVAL":
        return "HUMAN_REVIEW"
    if normalized == "SANITIZE_ARGS":
        return "REDACT"
    return normalized


def map_cyberlace_decision_to_runtime(
    decision: Dict[str, Any] | None,
    *,
    mode: str | None = None,
) -> Dict[str, Any]:
    """Return a runtime-safe decision without replacing existing command policy."""

    decision = decision if isinstance(decision, dict) else {}
    raw_action = str(decision.get("action") or decision.get("runtimeAction") or "ALLOW").strip().upper()
    normalized_action = normalize_cyberlace_action(raw_action)
    normalized_mode = str(mode or decision.get("mode") or "monitor").strip().lower()

    if normalized_mode != "enforce":
        runtime_action = "ALLOW"
        runtime_allowed = True
    elif normalized_action in BLOCK_ACTIONS:
        runtime_action = normalized_action
        runtime_allowed = False
    elif normalized_action in HUMAN_REVIEW_ACTIONS:
        runtime_action = "HUMAN_REVIEW"
        runtime_allowed = False
    elif normalized_action in REDACT_ACTIONS:
        runtime_action = "REDACT"
        runtime_allowed = True
    else:
        runtime_action = "ALLOW"
        runtime_allowed = True

    return {
        **decision,
        "action": normalized_action,
        "recommendedAction": normalized_action,
        "runtimeAction": runtime_action,
        "allowed": runtime_allowed,
        "requiresHumanReview": runtime_action == "HUMAN_REVIEW",
        "blocksRuntime": runtime_action in BLOCK_ACTIONS,
        "redactsPayload": runtime_action == "REDACT",
    }


def should_require_human_review(decision: Dict[str, Any] | None) -> bool:
    mapped = map_cyberlace_decision_to_runtime(decision, mode=(decision or {}).get("mode") if isinstance(decision, dict) else None)
    return bool(mapped.get("requiresHumanReview"))


def should_block_action(decision: Dict[str, Any] | None) -> bool:
    mapped = map_cyberlace_decision_to_runtime(decision, mode=(decision or {}).get("mode") if isinstance(decision, dict) else None)
    return bool(mapped.get("blocksRuntime") or mapped.get("runtimeAction") == "HUMAN_REVIEW")


def should_redact_payload(decision: Dict[str, Any] | None) -> bool:
    mapped = map_cyberlace_decision_to_runtime(decision, mode=(decision or {}).get("mode") if isinstance(decision, dict) else None)
    return bool(mapped.get("redactsPayload") and mapped.get("modified_payload") is not None)
