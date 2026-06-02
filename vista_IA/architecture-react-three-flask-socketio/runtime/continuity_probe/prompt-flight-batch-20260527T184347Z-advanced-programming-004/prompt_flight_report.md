# Prompt Flight Report - prompt-flight-batch-20260527T184347Z-advanced-programming-004

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-004`
- durationSeconds: `192.694794`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.662` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.236` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `18.529` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.115` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.408` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `5.33` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.471` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `36.113` | Backend health checked. |
| `observer_status` | `ok` | `11.081` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `729.412` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.325` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `205.872` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `180715.335` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `2262.257` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `6549.968` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `302.552` | Response synthesized from stage evidence and runtime output. |
