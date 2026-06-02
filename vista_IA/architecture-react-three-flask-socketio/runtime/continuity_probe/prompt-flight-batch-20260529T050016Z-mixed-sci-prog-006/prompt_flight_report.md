# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-006

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-006`
- durationSeconds: `53.777247`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `2.811` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.025` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `16.443` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.563` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `22.462` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `7.285` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `30.29` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `18.569` | Backend health checked. |
| `observer_status` | `ok` | `6.475` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `769.21` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.933` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `157.459` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `52421.557` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `110.441` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `53.187` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `2.786` | Response synthesized from stage evidence and runtime output. |
