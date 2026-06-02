# Prompt Flight Report - prompt-flight-batch-20260528T203546Z-advanced-programming-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001-6`
- durationSeconds: `484.350525`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.425` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.351` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.931` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.147` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `3.567` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.244` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.241` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `35.526` | Backend health checked. |
| `observer_status` | `ok` | `2.393` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `41.429` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.213` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `57.181` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `484069.152` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `40.251` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `39.967` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.62` | Response synthesized from stage evidence and runtime output. |
