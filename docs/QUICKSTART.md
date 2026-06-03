# Quickstart

This guide gives a minimal path to inspect and run the main parts of HABLA Procedural Runtime Execution.

HABLA is best treated as a Linux/WSL-first prototype. Some runtime pieces use POSIX APIs such as `pwd` and `pty`, so native Windows execution may require adaptation. The root HABLA BASIC demo only requires Node.js and is the recommended first check.

## Recommended Environment

- OS: Ubuntu, Debian, Linux, or WSL2 on Windows
- Python: 3.11
- Node.js: 20 LTS
- npm: 10+
- Git: 2.40+

## 0. Run The HABLA BASIC Demo

From the repository root:

```bash
npm run habla:demo
npm run habla:verify
```

The demo generates local evidence artifacts:

```text
runtime/demo/project_state.json
runtime/demo/task_queue.json
runtime/demo/artifacts/cyberlace_decision.json
runtime/demo/artifacts/observer_findings.json
runtime/demo/artifacts/closure_certificate.json
runtime/demo/artifacts/demo_summary.md
```

The expected cycle is:

```text
prompt -> plan -> task queue -> CyberLACE guard -> Observer -> closure certificate
```

The verification passes only if:

```text
closure_certificate.status = closed_with_evidence
task_queue_completed = true
cyberlace_critical_findings = 0
observer_terminal = true
validation_passed = true
```

## Repository Areas

```text
habla_agentic_engine_v5_1_lace_visual/              # HABLA V5 cognitive engine + LACE
vista_IA/architecture-react-three-flask-socketio/   # visual workbench, backend, orchestrator
HABLA_CyberLACE_Security_Engine(1)/                 # security layer prototype
```

## 1. Run HABLA Engine V5 Checks

```bash
cd habla_agentic_engine_v5_1_lace_visual
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pytest
python -m pytest -q
```

Optional CLI probes:

```bash
python -m runtime.lace_cli "Crear un juego en Python" --scaffold
python -m runtime.lace_visual_cli --init --prompt "Crear un juego en Python"
python -m chat.chat_cli --provider echo --show-debug
```

## 2. Run The Visual Runtime Backend

```bash
cd vista_IA/architecture-react-three-flask-socketio/backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Default backend URL:

```text
http://localhost:5000
```

## 3. Run The Frontend Workbench

Open a second terminal:

```bash
cd vista_IA/architecture-react-three-flask-socketio/frontend
npm install
npm run dev
```

Default frontend URL:

```text
http://localhost:5173
```

## 4. Build And Test The Frontend

```bash
cd vista_IA/architecture-react-three-flask-socketio/frontend
npm test
npm run build
```

## 5. What To Verify First

A successful first review should confirm:

- the HABLA BASIC demo generates a closure certificate;
- the backend starts without import errors;
- the frontend Vite app builds;
- the workbench can connect to the backend;
- the runtime can load project state and task queue artifacts;
- Observer, scanner, sandbox and integrity panels show persisted evidence instead of only chat output.

## Current Practical Scope

This repository is an advanced research and engineering prototype. The strongest first demo is not a full autonomous multi-hour run. The strongest first demo is a small procedural cycle:

```text
human request -> task plan -> persistent queue -> worker/directive -> validation -> evidence -> Observer/status
```

Once this path runs reproducibly, longer autonomous runs become easier to defend.
