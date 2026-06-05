# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-017

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-017`
- durationSeconds: `68.579918`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `15.889` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.379` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `60.841` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `11.899` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.738` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `12.956` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.924` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `62.363` | Backend health checked. |
| `observer_status` | `ok` | `19.864` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4283.206` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `15.311` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `428.646` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `62022.241` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `783.363` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `176.464` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `12.698` | Response synthesized from stage evidence and runtime output. |
