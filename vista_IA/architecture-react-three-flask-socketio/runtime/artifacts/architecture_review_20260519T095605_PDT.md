# Revision arquitectonica - 2026-05-19 09:56:05 PDT

## Solicitud
Revisar la arquitectura del repositorio:
`/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio`.

## Lecturas base
- `AGENTS.md`
- `PLANS.md`
- `ULTIMO_CONTEXTO_CODEX.md`
- `recuperacioncontexto.md`
- `docs/observer_engine_algorithm.md`
- modulos principales en `backend/`, `orchestrator/`, `workers/`, `frontend/src/`, `schemas/` y `runtime/`.

## Mapa de arquitectura real
- Control plane: `orchestrator/`, integrado por `backend/agent_runtime.py`.
- Worker plane: `workers/codex_worker.py` y ruta Codex CLI/PTY en `backend/agent_runtime.py`.
- Verification plane: `orchestrator/validator.py`, `orchestrator/real_validation.py`, scanner/integridad/sandbox en `backend/app.py`.
- Memory plane: `orchestrator/state_store.py`, runtimes por proyecto en `workspace/projects/*/runtime/`, `runtime/artifacts/`, `runtime/checkpoints/`, `runtime/directives/`.
- Observer plane: `orchestrator/observer_plane.py`, con incidentes finitos, timeline y findings persistidos.
- UI plane: React/Vite en `frontend/src/`, especialmente `App.jsx`, `AgentStudio.jsx`, `CodeWorkbench.jsx` y `ArchitectureCanvas.jsx`.
- Microservicio lateral: `microservice-js/`, que publica un snapshot a `/api/architecture`.

## Hallazgos
1. Alto - Drift entre contrato Python y schema JSON de `ProjectState`.
   - `orchestrator/contracts.py` permite `human_alignment_pending` y `pending_human_alignment_tasks`.
   - `backend/human_alignment_review.py` escribe esos campos al recibir feedback HAR.
   - `schemas/project_state.schema.json` no incluye ese estado ni ese campo, con `additionalProperties=false`.
   - Riesgo: cualquier validador externo basado en `schemas/` rechazara estados que el runtime Python considera validos.

2. Alto - El `StateStore` por defecto apunta a `runtime/`, pero ahi faltan `project_state.json` y `task_queue.json`.
   - `orchestrator/state_store.py` usa `repo_root/runtime` por defecto.
   - En disco no existen `runtime/project_state.json` ni `runtime/task_queue.json`.
   - El runtime funcional vive por proyecto, por ejemplo `workspace/projects/sesion-20260518014728-jeego-en-3d/runtime/`.
   - Riesgo: herramientas/CLI que instancien `StateStore()` sin `runtime_dir` fallaran o leeran un plano de memoria equivocado.

3. Medio - `backend/app.py` concentra demasiados planos.
   - El archivo tiene 6791 lineas y mezcla rutas HTTP/socket, cache de grafo, scanner final, integridad forense, Frozen Sniper, sandbox, editor, observer snapshot, repair, reset y blanqueo.
   - Riesgo: cambios en un plano pueden romper otros planos y dificultan pruebas enfocadas.
   - Direccion sugerida: extraer `scanner_service.py`, `integrity_service.py`, `sandbox_service.py`, `editor_service.py`, `observer_snapshot.py` y dejar `app.py` como capa de rutas.

4. Medio - Coexisten dos runtimes de worker: control plane y ruta legacy Codex PTY.
   - El control plane ejecuta tareas aisladas via `execute_task_with_details`.
   - La ruta legacy aun lanza Codex con PTY y guardrails de sesion larga.
   - Riesgo: la tesis "Codex es solo un worker reemplazable" queda parcialmente cumplida, pero todavia acoplada a `AgentRuntime`.
   - Direccion sugerida: definir un `WorkerAdapter` formal con implementaciones `CodexCliWorker`, `NoopWorker`, `TestWorker`.

5. Medio - Frontend con control de runtime repartido en componentes grandes.
   - `frontend/src/App.jsx`: 2997 lineas.
   - `frontend/src/components/CodeWorkbench.jsx`: 2550 lineas.
   - `frontend/src/components/AgentStudio.jsx`: 2111 lineas.
   - Riesgo: polling, sockets, Observer, HAR, sandbox y cierre final se vuelven dificiles de razonar.
   - Direccion sugerida: extraer hooks (`useObserver`, `useSandbox`, `useAgentSessions`, `useCodeWorkbench`, `useHarReview`) y dejar componentes mas declarativos.

6. Medio/Bajo - `orchestrator/validator.py` ejecuta comandos de validacion con `shell=True`.
   - Esto puede ser aceptable si las directivas y tareas son confiables, pero debe estar ligado explicitamente a `security_policy.py` o documentado como frontera de confianza.

## Fortalezas
- El runtime ya tiene modelos explicitos de `smoke`, `build`, `medium`, `long-run`.
- Hay ejecucion por tarea con worker separado y timeout propio.
- El executor y worker hacen `terminate()` y luego `kill()` si el proceso no cierra.
- Hay persistencia real de task history, failures, checkpoints y directives.
- Observer ya tiene incidente finito, deduplicacion, timeline y `observer_findings.json`.
- HAR y blanqueo tienen politica y pruebas especificas.
- Sandbox real persiste estado, proceso, puerto, URL y healthcheck.

## Estado observado del proyecto activo
- Proyecto activo: `workspace/projects/sesion-20260518014728-jeego-en-3d`.
- `project_state.status`: `completed`.
- `current_task_id`: `null`.
- tareas completadas en `project_state`: `76`.
- `task_queue.json`: `76` tareas, todas `completed`.

## Validacion ejecutada
- `python3 -m py_compile backend/app.py backend/agent_runtime.py orchestrator/observer_plane.py orchestrator/contracts.py orchestrator/state_store.py orchestrator/task_queue.py orchestrator/validator.py orchestrator/recovery.py workers/codex_worker.py`: OK.
- `npm test` en `frontend/`: OK, `agentClosureCertificate tests passed`.
- `python3 -m unittest backend.test_executor_pipe_drain backend.test_project_state_runtime_metadata backend.test_security_policy -v`: OK, 10 tests.
- `python3 -m unittest backend.test_human_alignment_review backend.test_observer_plane backend.test_runtime_sandbox backend.test_workspace_blanqueo -v`: fallo dentro del sandbox por permisos de socket; reejecutado fuera del sandbox con aprobacion y paso OK, 23 tests.

## Recomendacion de orden
1. Corregir drift de `schemas/project_state.schema.json`.
2. Decidir contrato de runtime raiz vs runtime por proyecto y hacerlo explicito.
3. Extraer servicios de `backend/app.py` sin cambiar comportamiento.
4. Formalizar `WorkerAdapter`.
5. Separar hooks de frontend para Observer/sandbox/sesiones/HAR.
