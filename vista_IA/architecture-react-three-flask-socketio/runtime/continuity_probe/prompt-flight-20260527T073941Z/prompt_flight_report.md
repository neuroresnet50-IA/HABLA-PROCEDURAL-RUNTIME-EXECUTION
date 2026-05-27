# Prompt Flight Report - prompt-flight-20260527T073941Z

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-probe-canary`
- durationSeconds: `123.644003`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `64.779` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `26.94` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `626.048` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `78.368` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `52.893` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `101.182` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `98.81` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `261.656` | Backend health checked. |
| `observer_status` | `ok` | `9.269` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `575.835` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.28` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `17.318` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `120104.215` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `18.873` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `20.894` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.004` | Response synthesized from stage evidence and runtime output. |
