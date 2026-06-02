# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-025

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-math-pf-025`
- durationSeconds: `122.830564`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `12.52` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `8.242` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `45.826` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.902` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.339` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `9.422` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `17.489` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `78.001` | Backend health checked. |
| `observer_status` | `ok` | `44.176` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `16157.76` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `26.882` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `2034.819` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `101234.839` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1321.714` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `222.466` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `29.003` | Response synthesized from stage evidence and runtime output. |
