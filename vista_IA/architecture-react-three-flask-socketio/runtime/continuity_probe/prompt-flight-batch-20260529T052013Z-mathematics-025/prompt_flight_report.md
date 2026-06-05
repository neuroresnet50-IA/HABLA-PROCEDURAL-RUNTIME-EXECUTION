# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-025

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-025-2`
- durationSeconds: `494.212398`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.374` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `27.085` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `313.526` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `44.205` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `36.627` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `88.549` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `82.911` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `327.081` | Backend health checked. |
| `observer_status` | `ok` | `84.712` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `5128.812` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `8.22` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `394.614` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `485638.605` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `311.459` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `68.627` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.05` | Response synthesized from stage evidence and runtime output. |
