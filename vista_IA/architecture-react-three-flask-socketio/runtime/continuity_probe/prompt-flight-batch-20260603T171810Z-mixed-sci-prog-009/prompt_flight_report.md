# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-009

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-009`
- durationSeconds: `181.843748`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `12.223` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `66.37` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `180.418` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `23.359` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.35` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `7.8` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `8.048` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `89.39` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `11.063` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `16.451` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1808.231` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.429` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `225.075` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `164824.348` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `8550.235` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `3366.807` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `166.92` | Response synthesized from stage evidence and runtime output. |
