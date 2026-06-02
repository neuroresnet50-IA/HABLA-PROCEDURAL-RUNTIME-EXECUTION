# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-009

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-009-2`
- durationSeconds: `132.600215`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.587` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.927` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `21.008` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.67` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `19.401` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `20.907` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `13.39` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `78.85` | Backend health checked. |
| `observer_status` | `ok` | `29.252` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2135.615` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.856` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `285.413` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `127530.131` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1788.878` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `130.067` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `10.867` | Response synthesized from stage evidence and runtime output. |
