# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-028

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-028`
- durationSeconds: `64.309732`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.804` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `11.808` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `40.718` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.008` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `16.364` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `21.662` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `12.672` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `57.651` | Backend health checked. |
| `observer_status` | `ok` | `17.493` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2029.94` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `10.86` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `233.083` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `60396.148` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `814.013` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `112.871` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `10.931` | Response synthesized from stage evidence and runtime output. |
