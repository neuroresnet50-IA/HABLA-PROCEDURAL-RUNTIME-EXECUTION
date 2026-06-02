# Prompt Flight Report - prompt-flight-batch-20260528T185247Z-advanced-programming-003

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003-5`
- durationSeconds: `47.793944`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `12.609` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.596` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `12.219` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.607` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.673` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `8.379` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.293` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `22.731` | Backend health checked. |
| `observer_status` | `ok` | `9.237` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `733.839` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `8.613` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `976.122` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `44482.497` | Real UI session reached terminal status: stopped. |
| `ui_runtime_truth_read` | `ok` | `934.942` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `102.688` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.4` | Response synthesized from stage evidence and runtime output. |
