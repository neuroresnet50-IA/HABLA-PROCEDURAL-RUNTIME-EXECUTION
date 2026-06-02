# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-035

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-035`
- durationSeconds: `115.570587`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.281` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `79.812` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `115.033` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `11.808` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `6.207` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `23.055` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `48.997` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `173.978` | Backend health checked. |
| `observer_status` | `ok` | `30.891` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `7078.205` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `13.719` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1681.546` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `101494.209` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `3385.78` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `278.661` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `25.587` | Response synthesized from stage evidence and runtime output. |
