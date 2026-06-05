# Prompt Flight Report - faro-prompt-flight-exact-20260528T0029Z

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `faro-prompt-flight-exact-20260528`
- durationSeconds: `268.472692`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.255` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.135` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `6.971` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.493` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `14.329` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `1.172` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.993` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `28.883` | Backend health checked. |
| `observer_status` | `ok` | `4.197` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `91.643` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.071` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `144.021` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `258402.611` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `5866.978` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `2327.294` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `55.019` | Response synthesized from stage evidence and runtime output. |
