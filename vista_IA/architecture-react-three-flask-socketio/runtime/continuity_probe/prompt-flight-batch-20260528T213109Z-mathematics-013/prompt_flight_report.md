# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-013

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-013`
- durationSeconds: `413.097706`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `12.881` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `16.913` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `86.393` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `10.761` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `29.653` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `13.743` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `10.803` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `117.9` | Backend health checked. |
| `observer_status` | `ok` | `37.003` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `7837.447` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `26.936` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `571.193` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `403198.676` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `386.367` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `95.116` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.249` | Response synthesized from stage evidence and runtime output. |
