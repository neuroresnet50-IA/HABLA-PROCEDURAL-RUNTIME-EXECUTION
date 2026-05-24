# HABLA Procedural Runtime Execution

## HABLA Engine V5: Advanced Harness Engineering Runtime

HABLA Engine V5 no es un editor de codigo y no es simplemente un chat que escribe archivos. Este repositorio es un proyecto de **harness engineering avanzado**: un runtime procedural para descomponer, ejecutar, verificar, observar, asegurar y recuperar trabajo de software realizado con agentes de IA reemplazables.

La idea central es esta: un agente puede generar codigo, pero un proyecto serio necesita un harness alrededor del agente. Ese harness debe saber que se pidio, dividir el trabajo en tareas verificables, persistir estado, validar evidencia, bloquear cierres prematuros, recuperarse de fallos y explicar por que el sistema cree que el trabajo esta realmente completo.

Esa es la diferencia entre HABLA y un asistente de programacion normal.

## Tesis Tecnico-Cientifica Del Proyecto

La lectura del paper tecnico-cientifico del repositorio define este proyecto como una **plataforma de ejecucion autonoma de proyectos** nacida de HABLA Agentic Engine V5 + LACE. Su unidad real de avance no es la conversacion ni el archivo abierto, sino la **tarea verificable** dentro de un proyecto persistente.

La tesis operacional es:

```text
intencion humana -> HABLA/LACE -> proyecto ejecutable -> runtime persistente
```

Desde ahi, el sistema convierte informacion humana, tecnica y runtime en estado verificable:

```text
Solicitud humana
  -> lectura HABLA/LACE
  -> requerimiento normalizado
  -> proyecto y runtime
  -> plan de tareas
  -> cola persistente
  -> directiva por tarea
  -> worker aislado
  -> resultado estructurado
  -> validacion
  -> historial/checkpoint
  -> Observer/sandbox/scanner/HAR
```

Por eso la contribucion principal no es solo generar codigo. La contribucion es epistemica: transformar una conversacion de IA en un proceso de ejecucion auditable, con memoria, evidencia, validacion y cierre reanudable.

## Que Es HABLA

HABLA es un runtime cognitivo y procedural por capas para ejecucion agentica de software.

En el nivel del motor, HABLA V5 combina:

- Clasificacion semantica de la solicitud.
- Ejecucion tipo ReAct: pensar, actuar, observar y reintentar.
- Recuperacion de evidencia mediante herramientas.
- Triangulacion entre fuentes y observaciones.
- Confianza por componente.
- Revision constitucional antes de responder o cerrar.
- Memoria episodica para mejorar el orden de herramientas.
- Planificacion de tareas compuestas.
- LACE como puerta de calidad ejecutable.

En el nivel del harness, HABLA se expande a:

- **Control plane:** planifica, encola y supervisa trabajo.
- **Worker plane:** ejecuta tareas con workers reemplazables; Codex es solo un worker posible.
- **Verification plane:** valida archivos, pruebas, scanner, sandbox y artefactos.
- **Memory plane:** persiste estado, historial, checkpoints, fallos y evidencia.
- **Observer plane:** compara UI, backend, runtime, scanner, sandbox e integridad.
- **CyberLACE security layer:** protege prompt, memoria, herramientas, salida, autonomia y acciones externas.

## Por Que No Es Lo Mismo Que Cursor U OpenCode

Cursor y herramientas tipo OpenCode son principalmente superficies de edicion asistida: ayudan a un humano o a un agente a modificar codigo. HABLA opera en otra capa: es un harness de ejecucion de proyectos alrededor de agentes.

La diferencia es arquitectonica:

| Capacidad | Asistente/editor tipico | HABLA Engine V5 / Runtime |
| --- | --- | --- |
| Rol principal | Ayudar a editar codigo | Ejecutar proyectos proceduralmente |
| Identidad del worker | El producto suele ser el agente central | Workers reemplazables; Codex es solo uno |
| Estado | Orientado a sesion o conversacion | Persistido en disco: estado, colas, historial y checkpoints |
| Modelo de trabajo | Prompt/chat | Tareas planificadas con modo, timeout, validacion y retry |
| Cierre | El humano o agente dice "termine" | LACE y verificacion bloquean cierre prematuro |
| Evidencia | Conversacional | Scanner, sandbox, manifests, integridad y artefactos |
| Recuperacion | Manual o ad hoc | Retry, recovery, blanqueo selectivo, Frozen Sniper y baseline |
| Seguridad | Permisos del editor/herramienta | CyberLACE sobre prompt, memoria, tools, output, autonomia y acciones |
| Observabilidad | UI del editor | Observer plane con hallazgos persistentes y evidencia visual |

Por eso HABLA no debe entenderse como "otro Cursor". HABLA es una capa superior de orquestacion, evidencia y gobierno. Puede usar editores y agentes como workers, pero mantiene control independiente sobre el proceso, la verificacion, la memoria y la recuperacion.

## Por Que Puede Ser Mas Que Un Asistente De Codigo

HABLA es mas que un asistente de codigo porque no acepta el mensaje final del agente como prueba. Exige evidencia verificable y persistente.

Razones concretas:

1. **Codex no es el centro.** La politica del repositorio dice explicitamente que el sistema no debe acoplarse fuertemente a Codex; Codex es solo un worker.
2. **Los proyectos largos no son una sesion larga de chat.** El control plane divide el trabajo en tareas pequenas, verificables, persistentes y reanudables.
3. **El cierre esta gobernado.** LACE exige ciclos documentados de mejora antes de considerar un proyecto terminado.
4. **La evidencia queda en disco.** Scanner, sandbox, integridad y Observer producen artefactos persistentes.
5. **Puede detectar manipulacion externa.** El scanner de integridad compara archivos actuales contra baselines selladas, boveda, ledger de escrituras y anclas externas opcionales.
6. **Puede recuperar estado.** Frozen Sniper restaura archivos generados modificados o eliminados desde baseline y pone archivos no registrados en cuarentena.
7. **La UI es un workbench operativo.** React, Three.js y Socket.IO exponen mapa, workbench, Observer, scanner, sandbox e integridad.
8. **La seguridad es parte del harness.** CyberLACE vigila memoria, prompt, tools, salida y acciones externas.

## Ciclo De Cierre Auditable

El sistema no deberia marcar un proyecto como terminado solo porque el worker termino sus tareas. El cierre correcto exige evidencia material:

- tareas completadas con archivos y validaciones;
- `task_history.jsonl`, `failures.jsonl` y checkpoints actualizados;
- scanner final valido con lectura hasta ultima linea;
- typewriter final persistido;
- sandbox local corriendo con HTTP ready y URL embebible;
- reporte de integridad sin contradicciones criticas;
- Observer sin gates pendientes;
- Human Alignment Review creada o resuelta segun politica.

Si falta evidencia, el estado correcto no es "terminado sin reservas". Debe ser `verifying_scanner`, `verifying_sandbox`, `blocked`, `human_alignment_pending` o el estado degradado que corresponda.

## Componentes Reales Del Repositorio

### 1. HABLA Agentic Engine V5 + LACE

Ruta: `habla_agentic_engine_v5_1_lace_visual/`

Este es el motor cognitivo. `runtime/engine.py` define `HablaEngineV5`, que carga LACE antes del flujo LLM/agente, clasifica la solicitud, planifica subtareas, ejecuta herramientas, triangula evidencia, calcula confianza, aplica revision constitucional y construye una directiva de respuesta controlada.

Archivos importantes:

- `runtime/engine.py`: flujo de ejecucion HABLA V5.
- `runtime/lace.py`: politica LACE ejecutable, modelo visual, log de ciclos y puerta de cierre.
- `runtime/tools.py`: registro de herramientas con calculadora, RAG local, fuentes oficiales y herramientas inyectables.
- `runtime/planner.py`: planner de tareas compuestas.
- `runtime/types.py`: `HablaState`, `Evidence`, `Confidence` y `SubTask`.
- `LACE.md`: constitucion operativa de razonamiento por capas.
- `LACE_LOG.md`: bitacora de evidencia por ciclos.

### 2. LACE: Loop De Autocritica Y Creatividad Evolutiva

LACE es la puerta de calidad que evita aceptar "ya termine" como prueba.

Activa las diez capas HABLA:

1. Interpretacion.
2. Clasificacion semantica.
3. Planificacion del razonamiento.
4. ReAct.
5. Recuperacion y evidencia.
6. Triangulacion.
7. Confianza por componente.
8. Autocritica.
9. Memoria episodica.
10. Accion o respuesta final.

El runtime lee `LACE.md`, crea o actualiza `LACE_LOG.md`, cuenta ciclos requeridos y expone estado de cierre. LACE no es documentacion decorativa: esta parseado y usado por codigo ejecutable.

### 3. Runtime Orchestrator Y Agent Harness

Ruta: `vista_IA/architecture-react-three-flask-socketio/`

Este es el harness de ejecucion de proyectos y el workbench visual. Su politica dice que el producto final no es "un chat que programa", sino un sistema operativo de ejecucion de proyectos con agentes reemplazables.

Areas importantes:

- `backend/agent_runtime.py`: runtime de sesiones, lanzamiento de workers, modos de tarea, checks LACE y puente con control plane.
- `orchestrator/planner.py`: planificacion de proyectos.
- `orchestrator/task_queue.py`: cola persistente.
- `orchestrator/executor.py`: ejecucion de tareas.
- `orchestrator/validator.py`: validacion.
- `orchestrator/recovery.py`: recuperacion.
- `orchestrator/state_store.py`: estado persistido del proyecto.
- `orchestrator/directive_generator.py`: directivas generadas desde politica, plan, estado y checkpoint.
- `orchestrator/agent_tools.py`: CLI para que agentes usen scanner, Observer, integridad y Sniper reales.

### 4. Verification Plane

El harness valida con artefactos, no con confianza verbal.

Ejemplos:

- `backend/code_scanner_service.py` genera reportes finales con hashes, lineas, caracteres y blockers.
- `backend/sandbox_service.py` detecta proyectos Node, Python o estaticos, lanza servidor local, asigna puerto y espera HTTP ready.
- `orchestrator/real_validation.py` y `orchestrator/validator.py` definen validacion alrededor de la ejecucion.
- Los artefactos viven en `runtime/artifacts/`, `runtime/checkpoints/`, `runtime/logs/` y carpetas relacionadas.

### 5. Observer E Integridad Forense

El Observer plane esta disenado para detectar contradicciones que un agente normal puede no ver.

Segun `docs/observer_engine_algorithm.md`, Observer Engine **no es un worker, no es un chat y no es un scanner infinito**. Es un motor de procesamiento de evidencia que abre incidentes finitos, mira el estado real, clasifica lo que ocurre, propone una accion y cierra con razon auditable.

Su ciclo canonico es:

```text
trigger -> incidente -> snapshot -> clasificacion -> inspeccion -> decision -> evidencia -> cierre
```

Observer solo debe abrir incidentes por triggers permitidos como `agent_started`, `agent_closed`, `observe_now`, `scanner_requested`, `sandbox_check_requested`, `integrity_scan_requested` o `runtime_contradiction_detected`. No debe abrir incidentes por polling de UI, heartbeat de Socket.IO, navegador abierto o lectura de status.

Cada incidente tiene presupuesto, deadline, fingerprint y estado terminal. Si no hay una pregunta activa, Observer debe estar en `idle`; si encuentra un problema repetido, debe dejar evidencia y pasar a `waiting_human`, `blocked`, `completed` o `expired`, no quedarse barriendo lineas indefinidamente.

Revisa:

- estado del proyecto,
- artefactos del scanner,
- estado del sandbox,
- historial del runtime,
- integridad de archivos,
- cambios externos,
- archivos generados eliminados,
- archivos no registrados,
- manipulacion por linea o caracter.

Archivos importantes:

- `orchestrator/observer_plane.py`
- `backend/observer_runtime_service.py`
- `backend/integrity_service.py`
- `frontend/src/components/AppObserverPanel.jsx`
- `frontend/src/components/CodeWorkbenchIntegrityAlert.jsx`

Estados y salidas relevantes del algoritmo Observer:

- `idle`: no hay incidente activo.
- `snapshotting`, `classifying`, `inspecting`, `deciding`: ciclo finito de evidencia.
- `waiting_human`: hay evidencia y se requiere decision humana.
- `completed`, `blocked`, `expired`, `cancelled`: estados terminales.
- `close_clean`, `close_with_findings`, `propose_repair_task`, `propose_sandbox_restart`, `propose_typewriter_binary_fix`: decisiones posibles.

El criterio final es que Observer demuestra inteligencia cuando sabe parar: mirar mejor, explicar evidencia, proponer el siguiente paso correcto y cerrar el ciclo.

### 6. CyberLACE Security Engine

Ruta: `HABLA_CyberLACE_Security_Engine(1)/HABLA_CyberLACE_Security_Engine/`

CyberLACE es la capa de seguridad para harnesses de agentes. No es un firewall tradicional. Protege superficies cognitivas y operativas:

- prompt,
- contexto,
- memoria,
- tool calling,
- salida del modelo,
- acciones externas,
- autonomia,
- evidencia,
- decisiones de politica.

Puede usarse como SDK Python o como REST API, con modos como `monitor` y `enforce`.

### 7. Visual Workbench

La capa visual usa React, Vite, Three.js y Socket.IO.

Componentes frontend importantes:

- `ArchitectureCanvas.jsx`: canvas de arquitectura conceptual.
- `AgentStudio.jsx`: interfaz de agentes/proyectos.
- `CodeWorkbench.jsx`: workbench de codigo.
- `AppObserverPanel.jsx`: panel Observer.
- `CodeWorkbenchSandboxModal.jsx`: preview de sandbox.
- `CodeWorkbenchIntegrityAlert.jsx`: alertas de integridad.
- `LiveReviewerPanel.jsx`: revision en vivo.

La UI no intenta ocultar el runtime. Expone evidencia operacional del harness.

## Mapa Del Repositorio

```text
.
|-- habla_agentic_engine_v5_1_lace_visual/
|   |-- runtime/                 # HABLA V5, LACE, tools, memoria, planner
|   |-- connectors/              # echo, Ollama, Codex CLI
|   |-- chat/                    # chat humano hacia HABLA
|   |-- docs/                    # documentacion HABLA/LACE
|   `-- tests/
|-- vista_IA/
|   |-- architecture-react-three-flask-socketio/
|   |   |-- backend/             # APIs Flask/SocketIO
|   |   |-- frontend/            # React + Three.js workbench
|   |   |-- orchestrator/        # control plane, validacion, recovery
|   |   |-- workers/             # adapters de workers
|   |   |-- schemas/             # contratos del runtime
|   |   |-- runtime/             # artefactos, checkpoints, historial
|   |   `-- workspace/           # proyectos generados/gestionados
|   `-- habla_agentic_engine/    # version previa del motor HABLA
|-- HABLA_CyberLACE_Security_Engine(1)/
|   `-- HABLA_CyberLACE_Security_Engine/
|       |-- cyberlace/           # motor de seguridad
|       |-- examples/
|       `-- tests/
|-- .codex_handoff/              # continuidad y comandos de lanzamiento
`-- aurorizacion.py
```

## Como Ejecutar Partes Clave

### HABLA Engine V5

```bash
cd habla_agentic_engine_v5_1_lace_visual
python -m pytest -q
python -m runtime.lace_cli "Crear un juego en Python" --scaffold
python -m runtime.lace_visual_cli --init --prompt "Crear un juego en Python"
python -m chat.chat_cli --provider echo --show-debug
```

### Backend Del Runtime Visual

```bash
cd vista_IA/architecture-react-three-flask-socketio/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Backend: `http://localhost:5000`

### Frontend Del Runtime Visual

```bash
cd vista_IA/architecture-react-three-flask-socketio/frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

### CyberLACE Security Engine

```bash
cd "HABLA_CyberLACE_Security_Engine(1)/HABLA_CyberLACE_Security_Engine"
pip install -r requirements.txt
python scripts/run_api.py
```

## Estado Actual Del Proyecto

Este repositorio contiene prototipos funcionales, servicios runtime, pruebas, documentacion, evidencia generada de workspace y modulos de seguridad. Debe leerse como un proyecto avanzado de investigacion e ingenieria de harness, no como un producto empaquetado final.

La auditoria de la seccion 19, documentada en `docs/reporte_cierre_auditoria_seccion_19_2026-05-20.md`, registro el cierre de las seis deudas tecnicas que el paper habia observado como riesgos:

| ID | Deuda auditada | Estado |
| --- | --- | --- |
| 19.1 | Drift entre contratos Python y schemas JSON | Cerrada |
| 19.2 | Ambiguedad entre runtime raiz y runtime por proyecto | Cerrada |
| 19.3 | Backend monolitico | Cerrada |
| 19.4 | Doble ruta de worker | Cerrada |
| 19.5 | Frontend con componentes grandes | Cerrada |
| 19.6 | Frontera de seguridad de validaciones | Cerrada |

La evidencia de cierre incluye checkpoints por fase, pruebas backend, build frontend, test frontend, validacion de checkpoints y el workflow `.github/workflows/audit.yml`. El riesgo residual aceptado es que `backend/app.py` sigue siendo composition root Flask/Socket.IO, pero los dominios pesados auditados fueron extraidos a servicios o rutas dedicadas.

Documentos base para esta descripcion:

- `docs/paper_cientifico_orquestador_autonomo_habla_observer_ia.md`
- `docs/observer_engine_algorithm.md`
- `docs/reporte_cierre_auditoria_seccion_19_2026-05-20.md`

La verdad arquitectonica mas importante es esta:

> HABLA Engine V5 es un harness procedural de ejecucion para trabajo de software con IA. Puede usar Codex, Ollama u otros workers, pero no se reduce a ninguno de ellos. Su valor esta en el control plane, verification plane, memory plane, Observer plane, LACE gate y CyberLACE security layer alrededor del worker.
