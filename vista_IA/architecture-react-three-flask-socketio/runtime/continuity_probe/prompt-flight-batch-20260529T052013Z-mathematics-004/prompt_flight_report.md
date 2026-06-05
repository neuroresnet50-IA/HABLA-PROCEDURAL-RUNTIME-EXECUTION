# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-004

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-004-2`
- durationSeconds: `52.985406`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.922` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `9.767` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `25.001` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.041` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `6.461` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `9.562` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `7.553` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `28.097` | Backend health checked. |
| `observer_status` | `ok` | `10.58` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1049.032` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.121` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `178.497` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `51209.643` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `163.146` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `79.774` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.012` | Response synthesized from stage evidence and runtime output. |
