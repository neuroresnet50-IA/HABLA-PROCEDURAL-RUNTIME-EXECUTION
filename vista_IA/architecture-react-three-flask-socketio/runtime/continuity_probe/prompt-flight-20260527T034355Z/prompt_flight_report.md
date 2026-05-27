# Prompt Flight Report - prompt-flight-20260527T034355Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `continuity-probe-canary`
- durationSeconds: `0.13306`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.845` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.842` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.405` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.745` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.653` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.821` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.834` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `24.236` | Backend health checked. |
| `observer_status` | `ok` | `3.835` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `55.891` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `0.893` | Diagnostic response synthesized from stage evidence. |
