# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-005

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-005`
- durationSeconds: `53.524497`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `2.25` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `7.822` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `45.433` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `15.611` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `14.784` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `6.983` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `11.248` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `52.604` | Backend health checked. |
| `observer_status` | `ok` | `19.991` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1856.869` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.599` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `154.541` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `50123.342` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `641.649` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `172.919` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `16.103` | Response synthesized from stage evidence and runtime output. |
