# Prompt Flight Report - prompt-flight-20260527T172235Z

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-probe-canary`
- durationSeconds: `1.498816`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.838` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.955` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.526` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.683` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.228` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.858` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.861` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `25.168` | Backend health checked. |
| `observer_status` | `ok` | `4.594` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `96.609` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.414` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `143.403` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `1035.599` | Real UI session reached terminal status: failed. |
| `ui_runtime_truth_read` | `ok` | `29.738` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `49.447` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.851` | Response synthesized from stage evidence and runtime output. |
