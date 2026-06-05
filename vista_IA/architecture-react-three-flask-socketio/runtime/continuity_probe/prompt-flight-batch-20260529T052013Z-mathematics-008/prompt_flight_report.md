# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-008

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-008-2`
- durationSeconds: `123.699143`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `3.385` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.805` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `11.075` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `6.493` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `16.764` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `18.606` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `10.111` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `57.451` | Backend health checked. |
| `observer_status` | `ok` | `17.66` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1494.335` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `3.612` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `288.678` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `119665.331` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `1318.836` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `89.257` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `6.999` | Response synthesized from stage evidence and runtime output. |
