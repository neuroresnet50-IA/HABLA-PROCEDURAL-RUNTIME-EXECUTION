# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-024

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-024-2`
- durationSeconds: `71.834114`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.709` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.784` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `18.618` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.463` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.754` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.136` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.107` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `30.413` | Backend health checked. |
| `observer_status` | `ok` | `12.745` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1312.761` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.242` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `200.322` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `69243.764` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `545.094` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `167.735` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `21.195` | Response synthesized from stage evidence and runtime output. |
