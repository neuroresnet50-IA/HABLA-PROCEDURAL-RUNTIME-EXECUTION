# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-037

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-037`
- durationSeconds: `127.916968`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.083` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.591` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `45.598` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `9.701` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.605` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `12.712` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `6.758` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `57.982` | Backend health checked. |
| `observer_status` | `ok` | `10.676` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2955.663` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `13.55` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `2208.3` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `119783.317` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `2318.073` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `118.977` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `11.018` | Response synthesized from stage evidence and runtime output. |
