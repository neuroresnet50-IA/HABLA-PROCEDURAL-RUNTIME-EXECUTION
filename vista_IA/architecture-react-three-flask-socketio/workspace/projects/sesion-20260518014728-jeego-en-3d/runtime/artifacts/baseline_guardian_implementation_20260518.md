# Baseline Guardian Implementation - 2026-05-18

## Problem

Frozen Sniper can only recover safely if `agent_file_manifest.json` is trustworthy. If an attacker corrupts the baseline itself, recovery could restore malicious content.

## Implemented Protection

- Every new agent file manifest is sealed.
- Seal path: `runtime/artifacts/agent_file_manifest.seal.json`.
- Vault copy path: `runtime/baseline_vault/<manifest_sha256>/agent_file_manifest.json`.
- Seal ledger path: `runtime/baseline_vault/baseline_seals.jsonl`.
- Integrity scan verifies the seal before trusting the baseline.
- If the manifest changes without a matching seal, scan emits `baseline_manifest_tampered`.
- If the seal is missing, scan emits `baseline_unsealed`.
- If the seal changes, scan emits `baseline_seal_tampered`.
- If the vault copy changes, scan emits `baseline_vault_tampered`.
- Frozen Sniper can restore a tampered baseline from the vault when the seal and vault are still valid.

## Important Limit

This is tamper-evident protection, not cryptographic immunity against an attacker with full filesystem control. A fully trusted design still needs an external anchor or secret-backed signature outside the writable project tree.

## Validation

- `python3 -m py_compile backend/app.py backend/test_code_scanner.py`
- `python3 -m unittest backend.test_code_scanner`

Result:

- `Ran 8 tests in 0.610s - OK`
