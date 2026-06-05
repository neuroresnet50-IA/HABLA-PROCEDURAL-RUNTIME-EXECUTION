# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-004

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-004`
- durationSeconds: `769.281803`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `396.429` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `102.492` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1049.306` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `106.189` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `581.105` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `262.631` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `418.055` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `610.105` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `72.153` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `97.881` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `16047.117` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `148.132` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1801.197` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `736482.501` | Real UI session timed out; stop was requested before continuing. |
| `ui_runtime_truth_read` | `ok` | `2238.222` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `2636.915` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `187.963` | Response synthesized from stage evidence and runtime output. |
