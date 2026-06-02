# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-045

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-045`
- durationSeconds: `88.6888`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.796` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `4.0` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `26.496` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `8.583` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `16.109` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.599` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `17.369` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `40.056` | Backend health checked. |
| `observer_status` | `ok` | `16.332` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1524.026` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `6.315` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `247.31` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `85718.43` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `614.617` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `134.513` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `10.785` | Response synthesized from stage evidence and runtime output. |
