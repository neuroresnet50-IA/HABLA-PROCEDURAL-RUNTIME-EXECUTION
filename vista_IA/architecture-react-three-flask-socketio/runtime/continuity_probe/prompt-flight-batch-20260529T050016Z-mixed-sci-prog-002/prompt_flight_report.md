# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-002

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-002`
- durationSeconds: `51.54294`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.187` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `3.014` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `10.772` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.356` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `4.172` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `1.459` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `1.667` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `18.994` | Backend health checked. |
| `observer_status` | `ok` | `5.138` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `460.282` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.321` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `89.427` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `50700.924` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `69.034` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `64.114` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.22` | Response synthesized from stage evidence and runtime output. |
