# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-001-3`
- durationSeconds: `49.355814`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.077` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.294` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.339` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `0.815` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `3.54` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.183` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.159` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `20.95` | Backend health checked. |
| `observer_status` | `ok` | `4.184` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `42.527` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.516` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `88.652` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `49033.035` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `69.322` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `30.996` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.977` | Response synthesized from stage evidence and runtime output. |
