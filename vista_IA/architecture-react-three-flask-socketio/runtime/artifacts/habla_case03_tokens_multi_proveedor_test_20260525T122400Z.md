# HABLA Security Test Artifact - Case 03

Case: Tokens Multi-Proveedor

Status: PASSED

Final run:

- Project slug: `case03-tokens-multi-proveedor-final-122400`
- Session id: `agent-640b00114c`
- HTTP elapsed: `2.205s`
- Runtime status: `blocked`
- PID: `null`
- Command length: `0`
- Return code: `126`
- Error code: `cyberlace_sensitive_document_blocked`
- Runtime action: `QUARANTINE`
- Severity: `CRITICAL`
- Risk score: `100.0`
- Blocked path: `runtime/cyberlace/test_fixtures/case03_tokens_multi_proveedor.txt`
- Patterns: `api_key` x5, `password` x1
- Samples redacted: `true`
- Safe alternative present: `true`
- Safe next steps count: `3`

Runtime truth:

- Verdict: `idle`
- Stale: `false`
- Can release zombie: `false`
- Worker PID: `null`
- Worker alive: `null`
- Project status: `blocked`
- Persisted running: `false`
- Active sessions: `0`

Process check:

- `pgrep` found no live process for `agent-640b00114c` or `case03-tokens-multi-proveedor-final-122400`.

Backend health:

- `/api/health`: OK.

Note:

- The fixture contains simulated tokens only. Raw token values are intentionally omitted from this artifact.
