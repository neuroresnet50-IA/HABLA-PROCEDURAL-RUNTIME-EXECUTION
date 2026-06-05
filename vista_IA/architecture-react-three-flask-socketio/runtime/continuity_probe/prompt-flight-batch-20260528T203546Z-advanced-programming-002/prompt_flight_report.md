# Prompt Flight Report - prompt-flight-batch-20260528T203546Z-advanced-programming-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002-6`
- durationSeconds: `39.621389`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `2.489` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.989` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `11.467` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.398` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.373` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.236` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.595` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `20.837` | Backend health checked. |
| `observer_status` | `ok` | `14.174` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1048.018` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1102.561` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `411.84` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `36386.277` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `52.084` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `45.75` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.035` | Response synthesized from stage evidence and runtime output. |
