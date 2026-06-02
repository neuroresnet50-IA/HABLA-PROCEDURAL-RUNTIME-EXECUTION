# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-009

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-009`
- durationSeconds: `58.25521`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.623` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `16.156` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `17.614` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.302` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.384` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `5.632` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `9.898` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `42.72` | Backend health checked. |
| `observer_status` | `ok` | `20.726` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3103.26` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `10.491` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `198.306` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `53905.444` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `355.638` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `158.724` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `13.492` | Response synthesized from stage evidence and runtime output. |
