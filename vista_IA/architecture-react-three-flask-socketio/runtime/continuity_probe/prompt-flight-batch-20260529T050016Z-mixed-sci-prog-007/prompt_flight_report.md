# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-007

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-007`
- durationSeconds: `51.644076`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `6.84` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.247` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `15.638` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.107` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.789` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.612` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `2.505` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `53.086` | Backend health checked. |
| `observer_status` | `ok` | `8.04` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `960.295` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.025` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `147.457` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `49983.311` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `131.007` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `94.083` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `9.719` | Response synthesized from stage evidence and runtime output. |
