# Prompt Flight Report - faro-prompt-flight-e2e-20260528T0024Z

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `faro-prompt-flight-e2e-20260528`
- durationSeconds: `263.384617`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.137` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.917` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `7.448` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.308` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.026` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.499` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.476` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `61.574` | Backend health checked. |
| `observer_status` | `ok` | `5.006` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `79.95` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.628` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `31.252` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `259202.478` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `948.204` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `1016.23` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.298` | Response synthesized from stage evidence and runtime output. |
