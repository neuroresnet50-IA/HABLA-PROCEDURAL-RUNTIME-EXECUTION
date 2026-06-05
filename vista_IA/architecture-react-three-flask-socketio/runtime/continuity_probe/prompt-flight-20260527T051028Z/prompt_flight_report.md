# Prompt Flight Report - prompt-flight-20260527T051028Z

- result: `prompt_flight_ok`
- mode: `safe_canary`
- project: `continuity-probe-canary`
- durationSeconds: `0.463072`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.837` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.972` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.467` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.747` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `9.128` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.469` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.452` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `21.863` | Backend health checked. |
| `observer_status` | `ok` | `3.59` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `56.625` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `ok` | `339.888` | Safe canary continuity run completed. |
| `response_synthesized` | `ok` | `0.682` | Response synthesized from stage evidence and runtime output. |
