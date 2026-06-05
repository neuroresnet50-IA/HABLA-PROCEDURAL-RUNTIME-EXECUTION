# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-003

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-003`
- durationSeconds: `36.867941`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.744` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.441` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `10.815` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.106` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `4.67` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.91` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.238` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `17.362` | Backend health checked. |
| `observer_status` | `ok` | `5.188` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1741.882` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `9.483` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `197.307` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `34416.281` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `92.322` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `129.071` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.597` | Response synthesized from stage evidence and runtime output. |
