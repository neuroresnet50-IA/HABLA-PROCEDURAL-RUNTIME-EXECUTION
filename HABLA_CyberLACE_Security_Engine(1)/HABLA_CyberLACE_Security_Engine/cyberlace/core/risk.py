from typing import Dict, Any


class RiskEngine:
    def __init__(self, weights: Dict[str, float] | None = None):
        self.weights = weights or {
            "prompt": 0.20,
            "memory": 0.20,
            "tool": 0.20,
            "context": 0.15,
            "behavior": 0.10,
            "autonomy": 0.10,
            "output": 0.05,
        }

    def severity(self, score: float) -> str:
        if score >= 76:
            return "CRITICAL"
        if score >= 51:
            return "HIGH"
        if score >= 21:
            return "MEDIUM"
        return "LOW"

    def combine(self, scores: Dict[str, float]) -> float:
        total_weight = 0.0
        total = 0.0
        for key, value in scores.items():
            w = float(self.weights.get(key, 0.0))
            total += float(value) * w
            total_weight += w
        if total_weight <= 0:
            return max(scores.values()) if scores else 0.0
        return round(total / total_weight, 2)
