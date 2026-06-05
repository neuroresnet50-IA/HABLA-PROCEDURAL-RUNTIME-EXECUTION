# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-006

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-006`
- durationSeconds: `329.053899`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `24.027` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `38.849` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `156.18` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.321` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.441` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `19.497` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `15.301` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `52.448` | Backend health checked. |
| `observer_status` | `ok` | `18.452` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `7698.684` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `26.998` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `279.338` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `319833.229` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `112.728` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `132.25` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `18.019` | Response synthesized from stage evidence and runtime output. |
