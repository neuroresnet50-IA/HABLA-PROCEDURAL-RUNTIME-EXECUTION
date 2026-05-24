from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from cyberlace.core.models import CognitiveEvent, CognitiveState, GuardDecision
from cyberlace.utils.config import load_config
from cyberlace.guards.prompt_guard import PromptGuard
from cyberlace.guards.memory_guard import MemoryGuard
from cyberlace.guards.tool_guard import ToolGuard
from cyberlace.guards.output_guard import OutputGuard
from cyberlace.core.risk import RiskEngine
from cyberlace.core.policy import PolicyEngine
from cyberlace.core.autonomy import AutonomyGovernor
from cyberlace.storage.evidence_graph import EvidenceGraph
from cyberlace.supervisor.lace_security_supervisor import LACESecuritySupervisor


class CyberLACEEngine:
    def __init__(self, config: Dict[str, Any] | None = None, base_path: str | Path | None = None):
        self.config = config or load_config()
        self.base_path = Path(base_path or ".")
        self.mode = self.config.get("mode", "monitor")
        storage = self.config.get("storage", {})
        self.evidence = EvidenceGraph(
            storage.get("evidence_jsonl", "data/evidence/evidence.jsonl"),
            storage.get("events_jsonl", "data/evidence/events.jsonl"),
        )
        self.prompt_guard = PromptGuard()
        self.memory_guard = MemoryGuard()
        self.tool_guard = ToolGuard()
        self.output_guard = OutputGuard()
        self.risk_engine = RiskEngine(self.config.get("risk_weights"))
        self.policy_engine = PolicyEngine()
        self.autonomy = AutonomyGovernor()
        self.supervisor = LACESecuritySupervisor()
        self.states: Dict[str, CognitiveState] = {}

    @classmethod
    def from_config(cls, path: str | Path = "cyberlace_config.yaml") -> "CyberLACEEngine":
        return cls(load_config(path))

    def _state(self, agent_id: str, session_id: str = "default") -> CognitiveState:
        key = f"{session_id}:{agent_id}"
        if key not in self.states:
            self.states[key] = CognitiveState(agent_id=agent_id, session_id=session_id)
        return self.states[key]

    def _finalize(self, event: CognitiveEvent, *decisions: GuardDecision) -> Dict[str, Any]:
        if self.mode == "off":
            final = GuardDecision(True, "ALLOW", 0, "LOW", "CyberLACE está apagado", "off")
        else:
            final = self.supervisor.supervise(list(decisions), mode=self.mode)

        event.risk_score = final.risk_score
        event.decision = final.action
        event.evidence = final.evidence
        self._state(event.agent_id, event.session_id).update_from_event(event)
        self.evidence.record_event(event)
        self.evidence.record_decision(event, final)
        return final.to_dict()

    def before_prompt(self, agent_id: str, user_id: str, prompt: str, context: Dict[str, Any] | None = None, session_id: str = "default") -> Dict[str, Any]:
        event = CognitiveEvent(
            event_type="prompt.received",
            agent_id=agent_id,
            user_id=user_id,
            content=prompt,
            source="user",
            target="agent",
            session_id=session_id,
            metadata={"context": context or {}},
        )
        d = self.prompt_guard.inspect(prompt, context)
        return self._finalize(event, d)

    def before_memory_read(self, agent_id: str, user_id: str, memory_text: str, task_context: Dict[str, Any] | None = None, session_id: str = "default") -> Dict[str, Any]:
        event = CognitiveEvent(
            event_type="memory.read",
            agent_id=agent_id,
            user_id=user_id,
            content=memory_text,
            source="memory",
            target="agent",
            session_id=session_id,
            metadata={"task_context": task_context or {}},
        )
        d = self.memory_guard.inspect_read(memory_text, task_context)
        return self._finalize(event, d)

    def before_tool_call(self, agent_id: str, user_id: str, tool_name: str, tool_args: Dict[str, Any], task_context: Dict[str, Any] | None = None, session_id: str = "default") -> Dict[str, Any]:
        event = CognitiveEvent(
            event_type="tool.call",
            agent_id=agent_id,
            user_id=user_id,
            content=tool_args,
            source="agent",
            target=tool_name,
            session_id=session_id,
            metadata={"tool_name": tool_name, "task_context": task_context or {}},
        )
        d = self.tool_guard.inspect_call(agent_id, tool_name, tool_args, task_context)
        return self._finalize(event, d)

    def after_model_output(self, agent_id: str, user_id: str, output: str, context: Dict[str, Any] | None = None, session_id: str = "default") -> Dict[str, Any]:
        event = CognitiveEvent(
            event_type="output.generated",
            agent_id=agent_id,
            user_id=user_id,
            content=output,
            source="model",
            target="user_or_tool",
            session_id=session_id,
            metadata={"context": context or {}},
        )
        d = self.output_guard.inspect_output(output, context)
        return self._finalize(event, d)

    def before_external_action(self, agent_id: str, user_id: str, action_type: str, payload: Dict[str, Any], context: Dict[str, Any] | None = None, session_id: str = "default") -> Dict[str, Any]:
        return self.before_tool_call(
            agent_id=agent_id,
            user_id=user_id,
            tool_name=action_type,
            tool_args=payload,
            task_context=context or {},
            session_id=session_id,
        )

    def evaluate_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_type = event.get("event_type", "")
        if event_type.startswith("prompt"):
            return self.before_prompt(event.get("agent_id", "unknown"), event.get("user_id", "anonymous"), event.get("content", ""), event.get("metadata", {}), event.get("session_id", "default"))
        if event_type.startswith("memory"):
            return self.before_memory_read(event.get("agent_id", "unknown"), event.get("user_id", "anonymous"), event.get("content", ""), event.get("metadata", {}), event.get("session_id", "default"))
        if event_type.startswith("tool"):
            meta = event.get("metadata", {})
            return self.before_tool_call(event.get("agent_id", "unknown"), event.get("user_id", "anonymous"), meta.get("tool_name", "unknown_tool"), event.get("content", {}), meta.get("task_context", {}), event.get("session_id", "default"))
        if event_type.startswith("output"):
            return self.after_model_output(event.get("agent_id", "unknown"), event.get("user_id", "anonymous"), event.get("content", ""), event.get("metadata", {}), event.get("session_id", "default"))
        return {"allowed": True, "action": "ALLOW", "risk_score": 0, "reason": "Evento no reconocido; permitido por defecto"}
