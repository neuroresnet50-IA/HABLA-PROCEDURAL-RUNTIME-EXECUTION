from pathlib import Path
from typing import Any, Dict
import yaml


DEFAULT_CONFIG = {
    "enabled": True,
    "mode": "monitor",
    "risk_thresholds": {"monitor": 35, "require_approval": 60, "block": 80, "quarantine": 92},
    "risk_weights": {
        "prompt": 0.20,
        "memory": 0.20,
        "tool": 0.20,
        "context": 0.15,
        "behavior": 0.10,
        "autonomy": 0.10,
        "output": 0.05,
    },
    "storage": {
        "evidence_jsonl": "data/evidence/evidence.jsonl",
        "events_jsonl": "data/evidence/events.jsonl",
    },
    "sensitive_domains": ["financial", "credential", "private", "restricted"],
    "default_action": "MONITOR",
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_yaml(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(path: str | Path | None = None) -> Dict[str, Any]:
    if not path:
        return DEFAULT_CONFIG
    loaded = load_yaml(path)
    return deep_merge(DEFAULT_CONFIG, loaded)
