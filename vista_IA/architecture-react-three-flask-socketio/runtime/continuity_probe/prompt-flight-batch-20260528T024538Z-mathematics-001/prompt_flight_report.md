# Prompt Flight Report - prompt-flight-batch-20260528T024538Z-mathematics-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-001`
- durationSeconds: `32.567809`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.172` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.145` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.578` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `0.82` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `2.63` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.195` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.191` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `30.176` | Backend health checked. |
| `observer_status` | `ok` | `3.037` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `50.662` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.877` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `32.418` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `32095.69` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `244.286` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `47.735` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `2.657` | Response synthesized from stage evidence and runtime output. |
