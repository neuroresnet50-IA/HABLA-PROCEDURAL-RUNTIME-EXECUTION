# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-002-2`
- durationSeconds: `51.702684`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `2.728` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.089` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `11.667` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.03` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `18.665` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.32` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `2.603` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `21.139` | Backend health checked. |
| `observer_status` | `ok` | `3.634` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `617.927` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.241` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `136.442` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `50611.409` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `89.727` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `37.015` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `2.498` | Response synthesized from stage evidence and runtime output. |
