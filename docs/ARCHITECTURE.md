# Architecture

HABLA Procedural Runtime Execution is a harness for agentic software work. Its main idea is that an AI worker should not be trusted only because it says a task is done. The harness surrounds replaceable workers with planning, persistence, validation, observability, recovery and security.

## Core Thesis

```text
human intent -> HABLA/LACE -> project runtime -> task queue -> worker -> evidence -> verification -> closure
```

The project is not primarily an editor and not only a chat interface. It is a procedural runtime that treats progress as verified state.

## Planes

## 1. Cognitive Engine

Path:

```text
habla_agentic_engine_v5_1_lace_visual/
```

Responsibilities:

- classify requests semantically;
- plan compound tasks;
- run tools and collect evidence;
- triangulate evidence;
- score confidence by component;
- apply constitutional checks;
- inject LACE policy before final response or closure.

Important files:

```text
runtime/engine.py
runtime/lace.py
runtime/tools.py
runtime/planner.py
runtime/types.py
```

## 2. Control Plane

Path:

```text
vista_IA/architecture-react-three-flask-socketio/orchestrator/
```

Responsibilities:

- normalize project state;
- plan tasks;
- maintain a persistent queue;
- resolve dependencies;
- generate worker directives;
- validate task results;
- recover failed or incomplete work.

Important files:

```text
planner.py
task_queue.py
executor.py
validator.py
recovery.py
state_store.py
directive_generator.py
```

## 3. Worker Plane

The worker is replaceable. Codex, Ollama or another local/remote agent can be treated as an execution backend. HABLA should remain the owner of process state, evidence and closure criteria.

Important areas:

```text
backend/agent_runtime.py
backend/agent_worker_adapters.py
workers/
```

## 4. Verification Plane

Verification turns worker claims into inspected evidence.

Examples:

- expected file checks;
- command validation under a restrictive policy;
- scanner reports;
- sandbox readiness checks;
- integrity reports;
- task result contracts.

Important files:

```text
orchestrator/validator.py
backend/code_scanner_service.py
backend/sandbox_service.py
backend/integrity_service.py
```

## 5. Observer Plane

The Observer reads persisted runtime evidence and emits finite findings. It should not behave like an infinite scanner. A healthy Observer cycle has a trigger, a bounded incident, evidence and a terminal state.

Canonical cycle:

```text
trigger -> incident -> snapshot -> classification -> inspection -> decision -> evidence -> closure
```

Important files:

```text
orchestrator/observer_plane.py
backend/observer_runtime_service.py
frontend/src/components/AppObserverPanel.jsx
```

## 6. Memory And Evidence Plane

HABLA persists state so a project can be resumed, audited and defended after the chat session.

Common evidence areas:

```text
runtime/task_queue.json
runtime/project_state.json
runtime/task_history.jsonl
runtime/failures.jsonl
runtime/checkpoints/
runtime/artifacts/
runtime/logs/
```

## 7. Security Layer

CyberLACE is the security-oriented layer around prompt, memory, tools, output, autonomy and external actions. In the current repository it should be treated as a prototype security engine that can evolve into a policy enforcement boundary.

## Closure Rule

A project should not be marked complete only because a worker finished. Closure should require material evidence:

- completed task queue;
- validated expected files;
- passed validation commands;
- scanner report;
- sandbox readiness when applicable;
- integrity report;
- Observer state without unresolved gates;
- documented LACE cycle evidence.

If any required evidence is missing, the runtime state should remain in a verification, blocked or human-review state.