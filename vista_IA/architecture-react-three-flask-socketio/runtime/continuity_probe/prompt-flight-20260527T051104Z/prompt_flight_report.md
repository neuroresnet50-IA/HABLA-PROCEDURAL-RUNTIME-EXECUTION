# Prompt Flight Report - prompt-flight-20260527T051104Z

- result: `prompt_flight_ok`
- mode: `safe_canary`
- project: `continuity-probe-canary`
- durationSeconds: `6.433425`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `32.455` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `136.158` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `184.588` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `71.687` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `70.038` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `71.9` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `130.523` | Diagnostic task model planned without hidden execution. |
| `backend_health` | `ok` | `171.497` | Backend health checked. |
| `observer_status` | `ok` | `62.869` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2904.262` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `ok` | `985.58` | Safe canary continuity run completed. |
| `response_synthesized` | `ok` | `5.203` | Response synthesized from stage evidence and runtime output. |
