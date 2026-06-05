# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-015

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-015-2`
- durationSeconds: `67.305453`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `5.929` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `10.905` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `47.389` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `6.04` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `20.61` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `24.643` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `15.373` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `65.132` | Backend health checked. |
| `observer_status` | `ok` | `14.638` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2274.724` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `4.95` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `297.999` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `63269.882` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `493.642` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `205.718` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `19.047` | Response synthesized from stage evidence and runtime output. |
