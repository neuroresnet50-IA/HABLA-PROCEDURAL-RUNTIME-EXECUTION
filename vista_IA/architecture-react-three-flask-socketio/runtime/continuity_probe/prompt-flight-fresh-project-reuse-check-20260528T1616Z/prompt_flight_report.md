# Prompt Flight Report - prompt-flight-fresh-project-reuse-check-20260528T1616Z

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003-2`
- durationSeconds: `22.788644`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.312` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.177` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.827` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `0.899` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `2.667` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.17` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.151` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `31.681` | Backend health checked. |
| `observer_status` | `ok` | `3.869` | Observer status checked without starting a mission. |
| `harness_summary` | `skipped` | `0.0` | Harness checks disabled. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.401` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `53.013` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `22484.397` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `36.26` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `57.076` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.736` | Response synthesized from stage evidence and runtime output. |
