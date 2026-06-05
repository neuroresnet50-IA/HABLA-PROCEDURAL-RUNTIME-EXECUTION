# Prompt Flight Report - prompt-flight-batch-20260602T202937Z-mixed-sci-prog-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-001-2`
- durationSeconds: `737.397936`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.664` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.586` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `5.017` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.548` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `3.939` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.688` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.835` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `29.827` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `2.487` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `2.158` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `78.481` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.621` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `87.327` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `735815.597` | Real UI session timed out; stop was requested before continuing. |
| `ui_runtime_truth_read` | `ok` | `310.788` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `673.698` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `2.912` | Response synthesized from stage evidence and runtime output. |
