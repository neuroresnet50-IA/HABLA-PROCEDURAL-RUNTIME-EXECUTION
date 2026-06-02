# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-039

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-039`
- durationSeconds: `51.53011`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `5.08` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.683` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `21.249` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.008` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.663` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.55` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `6.501` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `21.861` | Backend health checked. |
| `observer_status` | `ok` | `11.224` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1382.6` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.365` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `183.874` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `48802.966` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `771.532` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `108.475` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.695` | Response synthesized from stage evidence and runtime output. |
