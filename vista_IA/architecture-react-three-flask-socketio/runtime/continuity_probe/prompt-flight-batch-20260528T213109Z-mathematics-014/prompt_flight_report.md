# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-014

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-014`
- durationSeconds: `53.116787`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `5.04` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `17.166` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `147.897` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `25.278` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `76.765` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `58.434` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `27.42` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `52.793` | Backend health checked. |
| `observer_status` | `ok` | `25.484` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2400.314` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.934` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `182.286` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `49060.686` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `349.374` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `153.061` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `13.172` | Response synthesized from stage evidence and runtime output. |
