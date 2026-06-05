# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-008

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-008`
- durationSeconds: `1094.443564`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `36.968` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `420.412` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1137.661` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `174.878` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `161.899` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `405.956` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `249.016` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `379.151` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `148.276` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `151.019` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `15691.943` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `411.472` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `15111.585` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `1042569.276` | Real UI session timed out; stop was requested before continuing. |
| `ui_runtime_truth_read` | `ok` | `2932.867` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `506.94` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `10.265` | Response synthesized from stage evidence and runtime output. |
