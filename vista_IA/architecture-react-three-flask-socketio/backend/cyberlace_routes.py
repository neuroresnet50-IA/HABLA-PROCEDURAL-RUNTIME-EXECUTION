"""Flask routes exposing CyberLACE to the dashboard and runtime."""

from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request

try:
    from cyberlace_integration import (
        cyberlace_after_model_output,
        cyberlace_before_external_action,
        cyberlace_before_memory_read,
        cyberlace_before_prompt,
        cyberlace_before_tool_call,
        cyberlace_health,
        read_recent_cyberlace_evidence,
    )
except ImportError:  # pragma: no cover - package import path during unittest.
    from backend.cyberlace_integration import (
        cyberlace_after_model_output,
        cyberlace_before_external_action,
        cyberlace_before_memory_read,
        cyberlace_before_prompt,
        cyberlace_before_tool_call,
        cyberlace_health,
        read_recent_cyberlace_evidence,
    )


def _payload() -> Dict[str, Any]:
    value = request.get_json(silent=True) or {}
    return value if isinstance(value, dict) else {}


def _dict_field(body: Dict[str, Any], *names: str) -> Dict[str, Any]:
    for name in names:
        value = body.get(name)
        if isinstance(value, dict):
            return value
    return {}


def _emit(socketio: Any, decision: Dict[str, Any]) -> None:
    if socketio is None:
        return
    try:
        socketio.emit(
            "agent:cyberlace",
            {
                "op": "cyberlace_decision",
                "stage": decision.get("stage"),
                "mode": decision.get("mode"),
                "action": decision.get("runtimeAction") or decision.get("action"),
                "riskScore": decision.get("riskScore"),
                "sessionId": decision.get("sessionId"),
                "agentId": decision.get("agentId"),
                "reason": decision.get("reason"),
            },
        )
    except Exception:
        pass


def register_cyberlace_routes(app: Any, socketio: Any = None) -> None:
    @app.get("/api/cyberlace/health")
    def get_cyberlace_health():
        return jsonify(cyberlace_health())

    @app.post("/api/cyberlace/guard/prompt")
    def guard_cyberlace_prompt():
        body = _payload()
        decision = cyberlace_before_prompt(
            str(body.get("agent_id") or body.get("agentId") or "dashboard"),
            str(body.get("user_id") or body.get("userId") or "anonymous"),
            str(body.get("prompt") or ""),
            body.get("context") if isinstance(body.get("context"), dict) else {},
            str(body.get("session_id") or body.get("sessionId") or "dashboard"),
        )
        _emit(socketio, decision)
        return jsonify(decision)

    @app.post("/api/cyberlace/guard/memory")
    def guard_cyberlace_memory():
        body = _payload()
        decision = cyberlace_before_memory_read(
            str(body.get("agent_id") or body.get("agentId") or "dashboard"),
            str(body.get("user_id") or body.get("userId") or "anonymous"),
            str(body.get("memory_text") or body.get("memoryText") or ""),
            _dict_field(body, "task_context", "taskContext"),
            str(body.get("session_id") or body.get("sessionId") or "dashboard"),
        )
        _emit(socketio, decision)
        return jsonify(decision)

    @app.post("/api/cyberlace/guard/tool")
    def guard_cyberlace_tool():
        body = _payload()
        decision = cyberlace_before_tool_call(
            str(body.get("agent_id") or body.get("agentId") or "dashboard"),
            str(body.get("user_id") or body.get("userId") or "anonymous"),
            str(body.get("tool_name") or body.get("toolName") or "unknown_tool"),
            _dict_field(body, "tool_args", "toolArgs"),
            _dict_field(body, "task_context", "taskContext"),
            str(body.get("session_id") or body.get("sessionId") or "dashboard"),
        )
        _emit(socketio, decision)
        return jsonify(decision)

    @app.post("/api/cyberlace/guard/output")
    def guard_cyberlace_output():
        body = _payload()
        decision = cyberlace_after_model_output(
            str(body.get("agent_id") or body.get("agentId") or "dashboard"),
            str(body.get("user_id") or body.get("userId") or "anonymous"),
            str(body.get("output") or ""),
            body.get("context") if isinstance(body.get("context"), dict) else {},
            str(body.get("session_id") or body.get("sessionId") or "dashboard"),
        )
        _emit(socketio, decision)
        return jsonify(decision)

    @app.post("/api/cyberlace/guard/external-action")
    def guard_cyberlace_external_action():
        body = _payload()
        decision = cyberlace_before_external_action(
            str(body.get("agent_id") or body.get("agentId") or "dashboard"),
            str(body.get("user_id") or body.get("userId") or "anonymous"),
            str(body.get("action_type") or body.get("actionType") or "external_action"),
            body.get("payload") if isinstance(body.get("payload"), dict) else {},
            body.get("context") if isinstance(body.get("context"), dict) else {},
            str(body.get("session_id") or body.get("sessionId") or "dashboard"),
        )
        _emit(socketio, decision)
        return jsonify(decision)

    @app.get("/api/cyberlace/evidence/recent")
    def get_recent_cyberlace_evidence():
        try:
            limit = int(request.args.get("limit") or 20)
        except (TypeError, ValueError):
            limit = 20
        return jsonify({"ok": True, **read_recent_cyberlace_evidence(limit=limit)})
