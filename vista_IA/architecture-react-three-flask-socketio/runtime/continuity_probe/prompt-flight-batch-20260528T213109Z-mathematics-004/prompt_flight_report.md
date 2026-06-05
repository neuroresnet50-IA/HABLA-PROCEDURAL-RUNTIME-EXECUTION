# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-004

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-004`
- durationSeconds: `51.142064`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.006` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `15.151` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `42.778` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `13.172` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.608` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `17.765` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `10.502` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `49.721` | Backend health checked. |
| `observer_status` | `ok` | `26.643` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3081.592` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `8.416` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `269.503` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `46515.124` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `211.074` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `232.976` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `13.787` | Response synthesized from stage evidence and runtime output. |
