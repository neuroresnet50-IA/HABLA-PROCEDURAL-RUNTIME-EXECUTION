# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-019

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-math-pf-019`
- durationSeconds: `744.471256`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `16.581` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `30.864` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `60.233` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.81` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.352` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `12.226` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `24.662` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `85.646` | Backend health checked. |
| `observer_status` | `ok` | `19.042` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4385.623` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `10.044` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `2444.46` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `736067.979` | Real UI session timed out; stop was requested before continuing. |
| `ui_runtime_truth_read` | `ok` | `330.05` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `122.336` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.694` | Response synthesized from stage evidence and runtime output. |
