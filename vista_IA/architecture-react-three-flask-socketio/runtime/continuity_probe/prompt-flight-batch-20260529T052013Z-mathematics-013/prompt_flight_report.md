# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-013

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-013-2`
- durationSeconds: `80.248437`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.41` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `11.988` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `26.4` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `17.87` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `14.865` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `5.906` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `9.567` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `56.763` | Backend health checked. |
| `observer_status` | `ok` | `22.675` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1891.591` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `11.484` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `370.381` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `76873.809` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `394.397` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `119.989` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.746` | Response synthesized from stage evidence and runtime output. |
