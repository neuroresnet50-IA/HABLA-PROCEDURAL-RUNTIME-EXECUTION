# Prompt Flight Report - prompt-flight-20260527T051036Z

- result: `prompt_flight_ok`
- mode: `safe_canary`
- project: `continuity-probe-canary`
- durationSeconds: `5.070776`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `115.094` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `52.199` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `349.718` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `64.221` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `33.878` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `109.544` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `31.895` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `255.065` | Backend health checked. |
| `observer_status` | `ok` | `51.629` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1455.728` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `ok` | `816.487` | Safe canary continuity run completed. |
| `response_synthesized` | `ok` | `1.157` | Response synthesized from stage evidence and runtime output. |
