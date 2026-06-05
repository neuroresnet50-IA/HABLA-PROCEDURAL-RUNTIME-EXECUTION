# Prompt Flight Report - prompt-flight-batch-20260528T182139Z-advanced-programming-003

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003-4`
- durationSeconds: `479.54654`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.822` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.958` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `231.53` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.858` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `6.185` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.384` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `2.696` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `23.676` | Backend health checked. |
| `observer_status` | `ok` | `6.35` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1120.195` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.384` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `616.042` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `475660.603` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `648.673` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `264.805` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `10.014` | Response synthesized from stage evidence and runtime output. |
