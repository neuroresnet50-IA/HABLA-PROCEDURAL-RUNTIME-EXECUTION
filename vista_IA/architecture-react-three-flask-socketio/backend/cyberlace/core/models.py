from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


DecisionAction = str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CognitiveEvent:
    event_type: str
    agent_id: str
    user_id: str = "anonymous"
    content: Any = None
    source: str = "unknown"
    target: str = "unknown"
    session_id: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0
    decision: str = "PENDING"
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    event_id: str = field(default_factory=lambda: f"evt_{uuid4().hex}")
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CognitiveState:
    agent_id: str
    session_id: str = "default"
    prompt_state: Dict[str, Any] = field(default_factory=dict)
    context_state: Dict[str, Any] = field(default_factory=dict)
    memory_state: Dict[str, Any] = field(default_factory=dict)
    tool_state: Dict[str, Any] = field(default_factory=dict)
    reasoning_state: Dict[str, Any] = field(default_factory=dict)
    behavior_state: Dict[str, Any] = field(default_factory=dict)
    autonomy_state: Dict[str, Any] = field(default_factory=lambda: {"level": 2})
    trust_state: Dict[str, Any] = field(default_factory=lambda: {"score": 75})
    event_count: int = 0
    last_updated: str = field(default_factory=utc_now)

    def update_from_event(self, event: CognitiveEvent) -> None:
        self.event_count += 1
        self.last_updated = utc_now()

        if event.event_type.startswith("prompt"):
            self.prompt_state["last_prompt"] = event.content
        elif event.event_type.startswith("memory"):
            self.memory_state["last_memory_event"] = event.metadata
        elif event.event_type.startswith("tool"):
            self.tool_state["last_tool_event"] = event.metadata
        elif event.event_type.startswith("output"):
            self.behavior_state["last_output_risk"] = event.risk_score

        previous_risk = float(self.trust_state.get("last_risk", 0))
        drift = abs(float(event.risk_score) - previous_risk)
        self.trust_state["last_risk"] = event.risk_score
        self.trust_state["drift"] = drift

    def calculate_state_drift(self) -> float:
        return float(self.trust_state.get("drift", 0))

    def detect_context_mismatch(self, task_domain: Optional[str], memory_domain: Optional[str]) -> bool:
        if not task_domain or not memory_domain:
            return False
        if memory_domain in {"financial", "credential", "restricted"} and task_domain not in {
            "finance", "security", "credential_management"
        }:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GuardDecision:
    allowed: bool
    action: DecisionAction
    risk_score: float
    severity: str
    reason: str
    category: str = "general"
    confidence: float = 0.75
    modified_payload: Any = None
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    policy_matches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
