# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-023

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-023-2`
- durationSeconds: `59.275857`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.168` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `7.376` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `11.701` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.305` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.585` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.386` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.245` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `33.668` | Backend health checked. |
| `observer_status` | `ok` | `11.067` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1408.893` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.761` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `238.344` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `57068.441` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `243.774` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `49.732` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `10.092` | Response synthesized from stage evidence and runtime output. |
