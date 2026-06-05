# Prompt Flight Report - prompt-flight-20260527T044731Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `continuity-probe-canary`
- durationSeconds: `0.120374`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.508` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.5` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.443` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.969` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.841` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.461` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.441` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `22.221` | Backend health checked. |
| `observer_status` | `ok` | `3.606` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `58.796` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `1.574` | Response synthesized from stage evidence and runtime output. |
