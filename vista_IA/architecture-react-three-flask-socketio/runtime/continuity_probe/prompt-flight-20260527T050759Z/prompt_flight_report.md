# Prompt Flight Report - prompt-flight-20260527T050759Z

- result: `prompt_flight_ok`
- mode: `safe_canary`
- project: `continuity-probe-canary`
- durationSeconds: `0.45175`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.833` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.857` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.565` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.023` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.841` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.461` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.458` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `21.697` | Backend health checked. |
| `observer_status` | `ok` | `3.817` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `56.953` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `ok` | `334.185` | Safe canary continuity run completed. |
| `response_synthesized` | `ok` | `0.722` | Response synthesized from stage evidence and runtime output. |
