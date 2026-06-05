# Prompt Flight Report - prompt-flight-batch-20260528T200325Z-advanced-programming-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002-5`
- durationSeconds: `38.756081`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `5.614` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `8.912` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `7.503` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.758` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `3.896` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.321` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.297` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `22.705` | Backend health checked. |
| `observer_status` | `ok` | `3.75` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1279.343` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.978` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `107.411` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `36718.299` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `78.586` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `329.407` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.008` | Response synthesized from stage evidence and runtime output. |
