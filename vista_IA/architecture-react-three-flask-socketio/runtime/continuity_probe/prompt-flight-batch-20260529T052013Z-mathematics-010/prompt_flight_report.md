# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-010

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-010-2`
- durationSeconds: `173.724591`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `6.586` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `17.954` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `33.222` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `11.779` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `18.041` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `11.268` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `12.232` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `84.824` | Backend health checked. |
| `observer_status` | `ok` | `206.289` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4013.634` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.043` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `437.275` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `162740.608` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `4663.794` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `265.905` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `21.814` | Response synthesized from stage evidence and runtime output. |
