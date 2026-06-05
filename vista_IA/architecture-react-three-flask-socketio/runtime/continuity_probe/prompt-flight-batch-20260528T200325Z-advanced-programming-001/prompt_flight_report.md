# Prompt Flight Report - prompt-flight-batch-20260528T200325Z-advanced-programming-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001-5`
- durationSeconds: `524.886053`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.332` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.323` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.79` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.185` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `2.983` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.17` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.158` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `27.709` | Backend health checked. |
| `observer_status` | `ok` | `4.375` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `41.093` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.586` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `78.463` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `522391.069` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `405.705` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `1391.084` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `139.464` | Response synthesized from stage evidence and runtime output. |
