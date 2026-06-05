# Prompt Flight Report - prompt-flight-batch-20260527T184347Z-advanced-programming-002

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002`
- durationSeconds: `193.355679`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.523` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `12.961` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `35.706` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.082` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.8` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.948` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `28.114` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `42.776` | Backend health checked. |
| `observer_status` | `ok` | `17.688` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `4988.593` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.56` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `198.852` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `180278.407` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `4616.902` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `1818.426` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `370.37` | Response synthesized from stage evidence and runtime output. |
