# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-042

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-042`
- durationSeconds: `64.344834`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.661` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `8.546` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `16.185` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.449` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `4.856` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `5.155` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.985` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `28.615` | Backend health checked. |
| `observer_status` | `ok` | `11.972` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1572.754` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `11.141` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1104.7` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `60705.109` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `516.627` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `128.863` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `4.225` | Response synthesized from stage evidence and runtime output. |
