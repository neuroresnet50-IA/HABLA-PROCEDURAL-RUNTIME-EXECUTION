# Prompt Flight Report - prompt-flight-batch-20260528T213109Z-mathematics-007

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-007`
- durationSeconds: `42.411063`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.475` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `55.443` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `12.211` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.22` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.308` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `7.28` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `4.631` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `36.756` | Backend health checked. |
| `observer_status` | `ok` | `12.887` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1007.95` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.225` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `892.949` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `39906.214` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `112.136` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `41.388` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.268` | Response synthesized from stage evidence and runtime output. |
