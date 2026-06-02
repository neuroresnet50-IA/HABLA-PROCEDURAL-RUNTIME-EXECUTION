# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-044

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-044`
- durationSeconds: `286.555898`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `28.736` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `25.44` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `56.353` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `6.608` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `17.484` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.28` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `11.143` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `62.545` | Backend health checked. |
| `observer_status` | `ok` | `22.591` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `3619.004` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `90.956` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `1632.435` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `279479.791` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `522.713` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `80.029` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.814` | Response synthesized from stage evidence and runtime output. |
