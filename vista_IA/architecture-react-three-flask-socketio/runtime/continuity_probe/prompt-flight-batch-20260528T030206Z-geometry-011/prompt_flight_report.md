# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-011

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-011`
- durationSeconds: `69.518569`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `30.05` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `52.529` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `133.878` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.185` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.074` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `7.274` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `73.008` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `44.813` | Backend health checked. |
| `observer_status` | `ok` | `28.986` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4517.498` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `74.098` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `704.168` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `61134.773` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `637.025` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `374.668` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `17.667` | Response synthesized from stage evidence and runtime output. |
