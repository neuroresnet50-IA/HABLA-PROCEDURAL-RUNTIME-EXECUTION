# Prompt Flight Report - prompt-flight-batch-20260528T030206Z-geometry-007

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-geom-pf-007`
- durationSeconds: `45.122343`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `10.719` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `4.87` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `53.196` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `12.567` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `76.553` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `110.944` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `161.072` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `457.184` | Backend health checked. |
| `observer_status` | `ok` | `97.773` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `5190.572` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.833` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `213.328` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `37631.486` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `88.316` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `93.857` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `11.353` | Response synthesized from stage evidence and runtime output. |
