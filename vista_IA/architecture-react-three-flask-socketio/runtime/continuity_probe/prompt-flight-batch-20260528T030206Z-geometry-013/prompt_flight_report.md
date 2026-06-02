# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-013

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-013`
- durationSeconds: `18.389141`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.021` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `12.262` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `51.553` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `15.836` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `34.62` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.224` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `6.502` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `50.151` | Backend health checked. |
| `observer_status` | `ok` | `35.043` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1799.699` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `6.047` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `508.731` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `14567.161` | Real UI session reached terminal status: stopped. |
| `ui_runtime_truth_read` | `ok` | `210.391` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `119.65` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `11.778` | Response synthesized from stage evidence and runtime output. |
