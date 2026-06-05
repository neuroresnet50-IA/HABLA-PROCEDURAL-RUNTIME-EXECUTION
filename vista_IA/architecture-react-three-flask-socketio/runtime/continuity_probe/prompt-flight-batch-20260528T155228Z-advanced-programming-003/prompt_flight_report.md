# Prompt Flight Report - prompt-flight-batch-20260528T155228Z-advanced-programming-003

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003`
- durationSeconds: `50.671957`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.656` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.866` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `22.535` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.561` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `6.735` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.356` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.876` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `32.073` | Backend health checked. |
| `observer_status` | `ok` | `13.817` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1113.426` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.089` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `205.173` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `48856.095` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `63.986` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `83.1` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.052` | Response synthesized from stage evidence and runtime output. |
