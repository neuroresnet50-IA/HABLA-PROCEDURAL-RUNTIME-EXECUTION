# Prompt Flight Report - prompt-flight-20260527T050907Z

- result: `prompt_flight_ok`
- mode: `real_session_guarded`
- project: `continuity-probe-canary`
- durationSeconds: `0.381731`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.845` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.893` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.408` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.918` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.94` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.485` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.486` | Real guarded Task model planned for runtime execution. |
| `backend_health` | `ok` | `21.875` | Backend health checked. |
| `observer_status` | `ok` | `3.731` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `57.552` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is real_session_guarded; guarded runtime session follows. |
| `real_session_bootstrap` | `ok` | `6.074` | Project runtime bootstrapped for guarded prompt execution. |
| `task_queue_persisted` | `ok` | `2.056` | Prompt task persisted and reloaded from task_queue.json. |
| `directive_generated` | `ok` | `22.311` | Directive generated from policy, plan, state, task queue and HABLA guide. |
| `worker_executed` | `ok` | `169.273` | Worker processed the real prompt into response evidence. |
| `validator_passed` | `ok` | `41.617` | Validator confirmed prompt response evidence and validation command. |
| `history_written` | `ok` | `1.546` | Task history event appended for guarded prompt task. |
| `checkpoint_written` | `ok` | `4.181` | Checkpoint written and project state closed for guarded prompt task. |
| `response_synthesized` | `ok` | `0.681` | Response synthesized from stage evidence and runtime output. |
