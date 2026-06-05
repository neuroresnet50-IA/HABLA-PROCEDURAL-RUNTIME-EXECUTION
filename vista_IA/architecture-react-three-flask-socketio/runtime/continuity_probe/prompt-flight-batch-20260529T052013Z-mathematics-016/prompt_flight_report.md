# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-016

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-016-2`
- durationSeconds: `105.660579`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.527` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `15.011` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `48.03` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `12.532` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `21.436` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `11.993` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.965` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `42.121` | Backend health checked. |
| `observer_status` | `ok` | `14.856` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2592.96` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `14.452` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1658.74` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `99878.946` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `590.798` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `206.9` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `27.517` | Response synthesized from stage evidence and runtime output. |
