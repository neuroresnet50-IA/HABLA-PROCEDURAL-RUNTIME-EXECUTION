# Roadmap

This roadmap prioritizes credibility, reproducibility and clear evidence.

## Phase 1: Reproducible Review

Goal: a new developer can run the core project on Linux/WSL.

- Pin frontend dependencies.
- Pin backend dependencies.
- Document Python and Node versions.
- Add quickstart steps.
- Add a minimal smoke test path.
- Document native Windows limitations.

Exit criteria:

- `npm test` passes.
- `npm run build` passes.
- backend starts from documented steps.
- the quickstart is accurate.

## Phase 2: Minimal Procedural Demo

Goal: prove the harness loop without requiring a multi-hour autonomous run.

- Add one sample project runtime fixture.
- Add one sample task queue.
- Add one validation scenario.
- Show Observer status from persisted evidence.
- Produce a small final artifact report.

Exit criteria:

- reviewer can run one command or short sequence;
- generated or loaded evidence is visible;
- project state moves through a clear lifecycle.

## Phase 3: Worker Abstraction Hardening

Goal: make worker replacement explicit.

- Define worker adapter contract.
- Document Codex worker as one adapter, not the core identity.
- Add mock worker for deterministic tests.
- Add failure and retry fixtures.

Exit criteria:

- the harness can validate a task using a mock worker;
- worker-specific failures do not corrupt control-plane state.

## Phase 4: Verification And Security Gates

Goal: make closure defensible.

- Formalize closure states.
- Require scanner and sandbox gates where applicable.
- Store validation command logs.
- Make integrity reports part of closure.
- Add CyberLACE policy examples.

Exit criteria:

- a completed project has a closure certificate;
- missing evidence blocks completion;
- external changes produce visible findings.

## Phase 5: Productization

Goal: make HABLA easier to install, explain and demonstrate.

- Add Docker or devcontainer support.
- Add screenshots and a short demo video path.
- Add CI checks for backend and frontend.
- Add architecture diagrams.
- Reduce monolithic startup complexity.

Exit criteria:

- clean install works from documented environment;
- CI proves basic health;
- README is concise and points to deeper docs.