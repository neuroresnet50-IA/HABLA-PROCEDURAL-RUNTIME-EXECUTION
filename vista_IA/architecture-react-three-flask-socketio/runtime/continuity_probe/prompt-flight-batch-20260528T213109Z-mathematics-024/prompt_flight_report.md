# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-024

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-024`
- durationSeconds: `82.678169`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `5.862` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `12.776` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `29.794` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `14.905` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `14.672` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `13.863` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `10.714` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `49.364` | Backend health checked. |
| `observer_status` | `ok` | `14.353` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1723.014` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.752` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1175.499` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `76983.416` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1719.091` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `212.528` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `16.407` | Response synthesized from stage evidence and runtime output. |
