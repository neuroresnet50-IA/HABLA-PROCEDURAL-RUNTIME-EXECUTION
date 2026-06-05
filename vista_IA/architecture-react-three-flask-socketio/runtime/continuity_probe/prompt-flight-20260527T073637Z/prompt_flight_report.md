# Prompt Flight Report - prompt-flight-20260527T073637Z

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-probe-canary`
- durationSeconds: `123.02875`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.138` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.24` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `10.873` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.445` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.375` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.642` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.584` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `27.117` | Backend health checked. |
| `observer_status` | `ok` | `4.991` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `55.607` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.514` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `198.248` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `121282.575` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `698.1` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `320.645` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.18` | Response synthesized from stage evidence and runtime output. |
