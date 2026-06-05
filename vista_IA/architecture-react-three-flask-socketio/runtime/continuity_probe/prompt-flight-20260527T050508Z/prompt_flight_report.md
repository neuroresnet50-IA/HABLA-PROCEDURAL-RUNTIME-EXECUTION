# Prompt Flight Report - prompt-flight-20260527T050508Z

- result: `prompt_flight_ok`
- mode: `real_session_guarded`
- project: `continuity-probe-canary`
- durationSeconds: `0.393229`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `1.468` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.878` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `1.631` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.112` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `7.89` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.462` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.473` | Real guarded Task model planned for runtime execution. |
| `backend_health` | `ok` | `22.766` | Backend health checked. |
| `observer_status` | `ok` | `3.529` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `55.911` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is real_session_guarded; guarded runtime session follows. |
| `real_session_bootstrap` | `ok` | `4.078` | Project runtime bootstrapped for guarded prompt execution. |
| `task_queue_persisted` | `ok` | `1.763` | Prompt task persisted and reloaded from task_queue.json. |
| `directive_generated` | `ok` | `20.724` | Directive generated from policy, plan, state, task queue and HABLA guide. |
| `worker_executed` | `ok` | `182.308` | Worker processed the real prompt into response evidence. |
| `validator_passed` | `ok` | `46.134` | Validator confirmed prompt response evidence and validation command. |
| `history_written` | `ok` | `1.641` | Task history event appended for guarded prompt task. |
| `checkpoint_written` | `ok` | `4.774` | Checkpoint written and project state closed for guarded prompt task. |
| `response_synthesized` | `ok` | `0.77` | Response synthesized from stage evidence and runtime output. |
