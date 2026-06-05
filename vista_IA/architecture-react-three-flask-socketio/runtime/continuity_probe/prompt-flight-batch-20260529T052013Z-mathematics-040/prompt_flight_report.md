# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-040

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-040`
- durationSeconds: `68.299786`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `5.321` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `4.34` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `16.403` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.347` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.248` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.061` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `6.484` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `33.354` | Backend health checked. |
| `observer_status` | `ok` | `12.371` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2062.702` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.531` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `279.964` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `64251.293` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1161.049` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `119.966` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `13.484` | Response synthesized from stage evidence and runtime output. |
