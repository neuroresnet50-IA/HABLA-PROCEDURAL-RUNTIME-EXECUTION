# Prompt Flight Report - prompt-flight-batch-20260528T185247Z-advanced-programming-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001-4`
- durationSeconds: `227.574822`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.912` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.458` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `67.451` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `53.327` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.614` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `1.239` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.955` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `15.899` | Backend health checked. |
| `observer_status` | `ok` | `2.052` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `983.159` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.136` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `97.092` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `225107.175` | Real UI session reached terminal status: stopped. |
| `ui_runtime_truth_read` | `ok` | `680.745` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `23.095` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.395` | Response synthesized from stage evidence and runtime output. |
