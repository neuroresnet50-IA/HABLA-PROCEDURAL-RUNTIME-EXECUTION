# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-001`
- durationSeconds: `135.405047`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.203` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.139` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `5.898` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.173` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `6.63` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.469` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.486` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `57.048` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `3.955` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `3.934` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `68.989` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.933` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `28.412` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `124797.996` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `2420.24` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `3890.639` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `295.828` | Response synthesized from stage evidence and runtime output. |
