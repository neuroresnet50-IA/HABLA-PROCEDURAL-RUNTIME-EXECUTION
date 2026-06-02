# Prompt Flight Report - prompt-flight-batch-20260528T182139Z-advanced-programming-001

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-001-3`
- durationSeconds: `489.2943`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.422` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.385` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.564` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `0.809` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `2.772` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.172` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.134` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `29.275` | Backend health checked. |
| `observer_status` | `ok` | `3.874` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `65.011` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.442` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `19.607` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `488234.703` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `385.214` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `38.202` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.626` | Response synthesized from stage evidence and runtime output. |
