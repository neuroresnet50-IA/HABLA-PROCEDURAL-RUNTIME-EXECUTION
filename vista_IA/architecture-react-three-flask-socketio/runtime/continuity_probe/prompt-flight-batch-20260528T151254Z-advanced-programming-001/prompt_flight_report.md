# Prompt Flight Report - prompt-flight-batch-20260528T151254Z-advanced-programming-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001`
- durationSeconds: `235.854849`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.985` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.313` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `7.098` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.093` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.35` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.295` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.215` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `25.813` | Backend health checked. |
| `observer_status` | `ok` | `2.688` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `48.435` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.851` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `44.734` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `235646.465` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `12.615` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `15.372` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `0.802` | Response synthesized from stage evidence and runtime output. |
