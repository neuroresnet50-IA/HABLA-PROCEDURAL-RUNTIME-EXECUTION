# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-003

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-003`
- durationSeconds: `808.157905`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.051` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.464` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `14.968` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.943` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.262` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.089` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `11.248` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `33.094` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `4.252` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `7.281` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4734.269` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.088` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `430.954` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `791143.94` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `4538.649` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `4599.753` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `286.662` | Response synthesized from stage evidence and runtime output. |
