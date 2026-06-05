# Prompt Flight Report - prompt-flight-batch-20260603T171810Z-mixed-sci-prog-006

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-006`
- durationSeconds: `189.993384`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `139.758` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `34.963` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `663.121` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `108.404` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `156.309` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `66.655` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `188.497` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `430.215` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `218.569` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `276.616` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `15326.95` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `42.531` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `3265.191` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `161065.702` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `3127.306` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `1263.358` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `34.711` | Response synthesized from stage evidence and runtime output. |
