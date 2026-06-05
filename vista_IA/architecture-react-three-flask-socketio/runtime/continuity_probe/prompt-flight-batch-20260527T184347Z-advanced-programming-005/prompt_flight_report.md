# Prompt Flight Report - prompt-flight-batch-20260527T184347Z-advanced-programming-005

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-005`
- durationSeconds: `236.299607`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `346.797` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `98.003` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1470.344` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `554.817` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `423.816` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `48.205` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `459.567` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `1154.949` | Backend health checked. |
| `observer_status` | `ok` | `609.677` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `16610.623` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `744.128` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `7720.352` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `181459.817` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `4775.943` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `7912.05` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `329.022` | Response synthesized from stage evidence and runtime output. |
