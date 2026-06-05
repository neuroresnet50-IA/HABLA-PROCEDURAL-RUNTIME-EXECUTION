# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-010

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-010`
- durationSeconds: `53.876253`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.054` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.844` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `35.796` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.913` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.074` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.097` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `8.346` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `31.365` | Backend health checked. |
| `observer_status` | `ok` | `9.15` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3061.731` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.607` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `293.316` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `49219.174` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `554.523` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `258.651` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `17.666` | Response synthesized from stage evidence and runtime output. |
