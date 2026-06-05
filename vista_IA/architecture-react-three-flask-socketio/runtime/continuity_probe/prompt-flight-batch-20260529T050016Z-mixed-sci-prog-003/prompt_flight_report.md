# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-003

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-003`
- durationSeconds: `54.507117`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.517` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.335` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `15.763` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.481` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `6.516` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.819` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `2.296` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `32.357` | Backend health checked. |
| `observer_status` | `ok` | `12.319` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `907.758` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.241` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `164.912` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `52998.08` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `90.85` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `85.18` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.151` | Response synthesized from stage evidence and runtime output. |
