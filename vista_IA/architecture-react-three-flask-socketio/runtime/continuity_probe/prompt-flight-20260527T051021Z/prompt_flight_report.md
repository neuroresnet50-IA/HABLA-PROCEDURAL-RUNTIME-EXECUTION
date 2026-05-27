# Prompt Flight Report - prompt-flight-20260527T051021Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `continuity-probe-canary`
- durationSeconds: `0.133849`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.836` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `1.207` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.423` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.713` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `11.938` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.797` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.828` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `23.362` | Backend health checked. |
| `observer_status` | `ok` | `3.764` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `57.792` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `1.013` | Response synthesized from stage evidence and runtime output. |
