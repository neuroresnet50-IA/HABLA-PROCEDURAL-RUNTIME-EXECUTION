# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-012

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-012`
- durationSeconds: `431.606335`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `90.697` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `16.562` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `65.83` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `7.994` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `34.999` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `13.357` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `7.217` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `91.676` | Backend health checked. |
| `observer_status` | `ok` | `20.662` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `6471.868` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `13.968` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `282.694` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `417743.686` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `5677.842` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `135.805` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.854` | Response synthesized from stage evidence and runtime output. |
