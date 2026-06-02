# Prompt Flight Report - prompt-flight-batch-20260527T221820Z-advanced-programming-002

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002`
- durationSeconds: `170.408896`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.582` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.646` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `22.859` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.743` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.502` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.091` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.176` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `32.935` | Backend health checked. |
| `observer_status` | `ok` | `11.632` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `480.386` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.926` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `261.34` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `164744.385` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `1955.311` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `1497.275` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `39.241` | Response synthesized from stage evidence and runtime output. |
