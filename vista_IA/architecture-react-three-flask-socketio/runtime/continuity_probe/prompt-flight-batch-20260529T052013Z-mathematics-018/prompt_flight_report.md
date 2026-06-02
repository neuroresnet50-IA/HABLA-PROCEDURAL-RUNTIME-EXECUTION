# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-018

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-018-2`
- durationSeconds: `92.660512`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `35.189` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `20.376` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `133.857` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `27.637` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `35.878` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `17.121` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `34.997` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `303.582` | Backend health checked. |
| `observer_status` | `ok` | `183.08` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `12096.492` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `107.775` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `2582.163` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `74344.882` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `892.145` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `183.091` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `13.935` | Response synthesized from stage evidence and runtime output. |
