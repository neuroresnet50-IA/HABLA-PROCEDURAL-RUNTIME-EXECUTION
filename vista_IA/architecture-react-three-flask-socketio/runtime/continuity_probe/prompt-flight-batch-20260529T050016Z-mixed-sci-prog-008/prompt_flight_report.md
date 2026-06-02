# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-008

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-008`
- durationSeconds: `59.609147`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `9.636` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `7.833` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `37.359` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.671` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.48` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `7.973` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `15.711` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `52.25` | Backend health checked. |
| `observer_status` | `ok` | `20.492` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1872.064` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `15.137` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `244.719` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `56912.187` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `78.751` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `55.669` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.004` | Response synthesized from stage evidence and runtime output. |
