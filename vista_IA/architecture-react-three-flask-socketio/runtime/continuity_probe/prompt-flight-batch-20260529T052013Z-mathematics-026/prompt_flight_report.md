# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-026

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-026-2`
- durationSeconds: `71.962118`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.377` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.979` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `16.405` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.371` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.227` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.714` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `7.16` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `27.723` | Backend health checked. |
| `observer_status` | `ok` | `11.72` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1484.382` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `8.063` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `199.406` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `69452.438` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `434.13` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `63.789` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.105` | Response synthesized from stage evidence and runtime output. |
