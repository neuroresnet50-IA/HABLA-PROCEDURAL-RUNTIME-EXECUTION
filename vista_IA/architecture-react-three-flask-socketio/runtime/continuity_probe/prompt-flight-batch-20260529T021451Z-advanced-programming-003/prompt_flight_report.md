# Prompt Flight Report - prompt-flight-batch-20260529T021451Z-advanced-programming-003

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003-8`
- durationSeconds: `122.883827`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.269` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `7.974` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `28.857` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.208` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `13.382` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `7.062` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `6.157` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `63.547` | Backend health checked. |
| `observer_status` | `ok` | `16.798` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2150.128` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `12.266` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `330.57` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `117858.308` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1144.857` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `483.719` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.001` | Response synthesized from stage evidence and runtime output. |
