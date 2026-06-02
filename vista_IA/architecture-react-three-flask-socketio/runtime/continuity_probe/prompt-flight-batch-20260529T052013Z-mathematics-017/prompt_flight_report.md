# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-017

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-017-2`
- durationSeconds: `141.62034`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.049` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.388` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `49.321` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `13.802` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `24.984` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `21.683` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.401` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `73.394` | Backend health checked. |
| `observer_status` | `ok` | `33.263` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `6050.694` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.219` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `424.641` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `132788.661` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1129.8` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `335.906` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `33.125` | Response synthesized from stage evidence and runtime output. |
