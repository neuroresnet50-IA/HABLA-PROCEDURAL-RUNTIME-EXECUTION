# Prompt Flight Report - prompt-flight-20260527T034240Z

- result: `prompt_flight_ok`
- mode: `trace_only`
- project: `continuity-probe-canary`
- durationSeconds: `0.307472`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.516` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.431` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.989` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.531` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `5.751` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.599` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `2.923` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `22.96` | Backend health checked. |
| `observer_status` | `ok` | `4.626` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `221.445` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is trace_only. |
| `response_synthesized` | `ok` | `0.947` | Diagnostic response synthesized from stage evidence. |
