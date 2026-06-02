# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-012

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-012`
- durationSeconds: `97.629013`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `22.171` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `11.902` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `51.409` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `6.104` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `30.971` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `14.048` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `15.337` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `86.419` | Backend health checked. |
| `observer_status` | `ok` | `41.03` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3793.752` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `128.667` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1205.196` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `90110.18` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `824.389` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `300.538` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `30.421` | Response synthesized from stage evidence and runtime output. |
