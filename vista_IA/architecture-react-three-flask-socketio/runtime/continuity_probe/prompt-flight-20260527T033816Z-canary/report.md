# HABLA CircuitProbe Report - prompt-flight-20260527T033816Z-canary

- result: `continuity_ok`
- mode: `active_canary`
- project: `continuity-probe-canary`
- durationSeconds: `0.365769`

| Check | Status | Message |
| --- | --- | --- |
| `prompt_input` | `ok` | Probe input persisted with traceId. |
| `policy_loaded` | `ok` | AGENTS.md loaded through policy_loader. |
| `plan_loaded` | `ok` | PLANS.md loaded through plan_loader. |
| `imports_loaded` | `ok` | Core orchestration imports resolved. |
| `backend_health` | `ok` | Backend health endpoint responded. |
| `task_created` | `ok` | Canary task built and validated. |
| `queue_persisted` | `ok` | Task queue persisted and reloaded. |
| `directive_generated` | `ok` | Worker directive generated and persisted. |
| `worker_executed` | `ok` | Codex subprocess worker executed canary command. |
| `validator_passed` | `ok` | Validator confirmed disk evidence and validation command. |
| `history_written` | `ok` | Task history event appended. |
| `checkpoint_written` | `ok` | Continuity checkpoint written and project state updated. |
| `observer_readable` | `ok` | Observer status is readable without starting a mission. |
| `harness_reachable` | `ok` | Harness training summary endpoint responded. |
| `safety_learning_readable` | `ok` | Safety Learning status endpoint responded. |
| `autopilot_memory` | `ok` | Autopilot persistent run directory is present. |
