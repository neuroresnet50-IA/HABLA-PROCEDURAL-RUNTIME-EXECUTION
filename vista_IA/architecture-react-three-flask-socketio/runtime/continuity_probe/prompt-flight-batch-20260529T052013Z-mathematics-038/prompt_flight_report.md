# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-038

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-038`
- durationSeconds: `390.484234`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.357` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `52.677` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `318.809` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `60.757` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `16.683` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `28.196` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.586` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `145.937` | Backend health checked. |
| `observer_status` | `ok` | `27.899` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `6700.915` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.429` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `403.544` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `380223.924` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1507.028` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `73.029` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `8.704` | Response synthesized from stage evidence and runtime output. |
