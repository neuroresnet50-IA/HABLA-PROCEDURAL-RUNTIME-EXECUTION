# Prompt Flight Report - prompt-flight-20260527T044433Z

- result: `prompt_flight_ok`
- mode: `real_session_guarded`
- project: `continuity-probe-canary`
- durationSeconds: `0.51716`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.836` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.881` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `3.601` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `1.973` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `12.491` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.553` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.477` | Real guarded Task model planned for runtime execution. |
| `backend_health` | `ok` | `54.248` | Backend health checked. |
| `observer_status` | `ok` | `2.626` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `109.931` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is real_session_guarded; guarded runtime session follows. |
| `real_session_bootstrap` | `ok` | `4.956` | Project runtime bootstrapped for guarded prompt execution. |
| `task_queue_persisted` | `ok` | `2.076` | Prompt task persisted and reloaded from task_queue.json. |
| `directive_generated` | `ok` | `29.052` | Directive generated from policy, plan, state, task queue and HABLA guide. |
| `worker_executed` | `ok` | `165.938` | Worker processed the real prompt into response evidence. |
| `validator_passed` | `ok` | `62.895` | Validator confirmed prompt response evidence and validation command. |
| `history_written` | `ok` | `1.993` | Task history event appended for guarded prompt task. |
| `checkpoint_written` | `ok` | `6.723` | Checkpoint written and project state closed for guarded prompt task. |
| `response_synthesized` | `ok` | `3.709` | Response synthesized from stage evidence and runtime output. |
