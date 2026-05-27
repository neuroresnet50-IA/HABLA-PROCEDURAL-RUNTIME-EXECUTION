# Prompt Flight Report - prompt-flight-20260527T072105Z

- result: `prompt_flight_blocked`
- mode: `ui_session_rest`
- project: `continuity-probe-canary`
- durationSeconds: `0.307672`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.992` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.017` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `blocked` | `95.126` | CyberLACE blocked the prompt before execution. |
| `policy_loaded` | `ok` | `3.781` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.597` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.492` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.36` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `73.704` | Backend health checked. |
| `observer_status` | `ok` | `4.899` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `74.212` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `skipped` | `0.0` | Skipped because CyberLACE preflight blocked the prompt. |
| `ui_agent_session_posted` | `skipped` | `0.0` | Skipped because CyberLACE preflight blocked the prompt. |
| `ui_agent_session_polled` | `skipped` | `0.0` | Skipped because CyberLACE preflight blocked the prompt. |
| `ui_runtime_truth_read` | `skipped` | `0.0` | Skipped because CyberLACE preflight blocked the prompt. |
| `ui_runtime_artifacts_read` | `skipped` | `0.0` | Skipped because CyberLACE preflight blocked the prompt. |
| `response_synthesized` | `ok` | `1.91` | Response synthesized from stage evidence and runtime output. |
