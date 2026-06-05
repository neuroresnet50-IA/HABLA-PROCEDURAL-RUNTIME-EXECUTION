# Prompt Flight Report - prompt-flight-20260527T033802Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `continuity-probe-canary`
- durationSeconds: `1.308872`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `60.328` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `113.235` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `168.37` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `69.368` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.733` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.516` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.525` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `62.094` | Backend health checked. |
| `observer_status` | `ok` | `3.44` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `65.869` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `0.65` | Diagnostic response synthesized from stage evidence. |
