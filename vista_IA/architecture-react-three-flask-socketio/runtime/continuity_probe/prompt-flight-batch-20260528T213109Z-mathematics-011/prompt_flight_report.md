# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-011

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-011`
- durationSeconds: `96.573029`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `20.125` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `75.678` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `171.227` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `55.56` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `58.966` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `22.318` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `18.959` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `74.987` | Backend health checked. |
| `observer_status` | `ok` | `26.7` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4420.211` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `76.97` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1195.752` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `88261.749` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `507.984` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `178.343` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `24.351` | Response synthesized from stage evidence and runtime output. |
