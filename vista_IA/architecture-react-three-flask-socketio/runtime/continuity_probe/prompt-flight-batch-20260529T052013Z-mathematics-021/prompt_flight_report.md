# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-021

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-021-2`
- durationSeconds: `56.661408`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `140.791` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `17.362` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `33.443` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.843` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `14.798` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `8.751` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.74` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `28.879` | Backend health checked. |
| `observer_status` | `ok` | `9.952` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3188.98` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.028` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `183.814` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `51827.466` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `385.822` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `317.467` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `12.02` | Response synthesized from stage evidence and runtime output. |
