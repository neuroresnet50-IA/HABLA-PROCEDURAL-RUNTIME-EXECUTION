# HABLA CyberLACE Integration

HABLA CyberLACE Security Engine is integrated as a lateral cognitive security layer for the existing HABLA/LACE harness. It does not replace the orchestrator, LACE, AgentRuntime, worker adapters, security_policy, validator, Observer, scanner, sandbox, or HAR.

## Protection Scope

CyberLACE inspects critical cognitive boundaries:

- prompts and generated worker directives,
- memory/context reads from HABLA preflight or other task context,
- tool and external action intent,
- model/worker output,
- autonomy and trust decisions exposed by the CyberLACE engine.

The existing `orchestrator/security_policy.py` remains authoritative for shell and validation command decisions. CyberLACE adds prompt risk, memory risk, tool risk, output risk and evidence.

## Import Mode

Set:

```bash
export CYBERLACE_ENABLED=true
export CYBERLACE_MODE=monitor
export CYBERLACE_TRANSPORT=import
```

The runtime imports:

```python
from cyberlace import CyberLACEEngine
```

The backend adapter is `backend/cyberlace_integration.py`.

## REST Mode

Run the microservice:

```bash
CYBERLACE_PORT=8088 ./scripts/run_cyberlace_api.sh
```

Then set:

```bash
export CYBERLACE_ENABLED=true
export CYBERLACE_MODE=monitor
export CYBERLACE_TRANSPORT=rest
export CYBERLACE_REST_URL=http://127.0.0.1:8088
```

## Modes

- `off`: no runtime change; decisions allow everything.
- `monitor`: records CyberLACE evidence but never blocks runtime.
- `enforce`: maps `BLOCK`, `QUARANTINE` and `HUMAN_REVIEW` to runtime blocking; maps `REDACT` to sanitized payload when available.

## Flask Endpoints

Registered from `backend/cyberlace_routes.py`:

- `GET /api/cyberlace/health`
- `POST /api/cyberlace/guard/prompt`
- `POST /api/cyberlace/guard/memory`
- `POST /api/cyberlace/guard/tool`
- `POST /api/cyberlace/guard/output`
- `POST /api/cyberlace/guard/external-action`
- `GET /api/cyberlace/evidence/recent`

## Runtime Hooks

`backend/agent_runtime.py` now calls CyberLACE at these boundaries:

- worker directive/prompt before a Codex command is built,
- legacy PTY prompt before process launch,
- control-plane worker command before execution,
- control-plane task output after validation,
- legacy session output before final session emission.

`CYBERLACE_ENABLED=false` leaves the normal path as a no-op.

## Evidence

Decisions are persisted under:

```text
runtime/cyberlace/evidence/cyberlace_events.jsonl
runtime/cyberlace/evidence/cyberlace_decisions.jsonl
runtime/cyberlace/evidence/cyberlace_engine_events.jsonl
runtime/cyberlace/evidence/cyberlace_engine_evidence.jsonl
runtime/cyberlace/logs/cyberlace_failures.jsonl
```

The frontend panel `frontend/src/components/CyberLACEPanel.jsx` reads health and recent evidence without changing existing panels.

## Example

A social media agent tries to publish a harmless post, but memory contains `PIN: 1234`, `CVV: 999`, or a bank account. CyberLACE can detect the context mismatch, redact sensitive output, or require human review/block the external tool in `enforce` mode. The event and decision are stored in JSONL evidence.

## Verification

Run:

```bash
./scripts/test_cyberlace_integration.sh
npm --prefix frontend run build
```

A healthy integration keeps existing agents working, preserves current Flask/SocketIO routes, and only enforces CyberLACE when explicitly enabled.
