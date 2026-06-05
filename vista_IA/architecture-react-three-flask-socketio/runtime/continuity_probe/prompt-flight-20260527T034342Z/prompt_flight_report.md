# Prompt Flight Report - prompt-flight-20260527T034342Z

- result: `prompt_flight_ok`
- mode: `safe_canary`
- project: `continuity-probe-canary`
- durationSeconds: `0.476958`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.866` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.967` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.557` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.712` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.801` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.458` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.452` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `22.65` | Backend health checked. |
| `observer_status` | `ok` | `3.13` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `57.782` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `ok` | `353.643` | Safe canary continuity run completed. |
| `response_synthesized` | `ok` | `0.488` | Diagnostic response synthesized from stage evidence. |
