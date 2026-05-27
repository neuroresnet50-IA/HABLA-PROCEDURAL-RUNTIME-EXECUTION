# HABLA CircuitProbe Report - continuity-20260527T051001Z

- result: `continuity_ok`
- mode: `harness_canary`
- project: `continuity-probe-canary`
- durationSeconds: `0.125089`

| Check | Status | Message |
| --- | --- | --- |
| `prompt_input` | `ok` | Probe input persisted with traceId. |
| `policy_loaded` | `ok` | AGENTS.md loaded through policy_loader. |
| `plan_loaded` | `ok` | PLANS.md loaded through plan_loader. |
| `imports_loaded` | `ok` | Core orchestration imports resolved. |
| `backend_health` | `ok` | Backend health endpoint responded. |
| `task_created` | `skipped` | Skipped because probe mode is not active_canary. |
| `queue_persisted` | `skipped` | Skipped because probe mode is not active_canary. |
| `directive_generated` | `skipped` | Skipped because probe mode is not active_canary. |
| `worker_executed` | `skipped` | Skipped because probe mode is not active_canary. |
| `validator_passed` | `skipped` | Skipped because probe mode is not active_canary. |
| `history_written` | `skipped` | Skipped because probe mode is not active_canary. |
| `checkpoint_written` | `skipped` | Skipped because probe mode is not active_canary. |
| `observer_readable` | `ok` | Observer status is readable without starting a mission. |
| `harness_reachable` | `ok` | Harness training summary endpoint responded. |
| `safety_learning_readable` | `ok` | Safety Learning status endpoint responded. |
| `autopilot_memory` | `ok` | Autopilot persistent run directory is present. |
