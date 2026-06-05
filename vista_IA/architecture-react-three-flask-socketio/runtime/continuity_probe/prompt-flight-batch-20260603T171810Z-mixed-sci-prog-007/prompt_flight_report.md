# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-007

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-007`
- durationSeconds: `221.637964`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.813` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `302.39` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `4352.036` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `99.542` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `66.535` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `275.155` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `231.702` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `354.329` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `81.337` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `545.494` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `15556.039` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `25.713` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `4354.554` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `181717.375` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `8147.71` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `2104.035` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `121.727` | Response synthesized from stage evidence and runtime output. |
