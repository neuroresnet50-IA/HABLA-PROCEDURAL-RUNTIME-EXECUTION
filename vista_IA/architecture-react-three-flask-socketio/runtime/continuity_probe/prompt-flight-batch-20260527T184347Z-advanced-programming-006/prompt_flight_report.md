# Prompt Flight Report - prompt-flight-batch-20260527T184347Z-advanced-programming-006

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-code-pf-006`
- durationSeconds: `99.349004`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `117.202` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `39.76` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `295.911` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `35.281` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `179.036` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `127.044` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `628.641` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `1009.271` | Backend health checked. |
| `observer_status` | `ok` | `315.599` | Observer status checked without starting a mission. |
| `harness_summary` | `failed` | `19037.432` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `805.046` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `6218.654` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `51840.99` | Real UI session reached terminal status: stopped. |
| `ui_runtime_truth_read` | `ok` | `6090.716` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `4585.952` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `136.505` | Response synthesized from stage evidence and runtime output. |
