# HABLA CircuitProbe Report - continuity-local-debug

- result: `continuity_ok`
- mode: `active_canary`
- project: `continuity-probe-canary`
- durationSeconds: `0.271626`

| Check | Status | Message |
| --- | --- | --- |
| `prompt_input` | `ok` | Probe input persisted with traceId. |
| `policy_loaded` | `ok` | AGENTS.md loaded through policy_loader. |
| `plan_loaded` | `ok` | PLANS.md loaded through plan_loader. |
| `imports_loaded` | `ok` | Core orchestration imports resolved. |
| `backend_health` | `skipped` | No baseUrl supplied. |
| `task_created` | `ok` | Canary task built and validated. |
| `queue_persisted` | `ok` | Task queue persisted and reloaded. |
| `directive_generated` | `ok` | Worker directive generated and persisted. |
| `worker_executed` | `ok` | Codex subprocess worker executed canary command. |
| `validator_passed` | `ok` | Validator confirmed disk evidence and validation command. |
| `history_written` | `ok` | Task history event appended. |
| `checkpoint_written` | `ok` | Continuity checkpoint written and project state updated. |
| `observer_readable` | `skipped` | No baseUrl supplied. |
| `harness_reachable` | `skipped` | Harness checks disabled by request. |
| `safety_learning_readable` | `skipped` | Harness checks disabled by request. |
| `autopilot_memory` | `skipped` | Harness checks disabled by request. |
