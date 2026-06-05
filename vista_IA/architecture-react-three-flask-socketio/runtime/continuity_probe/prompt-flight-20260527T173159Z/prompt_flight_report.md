# Prompt Flight Report - prompt-flight-20260527T173159Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `continuity-probe-canary`
- durationSeconds: `0.064431`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.521` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.374` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.219` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `3.622` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.981` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.483` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.376` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `23.107` | Backend health checked. |
| `observer_status` | `ok` | `5.403` | Observer status checked without starting a mission. |
| `harness_summary` | `skipped` | `0.0` | Harness checks disabled. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `0.804` | Response synthesized from stage evidence and runtime output. |
