# Prompt Flight Report - faro-prompt-flight-live-repair-20260528T0058Z

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `faro-prompt-flight-live-repair-20260528-0058`
- durationSeconds: `108.473281`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `78.917` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `106.771` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `461.494` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `27.286` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `60.061` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `67.071` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `559.934` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `371.993` | Backend health checked. |
| `observer_status` | `ok` | `88.836` | Observer status checked without starting a mission. |
| `harness_summary` | `skipped` | `0.0` | Harness checks disabled. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `72.329` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1774.833` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `97223.935` | Real UI session reached terminal status: stopped. |
| `ui_runtime_truth_read` | `ok` | `1976.871` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `1491.897` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1098.699` | Response synthesized from stage evidence and runtime output. |
