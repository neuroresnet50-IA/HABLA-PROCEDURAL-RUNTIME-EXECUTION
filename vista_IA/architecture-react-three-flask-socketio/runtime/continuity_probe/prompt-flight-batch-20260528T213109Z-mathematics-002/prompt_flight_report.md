# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-002`
- durationSeconds: `40.558276`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.899` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.295` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `22.351` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.348` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.18` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.65` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `2.987` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `27.67` | Backend health checked. |
| `observer_status` | `ok` | `10.979` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `943.797` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.771` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `143.467` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `38898.407` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `181.323` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `83.439` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `7.014` | Response synthesized from stage evidence and runtime output. |
