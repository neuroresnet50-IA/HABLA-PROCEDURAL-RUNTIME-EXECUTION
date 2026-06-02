# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-003

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-003-2`
- durationSeconds: `50.706994`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.009` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.65` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `24.434` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.12` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `6.985` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.372` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.766` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `26.856` | Backend health checked. |
| `observer_status` | `ok` | `9.973` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `793.153` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.145` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `142.436` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `49320.056` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `130.471` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `67.695` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.741` | Response synthesized from stage evidence and runtime output. |
