# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-029

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-029`
- durationSeconds: `88.135342`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.761` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `9.382` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `27.956` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `7.957` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.781` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `3.458` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `7.724` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `29.494` | Backend health checked. |
| `observer_status` | `ok` | `20.317` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1784.475` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `16.711` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `540.359` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `84061.465` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1084.855` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `112.394` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `10.795` | Response synthesized from stage evidence and runtime output. |
