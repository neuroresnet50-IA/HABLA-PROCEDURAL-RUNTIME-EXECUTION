# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-005

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-005`
- durationSeconds: `776.479528`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `105.621` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `63.164` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1317.112` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `44.229` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `60.624` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `125.987` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `145.57` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `275.222` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `44.34` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `163.118` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `15665.493` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `29.892` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `9234.206` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `736977.989` | Real UI session timed out; stop was requested before continuing. |
| `ui_runtime_truth_read` | `ok` | `1634.311` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `4978.559` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `257.216` | Response synthesized from stage evidence and runtime output. |
