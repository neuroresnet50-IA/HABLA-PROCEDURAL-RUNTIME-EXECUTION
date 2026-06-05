# Prompt Flight Report - prompt-flight-batch-20260528T155228Z-advanced-programming-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001`
- durationSeconds: `945.162505`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.353` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.336` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.865` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.179` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `3.007` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.166` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.142` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `27.951` | Backend health checked. |
| `observer_status` | `ok` | `3.645` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `42.452` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.29` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `32.984` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `944826.174` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `33.303` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `91.217` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `4.634` | Response synthesized from stage evidence and runtime output. |
