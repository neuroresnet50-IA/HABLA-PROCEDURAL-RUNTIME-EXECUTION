# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-019

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-019-2`
- durationSeconds: `267.076963`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.475` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `9.306` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `41.677` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.656` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `13.342` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `10.902` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `12.977` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `33.244` | Backend health checked. |
| `observer_status` | `ok` | `20.279` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2411.585` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `32.82` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `555.178` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `262756.643` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `568.301` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `150.729` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `13.927` | Response synthesized from stage evidence and runtime output. |
