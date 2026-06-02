# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-012

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-012-2`
- durationSeconds: `91.965506`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.235` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `15.007` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `49.486` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `47.025` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `163.224` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `171.065` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `107.96` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `109.302` | Backend health checked. |
| `observer_status` | `ok` | `27.698` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `9401.919` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `11.468` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `497.884` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `79530.322` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `344.657` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `123.624` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `9.937` | Response synthesized from stage evidence and runtime output. |
