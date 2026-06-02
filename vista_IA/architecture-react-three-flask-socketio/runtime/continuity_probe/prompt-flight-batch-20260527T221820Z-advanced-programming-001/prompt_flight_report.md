# Prompt Flight Report - prompt-flight-batch-20260527T221820Z-advanced-programming-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001`
- durationSeconds: `196.973552`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.558` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.233` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `10.081` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.203` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.998` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `1.041` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `1.022` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `93.503` | Backend health checked. |
| `observer_status` | `ok` | `4.576` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `92.919` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.088` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `183.228` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `196165.562` | Real UI session timed out; stop was requested before continuing. |
| `ui_runtime_truth_read` | `ok` | `45.378` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `116.398` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.98` | Response synthesized from stage evidence and runtime output. |
