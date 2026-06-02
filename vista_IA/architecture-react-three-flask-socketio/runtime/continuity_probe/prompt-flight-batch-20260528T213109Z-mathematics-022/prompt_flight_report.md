# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-022

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-022`
- durationSeconds: `66.340215`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `19.799` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `21.064` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `23.465` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `6.284` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `14.078` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `9.609` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.838` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `78.818` | Backend health checked. |
| `observer_status` | `ok` | `27.395` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2599.304` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `12.788` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `374.797` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `61809.223` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `733.951` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `169.063` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `11.256` | Response synthesized from stage evidence and runtime output. |
