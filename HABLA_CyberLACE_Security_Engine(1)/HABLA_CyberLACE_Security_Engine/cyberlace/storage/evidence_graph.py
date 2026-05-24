from pathlib import Path
import json
from typing import Dict, Any, List
from cyberlace.core.models import CognitiveEvent, GuardDecision


class EvidenceGraph:
    def __init__(self, evidence_path: str = "data/evidence/evidence.jsonl", events_path: str = "data/evidence/events.jsonl"):
        self.evidence_path = Path(evidence_path)
        self.events_path = Path(events_path)
        self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def record_event(self, event: CognitiveEvent) -> None:
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def record_decision(self, event: CognitiveEvent, decision: GuardDecision) -> None:
        payload = {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "agent_id": event.agent_id,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "event_type": event.event_type,
            "decision": decision.to_dict(),
            "edges": [
                {"from": f"user:{event.user_id}", "to": f"event:{event.event_id}", "type": "generated"},
                {"from": f"event:{event.event_id}", "to": f"agent:{event.agent_id}", "type": "processed_by"},
                {"from": f"agent:{event.agent_id}", "to": f"decision:{decision.action}", "type": "resolved_as"},
            ],
        }
        with self.evidence_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.evidence_path.exists():
            return []
        lines = self.evidence_path.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
