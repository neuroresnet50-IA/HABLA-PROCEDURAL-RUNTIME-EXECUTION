# Prompt Flight Report - prompt-flight-20260527T050815Z

- result: `prompt_flight_ok`
- mode: `real_session_guarded`
- project: `continuity-probe-canary`
- durationSeconds: `0.37582`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `0.826` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `0.892` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `2.555` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `2.133` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `8.478` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `0.501` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `0.566` | Real guarded Task model planned for runtime execution. |
| `backend_health` | `ok` | `22.741` | Backend health checked. |
| `observer_status` | `ok` | `3.735` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `58.204` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is real_session_guarded; guarded runtime session follows. |
| `real_session_bootstrap` | `ok` | `5.594` | Project runtime bootstrapped for guarded prompt execution. |
| `task_queue_persisted` | `ok` | `2.083` | Prompt task persisted and reloaded from task_queue.json. |
| `directive_generated` | `ok` | `23.095` | Directive generated from policy, plan, state, task queue and HABLA guide. |
| `worker_executed` | `ok` | `159.541` | Worker processed the real prompt into response evidence. |
| `validator_passed` | `ok` | `40.319` | Validator confirmed prompt response evidence and validation command. |
| `history_written` | `ok` | `1.751` | Task history event appended for guarded prompt task. |
| `checkpoint_written` | `ok` | `4.905` | Checkpoint written and project state closed for guarded prompt task. |
| `response_synthesized` | `ok` | `0.914` | Response synthesized from stage evidence and runtime output. |
