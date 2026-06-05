# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-001`
- durationSeconds: `27.386259`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.29` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.266` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.267` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.11` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `3.708` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.294` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.266` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `48.594` | Backend health checked. |
| `observer_status` | `ok` | `3.508` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `43.882` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.38` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `16.604` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `27075.232` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `38.902` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `42.084` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `4.243` | Response synthesized from stage evidence and runtime output. |
