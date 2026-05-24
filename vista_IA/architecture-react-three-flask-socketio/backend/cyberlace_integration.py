"""Runtime adapter for HABLA CyberLACE Security Engine.

The adapter keeps CyberLACE lateral to the current runtime: disabled/off is a
no-op, monitor records evidence without blocking, and enforce maps decisions to
runtime actions through cyberlace_policy_bridge.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

try:
    from cyberlace_policy_bridge import map_cyberlace_decision_to_runtime
except ImportError:  # pragma: no cover - package import path during unittest.
    from backend.cyberlace_policy_bridge import map_cyberlace_decision_to_runtime


BACKEND_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

CYBERLACE_DEFAULT_REST_URL = "http://127.0.0.1:8088"
VALID_MODES = {"off", "monitor", "enforce"}
VALID_TRANSPORTS = {"import", "rest"}
_ENGINE_LOCK = threading.Lock()
_EVIDENCE_LOCK = threading.Lock()
_ENGINE: Any | None = None
_ENGINE_KEY: tuple[str, str, str] | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"", "0", "false", "no", "off"}


def _mode() -> str:
    if not _env_flag("CYBERLACE_ENABLED", default=False):
        return "off"
    raw_mode = str(os.environ.get("CYBERLACE_MODE") or "monitor").strip().lower()
    return raw_mode if raw_mode in VALID_MODES else "monitor"


def _transport() -> str:
    raw_transport = str(os.environ.get("CYBERLACE_TRANSPORT") or "import").strip().lower()
    return raw_transport if raw_transport in VALID_TRANSPORTS else "import"


def _runtime_root() -> Path:
    configured = str(os.environ.get("CYBERLACE_RUNTIME_DIR") or "").strip()
    return Path(configured).expanduser().resolve() if configured else REPO_ROOT / "runtime" / "cyberlace"


def cyberlace_paths() -> Dict[str, Path]:
    root = _runtime_root()
    return {
        "root": root,
        "evidence": root / "evidence",
        "logs": root / "logs",
        "events": root / "evidence" / "cyberlace_events.jsonl",
        "decisions": root / "evidence" / "cyberlace_decisions.jsonl",
        "failures": root / "logs" / "cyberlace_failures.jsonl",
        "engineEvents": root / "evidence" / "cyberlace_engine_events.jsonl",
        "engineEvidence": root / "evidence" / "cyberlace_engine_evidence.jsonl",
    }


def ensure_cyberlace_runtime() -> Dict[str, str]:
    paths = cyberlace_paths()
    for key in ("root", "evidence", "logs"):
        paths[key].mkdir(parents=True, exist_ok=True)
    for key in ("events", "decisions"):
        paths[key].touch(exist_ok=True)
    return {key: str(value) for key, value in paths.items()}


def cyberlace_settings() -> Dict[str, Any]:
    paths = ensure_cyberlace_runtime()
    return {
        "enabled": _mode() != "off",
        "mode": _mode(),
        "transport": _transport(),
        "restUrl": str(os.environ.get("CYBERLACE_REST_URL") or CYBERLACE_DEFAULT_REST_URL).rstrip("/"),
        "configPath": str(Path(os.environ.get("CYBERLACE_CONFIG_PATH") or BACKEND_ROOT / "cyberlace_config.yaml")),
        "paths": paths,
    }


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=True)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        return repr(value)


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_json_safe(payload), ensure_ascii=True, sort_keys=True)
    with _EVIDENCE_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def _persist_event(document: Dict[str, Any]) -> None:
    paths = cyberlace_paths()
    _append_jsonl(paths["events"], document)
    if document.get("recordType") in {"decision", "failure"}:
        _append_jsonl(paths["decisions"], document)
    if document.get("recordType") == "failure":
        _append_jsonl(paths["failures"], document)


def get_cyberlace_engine() -> Any:
    """Return the local CyberLACEEngine singleton for import transport."""

    global _ENGINE, _ENGINE_KEY
    settings = cyberlace_settings()
    mode = str(settings["mode"])
    config_path = str(settings["configPath"])
    engine_key = (mode, config_path, str(_runtime_root()))
    with _ENGINE_LOCK:
        if _ENGINE is not None and _ENGINE_KEY == engine_key:
            return _ENGINE

        from cyberlace import CyberLACEEngine

        config: Dict[str, Any] = {}
        try:
            from cyberlace.utils.config import load_config

            config = load_config(config_path)
        except Exception:
            config = {}
        config = dict(config or {})
        config["mode"] = mode
        storage = dict(config.get("storage") or {})
        paths = cyberlace_paths()
        storage["events_jsonl"] = str(paths["engineEvents"])
        storage["evidence_jsonl"] = str(paths["engineEvidence"])
        config["storage"] = storage
        _ENGINE = CyberLACEEngine(config=config, base_path=BACKEND_ROOT)
        _ENGINE_KEY = engine_key
        return _ENGINE


def _disabled_decision(stage: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "enabled": False,
        "mode": "off",
        "transport": _transport(),
        "stage": stage,
        "allowed": True,
        "action": "ALLOW",
        "runtimeAction": "ALLOW",
        "riskScore": 0,
        "severity": "LOW",
        "reason": "CyberLACE disabled",
        "modified_payload": payload.get("content"),
        "evidence": [],
        "timestamp": _utc_now(),
    }


def _call_import(stage: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    engine = get_cyberlace_engine()
    if stage == "prompt":
        return engine.before_prompt(
            payload["agent_id"],
            payload["user_id"],
            payload["prompt"],
            payload.get("context") or {},
            payload["session_id"],
        )
    if stage == "memory":
        return engine.before_memory_read(
            payload["agent_id"],
            payload["user_id"],
            payload["memory_text"],
            payload.get("task_context") or {},
            payload["session_id"],
        )
    if stage == "tool":
        return engine.before_tool_call(
            payload["agent_id"],
            payload["user_id"],
            payload["tool_name"],
            payload.get("tool_args") or {},
            payload.get("task_context") or {},
            payload["session_id"],
        )
    if stage == "output":
        return engine.after_model_output(
            payload["agent_id"],
            payload["user_id"],
            payload["output"],
            payload.get("context") or {},
            payload["session_id"],
        )
    if stage == "external-action":
        return engine.before_external_action(
            payload["agent_id"],
            payload["user_id"],
            payload["action_type"],
            payload.get("payload") or {},
            payload.get("context") or {},
            payload["session_id"],
        )
    return {"allowed": True, "action": "ALLOW", "risk_score": 0, "reason": "Unknown CyberLACE stage"}


def _call_rest(stage: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    endpoint_map = {
        "prompt": "/v1/guard/prompt",
        "memory": "/v1/guard/memory",
        "tool": "/v1/guard/tool",
        "output": "/v1/guard/output",
        "external-action": "/v1/guard/external-action",
    }
    endpoint = endpoint_map.get(stage)
    if endpoint is None:
        return {"allowed": True, "action": "ALLOW", "risk_score": 0, "reason": "Unknown CyberLACE stage"}
    settings = cyberlace_settings()
    body = json.dumps(_json_safe(payload), ensure_ascii=True).encode("utf-8")
    request = urllib.request.Request(
        str(settings["restUrl"]) + endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=float(os.environ.get("CYBERLACE_REST_TIMEOUT_SECONDS", "3"))) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def _normalize_decision(
    *,
    stage: str,
    payload: Dict[str, Any],
    raw_decision: Dict[str, Any],
    error: str | None = None,
) -> Dict[str, Any]:
    settings = cyberlace_settings()
    risk_score = raw_decision.get("risk_score", raw_decision.get("riskScore", 0))
    document = {
        "recordType": "failure" if error else "decision",
        "eventId": f"cyberlace_{uuid.uuid4().hex}",
        "timestamp": _utc_now(),
        "enabled": bool(settings["enabled"]),
        "mode": settings["mode"],
        "transport": settings["transport"],
        "stage": stage,
        "agentId": payload.get("agent_id"),
        "userId": payload.get("user_id"),
        "sessionId": payload.get("session_id"),
        "toolName": payload.get("tool_name") or payload.get("action_type"),
        "riskScore": float(risk_score or 0),
        "severity": raw_decision.get("severity", "LOW"),
        "reason": raw_decision.get("reason") or ("CyberLACE failure" if error else "CyberLACE decision"),
        "action": raw_decision.get("action", "ALLOW"),
        "allowed": bool(raw_decision.get("allowed", True)),
        "modified_payload": raw_decision.get("modified_payload"),
        "evidence": raw_decision.get("evidence") or [],
        "policyMatches": raw_decision.get("policy_matches") or [],
        "error": error,
        "rawDecision": raw_decision,
    }
    mapped = map_cyberlace_decision_to_runtime(document, mode=str(settings["mode"]))
    _persist_event(mapped)
    return {"ok": error is None, **mapped}


def _failure_decision(stage: str, payload: Dict[str, Any], error: Exception) -> Dict[str, Any]:
    settings = cyberlace_settings()
    action = "ALLOW" if settings["mode"] != "enforce" else "HUMAN_REVIEW"
    raw = {
        "allowed": settings["mode"] != "enforce",
        "action": action,
        "risk_score": 0 if settings["mode"] != "enforce" else 70,
        "severity": "LOW" if settings["mode"] != "enforce" else "HIGH",
        "reason": f"CyberLACE unavailable: {error}",
        "evidence": [{"type": "cyberlace_failure", "message": str(error), "stage": stage}],
    }
    return _normalize_decision(stage=stage, payload=payload, raw_decision=raw, error=str(error))


def _guard(stage: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = cyberlace_settings()
    if not settings["enabled"] or settings["mode"] == "off":
        return _disabled_decision(stage, payload)
    try:
        raw = _call_rest(stage, payload) if settings["transport"] == "rest" else _call_import(stage, payload)
        return _normalize_decision(stage=stage, payload=payload, raw_decision=raw)
    except Exception as error:
        return _failure_decision(stage, payload, error)


def cyberlace_before_prompt(agent_id: str, user_id: str, prompt: str, context: Dict[str, Any] | None, session_id: str) -> Dict[str, Any]:
    return _guard(
        "prompt",
        {
            "agent_id": agent_id or "unknown-agent",
            "user_id": user_id or "anonymous",
            "prompt": str(prompt or ""),
            "content": str(prompt or ""),
            "context": context or {},
            "session_id": session_id or "default",
        },
    )


def cyberlace_before_memory_read(
    agent_id: str,
    user_id: str,
    memory_text: str,
    task_context: Dict[str, Any] | None,
    session_id: str,
) -> Dict[str, Any]:
    return _guard(
        "memory",
        {
            "agent_id": agent_id or "unknown-agent",
            "user_id": user_id or "anonymous",
            "memory_text": str(memory_text or ""),
            "content": str(memory_text or ""),
            "task_context": task_context or {},
            "session_id": session_id or "default",
        },
    )


def cyberlace_before_tool_call(
    agent_id: str,
    user_id: str,
    tool_name: str,
    tool_args: Dict[str, Any] | None,
    task_context: Dict[str, Any] | None,
    session_id: str,
) -> Dict[str, Any]:
    return _guard(
        "tool",
        {
            "agent_id": agent_id or "unknown-agent",
            "user_id": user_id or "anonymous",
            "tool_name": tool_name or "unknown_tool",
            "tool_args": tool_args or {},
            "content": tool_args or {},
            "task_context": task_context or {},
            "session_id": session_id or "default",
        },
    )


def cyberlace_after_model_output(
    agent_id: str,
    user_id: str,
    output: str,
    context: Dict[str, Any] | None,
    session_id: str,
) -> Dict[str, Any]:
    return _guard(
        "output",
        {
            "agent_id": agent_id or "unknown-agent",
            "user_id": user_id or "anonymous",
            "output": str(output or ""),
            "content": str(output or ""),
            "context": context or {},
            "session_id": session_id or "default",
        },
    )


def cyberlace_before_external_action(
    agent_id: str,
    user_id: str,
    action_type: str,
    payload: Dict[str, Any] | None,
    context: Dict[str, Any] | None,
    session_id: str,
) -> Dict[str, Any]:
    return _guard(
        "external-action",
        {
            "agent_id": agent_id or "unknown-agent",
            "user_id": user_id or "anonymous",
            "action_type": action_type or "unknown_action",
            "payload": payload or {},
            "content": payload or {},
            "context": context or {},
            "session_id": session_id or "default",
        },
    )


def read_recent_cyberlace_evidence(limit: int = 20) -> Dict[str, Any]:
    ensure_cyberlace_runtime()
    bounded_limit = max(1, min(int(limit or 20), 200))
    paths = cyberlace_paths()
    return {
        "events": _read_jsonl_tail(paths["events"], bounded_limit),
        "decisions": _read_jsonl_tail(paths["decisions"], bounded_limit),
    }


def _read_jsonl_tail(path: Path, limit: int) -> list[Dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    items: list[Dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            items.append(value)
    return items


def cyberlace_health() -> Dict[str, Any]:
    settings = cyberlace_settings()
    evidence = read_recent_cyberlace_evidence(limit=1)
    engine_available = False
    engine_error = ""
    if settings["enabled"] and settings["transport"] == "import":
        try:
            get_cyberlace_engine()
            engine_available = True
        except Exception as error:
            engine_error = str(error)
    elif settings["enabled"] and settings["transport"] == "rest":
        try:
            request = urllib.request.Request(str(settings["restUrl"]) + "/health", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                engine_available = 200 <= int(getattr(response, "status", 200) or 200) < 500
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            engine_error = str(error)
    return {
        "ok": True,
        "engine": "HABLA CyberLACE Security Engine",
        "enabled": settings["enabled"],
        "mode": settings["mode"],
        "transport": settings["transport"],
        "restUrl": settings["restUrl"],
        "engineAvailable": engine_available or not settings["enabled"],
        "engineError": engine_error,
        "evidence": {
            "recentEvents": len(evidence["events"]),
            "recentDecisions": len(evidence["decisions"]),
            "paths": settings["paths"],
        },
    }
