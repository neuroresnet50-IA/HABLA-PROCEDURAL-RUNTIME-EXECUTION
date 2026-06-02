# Runtime Failure Investigation

Generated: 2026-05-27T21:13:54Z

Batch: `prompt-flight-batch-20260527T194827Z`
Case: `ADVANCED-PROGRAMMING-001`
Trace: `prompt-flight-batch-20260527T194827Z-advanced-programming-001`

## Root Cause
The inner Codex worker sandbox failed with bubblewrap/user-namespace errors. The worker could not execute local commands or write `docs/advanced_programming_case_001.md`.

## Evidence
- Missing expected file: `workspace/projects/continuity-code-pf-001/docs/advanced_programming_case_001.md`
- Worker output contained `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`.
- Worker output contained Codex bubblewrap/user namespace warning.
- `apply_patch` inside the inner worker failed to write the target file.
- The old recovery path misclassified this as retry/split territory instead of infrastructure failure.

## Changes Applied
- Added `orchestrator/runtime_failure_classifier.py`.
- `orchestrator/recovery.py` now blocks infrastructure failures immediately.
- `workers/codex_worker.py` preserves child-reported blockers and marks infrastructure failures.
- `orchestrator/prompt_flight_probe.py` exposes runtime infrastructure classification in evidence.
- `orchestrator/prompt_flight_batch.py` pauses immediately on fatal runtime infrastructure failure.

## Validation
- `py_compile`: OK.
- `python3 -m unittest backend.test_runtime_boundary backend.test_continuity_probe`: OK, 26 tests.
- `python3 orchestrator/agent_tools.py health`: statusCode=200, ok=true.
- Replay against old failure: classified as fatal infrastructure failure; recovery decision is `block`.

## Remaining Risk
This prevents false retries and batch overload. It does not by itself make the inner Codex sandbox writable. Actual processing still requires a working inner Codex execution mode or explicit backend environment configuration to bypass the broken bubblewrap sandbox under operator policy.
