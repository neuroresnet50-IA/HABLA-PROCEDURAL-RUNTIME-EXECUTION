# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-021

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-021`
- durationSeconds: `68.172288`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `11.566` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `16.251` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `23.022` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `9.24` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `17.947` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `6.526` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.264` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `47.478` | Backend health checked. |
| `observer_status` | `ok` | `20.102` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `5392.433` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `9.698` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1123.888` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `59941.642` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1067.276` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `139.391` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `14.326` | Response synthesized from stage evidence and runtime output. |
