# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-010

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-010`
- durationSeconds: `77.877066`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.176` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.612` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `32.466` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `8.199` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.265` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `16.845` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `8.627` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `46.69` | Backend health checked. |
| `observer_status` | `ok` | `8.543` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1791.939` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.569` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `236.945` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `74809.859` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `310.609` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `241.247` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `21.801` | Response synthesized from stage evidence and runtime output. |
