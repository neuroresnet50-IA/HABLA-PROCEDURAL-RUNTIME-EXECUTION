# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-016

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-016`
- durationSeconds: `64.405753`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.405` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `39.423` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `46.232` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `6.317` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `18.486` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `5.891` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `8.457` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `95.841` | Backend health checked. |
| `observer_status` | `ok` | `33.433` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2155.944` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `20.835` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1569.679` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `59055.659` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `416.853` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `153.556` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `16.323` | Response synthesized from stage evidence and runtime output. |
