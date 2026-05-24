from pathlib import Path
from typing import Any, Dict, List
import yaml


class PolicyEngine:
    def __init__(self, policy_path: str | Path | None = None):
        self.policy_path = Path(policy_path) if policy_path else Path(__file__).parents[1] / "policies" / "default_policies.yaml"
        self.policies = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.policy_path.exists():
            return {"policies": {}}
        with self.policy_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"policies": {}}

    def evaluate(self, facts: Dict[str, Any]) -> List[Dict[str, Any]]:
        matches = []
        for name, policy in self.policies.get("policies", {}).items():
            when = policy.get("when", {})
            if self._match_when(when, facts):
                matches.append({
                    "name": name,
                    "description": policy.get("description", ""),
                    "then": policy.get("then", {}),
                })
        return matches

    def _match_when(self, when: Dict[str, Any], facts: Dict[str, Any]) -> bool:
        for key, expected in when.items():
            if key == "risk_gte":
                if float(facts.get("risk_score", 0)) < float(expected):
                    return False
                continue

            actual = facts.get(key)
            if isinstance(expected, list):
                if isinstance(actual, list):
                    if not any(x in expected for x in actual):
                        return False
                elif actual not in expected:
                    return False
            else:
                if actual != expected:
                    return False
        return True
