# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-022

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-022-2`
- durationSeconds: `65.711159`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.419` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `8.612` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `38.368` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `7.107` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.91` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `14.691` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `7.908` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `44.502` | Backend health checked. |
| `observer_status` | `ok` | `13.324` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2189.133` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.249` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `770.333` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `61853.249` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `256.133` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `69.467` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `5.534` | Response synthesized from stage evidence and runtime output. |
