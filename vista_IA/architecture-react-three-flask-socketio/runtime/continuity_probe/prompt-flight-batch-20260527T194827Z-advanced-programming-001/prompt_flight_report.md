# Prompt Flight Report - prompt-flight-batch-20260527T194827Z-advanced-programming-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001`
- durationSeconds: `186.02031`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `117.83` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `113.731` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `4.228` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.179` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.976` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.731` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.651` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `23.778` | Backend health checked. |
| `observer_status` | `ok` | `4.579` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1577.874` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.108` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `146.785` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `181605.483` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `708.057` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `847.53` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `9.481` | Response synthesized from stage evidence and runtime output. |
