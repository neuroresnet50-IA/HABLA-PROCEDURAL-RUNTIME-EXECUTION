# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-005

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-005`
- durationSeconds: `630.942346`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.453` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.712` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `40.21` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `7.185` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.437` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `13.091` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `6.267` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `36.149` | Backend health checked. |
| `observer_status` | `ok` | `18.85` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1970.658` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.101` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1031.367` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `627344.426` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `93.287` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `48.428` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.029` | Response synthesized from stage evidence and runtime output. |
