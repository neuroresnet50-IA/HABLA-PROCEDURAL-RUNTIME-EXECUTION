import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .types import HablaState


class EpisodicMemory:
    """Memoria episódica JSONL con retroalimentación de herramientas."""

    def __init__(self, path: str = "memory/episodic_memory.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: HablaState) -> None:
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "question": state.question,
            "knowledge_type": state.knowledge_type,
            "tool_required": state.tool_required,
            "strategy": state.strategy,
            "attempts": state.attempt,
            "sources": [e.source for e in state.observations],
            "tools_tried": self._tools_from_debug(state.debug),
            "confidence": {
                "dato": state.confidence.dato,
                "fecha": state.confidence.fecha,
                "fuente": state.confidence.fuente,
                "calculo": state.confidence.calculo,
                "inferencia": state.confidence.inferencia,
                "global": state.confidence.global_score,
            },
            "safe_to_answer": state.safe_to_answer,
            "blocked": state.blocked,
            "block_reason": state.block_reason,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_recent(self, limit: int = 100) -> List[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        records = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def tool_stats(self, knowledge_type: Optional[str] = None, limit: int = 100) -> Dict[str, Dict[str, int]]:
        stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "fail": 0})
        for record in self.load_recent(limit=limit):
            if knowledge_type and record.get("knowledge_type") != knowledge_type:
                continue
            tools = record.get("tools_tried") or []
            success = bool(record.get("safe_to_answer")) and not bool(record.get("blocked"))
            for tool in tools:
                if success:
                    stats[tool]["success"] += 1
                else:
                    stats[tool]["fail"] += 1
        return dict(stats)

    def recommend_tool_order(self, base_order: List[str], knowledge_type: str) -> List[str]:
        stats = self.tool_stats(knowledge_type=knowledge_type)

        def score(tool: str) -> float:
            state = stats.get(tool, {"success": 0, "fail": 0})
            total = state["success"] + state["fail"]
            if total == 0:
                return 0.5
            return (state["success"] + 1) / (total + 2)

        return sorted(base_order, key=score, reverse=True)

    def _tools_from_debug(self, debug: List[str]) -> List[str]:
        tools = []
        for message in debug:
            if "tool=" in message:
                tools.append(message.split("tool=", 1)[1].strip())
        return tools
