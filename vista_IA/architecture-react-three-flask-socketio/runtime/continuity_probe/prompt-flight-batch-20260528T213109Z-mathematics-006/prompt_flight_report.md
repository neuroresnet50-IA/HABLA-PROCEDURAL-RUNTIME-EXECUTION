# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-006

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-006`
- durationSeconds: `46.751778`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.231` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `4.73` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `21.78` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.614` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `6.62` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.233` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.11` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `22.414` | Backend health checked. |
| `observer_status` | `ok` | `10.413` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1156.88` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.86` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `122.162` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `43857.397` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1271.467` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `94.128` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.894` | Response synthesized from stage evidence and runtime output. |
