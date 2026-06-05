# Prompt Flight Report - prompt-flight-batch-20260604T014622Z-advanced-programming-002

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002`
- durationSeconds: `110.110299`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `19.496` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `9.764` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `16.121` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `21.434` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `27.369` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `8.495` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `19.131` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `270.936` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `1148.351` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `173.588` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `15425.305` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `53.609` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `157.2` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `82921.21` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `2259.009` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `3811.469` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `227.887` | Response synthesized from stage evidence and runtime output. |
