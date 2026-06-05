# Prompt Flight Report - prompt-flight-20260527T050808Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `continuity-probe-canary`
- durationSeconds: `0.176317`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.833` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.864` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.854` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.205` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.569` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.514` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.515` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `22.64` | Backend health checked. |
| `observer_status` | `ok` | `3.578` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `107.594` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `1.065` | Response synthesized from stage evidence and runtime output. |
