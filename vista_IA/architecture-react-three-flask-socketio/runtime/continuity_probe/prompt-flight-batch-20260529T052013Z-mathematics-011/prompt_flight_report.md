# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-011

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-math-pf-011-2`
- durationSeconds: `743.503966`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `13.565` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `17.406` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `319.262` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `15.459` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `89.84` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `187.481` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `141.199` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `235.26` | Backend health checked. |
| `observer_status` | `ok` | `47.712` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4189.729` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `8.704` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `463.346` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `735788.919` | Real UI session timed out; stop was requested before continuing. |
| `ui_runtime_truth_read` | `ok` | `652.159` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `61.679` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.123` | Response synthesized from stage evidence and runtime output. |
