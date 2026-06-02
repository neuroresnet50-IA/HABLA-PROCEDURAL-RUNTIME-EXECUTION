# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-023

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-023`
- durationSeconds: `68.15604`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `13.628` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `7.7` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `84.922` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.085` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.82` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `17.007` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `24.193` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `80.915` | Backend health checked. |
| `observer_status` | `ok` | `23.974` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3826.685` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `10.1` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1120.032` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `61722.553` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `412.147` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `175.382` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `14.279` | Response synthesized from stage evidence and runtime output. |
