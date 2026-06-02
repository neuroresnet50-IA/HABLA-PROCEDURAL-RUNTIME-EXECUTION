# Prompt Flight Report - prompt-flight-batch-20260528T004634Z-mathematics-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-math-pf-001`
- durationSeconds: `223.767704`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.604` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.937` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `8.486` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.861` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.484` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.802` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.872` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `79.225` | Backend health checked. |
| `observer_status` | `ok` | `4.161` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `528.01` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.095` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `32.603` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `219318.369` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `1233.025` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `1570.147` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.465` | Response synthesized from stage evidence and runtime output. |
