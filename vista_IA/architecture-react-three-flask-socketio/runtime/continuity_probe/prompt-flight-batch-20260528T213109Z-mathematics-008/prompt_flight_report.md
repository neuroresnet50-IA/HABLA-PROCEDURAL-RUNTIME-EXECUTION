# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-008

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-008`
- durationSeconds: `52.557122`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.103` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `11.661` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `25.849` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `8.361` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.611` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.188` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.981` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `26.782` | Backend health checked. |
| `observer_status` | `ok` | `9.836` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1247.693` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.571` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `138.999` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `50188.391` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `168.421` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `149.993` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `15.234` | Response synthesized from stage evidence and runtime output. |
