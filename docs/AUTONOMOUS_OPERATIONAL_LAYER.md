# Autonomous Operational Layer

HABLA should not be understood as a decorative interface around an agent. The visual workbench exists to expose a real operational layer: agents observe runtime state, reason over evidence, select tools, trigger actions, validate results and leave durable memory.

The intended category is not only `chat -> code`. The intended category is:

```text
human intent -> cognitive runtime -> tool control -> real execution -> evidence -> memory -> next action
```

## Core Idea

A capable agentic system needs more than text generation. It needs a body inside the runtime:

- eyes: observe UI, files, scanner output, sandbox state, logs and integrity reports;
- hands: invoke tools, run controlled commands, open workbench panels and trigger runtime actions;
- head: maintain the active task, goal, constraints and execution context;
- brain: plan, reason, compare evidence, decide and recover;
- memory: persist project state, task history, checkpoints, failures and learned tool order;
- voice: communicate with humans through speech, which is the next integration layer.

This is why HABLA should be presented as an operational harness, not as a pretty dashboard.

## What The Workbench Represents

The workbench is a control surface over real runtime systems:

```text
frontend workbench
  -> backend runtime services
  -> orchestrator/control plane
  -> worker adapters
  -> validation tools
  -> sandbox/scanner/integrity/observer artifacts
```

The UI should reveal execution, not simulate it. Panels such as Observer, sandbox, scanner, integrity and workbench should be tied to persisted state and real tool results.

## Tool Control Loop

A practical autonomous loop should look like this:

```text
observe current state
  -> classify what is happening
  -> choose next tool or action
  -> execute through a controlled interface
  -> inspect the result
  -> write evidence
  -> update memory/checkpoint
  -> continue, recover or ask the human
```

For UI-level tools, this can include actions such as:

- click real controls;
- open or close panels;
- start or stop sandbox views;
- request scanner or integrity passes;
- inspect generated files;
- navigate runtime views;
- surface findings to the human.

For system-level tools, this can include:

- task queue operations;
- validation commands allowed by policy;
- sandbox launch and health checks;
- scanner report generation;
- integrity sealing and comparison;
- recovery tasks.

## Agent Body Model

HABLA can describe agent embodiment through runtime functions rather than metaphor alone:

| Body Function | Runtime Meaning | Evidence |
| --- | --- | --- |
| Eyes | Observer, scanner, sandbox, UI state, logs | snapshots, findings, screenshots, reports |
| Hands | tool invocation and UI actions | command logs, action events, artifacts |
| Head | active goal, task, policy and context | directives, state store, queue |
| Brain | planning, ReAct, validation and recovery | task history, LACE log, decisions |
| Memory | persistent project and episodic state | checkpoints, JSONL history, artifacts |
| Voice | spoken human/system interface | planned speech input/output artifacts |

## Voice Integration Direction

The missing layer is real voice communication with the system. This should be implemented as a first-class interface, not as a cosmetic microphone button.

A voice layer should support:

- speech-to-text for human commands;
- intent normalization through HABLA/LACE;
- voice confirmations for risky actions;
- spoken summaries of runtime state;
- text-to-speech responses from the system;
- transcripts stored as evidence;
- clear separation between casual conversation and executable directives.

Recommended voice pipeline:

```text
microphone input
  -> speech-to-text
  -> command/intent classifier
  -> HABLA policy and safety check
  -> runtime directive
  -> tool/action execution
  -> evidence update
  -> spoken response
  -> transcript memory
```

## Safety Boundary

Real tool control requires explicit boundaries. Voice and UI actions should not bypass the harness.

Rules:

- voice commands become normalized runtime directives before execution;
- risky actions require confirmation or policy approval;
- all tool actions produce evidence;
- the agent cannot mark work complete without validation;
- UI control is logged as operational evidence;
- memory stores what was asked, what was done and why.

## Public Positioning

Use this wording when describing the next evolution of the project:

> HABLA is an autonomous operational harness where agents can observe, decide and act through real tools. The visual layer is not decoration; it is the runtime surface for evidence, control and recovery. The next step is voice, so humans can speak to the system and the system can answer with grounded runtime state.
