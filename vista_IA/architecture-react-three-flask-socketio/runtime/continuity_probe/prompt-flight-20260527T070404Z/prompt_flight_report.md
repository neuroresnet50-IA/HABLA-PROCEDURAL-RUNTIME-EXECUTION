# Prompt Flight Report - prompt-flight-20260527T070404Z

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-ui-session-real-0700`
- durationSeconds: `192.021376`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `328.119` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `79.859` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `645.878` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `6.21` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `14.946` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `1.977` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `1.802` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `665.073` | Backend health checked. |
| `observer_status` | `ok` | `84.231` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `514.714` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.273` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `119.7` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `180263.836` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `2463.432` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `3300.988` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `573.386` | Response synthesized from stage evidence and runtime output. |
