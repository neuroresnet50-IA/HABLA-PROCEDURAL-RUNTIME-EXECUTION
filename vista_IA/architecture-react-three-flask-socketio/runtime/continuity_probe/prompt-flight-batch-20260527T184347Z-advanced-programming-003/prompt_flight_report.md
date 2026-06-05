# Prompt Flight Report - prompt-flight-batch-20260527T184347Z-advanced-programming-003

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-003`
- durationSeconds: `204.304613`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `197.982` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `230.651` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `672.832` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `126.982` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `140.62` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `199.889` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `127.108` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `448.151` | Backend health checked. |
| `observer_status` | `ok` | `244.537` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `15482.03` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `16.278` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `314.634` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `180841.061` | Real UI session did not reach a terminal status before monitor timeout. |
| `ui_runtime_truth_read` | `ok` | `48.896` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `47.178` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `4.086` | Response synthesized from stage evidence and runtime output. |
