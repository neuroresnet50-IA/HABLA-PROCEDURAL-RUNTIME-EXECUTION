# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-007

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-007-2`
- durationSeconds: `59.336089`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `2.986` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.207` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `6.862` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.932` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.407` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.654` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `2.69` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `19.686` | Backend health checked. |
| `observer_status` | `ok` | `8.637` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `659.793` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.757` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `170.704` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `57121.677` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1015.246` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `57.101` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `9.83` | Response synthesized from stage evidence and runtime output. |
