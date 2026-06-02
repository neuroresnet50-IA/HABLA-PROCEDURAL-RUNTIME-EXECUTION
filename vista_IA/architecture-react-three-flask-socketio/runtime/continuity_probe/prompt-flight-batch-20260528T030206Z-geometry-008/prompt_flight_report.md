# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-008

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-008`
- durationSeconds: `42.152502`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.604` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.516` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `17.746` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.516` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `15.961` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.109` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.26` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `30.271` | Backend health checked. |
| `observer_status` | `ok` | `16.8` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1874.765` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.142` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `149.045` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `39429.72` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `147.531` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `132.294` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `15.378` | Response synthesized from stage evidence and runtime output. |
