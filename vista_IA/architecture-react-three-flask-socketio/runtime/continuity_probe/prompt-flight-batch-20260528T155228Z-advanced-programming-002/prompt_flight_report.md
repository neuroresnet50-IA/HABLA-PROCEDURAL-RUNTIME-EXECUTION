# Prompt Flight Report - prompt-flight-batch-20260528T155228Z-advanced-programming-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002`
- durationSeconds: `38.640032`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.339` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.309` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `10.958` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.627` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.35` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.503` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `5.377` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `18.357` | Backend health checked. |
| `observer_status` | `ok` | `4.321` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `497.499` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.431` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `216.63` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `36778.408` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `221.288` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `582.718` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.087` | Response synthesized from stage evidence and runtime output. |
