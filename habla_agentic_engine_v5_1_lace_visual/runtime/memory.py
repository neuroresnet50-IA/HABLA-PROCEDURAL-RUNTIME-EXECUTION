import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from .types import HablaState


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class EpisodicMemory:
    """Memoria episódica JSONL.

    Ahora no solo escribe: también lee estadísticas recientes para retroalimentar
    la selección de herramientas del motor.
    """
    def __init__(self, path: str = "memory/episodic_memory.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: HablaState) -> None:
        record = {
            "timestamp": _utc_now(),
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
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

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
        for rec in self.load_recent(limit=limit):
            if knowledge_type and rec.get("knowledge_type") != knowledge_type:
                continue
            tools = rec.get("tools_tried") or []
            success = bool(rec.get("safe_to_answer")) and not bool(rec.get("blocked"))
            for tool in tools:
                if success:
                    stats[tool]["success"] += 1
                else:
                    stats[tool]["fail"] += 1
        return dict(stats)

    def recommend_tool_order(self, base_order: List[str], knowledge_type: str) -> List[str]:
        stats = self.tool_stats(knowledge_type=knowledge_type)
        def score(tool: str) -> float:
            s = stats.get(tool, {"success": 0, "fail": 0})
            total = s["success"] + s["fail"]
            if total == 0:
                return 0.5
            return (s["success"] + 1) / (total + 2)
        # No elimina herramientas: solo reordena. Así la memoria guía, no encierra.
        return sorted(base_order, key=score, reverse=True)

    def _tools_from_debug(self, debug: List[str]) -> List[str]:
        tools = []
        for msg in debug:
            if "tool=" in msg:
                tools.append(msg.split("tool=", 1)[1].strip())
        return tools
