# Prompt Flight Report - prompt-flight-batch-20260605T194922Z-advanced-programming-003

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003-2`
- durationSeconds: `834.102715`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.649` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `21.481` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `143.462` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `52.303` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `81.155` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `39.227` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `59.914` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `136.622` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `5.912` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `53.43` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `16045.092` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `97.974` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `2032.882` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `812821.664` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `888.106` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `30.334` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.048` | Response synthesized from stage evidence and runtime output. |
