# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-046

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-046`
- durationSeconds: `118.705643`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `6.723` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `9.738` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `51.887` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `7.193` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `16.919` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `15.724` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `27.486` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `149.394` | Backend health checked. |
| `observer_status` | `ok` | `70.106` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2382.029` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.146` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `187.343` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `114688.034` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `480.921` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `68.32` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.392` | Response synthesized from stage evidence and runtime output. |
