# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-041

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-041`
- durationSeconds: `74.373137`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `6.18` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.415` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `41.33` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `8.557` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.984` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.481` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.688` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `40.883` | Backend health checked. |
| `observer_status` | `ok` | `12.008` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1529.668` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `6.089` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `196.625` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `71717.024` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `436.664` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `71.152` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.0` | Response synthesized from stage evidence and runtime output. |
