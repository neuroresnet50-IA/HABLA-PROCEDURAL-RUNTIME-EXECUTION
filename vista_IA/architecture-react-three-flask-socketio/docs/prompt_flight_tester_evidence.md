# Prompt Flight Tester Evidence

Generated: `2026-05-27T21:37:06Z`

## Why This Tester Matters

The Tkinter Prompt Flight tester was not just a button that sends prompts. It forced a real end-to-end transaction through the system:

1. Tkinter selected a JSON prompt suite.
2. `Run Prompt Flight` sent one case at a time.
3. The backend created a real `ui_session_rest` session.
4. AgentRuntime built task queue state and a worker directive.
5. The worker launched inner Codex.
6. The validator checked disk evidence.
7. Recovery wrote failures/checkpoints.
8. Prompt Flight persisted batch state and monitor evidence.

That full chain exposed the internal truth. A normal chat-style test would not have shown this.

## Case That Revealed The Truth

- Batch: `prompt-flight-batch-20260527T194827Z`
- Suite: `advanced_programming`
- Case: `ADVANCED-PROGRAMMING-001`
- Trace: `prompt-flight-batch-20260527T194827Z-advanced-programming-001`
- Project: `continuity-code-pf-001`
- Expected file: `docs/advanced_programming_case_001.md`
- Visible state: `paused_cleanup_failed` after Prompt Flight monitor timeout

## Truth Revealed

The task did not fail because it was too hard and did not need more time. The inner Codex worker started in the correct workspace, but its execution tools were broken by the Linux sandbox:

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

The inner Codex process returned `0`, but its human output said it could not write the expected file. The validator was correct to fail because `docs/advanced_programming_case_001.md` did not exist.

## Evidence Map

| Evidence | What It Proves |
| --- | --- |
| `runtime/continuity_probe/batches/prompt-flight-batch-20260527T194827Z/batch_state.json` | Batch identity, case status, pause reason. |
| `runtime/continuity_probe/prompt-flight-batch-20260527T194827Z-advanced-programming-001/prompt_flight_report.json` | Stage timeline and outer Prompt Flight timeout. |
| `runtime/continuity_probe/prompt-flight-batch-20260527T194827Z-advanced-programming-001/ui_agent_session_polls.json` | Polls reached `Worker termino; validando salida`. |
| `workspace/projects/continuity-code-pf-001/runtime/directives/RUNTIME-20260527184348-002-SPLIT-002-20260527T194830Z-3324db6f0f0e.md` | Directive requested the correct expected file in the correct workspace. |
| `workspace/projects/continuity-code-pf-001/runtime/task_history.jsonl` | Validation failed because the expected file was missing. |
| `workspace/projects/continuity-code-pf-001/runtime/failures.jsonl` | Inner Codex reported bwrap/apply_patch blockers while returning process code 0. |
| `workspace/projects/continuity-code-pf-001/runtime/logs/agent-997316f222-terminal.log` | Control-plane preflight, worker run, postflight and retry/recovery sequence. |
| `runtime/artifacts/runtime_failure_investigation_20260527T211354Z.md` | First persisted forensic root-cause report. |

## Root Cause

Primary cause: inner Codex execution sandbox failed with bubblewrap/user namespace errors, so the worker could not execute commands or write evidence.

Secondary causes:

- The child Codex returned human Markdown instead of structured success/failure.
- The old control-plane path did not promote those blockers strongly enough.
- Recovery retried/split a task that could not succeed in the current environment.
- Prompt Flight showed an outer monitor timeout, which hid the real infrastructure failure until the tester forced us to inspect disk evidence.

## Repairs Already Applied

- Added `orchestrator/runtime_failure_classifier.py`.
- `orchestrator/recovery.py` now blocks infrastructure failures immediately.
- `workers/codex_worker.py` preserves child-reported blockers.
- `orchestrator/prompt_flight_probe.py` records runtime infrastructure classification.
- `orchestrator/prompt_flight_batch.py` pauses immediately on fatal runtime infrastructure failure.

Validation already run:

```text
python3 -m unittest backend.test_runtime_boundary backend.test_continuity_probe
# OK, 26 tests
```

Replay against the old failure now produces:

```text
fatalInfrastructureFailure=true
recovery decision=block
```

## Remaining Repair Agenda

1. Precreate parent directories for every `expected_files` path before launching a worker.
2. Render directives as evidence-first: create/update expected files before bridge, LACE, scanner or other tooling.
3. Stop split/retry from triggering on loose words like `timeout` inside directives/stdout.
4. Expose validating/failed/retry session states clearly instead of hiding behind `preparing`.
5. Restart backend/Tkinter and run one fresh Prompt Flight case to prove fast failure or successful evidence creation end-to-end.

## Artifact

Structured JSON evidence was persisted at:

`runtime/artifacts/prompt_flight_tester_evidence_20260527T213706Z.json`
