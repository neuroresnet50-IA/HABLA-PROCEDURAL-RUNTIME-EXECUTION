# Agent Internal Tools Contract

## Purpose

Codex workers can use HABLA internal tools as practical assistance while they
work on a project. The tools are not prompt text; they are executable commands
that call the local backend and persist an audit trail.

Canonical CLI:

```text
python3 orchestrator/agent_tools.py <command>
```

Audit log:

```text
runtime/agent_tool_invocations.jsonl
```

Output mode:

- Default output is compact JSON for agents: status, paths, summaries and a
  small sample of active findings.
- Use `--full` only when the complete backend payload is required for a bounded
  task. Full output can be large and should not be requested by default.

## Commands

```text
python3 orchestrator/agent_tools.py health
```

Checks whether the local backend is alive.

```text
python3 orchestrator/agent_tools.py observer-status
```

Reads Observer state. This must not start a mission or wake an idle Observer.

```text
python3 orchestrator/agent_tools.py observe
```

Asks Observer for one explicit observation. Use only when a task needs current
diagnostic context.

```text
python3 orchestrator/agent_tools.py scanner <projectSlug>
```

Runs the final code scanner and returns the persisted scanner report.

```text
python3 orchestrator/agent_tools.py integrity <projectSlug>
```

Runs file integrity scan against baseline/ledger evidence.

```text
python3 orchestrator/agent_tools.py findings <projectSlug>
```

Builds or reads Observer findings for a project.

```text
python3 orchestrator/agent_tools.py sniper <projectSlug> --dry-run
```

Runs Frozen Sniper as a non-destructive preview.

```text
python3 orchestrator/agent_tools.py sniper <projectSlug> --confirm FROZEN_SNIPER
```

Runs Frozen Sniper recovery. This is only allowed with human confirmation or an
explicit recovery policy.

## Required Agent Behavior

- Read the JSON output.
- Report `statusCode`, `ok`, report paths and real blockers.
- Do not claim a tool passed unless the returned JSON proves it.
- Prefer `sniper --dry-run` before any recovery.
- Never use Sniper recovery to hide unexplained changes.
- If the backend is down, record the blocker and use local validation as a
  fallback.

## Activation Model

Observer is allowed to work when:

- a project mission starts or resumes,
- Scanner is requested,
- Integrity scan is requested,
- Frozen Sniper is requested,
- the user explicitly requests `observe`.

Observer must not start work when:

- the browser reconnects,
- the UI polls status,
- an agent reads `observer-status`,
- no project task or explicit tool request exists.

## Tool Roles

```text
Observer: coordinates evidence and tool reasoning.
Scanner: reads code and persists scanner report.
Integrity: compares current files against baseline and ledger.
Sniper: recovers/quarantines only under safety rules.
Worker: makes bounded code changes.
Control plane: decides task state, retries and closure.
```
