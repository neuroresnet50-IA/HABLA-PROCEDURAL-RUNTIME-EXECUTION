# Directive POST-BLANQUEO-RECOVERY

- Generated at: `2026-05-27T14:49:40Z`
- Sprint: `None`
- Source hash: `b0c567c0e9179198e86b3b4915949f65bf502434523d1fb90336053542a9531a`
- Checkpoint: `post-blanqueo-recovery-checkpoint`

## Worker Instruction

```text
Task: POST-BLANQUEO-RECOVERY - POST-BLANQUEO-RECOVERY
System root: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio
Task workspace root: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/continuity-probe-canary
Mandatory write root: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/continuity-probe-canary
Forbidden paths:
- /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/runtime_orquestador_codex_pack
- /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/* except /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/continuity-probe-canary
Control-plane ownership:
- No edites runtime/project_state.json, runtime/task_queue.json, runtime/task_history.jsonl ni runtime/failures.jsonl.
- No edites runtime/checkpoints/, runtime/directives/ ni runtime/logs/.
- El worker solo entrega archivos de producto o artefactos declarados; el control plane persiste estado, cola, historial, retries y checkpoints.
- No marques una tarea como completada escribiendo archivos internos del runtime; devuelve TaskResult y deja que el control plane valide.
Sprint: None -
Goal: Analizar causa raiz, validar workspace limpio y ajustar politicas preventivas.
Complejidad operativa:
- Dificultad: Medio
- Score: 41 | confianza: 88
- Agentes recomendados: 3 de max 8
- Ciclos LACE recomendados: 4 (min 2 / max 10)
- Presupuesto: 10 tareas, 1200s timeout, 3 retries
- Herramientas requeridas: pytest, sandbox, scanner
Exact deliverables:
- lessons_learned/blanqueo-2026-05-27.md
Active restrictions:
- El modo smoke no puede inferirse por palabras sueltas.
- El modo smoke solo puede venir de una señal explícita de configuración.
- Deben existir modos explícitos:
- smoke
- build
- medium
- long-run
- Una sesión debe contener múltiples tareas.
- Cada tarea debe lanzar un worker propio.
- Cada tarea debe tener timeout propio.
- El retry debe ser por tarea, no por sesión completa.
- Si un proceso no cierra con terminate(), debe cerrarse con kill().
- long-run no puede comportarse igual que smoke.
- El progreso solo vale si existe evidencia real.
- Las instrucciones del worker deben derivarse de `AGENTS.md`, `PLANS.md`, el estado persistido y HABLA BASIC.
- `PROMPT_SPRINT_*.txt` solo puede existir como artefacto humano o bootstrap; el sistema final debe generar directivas por tarea.
- El runtime debe cargar `AGENTS.md` como constitución del repositorio.
- El runtime debe cargar `PLANS.md` como roadmap ejecutable.
- El runtime debe combinar política, plan, estado, historial y checkpoint para construir la directiva de la tarea actual.
- HABLA BASIC debe actuar como capa procedural para esa directiva, no como texto decorativo.
- Cada directiva generada para un worker debe persistirse en disco para auditoría y reanudación.
- Respect the selected sprint deliverables and do not advance future deliverables.
Required evidence:
- lessons_learned/blanqueo-2026-05-27.md
Expected validation:
- python3 -B -c "from pathlib import Path; missing=[p for p in ['lessons_learned/blanqueo-2026-05-27.md'] if not Path(p).is_file()]; assert not missing, missing"
- python3 -B -c "from pathlib import Path; assert Path('lessons_learned/blanqueo-2026-05-27.md').is_file()"
Bridge visual obligatorio:
- Comando base: `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py'`
- Si existe `VISTA_AGENT_BRIDGE`, usalo como comando base preferente.
- Antes de editar, emite `phase` describiendo que vas a observar o construir.
- Declara nodos del mapa conceptual con `upsert-node` para archivos importantes.
- Conecta nodos relacionados con `connect-nodes`.
- Enfoca el archivo activo con `focus-node`.
- Declara pasos de flujo con `upsert-step` y enlazalos con `connect-steps`.
- Despues de escribir o modificar cada archivo real, ejecuta `sync-file` inmediatamente.
- No declares progreso visual si no hay evento real del bridge o evidencia real en disco.
- Ejemplos obligatorios:
  - `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py' phase --label plan --message "Preparando la tarea con evidencia visual"`
  - `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py' upsert-node --path frontend/index.html --layer frontend --layer-label Frontend --language html --description "Pantalla principal" --x 220 --y 180`
  - `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py' connect-nodes --from-path frontend/app.js --to-path shared/crm_schema.json --type uses --label "usa esquema"`
  - `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py' focus-node --path frontend/app.js`
  - `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py' upsert-step --node-path frontend/app.js --step-id start --type start --label Inicio --x 260 --y 80`
  - `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py' upsert-step --node-path frontend/app.js --step-id render --type process --label "Renderizar estado" --x 260 --y 220`
  - `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py' connect-steps --node-path frontend/app.js --from-step start --to-step render`
  - `python3 '/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/vista_agent_bridge.py' sync-file --path frontend/app.js --language javascript --description "Logica sincronizada desde evidencia real"`
HABLA BASIC y LACE:
- HABLA guide: habla_basic_procedure
- LACE no detectado en el workspace de tarea para esta directiva.
Starting checkpoint:
- post-blanqueo-recovery-checkpoint
Known risks or blockers:
- Blocked task RUNTIME-20260527073638-002 missing dependencies: RUNTIME-20260527073638-001
- Blocked task RUNTIME-20260527073638-003 missing dependencies: RUNTIME-20260527073638-002
- Blocked task RUNTIME-20260527073638-004 missing dependencies: RUNTIME-20260527073638-003
Closure criteria:
- TaskResult.completed can be true only with real disk evidence.
- TaskResult.blockers must be empty before closing the task.
- Every expected file must exist under the repository root.
- Every declared validation command must run and return code 0.
- Validation results must be represented in the task result history.
```
