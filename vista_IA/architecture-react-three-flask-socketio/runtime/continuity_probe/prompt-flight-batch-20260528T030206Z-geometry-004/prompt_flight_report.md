# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-004

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-004`
- durationSeconds: `42.161249`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `11.815` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.422` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `12.739` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.8` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.056` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `9.752` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.293` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `28.465` | Backend health checked. |
| `observer_status` | `ok` | `8.976` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1642.945` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.069` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `154.217` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `39789.67` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `101.442` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `128.3` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `9.746` | Response synthesized from stage evidence and runtime output. |
