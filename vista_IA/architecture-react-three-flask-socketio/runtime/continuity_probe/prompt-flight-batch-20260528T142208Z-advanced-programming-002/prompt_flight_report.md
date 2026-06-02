# Prompt Flight Report - prompt-flight-batch-20260528T142208Z-advanced-programming-002

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002`
- durationSeconds: `139.049276`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.052` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.743` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `32.04` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.297` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `4.278` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `5.282` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `7.347` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `25.134` | Backend health checked. |
| `observer_status` | `ok` | `7.448` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `765.257` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.161` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `274.668` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `137694.284` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `12.252` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `17.045` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.578` | Response synthesized from stage evidence and runtime output. |
