# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-015

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-015`
- durationSeconds: `66.17992`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `19.774` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.692` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `27.28` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `7.998` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.948` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `12.9` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `12.038` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `49.076` | Backend health checked. |
| `observer_status` | `ok` | `53.803` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2780.747` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.527` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `269.355` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `61913.761` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `386.915` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `164.029` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `16.854` | Response synthesized from stage evidence and runtime output. |
