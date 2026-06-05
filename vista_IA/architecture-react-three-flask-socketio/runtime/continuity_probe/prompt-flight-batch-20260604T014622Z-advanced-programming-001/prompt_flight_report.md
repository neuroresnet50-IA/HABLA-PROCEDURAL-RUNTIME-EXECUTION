# Prompt Flight Report - prompt-flight-batch-20260604T014622Z-advanced-programming-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001`
- durationSeconds: `732.113445`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.144` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.142` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `6.973` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.252` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.332` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.879` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.728` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `81.223` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `3.802` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `4.29` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `69.882` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.96` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `70.344` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `729146.004` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `1585.102` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `546.962` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `15.34` | Response synthesized from stage evidence and runtime output. |
