# Prompt Flight Report - prompt-flight-20260527T064928Z

- result: `prompt_flight_failed`
- mode: `ui_session_rest`
- project: `continuity-ui-session-real-0649`
- durationSeconds: `124.730167`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.012` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.057` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `8.674` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.316` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.491` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.824` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.699` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `78.327` | Backend health checked. |
| `observer_status` | `ok` | `4.357` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `84.531` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `1.044` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `32.242` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `failed` | `116434.679` | Real UI session reached terminal status: blocked. |
| `ui_runtime_truth_read` | `ok` | `2181.892` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `4776.4` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `85.461` | Response synthesized from stage evidence and runtime output. |
