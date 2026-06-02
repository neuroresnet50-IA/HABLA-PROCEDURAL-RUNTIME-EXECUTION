# Project Status

This document separates implemented evidence from intended direction.

## Current Classification

HABLA Procedural Runtime Execution is an advanced research and engineering prototype for agentic project execution. It contains real runtime code, visual workbench code, orchestration modules, verification logic and evidence artifacts. It should not yet be presented as a fully packaged end-user product.

## Implemented Signals

The repository includes concrete implementations for:

- HABLA Engine V5 request flow;
- LACE policy loading and cycle logging;
- persistent task queue validation;
- dependency-aware task ordering;
- task result validation against expected files;
- restrictive validation command policy;
- Observer state and finding generation;
- integrity manifests, hashes and seal artifacts;
- React/Vite/Three.js frontend workbench;
- Flask/Socket.IO backend runtime;
- example generated project evidence.

## Strongest Technical Claim

The strongest defensible claim is:

> HABLA is a procedural harness around AI workers. It turns agent work into persistent, inspectable and verifiable project state.

This is stronger and safer than claiming it is a finished autonomous software engineer.

## Known Constraints

- The runtime is currently Linux/WSL-first because some backend pieces use POSIX APIs such as `pwd` and `pty`.
- Several subsystems are prototypes and need packaging work.
- Some dependency declarations should be pinned for reproducibility.
- The README is broad and ambitious; reviewers will benefit from smaller focused docs.
- The most credible demo should be small, repeatable and evidence-based.

## Recommended Demo Boundary

The first public demo should prove this path:

```text
prompt -> normalized task -> persistent queue -> worker directive -> validation -> artifact -> Observer status
```

Avoid making the first demo depend on a long autonomous run. Long runs are impressive after the smaller path is reproducible.

## What Counts As Done For A First Public Release

- Quickstart works on a clean Linux/WSL machine.
- Frontend builds with pinned dependencies.
- Backend starts with documented Python version and pinned dependencies.
- At least one minimal task queue scenario can be loaded and validated.
- Project status clearly says what is prototype, what is implemented and what is roadmap.
- README links to architecture, quickstart, status and roadmap.

## Suggested Label

Use this public positioning:

```text
Research prototype: procedural runtime and verification harness for AI software workers.
```