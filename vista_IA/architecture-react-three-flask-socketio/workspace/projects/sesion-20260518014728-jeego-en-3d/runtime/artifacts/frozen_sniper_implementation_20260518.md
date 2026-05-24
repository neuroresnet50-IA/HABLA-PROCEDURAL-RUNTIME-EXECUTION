# Frozen Sniper Implementation - 2026-05-18

## Meaning

Frozen Sniper is the safe recovery layer after an integrity attack:

- frozen: preserve the scene and copy current suspicious evidence first;
- sniper: touch only the exact paths reported by integrity findings.

## Implemented Behavior

- Endpoint: `POST /api/projects/<project_id>/integrity/frozen-sniper`.
- Required confirmation: `FROZEN_SNIPER`.
- Report: `runtime/artifacts/frozen_sniper_recovery_report.json`.
- Evidence folder: `runtime/frozen_sniper/<run>/evidence/`.
- Quarantine folder: `runtime/frozen_sniper/<run>/quarantine/`.
- Modified/generated files are restored from `agent_file_manifest.json`.
- Deleted/generated files are rebuilt from `agent_file_manifest.json`.
- Untracked files are moved to quarantine, not deleted.
- After recovery, integrity scan is rerun and included in the report.
- The Workbench alert now exposes a `Frozen Sniper` button.
- The Observer proposes `frozen_sniper_recovery` when integrity findings are active.

## Validation

- `python3 -m py_compile backend/app.py backend/test_code_scanner.py orchestrator/observer_plane.py`
- `python3 -m unittest backend.test_code_scanner backend.test_observer_plane`
- `npm test`
- `npm run build`

Result:

- backend scanner/observer tests: `Ran 19 tests in 0.501s - OK`;
- frontend component test: `agentClosureCertificate tests passed`;
- Vite build succeeded.
