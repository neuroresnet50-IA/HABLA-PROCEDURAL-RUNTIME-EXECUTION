# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-009

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-009`
- durationSeconds: `62.229224`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.578` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `9.675` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `32.251` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.936` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.81` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `8.191` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.46` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `60.065` | Backend health checked. |
| `observer_status` | `ok` | `16.173` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1779.655` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `13.044` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `225.021` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `59597.953` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `149.983` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `96.401` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.934` | Response synthesized from stage evidence and runtime output. |
