# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-033

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-033`
- durationSeconds: `61.480609`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `12.025` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.212` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `20.332` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.369` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `22.572` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.25` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.096` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `23.261` | Backend health checked. |
| `observer_status` | `ok` | `10.375` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1533.71` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.137` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `277.776` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `58537.784` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `611.821` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `62.393` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.208` | Response synthesized from stage evidence and runtime output. |
