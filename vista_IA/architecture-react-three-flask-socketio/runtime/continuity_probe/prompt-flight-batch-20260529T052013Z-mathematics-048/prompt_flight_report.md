# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-048

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-048`
- durationSeconds: `76.82681`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `12.22` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `12.517` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `56.091` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `14.591` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `18.82` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `11.343` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.369` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `80.532` | Backend health checked. |
| `observer_status` | `ok` | `22.89` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3067.765` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `10.056` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `370.69` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `69349.19` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `3072.659` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `183.469` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `18.482` | Response synthesized from stage evidence and runtime output. |
