# Prompt Flight Report - prompt-flight-batch-20260528T185247Z-advanced-programming-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002-4`
- durationSeconds: `44.071615`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `2.082` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.56` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `8.482` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.286` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `4.12` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.589` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.448` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `11.502` | Backend health checked. |
| `observer_status` | `ok` | `2.791` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1798.46` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.25` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `146.412` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `41612.365` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `187.816` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `52.958` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `2.528` | Response synthesized from stage evidence and runtime output. |
