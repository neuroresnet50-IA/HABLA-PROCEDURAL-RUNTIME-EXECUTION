# Prompt Flight Report - prompt-flight-batch-20260528T162124Z-advanced-programming-003

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003-3`
- durationSeconds: `549.598164`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `9.763` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `16.832` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `36.645` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.341` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `20.973` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `6.326` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.866` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `41.875` | Backend health checked. |
| `observer_status` | `ok` | `28.894` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3610.209` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `9.075` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `150.101` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `544240.249` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `931.958` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `22.267` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.267` | Response synthesized from stage evidence and runtime output. |
