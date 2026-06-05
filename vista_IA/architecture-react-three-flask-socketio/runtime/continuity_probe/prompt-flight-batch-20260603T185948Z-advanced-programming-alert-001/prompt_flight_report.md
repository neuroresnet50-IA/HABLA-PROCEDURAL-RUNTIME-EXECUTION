# Prompt Flight Report - prompt-flight-batch-20260603T185948Z-advanced-programming-alert-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-alert-antihack-pf-001`
- durationSeconds: `665.610238`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.853` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.777` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `4.406` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.358` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.69` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.425` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.339` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `16.939` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `3.051` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `1.995` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `28.648` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.231` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `90.065` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `665052.182` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `92.196` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `18.699` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.206` | Response synthesized from stage evidence and runtime output. |
