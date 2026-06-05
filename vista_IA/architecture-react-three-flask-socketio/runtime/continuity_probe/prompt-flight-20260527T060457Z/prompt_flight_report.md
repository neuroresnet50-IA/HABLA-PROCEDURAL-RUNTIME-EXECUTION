# Prompt Flight Report - prompt-flight-20260527T060457Z

- result: `prompt_flight_ok`
- mode: `real_session_guarded`
- project: `continuity-probe-canary`
- durationSeconds: `0.731065`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.029` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `2.128` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `3.698` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `4.826` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.154` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `1.195` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `1.82` | Real guarded Task model planned for runtime execution. |
| `backend_health` | `ok` | `28.918` | Backend health checked. |
| `observer_status` | `ok` | `5.271` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `139.699` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is real_session_guarded; guarded runtime session follows. |
| `real_session_bootstrap` | `ok` | `9.87` | Project runtime bootstrapped for guarded prompt execution. |
| `task_queue_persisted` | `ok` | `3.959` | Prompt task persisted and reloaded from task_queue.json. |
| `directive_generated` | `ok` | `41.462` | Directive generated from policy, plan, state, task queue and HABLA guide. |
| `worker_executed` | `ok` | `292.698` | Worker processed the real prompt into response evidence. |
| `validator_passed` | `ok` | `80.371` | Validator confirmed prompt response evidence and validation command. |
| `history_written` | `ok` | `2.818` | Task history event appended for guarded prompt task. |
| `checkpoint_written` | `ok` | `9.959` | Checkpoint written and project state closed for guarded prompt task. |
| `response_synthesized` | `ok` | `3.241` | Response synthesized from stage evidence and runtime output. |
