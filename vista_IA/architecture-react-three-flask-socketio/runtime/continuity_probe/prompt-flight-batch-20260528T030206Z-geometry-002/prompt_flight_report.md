# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-002`
- durationSeconds: `31.763669`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.522` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `9.555` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `21.617` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.071` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.974` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `5.389` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.095` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `29.115` | Backend health checked. |
| `observer_status` | `ok` | `9.543` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `538.504` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.713` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `92.869` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `30773.017` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `32.192` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `53.957` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.6` | Response synthesized from stage evidence and runtime output. |
