# Prompt Flight Report - prompt-flight-batch-20260529T021451Z-advanced-programming-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001-7`
- durationSeconds: `94.654999`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.434` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.403` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `4.201` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.287` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.167` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.46` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.447` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `54.185` | Backend health checked. |
| `observer_status` | `ok` | `4.305` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `82.956` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.82` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `27.37` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `90126.887` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `2511.812` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `901.419` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `15.209` | Response synthesized from stage evidence and runtime output. |
