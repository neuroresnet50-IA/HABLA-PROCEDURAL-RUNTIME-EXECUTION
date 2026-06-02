# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-006

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-006-2`
- durationSeconds: `258.962837`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `11.399` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `17.055` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `57.164` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `6.676` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `107.739` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `86.485` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `15.712` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `74.524` | Backend health checked. |
| `observer_status` | `ok` | `33.562` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `7850.428` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.198` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `320.037` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `249606.657` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `176.049` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `34.284` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `1.502` | Response synthesized from stage evidence and runtime output. |
