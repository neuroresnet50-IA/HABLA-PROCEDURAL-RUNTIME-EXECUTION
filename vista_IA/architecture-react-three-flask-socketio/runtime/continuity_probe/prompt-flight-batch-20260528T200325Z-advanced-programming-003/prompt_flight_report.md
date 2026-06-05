# Prompt Flight Report - prompt-flight-batch-20260528T200325Z-advanced-programming-003

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003-6`
- durationSeconds: `535.937942`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.12` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `10.158` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `20.451` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.874` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.559` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.364` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `1.931` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `27.122` | Backend health checked. |
| `observer_status` | `ok` | `5.697` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1028.319` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.417` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `234.228` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `533374.125` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `558.35` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `303.246` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.602` | Response synthesized from stage evidence and runtime output. |
