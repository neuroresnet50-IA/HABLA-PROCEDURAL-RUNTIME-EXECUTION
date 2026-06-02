# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-014

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-014-2`
- durationSeconds: `74.583905`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `5.167` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.803` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `34.649` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `9.447` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `13.481` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `13.596` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `11.65` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `40.123` | Backend health checked. |
| `observer_status` | `ok` | `21.994` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2770.951` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `12.653` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `351.8` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `70334.247` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `376.467` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `137.405` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `11.764` | Response synthesized from stage evidence and runtime output. |
