# Prompt Flight Report - prompt-flight-20260527T051024Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `continuity-probe-canary`
- durationSeconds: `0.124381`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.761` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.78` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.237` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.517` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.357` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.466` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.46` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `22.853` | Backend health checked. |
| `observer_status` | `ok` | `3.533` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `57.073` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `1.075` | Response synthesized from stage evidence and runtime output. |
