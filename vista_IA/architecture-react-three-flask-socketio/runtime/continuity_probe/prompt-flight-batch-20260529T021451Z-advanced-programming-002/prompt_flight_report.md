# Prompt Flight Report - prompt-flight-batch-20260529T021451Z-advanced-programming-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-code-pf-002-7`
- durationSeconds: `104.032841`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `100.027` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `80.595` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `66.724` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.296` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `13.517` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `10.445` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `13.991` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `51.828` | Backend health checked. |
| `observer_status` | `ok` | `21.351` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1055.944` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.8` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `256.903` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `99200.196` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `928.253` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `962.95` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `52.531` | Response synthesized from stage evidence and runtime output. |
