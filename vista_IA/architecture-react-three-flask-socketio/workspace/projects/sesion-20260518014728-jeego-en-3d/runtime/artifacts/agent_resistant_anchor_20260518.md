# Agent-Resistant Baseline Anchor - 2026-05-18

## Threat

The concern is not just a human editor. A capable AI agent could rewrite:

- `runtime/artifacts/agent_file_manifest.json`;
- `runtime/artifacts/agent_file_manifest.seal.json`;
- `runtime/baseline_vault/<sha256>/agent_file_manifest.json`;
- `runtime/baseline_vault/baseline_seals.jsonl`.

If all of those are inside the project tree, the agent can make the tampered state look internally consistent.

## Implemented Defense

- A baseline anchor is now written outside the project tree.
- Default anchor root: `.runtime/baseline_anchors/`.
- Configurable root: `HABLA_BASELINE_ANCHOR_ROOT`.
- Current anchor: `.runtime/baseline_anchors/<project>/latest_anchor.json`.
- Anchor ledger: `.runtime/baseline_anchors/<project>/anchors.jsonl`.
- The anchor stores the trusted manifest SHA-256, seal SHA-256 and vault path.
- Integrity scan compares the internal project seal against the external anchor.
- If an agent rewrites the project-local manifest, seal and vault coherently, scan emits `baseline_external_anchor_mismatch`.
- Frozen Sniper can restore the manifest from the externally anchored vault source when valid.

## Optional Signature

If `HABLA_BASELINE_SIGNING_KEY` is set in the backend environment:

- the external anchor is signed with HMAC-SHA256;
- scan verifies the signature;
- unsigned or modified anchors become critical findings.

## Limits

This protects against a project-scoped or policy-following AI worker. If an AI has unrestricted access to the whole filesystem and the signing key, it can still tamper with everything. The strong version requires keeping `HABLA_BASELINE_SIGNING_KEY` outside prompts, worker env, project files and writable runtime.

## Validation

- `python3 -m py_compile backend/app.py backend/test_code_scanner.py`
- `python3 -m unittest backend.test_code_scanner`

Result:

- `Ran 9 tests in 0.515s - OK`

## LACE-20260521-001 Anchor Extension

This task did not replace the external baseline mechanism. It adds a worker-local
evidence anchor for the scoped LACE 01 closure:

- task: `LACE-20260521-001`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-01.md`, context files and manifest files
- product improvement: explicit mode state is now exposed through `aria-pressed`
  and `data-active-mode`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.655`
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-002 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 02 closure:

- task: `LACE-20260521-002`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-02.md`, context files and manifest files
- product improvement: explicit mode metadata is centralized in `MODE_META` and
  synchronized to an accessible hidden summary plus `data-mode-summary`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.6807`
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-003 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 03 closure:

- task: `LACE-20260521-003`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-03.md`, context files and manifest files
- product improvement: WebGL render status is visible in the footer and mirrored
  through `data-render-status` plus `data-render-frames`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.6566`
- retry trace: one static signal check failed because the shell quoting embedded
  literal `\n`; the corrected one-line check passed with exit code 0
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-004 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 04 closure:

- task: `LACE-20260521-004`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-04.md`, context files and manifest files
- product improvement: runtime documentation is now machine-readable through
  `#runtime-contract` and verified through `data-contract-status`,
  `data-contract-input-size` and `data-contract-cycle`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.6825`
- DQN contract: `INPUT_SIZE = 18` remains aligned with the 18 values emitted by
  `buildState()`
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-005 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 05 closure:

- task: `LACE-20260521-005`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-05.md`, context files and manifest files
- product improvement: render cost is now budgeted by explicit mode through
  `pixelRatioCap`, `applyRendererBudget()` and performance HUD/DOM attributes
- performance contract: `#runtime-contract` now declares `laceCycle: 5` and
  `performanceEvidence` for `data-performance-tier`, `data-pixel-ratio` and
  `data-fps-average`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.657`
- mode budget: smoke uses pixel ratio cap `1.15`, build `1.35`, medium `1.50`
  and long-run `1.65`
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-006 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 06 closure:

- task: `LACE-20260521-006`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-06.md`, context files and manifest files
- product improvement: startup resilience now validates required DOM nodes through
  `REQUIRED_HUD_SELECTORS`, reports startup failures through `data-runtime-error`
  and publishes viewport guard evidence through `data-viewport-guard`
- error contract: `#runtime-contract` now declares `laceCycle: 6` and
  `errorEvidence` for `data-dom-contract`, `data-runtime-error` and
  `data-viewport-guard`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.6839`
- internal tooling: health on `http://127.0.0.1:5001` returned `ok=true`; scanner
  timed out without `reportPath`, so local validation evidence remains canonical
  for this micro-task
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-007 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 07 closure:

- task: `LACE-20260521-007`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-07.md`, context files and manifest files
- product improvement: basic query security now validates `mode` and `light`
  through bounded allowlists, duplicate rejection and safe-character checks
- security contract: `#runtime-contract` now declares `laceCycle: 7` and
  `securityEvidence` for `data-query-contract`, `data-mode-source`,
  `data-light-source` and `data-invalid-query-params`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.6576`
- mode policy: `smoke` remains accepted only through explicit `?mode=smoke`;
  invalid query values fall back to safe defaults with DOM evidence
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-008 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 08 closure:

- task: `LACE-20260521-008`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-08.md`, context files and manifest files
- product improvement: drone-war functionality now exposes machine-readable combat
  evidence through `#battle-audit-value`, `combatEvidence`,
  `updateBattleAudit()` and `data-combat-*` attributes
- combat contract: `#runtime-contract` now declares `laceCycle: 8` and
  `combatEvidence` for `data-combat-state`, `data-police-hull`,
  `data-enemy-lock`, `data-mission-escape-risk` and `data-mission-targets`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.6836`
- mode policy: `smoke` remains accepted only through explicit `?mode=smoke`;
  this cycle did not infer smoke from loose text or change mode budgets
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-009 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 09 closure:

- task: `LACE-20260521-009`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-09.md`, context files and manifest files
- product improvement: end-to-end UX evidence is now exposed through
  `#ux-audit-value`, `uxEvidence`, `updateEndToEndUxAudit()` and `data-ux-*`
  attributes
- UX contract: `#runtime-contract` now declares `laceCycle: 9` and `uxEvidence`
  for `data-ux-evidence`, `data-ux-flow`, `data-ux-target` and `data-ux-ready`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `central_non_dark_ratio=0.6576`
- retry trace: one static signal check failed because shell quoting embedded
  escaped newlines; the corrected heredoc check passed with exit code 0
- internal tooling: health on `http://127.0.0.1:5001` returned `ok=true`;
  scanner timed out both with default timeout and `--timeout-seconds 60`, so no
  `reportPath` was claimed
- mode policy: `smoke` remains accepted only through explicit `?mode=smoke`
  or `--mode smoke`; this cycle did not infer smoke from loose text or change
  mode budgets
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`

## LACE-20260521-010 Anchor Extension

This task adds a worker-local evidence anchor for the scoped LACE 10 closure:

- task: `LACE-20260521-010`
- scope: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`,
  `LACE_LOG.md`, `docs/lace_cycles/ciclo-10.md`, context files and manifest files
- product improvement: final LACE review evidence is now exposed through
  `#lace-final-audit-value`, `finalReviewEvidence`, `updateFinalLaceAudit()` and
  `data-lace-*` attributes
- final review contract: `#runtime-contract` now declares `laceCycle: 10` and
  `finalReviewEvidence` for `data-lace-final`, `data-lace-cycles`,
  `data-lace-ready` and `data-lace-review`
- validation: browser smoke returned `ok=true`, `render_mode=webgl`,
  `blockers=[]`, `distance_text="18 m"`, `speed_text="15.0 m/s"` and
  `central_non_dark_ratio=0.6576`
- mode policy: `smoke` remains accepted only through explicit `?mode=smoke`
  or `--mode smoke`; this cycle did not infer smoke from loose text or change
  mode budgets
- control-plane restriction: no edits were made to `runtime/project_state.json`,
  `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`,
  `runtime/checkpoints/`, `runtime/directives/` or `runtime/logs/`
