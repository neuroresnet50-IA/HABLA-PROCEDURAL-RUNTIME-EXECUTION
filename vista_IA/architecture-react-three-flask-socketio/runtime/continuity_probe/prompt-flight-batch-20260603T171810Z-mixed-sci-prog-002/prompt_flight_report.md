# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-002

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-002`
- durationSeconds: `1002.774763`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `352.447` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `59.333` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2167.754` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `78.186` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `366.896` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `174.62` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `121.856` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `335.225` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `86.179` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `88.508` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `6998.283` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.337` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `269.506` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `985572.363` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `959.232` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `464.731` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `4.875` | Response synthesized from stage evidence and runtime output. |
