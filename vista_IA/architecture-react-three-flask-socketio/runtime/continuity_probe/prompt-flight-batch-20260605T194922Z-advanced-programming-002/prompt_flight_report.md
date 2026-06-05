# Prompt Flight Report - prompt-flight-batch-20260605T194922Z-advanced-programming-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002-2`
- durationSeconds: `166.704227`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.492` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.588` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `11.578` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.689` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.504` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.817` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.487` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `16.583` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `2.309` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `5.232` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `403.716` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.906` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `863.672` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `160489.909` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1378.767` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `2245.083` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `20.215` | Response synthesized from stage evidence and runtime output. |
