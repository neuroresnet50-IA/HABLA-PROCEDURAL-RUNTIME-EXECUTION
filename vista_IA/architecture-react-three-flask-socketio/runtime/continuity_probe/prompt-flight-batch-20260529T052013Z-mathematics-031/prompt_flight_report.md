# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-031

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-031`
- durationSeconds: `66.538418`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `14.47` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `9.336` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `52.383` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `8.592` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `25.518` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `5.201` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `18.705` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `40.724` | Backend health checked. |
| `observer_status` | `ok` | `15.955` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1672.313` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.743` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `158.463` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `63660.74` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `508.367` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `80.288` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.52` | Response synthesized from stage evidence and runtime output. |
