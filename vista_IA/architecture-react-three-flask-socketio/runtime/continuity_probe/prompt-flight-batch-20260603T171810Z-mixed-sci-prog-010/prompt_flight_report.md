# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-010

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-010`
- durationSeconds: `357.900953`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `96.7` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `39.516` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `227.404` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `29.719` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `32.888` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `101.176` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `23.637` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `226.28` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `44.655` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `42.204` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `16905.872` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `163.995` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `6615.486` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `307417.112` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `failed` | `15496.498` | runtime-truth request failed. |
| `ui_runtime_artifacts_read` | `ok` | `4268.43` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `357.195` | Response synthesized from stage evidence and runtime output. |
