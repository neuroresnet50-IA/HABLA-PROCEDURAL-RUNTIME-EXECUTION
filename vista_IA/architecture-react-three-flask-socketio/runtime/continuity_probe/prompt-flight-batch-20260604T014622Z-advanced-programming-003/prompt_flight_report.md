# Prompt Flight Report - prompt-flight-batch-20260604T014622Z-advanced-programming-003

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003`
- durationSeconds: `375.629864`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `161.211` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `138.33` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `134.165` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `14.925` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `115.892` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `106.795` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `250.901` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `431.717` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `55.654` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `116.848` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `15590.684` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `180.373` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `3633.11` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `346324.064` | Real UI session reached terminal status: stopped. |
| `ui_runtime_truth_read` | `ok` | `1459.22` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `1913.151` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `275.205` | Response synthesized from stage evidence and runtime output. |
