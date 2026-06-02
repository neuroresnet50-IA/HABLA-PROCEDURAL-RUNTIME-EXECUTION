# Prompt Flight Report - pulso-no-bwrap-trace-20260528T0012Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `pulso-no-bwrap-trace`
- durationSeconds: `0.138261`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.149` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.204` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `5.853` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.081` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.538` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.673` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.57` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `81.53` | Backend health checked. |
| `observer_status` | `ok` | `4.922` | Observer status checked without starting a mission. |
| `harness_summary` | `skipped` | `0.0` | Harness checks disabled. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `1.073` | Response synthesized from stage evidence and runtime output. |
