# Prompt Flight Report - prompt-flight-batch-20260528T142208Z-advanced-programming-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001`
- durationSeconds: `39.443003`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.296` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.306` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.596` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.575` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.03` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.503` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.453` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `33.986` | Backend health checked. |
| `observer_status` | `ok` | `2.354` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `35.247` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.482` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `37.776` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `39043.994` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `30.463` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `100.519` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.901` | Response synthesized from stage evidence and runtime output. |
