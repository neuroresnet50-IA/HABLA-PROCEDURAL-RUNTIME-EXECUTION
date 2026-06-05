# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-010

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-010`
- durationSeconds: `71.9814`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `22.109` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `23.737` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `49.563` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.425` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.957` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `8.119` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `13.904` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `93.512` | Backend health checked. |
| `observer_status` | `ok` | `25.745` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3860.672` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `9.502` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `383.204` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `66199.196` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `470.857` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `226.169` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `17.072` | Response synthesized from stage evidence and runtime output. |
