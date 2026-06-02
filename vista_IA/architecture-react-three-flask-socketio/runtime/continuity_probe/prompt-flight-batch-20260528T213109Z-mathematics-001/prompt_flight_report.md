# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-001-2`
- durationSeconds: `39.448828`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.052` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.707` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.851` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.378` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `4.098` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.204` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.182` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `11.697` | Backend health checked. |
| `observer_status` | `ok` | `1.991` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `29.337` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.587` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `86.395` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `38407.522` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `733.326` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `89.284` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.343` | Response synthesized from stage evidence and runtime output. |
