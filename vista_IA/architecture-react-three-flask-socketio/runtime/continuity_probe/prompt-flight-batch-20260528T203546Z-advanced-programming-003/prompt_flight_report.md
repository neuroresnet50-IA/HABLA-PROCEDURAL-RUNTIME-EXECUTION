# Prompt Flight Report - prompt-flight-batch-20260528T203546Z-advanced-programming-003

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003-7`
- durationSeconds: `670.386205`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.985` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.684` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `28.226` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.591` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.176` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `11.463` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.604` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `22.3` | Backend health checked. |
| `observer_status` | `ok` | `12.274` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3827.22` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.348` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `154.384` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `666005.51` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `58.551` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `45.425` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `2.232` | Response synthesized from stage evidence and runtime output. |
