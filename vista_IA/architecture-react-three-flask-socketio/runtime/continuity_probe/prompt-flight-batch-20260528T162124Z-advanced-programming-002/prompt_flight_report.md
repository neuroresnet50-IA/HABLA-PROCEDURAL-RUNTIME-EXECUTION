# Prompt Flight Report - prompt-flight-batch-20260528T162124Z-advanced-programming-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002-2`
- durationSeconds: `41.44808`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `6.191` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.094` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `39.838` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.527` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.699` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.317` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `1.82` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `16.886` | Backend health checked. |
| `observer_status` | `ok` | `8.472` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `669.535` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `125.57` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `220.538` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `39175.609` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `99.672` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `128.092` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.376` | Response synthesized from stage evidence and runtime output. |
