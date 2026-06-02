# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-020

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-020`
- durationSeconds: `278.90008`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `6.708` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `7.711` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `19.065` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `11.429` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.781` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `13.752` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.061` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `52.327` | Backend health checked. |
| `observer_status` | `ok` | `17.843` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2291.23` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `6.294` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `370.33` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `275351.993` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `351.16` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `90.071` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `9.992` | Response synthesized from stage evidence and runtime output. |
