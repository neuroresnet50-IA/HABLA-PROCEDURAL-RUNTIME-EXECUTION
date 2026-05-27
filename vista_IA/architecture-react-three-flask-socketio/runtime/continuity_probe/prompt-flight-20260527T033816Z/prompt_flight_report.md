# Prompt Flight Report - prompt-flight-20260527T033816Z

- result: `prompt_flight_ok`
- mode: `safe_canary`
- project: `continuity-probe-canary`
- durationSeconds: `0.486876`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.383` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.36` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.103` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.466` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.757` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.349` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.338` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `21.547` | Backend health checked. |
| `observer_status` | `ok` | `3.948` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `62.831` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `ok` | `368.016` | Safe canary continuity run completed. |
| `response_synthesized` | `ok` | `0.865` | Diagnostic response synthesized from stage evidence. |
