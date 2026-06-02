# Prompt Flight Report - prompt-flight-batch-20260602T202937Z-mixed-sci-prog-002

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-002-2`
- durationSeconds: `990.383195`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `6.812` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.639` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `13.836` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.816` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `74.758` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `172.132` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `51.61` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `206.76` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `9.243` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `5.252` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `526.596` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.264` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `58.926` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `987744.348` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `145.762` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `9.907` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `2.452` | Response synthesized from stage evidence and runtime output. |
