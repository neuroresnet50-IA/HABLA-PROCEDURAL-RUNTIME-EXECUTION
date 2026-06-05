# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-036

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-036`
- durationSeconds: `104.429117`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `30.083` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `43.81` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `108.731` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `52.687` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `24.213` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `80.858` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `20.068` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `190.984` | Backend health checked. |
| `observer_status` | `ok` | `10.795` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4778.918` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `13.81` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `450.821` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `96829.567` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `850.19` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `113.264` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `10.925` | Response synthesized from stage evidence and runtime output. |
