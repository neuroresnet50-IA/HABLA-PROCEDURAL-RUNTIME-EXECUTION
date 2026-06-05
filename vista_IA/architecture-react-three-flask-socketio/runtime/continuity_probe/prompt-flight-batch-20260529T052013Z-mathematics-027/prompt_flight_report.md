# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-027

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-027`
- durationSeconds: `65.141733`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `9.986` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.713` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `16.079` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `8.509` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `14.531` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `10.103` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `6.493` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `32.708` | Backend health checked. |
| `observer_status` | `ok` | `11.48` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1529.697` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.322` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `277.736` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `61722.058` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1029.177` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `158.945` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `8.369` | Response synthesized from stage evidence and runtime output. |
