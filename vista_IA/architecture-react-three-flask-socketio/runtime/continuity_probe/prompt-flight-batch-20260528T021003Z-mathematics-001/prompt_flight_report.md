# Prompt Flight Report - prompt-flight-batch-20260528T021003Z-mathematics-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-math-pf-001`
- durationSeconds: `188.944817`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.085` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.137` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `6.282` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.028` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.294` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.463` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.422` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `57.12` | Backend health checked. |
| `observer_status` | `ok` | `4.304` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `49.733` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.009` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `102.768` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `186094.354` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `1184.27` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `911.368` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `4.048` | Response synthesized from stage evidence and runtime output. |
