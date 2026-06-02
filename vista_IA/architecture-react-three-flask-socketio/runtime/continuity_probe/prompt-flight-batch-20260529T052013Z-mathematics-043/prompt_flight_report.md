# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-043

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-043`
- durationSeconds: `96.800038`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `5.633` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.223` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `50.823` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `10.374` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `20.954` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.542` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.058` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `49.11` | Backend health checked. |
| `observer_status` | `ok` | `15.828` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3148.52` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `90.534` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1979.15` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `90100.833` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `544.482` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `108.618` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `9.38` | Response synthesized from stage evidence and runtime output. |
