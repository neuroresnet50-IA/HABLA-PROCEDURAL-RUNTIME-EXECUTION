# Prompt Flight Report - prompt-flight-batch-20260605T194922Z-advanced-programming-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001-2`
- durationSeconds: `1038.984819`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.595` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.43` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.581` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.259` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.554` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.306` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.266` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `46.577` | Backend health checked. |
| `worker_sandbox_preflight` | `ok` | `3.199` | Worker sandbox preflight passed before Prompt Flight execution. |
| `observer_status` | `ok` | `4.247` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `35.359` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.432` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `36.369` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `timeout` | `1035576.36` | Real UI session timed out; stop was requested before continuing. |
| `ui_runtime_truth_read` | `ok` | `302.184` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `2414.997` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `90.006` | Response synthesized from stage evidence and runtime output. |
