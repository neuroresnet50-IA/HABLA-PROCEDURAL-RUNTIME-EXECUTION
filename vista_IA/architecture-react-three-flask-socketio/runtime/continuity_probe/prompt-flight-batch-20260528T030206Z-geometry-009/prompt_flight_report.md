# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-009

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-009`
- durationSeconds: `43.020854`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `14.443` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `7.612` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `26.535` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `11.047` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `13.995` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `16.923` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `10.636` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `56.878` | Backend health checked. |
| `observer_status` | `ok` | `12.515` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2571.913` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.919` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `223.241` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `38910.389` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `439.321` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `168.052` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `12.098` | Response synthesized from stage evidence and runtime output. |
