# Prompt Flight Report - prompt-flight-20260527T072928Z

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-probe-canary`
- durationSeconds: `121.338337`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.145` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.226` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `11.624` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.22` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.474` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `1.393` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `1.144` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `25.764` | Backend health checked. |
| `observer_status` | `ok` | `5.105` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `75.77` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.463` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `118.627` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `120962.502` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `20.216` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `12.037` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `2.004` | Response synthesized from stage evidence and runtime output. |
