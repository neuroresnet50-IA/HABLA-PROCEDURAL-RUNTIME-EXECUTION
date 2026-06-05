# Prompt Flight Report - prompt-flight-batch-20260527T184347Z-advanced-programming-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001`
- durationSeconds: `182.759203`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.336` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.69` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `11.042` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.74` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.2` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `1.548` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.525` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `26.915` | Backend health checked. |
| `observer_status` | `ok` | `4.527` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `83.49` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.084` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `121.901` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `180855.124` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `538.649` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `359.499` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.3` | Response synthesized from stage evidence and runtime output. |
