# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-004

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-004`
- durationSeconds: `50.494644`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `9.849` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.329` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `24.05` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.207` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.165` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `4.43` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.761` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `34.426` | Backend health checked. |
| `observer_status` | `ok` | `13.182` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1163.331` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `2.91` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `173.843` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `47064.676` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1017.828` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `321.008` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `24.069` | Response synthesized from stage evidence and runtime output. |
