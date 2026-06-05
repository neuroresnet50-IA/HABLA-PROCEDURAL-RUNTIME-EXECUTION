# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-003

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-003`
- durationSeconds: `47.983257`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.908` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `4.029` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `13.051` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.801` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.306` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.246` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `6.78` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `26.485` | Backend health checked. |
| `observer_status` | `ok` | `9.329` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2397.2` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.485` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `168.189` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `44640.11` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `215.656` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `146.557` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.31` | Response synthesized from stage evidence and runtime output. |
