# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-001

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-001`
- durationSeconds: `44.888819`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.835` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.626` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.396` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.504` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.924` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.931` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.774` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `15.24` | Backend health checked. |
| `observer_status` | `ok` | `3.136` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `48.746` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `0.88` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `23.184` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `44603.296` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `34.775` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `28.672` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.767` | Response synthesized from stage evidence and runtime output. |
