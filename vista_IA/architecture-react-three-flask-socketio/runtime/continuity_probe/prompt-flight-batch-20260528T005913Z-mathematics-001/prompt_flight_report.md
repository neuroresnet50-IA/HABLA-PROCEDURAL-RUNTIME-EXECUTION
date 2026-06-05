# Prompt Flight Report - prompt-flight-batch-20260528T005913Z-mathematics-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-math-pf-001`
- durationSeconds: `183.535542`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.05` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.237` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `14.602` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.676` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.376` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.842` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `1.138` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `97.973` | Backend health checked. |
| `observer_status` | `ok` | `4.937` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `84.62` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.714` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `52.182` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `177357.089` | Real UI session reached terminal status: stopped. |
| `ui_runtime_truth_read` | `ok` | `1768.874` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `2020.794` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `71.314` | Response synthesized from stage evidence and runtime output. |
