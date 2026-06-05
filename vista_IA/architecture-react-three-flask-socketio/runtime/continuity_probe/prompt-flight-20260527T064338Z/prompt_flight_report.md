# Prompt Flight Report - prompt-flight-20260527T064338Z

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-ui-session-canary`
- durationSeconds: `8.773353`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `52.178` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `57.141` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `54.061` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `26.565` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `85.13` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `69.969` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `12.928` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `353.525` | Backend health checked. |
| `observer_status` | `ok` | `97.37` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `5052.074` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.29` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `123.899` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `1042.656` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `52.791` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `67.356` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `11.829` | Response synthesized from stage evidence and runtime output. |
