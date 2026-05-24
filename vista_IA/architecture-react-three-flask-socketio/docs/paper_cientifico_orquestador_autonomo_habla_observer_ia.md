# Paper tecnico-cientifico: Orquestador autonomo de proyectos nacido de HABLA Agentic Engine V5 + LACE

**Repositorio observado:** `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio`

**Motor de origen e inspiracion:** `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual`

**Fecha de observacion:** 2026-05-19 10:00:31 PDT

**Tipo de documento:** descripcion cientifico-tecnica del sistema real, su arquitectura interna, su ciclo operativo y su modelo de cierre con evidencia persistida.

## Resumen

Este repositorio implementa una plataforma de ejecucion autonoma de proyectos basada en agentes reemplazables, persistencia de estado, verificacion por tarea, observacion visual-operativa y cierre auditable. Su inspiracion y nucleo genealogico es **HABLA Agentic Engine V5 + LACE**, ubicado en `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual`. HABLA no es un nombre decorativo: es el corazon conceptual de la idea. El orquestador visual de este repositorio nace de la necesidad de llevar el motor HABLA, sus capas metacognitivas y la puerta LACE de cierre a un sistema de proyectos completos, con UI, runtime, workers, evidencia, sandbox y observacion.

Aunque su superficie visible combina React, Flask, Socket.IO y visualizacion de arquitectura, su proposito real no es ser una aplicacion de chat ni una interfaz grafica convencional. La tesis central del sistema es que un proyecto largo nunca debe tratarse como una sola sesion prolongada, sino como una sucesion de tareas pequenas, verificables, persistentes y reanudables.

El sistema se organiza alrededor de cuatro planos principales: control, worker, verificacion y memoria. Sobre ellos se integra un plano de observacion, denominado HABLA Observer IA, que cruza evidencia de runtime, scanner final, sandbox, UI, grafo de arquitectura, sesiones y hallazgos de integridad. El resultado es una arquitectura que busca comportarse como un sistema operativo de ejecucion de proyectos: recibe una intencion humana, la divide en tareas, genera directivas por tarea, lanza workers acotados, valida entregables, registra fallos, crea checkpoints, arranca un sandbox real, inspecciona evidencia final y abre revision de alineacion humana cuando corresponde.

El documento describe que contiene el proyecto, que hace, como trabaja internamente, cuales son sus herramientas y como fluye la informacion desde una solicitud humana hasta el cierre formal del proceso. Tambien distingue capacidades ya implementadas de deuda tecnica observada al momento de la revision.

## Palabras clave

HABLA Agentic Engine V5, LACE, orquestador autonomo, agentes reemplazables, control plane, worker plane, verification plane, memory plane, HABLA Observer IA, runtime persistente, checkpoint, sandbox local, scanner final, human alignment review, trazabilidad operacional.

## 1. Introduccion

Los sistemas de programacion asistida por inteligencia artificial suelen adoptar una forma conversacional: un humano escribe instrucciones, un agente responde, y el estado del trabajo queda distribuido entre la memoria implicita del modelo, el historial del chat y los archivos producidos. Esta estrategia funciona para tareas cortas, pero falla cuando el proyecto requiere continuidad, trazabilidad, reintentos, auditoria, recuperacion de contexto y cierre verificable.

El repositorio analizado propone otra tesis: la unidad basica de avance no debe ser la conversacion, sino la tarea verificable. Bajo esta tesis, Codex u otro agente no es el producto final ni la fuente unica de verdad; es solo un worker reemplazable dentro de un runtime mas amplio. El sistema real se orienta a convertir requerimientos humanos en proyectos ejecutados por ciclos controlados, donde cada paso deja evidencia material en disco.

La arquitectura observada combina:

- Un backend Flask con Socket.IO para API, eventos en tiempo real, sandbox, editor, scanner, integridad, Observer, HAR y control de sesiones.
- Un frontend React/Vite para visualizar arquitectura, sesiones, proyectos, workspace, Observer, sandbox embebido y herramientas de revision.
- Un orquestador Python con contratos, cola de tareas, planificador, executor, validador, recuperacion, generador de directivas y adaptador HABLA.
- Un worker Python que ejecuta una tarea acotada y devuelve un `TaskResult` estructurado.
- Un microservicio Node.js que publica un pulso de ecosistema hacia el backend.
- Un runtime persistente por proyecto con estado, cola, historial, fallos, checkpoints, artefactos, logs y directivas.

### 1.1 Origen e inspiracion: HABLA Agentic Engine V5 + LACE

El punto de origen del sistema es HABLA Agentic Engine V5 + LACE. Ese motor no es simplemente una libreria externa ni una pieza opcional; es la idea madre. HABLA define un lenguaje procedimental agentico para convertir una solicitud humana en razonamiento controlado: clasificar, buscar evidencia, actuar, observar, triangular, medir confianza, aplicar verificacion constitucional, registrar memoria y solo entonces responder o ejecutar.

El motor HABLA V5 observado en `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual` contiene:

- `runtime/engine.py`: `HablaEngineV5`, que integra clasificador semantico, herramientas, triangulacion, confianza, chequeo constitucional, memoria episodica, planner y preflight LACE.
- `LACE.md`: politica de arranque que debe leerse antes de activar LLM, Codex u otro agente.
- `runtime/lace.py`: politica ejecutable, `LaceRuntime`, puerta de cierre, modelo visual y registro de ciclos.
- `memory/episodic_memory.jsonl`: memoria episodica de preguntas, herramientas, fuentes, confianza y resultado.
- `docs/PAPER_HABLA_BILINGUE.md`: definicion de HABLA como lenguaje procedimental agentico con motor metacognitivo.
- `docs/GUIA_LACE_V5.md` y `docs/CHANGELOG_V5_1.md`: explicacion de la union HABLA + LACE, puerta ejecutable y capa visual/auditable.

En HABLA V5, la pregunta humana no va directo al LLM. Pasa por un runtime externo que decide si debe recuperar informacion, calcular, inferir, bloquear o responder. La cadena conceptual es:

```text
Humano -> HABLA -> LACE -> directiva razonada -> Codex/LLM -> respuesta procesada
```

LACE agrega una regla de cierre fuerte: no se puede declarar terminado un proyecto hasta registrar ciclos reales de mejora objetiva en `LACE_LOG.md`. En la version observada, `LACE.md` exige 10 ciclos y cada ciclo activa capas HABLA:

- interpretacion,
- clasificacion semantica,
- planificacion del razonamiento,
- ReAct,
- recuperacion y evidencia,
- triangulacion,
- confianza por componente,
- autocritica,
- memoria episodica,
- respuesta o accion final.

### 1.2 Por que el Motor V5 recibio el nombre LACE

La incorporacion de LACE al Motor V5 de HABLA marca un cambio de identidad. El sistema ya no era solamente un interprete de instrucciones HABLA Basic; se habia convertido en una capa mas avanzada de autocritica, planificacion y mejora evolutiva. Por eso se nombro **LACE: Loop de Autocritica y Creatividad Evolutiva**.

HABLA Basic organiza el pensamiento del agente en forma procedural:

```text
OBJETIVO -> ENTRADAS -> SALIDAS -> REGLAS -> FUNCIONES -> VALIDACION -> FALLBACK
```

Esa estructura permite que el humano no entregue una orden ambigua, sino una instruccion con forma de algoritmo. Sin embargo, al llegar al Motor V5 aparecio una necesidad mas fuerte: el agente no debia responder ni generar codigo en un solo disparo. Debia pasar por ciclos internos de revision:

```text
Pensar -> Planificar -> Ejecutar -> Criticar -> Mejorar -> Validar -> Recomendar
```

LACE nace precisamente para representar esa segunda identidad del motor. No reemplaza a HABLA; lo vuelve mas inteligente. HABLA aporta la gramatica procedural de la orden. LACE aporta el ciclo critico que revisa, mejora y valida antes de cerrar una respuesta o una accion.

La diferencia conceptual queda asi:

| Capa | Funcion |
| --- | --- |
| HABLA Basic | El usuario estructura una orden como algoritmo. |
| HABLA Engine | El sistema interpreta esa orden y la convierte en protocolo operativo. |
| HABLA Motor V5 / LACE | El sistema analiza, se autocritica, mejora el plan y valida si falta algo antes de ejecutar o cerrar. |

En el contexto de Harness Studio, HABLA/LACE tambien debia funcionar como motor de planificacion critica. El motor tenia que recibir informacion de negocio y contrato:

```text
business_description
business_profile
harness_contract
```

Y devolver una respuesta operacional de planificacion:

```text
planning_notes
missing_requirements
risks
suggested_agents
suggested_workflows
critique_cycles
final_recommendations
```

Este diseno muestra que LACE no es solo una palabra para "iterar". Es la formalizacion de un ciclo evolutivo donde el agente se obliga a detectar vacios, riesgos, agentes necesarios, workflows posibles y recomendaciones finales antes de declarar que entiende el trabajo.

En una frase: se le puso LACE porque el Motor V5 dejo de ser solo un ejecutor de prompts estructurados y paso a ser un ciclo evolutivo de razonamiento, critica, creatividad y validacion para agentes inteligentes.

El repositorio `architecture-react-three-flask-socketio` puede entenderse como la expansion sistemica de esa matriz. HABLA era el motor cognitivo: una forma de obligar al agente a pensar por capas, con evidencia y autocritica. Este repositorio toma esa intuicion y la convierte en infraestructura de proyecto:

- las capas de interpretacion y clasificacion se vuelven planificacion y grafo de arquitectura;
- ReAct se vuelve worker por tarea con observacion y validacion;
- recuperacion y evidencia se vuelven `failures.jsonl`, scanner, sandbox e integridad;
- triangulacion se vuelve Observer cruzando runtime, UI, grafo, scanner y sandbox;
- confianza por componente se vuelve validacion por archivos, comandos, estados y artefactos;
- autocritica se vuelve cierre bloqueado si falta evidencia;
- memoria episodica se vuelve `project_state`, `task_queue`, `task_history`, checkpoints y HAR;
- la puerta LACE se vuelve politica de cierre visual, scanner final, sandbox real y revision humana.

Por eso, decir que este repositorio es solo un editor de codigo seria incorrecto. Su nacimiento esta en HABLA: un motor que quiere que la IA no actue como texto libre, sino como procedimiento verificable. El orquestador actual es la version visual, operacional y persistente de esa intuicion.

## 2. Problema que intenta resolver

El problema de fondo es la fragilidad de los proyectos largos ejecutados por agentes conversacionales. En una sesion larga de chat, el progreso puede parecer continuo aunque no exista evidencia persistida. Las instrucciones pueden diluirse, los fallos pueden no registrarse, los reintentos pueden perder causa, y el cierre puede declararse sin validar que la aplicacion exista, compile, arranque o responda.

El repositorio responde a ese problema con una politica fuerte:

- No depender de memoria implicita.
- Persistir el estado real en disco.
- No contar progreso sin evidencia.
- Dividir el proyecto en tareas pequenas.
- Validar despues de cada tarea.
- Registrar fallos, retries y checkpoints.
- Generar directivas de worker desde politica, plan, estado e historial.
- Exigir scanner final, sandbox real y evidencia antes de cierre.
- Abrir revision humana posterior al cierre tecnico.

Por eso el producto conceptual no es "un chat que programa", sino "un sistema operativo de ejecucion de proyectos con agentes reemplazables".

## 3. Metodologia de observacion

Este documento se construyo mediante lectura estatica de los artefactos centrales del repositorio y de la memoria persistida disponible. La observacion incluyo:

- Politica operativa: `AGENTS.md`.
- Roadmap ejecutable: `PLANS.md`.
- Memoria de continuidad: `ULTIMO_CONTEXTO_CODEX.md` y `recuperacioncontexto.md`.
- Revision arquitectonica previa: `runtime/artifacts/architecture_review_20260519T095605_PDT.md`.
- Componentes de orquestacion: `orchestrator/`.
- Worker: `workers/codex_worker.py`.
- Runtime backend: `backend/app.py` y `backend/agent_runtime.py`.
- Vista frontend: `frontend/src/`.
- Microservicio lateral: `microservice-js/`.
- Pruebas y evidencias en `backend/test_*.py`, `runtime/`, `docs/` y `workspace/projects/`.
- Motor de origen HABLA: `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual/README.md`.
- Politica LACE del motor de origen: `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual/LACE.md`.
- Implementacion del motor: `habla_agentic_engine_v5_1_lace_visual/runtime/engine.py` y `runtime/lace.py`.
- Documento conceptual HABLA: `habla_agentic_engine_v5_1_lace_visual/docs/PAPER_HABLA_BILINGUE.md`.
- Guias de evolucion HABLA + LACE: `docs/GUIA_LACE_V5.md` y `docs/CHANGELOG_V5_1.md` del motor externo.
- Aclaracion historica del creador sobre por que LACE fue incorporado al Motor V5 de HABLA y su relacion con Harness Studio.

La descripcion distingue tres niveles:

- **Implementado y visible en codigo:** archivos, funciones, endpoints, clases y pruebas existentes.
- **Politica declarada:** reglas de `AGENTS.md` y `PLANS.md` que definen comportamiento obligatorio.
- **Riesgo o deuda observada:** diferencias entre intencion arquitectonica y estado actual del repositorio.

## 4. Hipotesis arquitectonica

La hipotesis central del proyecto es que la ejecucion autonoma confiable requiere que la inteligencia del agente sea subordinada a un sistema de control externo. El modelo de IA puede razonar y editar, pero no debe ser la unica memoria, ni el unico validador, ni el unico responsable del cierre.

En terminos arquitectonicos, esto implica separar:

- Decision de estado: la toma el control plane.
- Ejecucion puntual: la realiza un worker.
- Validacion: la realiza el verification plane.
- Memoria y auditoria: viven en disco.
- Observacion transversal: la realiza Observer IA sobre evidencia persistida.
- Alineacion humana: se formaliza en HAR despues del cierre tecnico.

Esta separacion reduce el riesgo de proyectos "aparentemente terminados" pero sin artefactos, pruebas, sandbox, reporte final o trazabilidad.

## 5. Arquitectura general del repositorio

El repositorio puede entenderse como una plataforma multi-plano:

```text
Humano / UI React
    |
    | HTTP + Socket.IO
    v
Backend Flask / Socket.IO
    |
    | crea proyecto, sesion, runtime, eventos
    v
HABLA V5 + LACE
    |
    | matriz cognitiva: capas, evidencia, ciclos y puerta de cierre
    v
Control plane Python
    |
    | planifica, selecciona tarea, genera directiva
    v
Worker plane
    |
    | ejecuta una tarea acotada
    v
Verification plane
    |
    | valida archivos, comandos, scanner, sandbox, integridad
    v
Memory plane
    |
    | project_state, task_queue, task_history, failures, checkpoints, artifacts
    v
Observer IA + HAR
    |
    | observa evidencia y abre alineacion humana
    v
Cierre tecnico y humano auditable
```

La clave del sistema no esta en un unico archivo, sino en la relacion entre runtime persistente, directivas por tarea, ejecucion aislada, verificacion y observacion.
La raiz conceptual de esa relacion viene de HABLA: primero convertir una intencion humana en procedimiento controlado; despues ejecutar el procedimiento con evidencia.

## 6. Plano de control

El control plane decide el estado real del proyecto. Su responsabilidad es transformar un objetivo general en unidades operativas verificables. Esta capa vive principalmente en `orchestrator/` y es integrada por `backend/agent_runtime.py`.

### 6.1 Contratos

`orchestrator/contracts.py` define los contratos minimos:

- `Task`
- `TaskResult`
- `ProjectState`
- `TaskQueue`

Los modos permitidos son:

- `smoke`
- `build`
- `medium`
- `long-run`

Los estados de tarea incluyen:

- `pending`
- `running`
- `completed`
- `failed`
- `blocked`

Los estados de proyecto incluyen:

- `initialized`
- `running`
- `paused`
- `completed`
- `failed`
- `blocked`
- `stopped`
- `human_alignment_pending`

La existencia de estos contratos indica que el sistema no depende solo de prompts. El estado debe ser una estructura validable.

### 6.2 Planificador

`orchestrator/planner.py` convierte objetivos humanos en listas de tareas. Contiene logica para distintos tipos de proyecto:

- proyectos web estaticos,
- scripts Python,
- aplicaciones Tkinter,
- blueprints de producto,
- modulos multiples,
- inferencia de archivos esperados,
- comandos de validacion,
- limites de alcance.

La funcion conceptual del planificador es impedir que un proyecto largo sea una instruccion monolitica. Cada objetivo debe descomponerse en tareas con `expected_files`, `validation_commands`, timeout, modo y dependencias.

### 6.3 Cola de tareas

`orchestrator/task_queue.py` administra readiness, dependencias, tareas bloqueadas y transiciones. La cola no es una lista decorativa; es la representacion persistente de que trabajo existe y que puede ejecutarse.

Una tarea solo puede avanzar si sus dependencias estan resueltas. Esto permite reanudacion y evita que el sistema dependa de la memoria de una sesion.

### 6.4 Estado persistente

`orchestrator/state_store.py` centraliza lectura y escritura de:

- `project_state.json`
- `task_queue.json`
- `task_history.jsonl`
- `failures.jsonl`
- checkpoints

El runtime funcional observado vive principalmente por proyecto, por ejemplo:

```text
workspace/projects/<project-slug>/runtime/
```

La raiz `runtime/` contiene artefactos globales, directivas historicas, benchmarks, logs, checkpoints y politicas, pero la ejecucion real de proyectos nuevos se orienta a runtimes por proyecto.

### 6.5 Generacion de directivas

`orchestrator/directive_context.py` ensambla el contexto que necesita un worker:

- politica de `AGENTS.md`,
- plan de `PLANS.md`,
- estado persistido,
- cola de tareas,
- historial,
- fallos,
- checkpoint,
- tarea activa,
- evidencia de archivos esperados,
- alcance del sprint.

`orchestrator/directive_generator.py` convierte ese contexto en una directiva operacional auditable. La directiva se persiste como JSON y Markdown en `runtime/directives/` o en el runtime del proyecto. Este punto es central: la instruccion del worker no deberia ser manual ni permanente; debe derivarse de politica, plan, estado, checkpoint y HABLA.

### 6.6 HABLA como nucleo cognitivo del control plane

La relacion entre HABLA V5 y este control plane es genealogica y funcional. En HABLA V5, `HablaEngineV5.run()` toma una pregunta humana, aplica preflight LACE, convierte la entrada a protocolo HABLA, clasifica semanticamente, planifica, ejecuta herramientas, triangula evidencia, calcula confianza, aplica chequeo constitucional, construye una directiva para el LLM/Codex y guarda memoria episodica.

El control plane de este repositorio toma esa misma idea y la escala del nivel "respuesta" al nivel "proyecto":

```text
HABLA V5:
  pregunta -> clasificacion -> herramientas -> evidencia -> confianza -> directiva -> respuesta

Orquestador visual:
  requerimiento -> tareas -> workers -> evidencia -> validacion -> checkpoint -> cierre
```

La diferencia no es de filosofia sino de escala. HABLA controla la cognicion del agente; el orquestador controla la ejecucion material del proyecto. Por eso `habla_adapter.py` no debe entenderse como un modulo menor, sino como un puente entre el motor original y el runtime actual. Su funcion esperada es mantener viva la disciplina HABLA dentro de cada directiva de worker: no actuar sin interpretar, no cerrar sin evidencia, no ignorar incertidumbre, no declarar exito sin validacion y no olvidar lo aprendido.

## 7. Plano worker

El worker plane ejecuta una sola tarea acotada. Su pieza mas clara es `workers/codex_worker.py`.

El worker:

- recibe un archivo `task.json`,
- trabaja dentro de un workspace concreto,
- ejecuta un comando definido o una ruta de trabajo,
- respeta timeout,
- detecta archivos creados o modificados,
- reporta validaciones ejecutadas,
- devuelve un `TaskResult`,
- no conserva memoria propia de largo plazo.

`orchestrator/executor.py` lanza un proceso nuevo por tarea mediante `workers.codex_worker`. Si el proceso excede su tiempo, primero intenta `terminate()` y luego `kill()` si no cierra. Esta decision cumple la politica del runtime: el retry debe ser por tarea y no por sesion completa.

Tambien existe una ruta heredada de ejecucion Codex CLI/PTY en `backend/agent_runtime.py`. Esa ruta conserva compatibilidad con sesiones visuales y terminales, pero la direccion arquitectonica del repositorio es que Codex sea un worker reemplazable, no el nucleo acoplado del sistema.

## 8. Plano de verificacion

El verification plane evita que el sistema declare progreso sin evidencia. Opera en varios niveles.

### 8.1 Validacion de tarea

`orchestrator/validator.py` valida:

- archivos esperados,
- comandos de validacion declarados,
- resultado estructurado,
- historial de validacion.

La tarea no deberia pasar a `completed` si sus evidencias minimas no existen.

### 8.2 Recuperacion y retry

`orchestrator/recovery.py` decide que hacer cuando una tarea falla:

- registrar causa,
- reintentar una tarea,
- bloquearla,
- crear recomendaciones,
- no reiniciar toda la sesion sin motivo.

La politica exige que todo retry tenga causa registrada y que cada fallo deje traza.

### 8.3 Scanner final

`backend/app.py` contiene la logica de `build_code_scanner_report` y `persist_code_scanner_report`. El scanner final debe recorrer archivos visibles desde la primera hasta la ultima linea real, registrar total de lineas, caracteres y archivos leidos, y certificar que la lupa visual llego hasta el final.

El artefacto esperado es:

```text
runtime/artifacts/final_code_scanner_report.json
```

El cierre no debe declararse completo si el scanner falta o no certifica `magnifier_line_by_line_to_last_line` y `scrolls_to_last_line`.

### 8.4 Typewriter final

El backend tambien persiste un reporte de writer final mediante `persist_final_typewriter_report`. Su funcion es dejar evidencia de reproduccion o cierre textual/visual del proceso.

El artefacto esperado es:

```text
runtime/artifacts/final_typewriter_report.json
```

### 8.5 Sandbox real

El sistema tiene un sandbox local real para proyectos generados. `backend/app.py` detecta el tipo de proyecto, asigna puerto, lanza servidor local, espera healthcheck HTTP y persiste estado en `runtime/sandbox.json`.

Un cierre valido requiere:

- proceso servidor vivo,
- puerto local,
- URL HTTP,
- `ready=true`,
- `running=true`,
- `embedUrl` disponible para iframe interno.

El frontend abre el sandbox en un modal/panel embebido con iframe. Esto evita que la UI solo muestre un link o un estado simulado.

### 8.6 Integridad forense

El backend contiene herramientas para:

- manifest de archivos,
- sellado de manifest,
- baseline vault,
- external anchor,
- reporte de integridad,
- ledger de escrituras,
- Frozen Sniper para restauracion/cuarentena ante cambios externos.

Estas herramientas no son simples validaciones de compilacion. Buscan detectar reemplazos de caracteres, archivos borrados, archivos no rastreados y cambios externos al flujo autorizado.

## 9. Plano de memoria

El memory plane es la base epistemica del sistema. El repositorio insiste en que la verdad del avance debe estar en disco, no en la memoria del chat.

La estructura esperada incluye:

```text
runtime/
  project_state.json
  task_queue.json
  task_history.jsonl
  failures.jsonl
  artifacts/
  checkpoints/
  directives/
  logs/
```

En proyectos reales, esta estructura aparece bajo:

```text
workspace/projects/<project-slug>/runtime/
```

La memoria registra:

- estado actual del proyecto,
- cola de tareas,
- eventos de tarea,
- fallos,
- decisiones de recuperacion,
- checkpoints,
- reportes de scanner,
- reportes de sandbox,
- directivas generadas,
- revisiones HAR,
- eventos visuales,
- logs de terminal.

La consecuencia es importante: una nueva terminal o un nuevo worker debe poder reanudar desde disco, sin depender de recordar el chat anterior.

## 10. Plano de observacion: HABLA Observer IA

HABLA Observer IA es el diferenciador conceptual del sistema. No se limita a mirar sesiones activas o puntos visuales en el mapa. Su funcion es observar evidencia que otros agentes podrian no ver.

`orchestrator/observer_plane.py` implementa una maquina de estados de observacion read-only. El Observer:

- lee snapshot de runtime,
- revisa grafo y lint,
- observa sesiones,
- cruza scanner final,
- cruza sandbox,
- cruza integridad,
- filtra por proyecto activo,
- deduplica eventos,
- persiste findings,
- emite acciones visuales explicables.

Sus estados incluyen situaciones como:

- `waiting_worker`
- `verifying_scanner`
- `verifying_sandbox`
- `external_file_deletion_detected`
- `untracked_file_detected`
- `char_level_tamper_detected`
- `detecting_issue`
- `scanning_map`
- `checking_flow`
- `observing_code`
- `idle`

La politica obliga a que cada evento del Observer tenga:

- `reason`,
- `evidence`,
- `snapshotSummary`,
- `projectSlug`,
- accion visual (`uiAction`).

Esto convierte al Observer en una capa de inspeccion explicable. Si un proyecto esta `completed` pero falta scanner final, el Observer debe emitir `verifying_scanner`. Si el scanner esta aprobado pero el sandbox no esta listo, debe emitir `verifying_sandbox`.

## 11. Plano frontend

El frontend esta construido con React/Vite. Su archivo principal es `frontend/src/App.jsx`, apoyado por componentes como:

- `AgentStudio.jsx`
- `CodeWorkbench.jsx`
- `ArchitectureCanvas.jsx`
- `AlgorithmFlow.jsx`
- `WelcomeAuthGate.jsx`
- `agentClosureCertificate.js`

La UI no es solo decorativa. Actua como cabina de mando:

- muestra proyectos,
- arranca sesiones,
- visualiza grafo de arquitectura,
- muestra eventos Socket.IO,
- permite editar archivos,
- muestra el Observer Plane,
- abre el sandbox embebido,
- muestra estados de cierre,
- expone acciones seguras del Observer,
- maneja revision y estado de runtime.

Tambien contiene pruebas frontend, por ejemplo `agentClosureCertificate.test.js`, orientadas a validar criterios de cierre visual.

## 12. Plano backend

`backend/app.py` es el nucleo HTTP y Socket.IO. Expone endpoints para:

- arquitectura,
- lint,
- reverse engineering,
- proyectos,
- sesiones de agente,
- editor de archivos,
- scanner final,
- integridad,
- Frozen Sniper,
- typewriter final,
- sandbox,
- Human Alignment Review,
- repair,
- reset,
- clean workspace,
- Observer,
- email command plane.

El backend tambien integra:

- `backend/agent_runtime.py`: control de proyectos, sesiones, comandos Codex, control plane, LACE/HABLA, eventos visuales.
- `backend/project_graph.py`: construccion de grafo del proyecto.
- `backend/map_lint.py`: lint visual/arquitectonico.
- `backend/architecture_ir.py` e `ir_adapters/`: representacion intermedia de arquitectura para Python, JavaScript, HTML/CSS y enlaces intermodulo.
- `backend/human_alignment_review.py`: creacion y gestion HAR.
- `backend/workspace_blanqueo.py`: politica de blanqueo, backup y recuperacion.
- `backend/reverse_engineering.py`: analisis inverso.
- `backend/auth_routes.py`: autenticacion.

Una observacion importante es que `backend/app.py` concentra demasiadas responsabilidades. Esto funciona como integrador actual, pero aumenta riesgo de acoplamiento. La direccion arquitectonica deseable es extraer servicios por dominio: scanner, integridad, sandbox, editor, Observer snapshot y HAR.

## 13. Microservicio JavaScript

`microservice-js/` contiene un servicio Node.js con endpoints:

- `/health`
- `/sync`

Su funcion es construir un snapshot del ecosistema y publicarlo hacia el backend mediante `architectureBridge.js`. Este microservicio opera como componente lateral de pulso, util para alimentar la vista de arquitectura o reportar estado del ecosistema.

## 14. Herramientas internas del sistema

El repositorio contiene un conjunto amplio de herramientas internas. Las principales son:

### 14.1 Task Queue

Gestiona tareas pendientes, listas, bloqueadas y completadas. Permite continuidad y evita que el sistema dependa del orden mental de una conversacion.

### 14.2 Planner

Convierte objetivos humanos en tareas pequenas con archivos esperados, validaciones, dependencias, prioridad, modo y timeout.

### 14.3 Executor

Lanza un worker nuevo para una tarea. Controla timeout, salida estructurada y cierre de proceso.

### 14.4 Codex Worker

Ejecuta una tarea acotada dentro de un workspace. Devuelve `TaskResult` y evidencia de archivos creados/modificados.

### 14.5 Validator

Valida que lo declarado como avance tenga soporte real: archivos, comandos, resultados y estado.

### 14.6 Recovery

Decide retry, bloqueo o recomendacion despues de fallos. Registra causa y evita reintentos opacos.

### 14.7 Directive Context

Ensambla politica, plan, estado, cola, historial, fallos, checkpoint y evidencia.

### 14.8 Directive Generator

Genera directivas operativas por tarea. Persiste JSON y Markdown para auditoria y reanudacion.

### 14.9 HABLA Adapter

Convierte el contexto operacional en guia procedural HABLA. Su funcion es que HABLA no sea texto decorativo, sino capa procedural de la directiva.

Esta herramienta existe porque el repositorio hereda su ADN de HABLA Agentic Engine V5 + LACE. En el motor original, HABLA convierte una pregunta humana en protocolo controlado antes de entregarla a Codex, Ollama u otro LLM. En este repositorio, el adaptador debe hacer algo equivalente para tareas de proyecto: tomar politica, plan, estado, historia, checkpoint y evidencia, y traducirlos a una directiva donde el worker actue bajo capas HABLA.

El adaptador ideal preserva estas obligaciones del motor de origen:

- interpretar antes de actuar,
- clasificar semanticamente el tipo de trabajo,
- formular THOUGHT/ACTION/OBSERVATION,
- usar evidencia y no intuicion libre,
- triangular resultado tecnico, funcional y humano,
- estimar confianza por componente,
- aplicar autocritica antes de cerrar,
- registrar memoria para el siguiente ciclo.

Asi, HABLA se vuelve el lenguaje interno de las directivas, mientras el control plane se encarga de persistir y ejecutar esas directivas a escala de proyecto.

### 14.10 Observer Plane

Observa runtime, scanner, sandbox, integridad, grafo, lint y sesiones. Emite eventos explicables y hallazgos persistidos.

### 14.11 Live Reviewer

Monitorea transiciones, checkpoints, tareas, validaciones y posibles inconsistencias durante la vida del proyecto.

### 14.12 Code Scanner Final

Recorre archivos visibles linea por linea, registra conteos y evidencia final de lectura completa.

### 14.13 Typewriter Final

Persiste evidencia de cierre narrativo/visual asociado al final del proceso.

### 14.14 Sandbox Real

Arranca la aplicacion generada en puerto local, valida HTTP readiness y expone URL embebible.

### 14.15 Integrity Baseline

Crea manifest, sellos, vault y anchor externo para detectar manipulacion posterior.

### 14.16 Frozen Sniper

Responde a hallazgos de integridad con restauracion/cuarentena bajo reglas controladas.

### 14.17 Human Alignment Review

Abre revision humana formal despues de cierre tecnico, sin modificar codigo al crear la revision.

### 14.18 Blanqueo

Define protocolo de limpieza selectiva o total, con backup obligatorio, decision auditable, confirmacion humana en modos seguros y tarea post-blanqueo.

### 14.19 Email Command Plane

Permite comandos por correo bajo configuracion y autorizacion, con pruebas de deduplicacion y allowlist.

### 14.20 Benchmarks

El sistema final debe soportar:

- `smoke-01`
- `crud-ui-02`
- `refactor-mid-03`
- `long-project-04`
- `recovery-05`

Estos benchmarks funcionan como contrato de madurez: si no pasan, no deberia desplegarse.

### 14.21 Implementacion actual: herramientas invocables por contrato para agentes

La etapa que se esta implementando ahora consiste en convertir herramientas internas que ya existen en la UI o en el backend en herramientas realmente invocables por agentes. Esta distincion es critica: no basta con escribir una regla en `AGENTS.md`. Para que Codex u otro worker pueda usar Scanner, Observer o Sniper de forma practica, deben existir contratos ejecutables.

La arquitectura correcta se expresa asi:

```text
AGENTS.md          = regla de uso
API/CLI interna    = herramienta real ejecutable
runtime/artifacts  = evidencia que el agente debe leer
```

El flujo esperado para un agente Codex dentro de este sistema es:

```text
Agente Codex
  -> lee AGENTS.md
  -> recibe directiva derivada de politica, plan, estado y checkpoint
  -> usa Scanner antes y despues de cambios
  -> consulta Observer para diagnostico
  -> usa Sniper solo con permiso o confirmacion
  -> lee reportes generados en runtime/artifacts
  -> decide siguiente accion con evidencia
```

Esto convierte la parte visual en infraestructura operacional. El Scanner no es solo una animacion; es una herramienta de revision. El Observer no es solo un ojo en pantalla; es un motor de diagnostico y coordinacion. Frozen Sniper no es solo un boton de emergencia; es una herramienta de recuperacion forense que solo puede actuar bajo reglas de seguridad.

El contrato minimo esperado por herramienta es:

| Herramienta | Uso por agentes | Salida esperada | Limite de seguridad |
| --- | --- | --- | --- |
| Scanner | Revisar estado antes/despues de cambios y certificar lectura final | `runtime/artifacts/final_code_scanner_report.json` u otro reporte de scanner | No declarar cierre si falta reporte valido |
| Observer | Diagnosticar contradicciones entre runtime, UI, scanner, sandbox, grafo e integridad | `runtime/artifacts/observer_findings.json` y eventos explicables | Read-only; propone acciones, no destruye |
| Integrity Scan | Comparar disco actual contra baseline y ledger | `runtime/artifacts/file_integrity_report.json` | Debe diferenciar cambios autorizados de externos |
| Frozen Sniper | Restaurar/cuarentenar ante hallazgos de integridad | `runtime/artifacts/frozen_sniper_recovery_report.json` | Requiere permiso/confirmacion si restaura o cuarentena |
| Parte visual | Dar feedback, foco, evidencia y trazabilidad humana | eventos UI, foco de archivo, modal sandbox, reportes visibles | Evidencia y supervision; no adorno |

La regla de uso queda incompleta si no existe API o CLI. Por eso el sistema debe exponer operaciones como:

```text
scanner.run(project_id)
observer.status(project_id)
observer.observe_once(project_id)
integrity.scan(project_id)
frozen_sniper.plan(project_id)
frozen_sniper.apply(project_id, confirmation)
sandbox.status(project_id)
sandbox.start(project_id)
```

Cada operacion debe devolver una respuesta estructurada, rutas de artefactos, estado de validacion y blockers. El agente no debe inventar que una herramienta paso; debe leer el reporte generado y citar su resultado en el `TaskResult`, checkpoint o historial de tarea.

La clave de esta fase es convertir Scanner, Sniper y Observer en herramientas invocables por contrato, no solo en botones de UI. Cuando esto ocurre, los agentes pueden trabajar junto con la parte visual con limites claros: Scanner revisa, Observer diagnostica, Sniper recupera con autorizacion, y la UI muestra evidencia y feedback. Esa es la diferencia entre una interfaz asistida y un sistema autonomo de ejecucion verificable.

## 15. Ciclo completo de informacion y cierre de proceso

Esta seccion describe el flujo completo ideal y observado del sistema.

### 15.1 Entrada humana

El ciclo inicia cuando el humano formula un requerimiento desde la UI o API. El requerimiento puede ser crear un proyecto, continuar uno existente, reparar, revisar o ejecutar una tarea.

La entrada debe incluir modo explicito:

- `smoke`
- `build`
- `medium`
- `long-run`

La politica prohibe inferir `smoke` por palabras sueltas. El modo debe venir de configuracion explicita.

### 15.2 Creacion o seleccion de proyecto

`backend/agent_runtime.py` crea o reutiliza un directorio bajo:

```text
workspace/projects/<project-slug>/
```

Alli inicializa estructura, metadata y runtime:

```text
workspace/projects/<project-slug>/runtime/
```

El proyecto puede contener `README.md`, `AGENTS.md`, `docs/`, `src/`, `shared/` y archivos generados por tareas.

### 15.3 Inicializacion del runtime

El control plane crea:

- `project_state.json`
- `task_queue.json`
- logs de sesion,
- archivos de eventos,
- preflight HABLA/LACE cuando aplica.

El proyecto inicia como `initialized` o `running` segun el momento del ciclo.

### 15.4 Planificacion

El planner convierte el requerimiento en tareas. Cada tarea contiene:

- `id`
- `title`
- `goal`
- `status`
- `priority`
- `dependencies`
- `expected_files`
- `validation_commands`
- `timeout_seconds`
- `max_retries`
- `mode`
- `checkpoint_key`

La cola queda persistida. Esto permite continuar si el proceso se interrumpe.

### 15.5 Seleccion de tarea activa

La cola determina cual tarea esta lista. El estado del proyecto registra `current_task_id`. Si una tarea depende de otra, no debe ejecutarse antes de tiempo.

### 15.6 Construccion de contexto

`directive_context.py` carga:

- politica (`AGENTS.md`),
- plan (`PLANS.md`),
- estado (`project_state.json`),
- cola (`task_queue.json`),
- historial (`task_history.jsonl`),
- fallos (`failures.jsonl`),
- checkpoints,
- evidencia de archivos.

Si algo falta, el contexto puede quedar degradado, pero esa degradacion queda registrada.

### 15.7 Generacion de directiva

`directive_generator.py` produce una directiva por tarea. Esa directiva incluye:

- raiz del sistema,
- raiz del workspace de tarea,
- rutas prohibidas,
- objetivo,
- entregables exactos,
- restricciones,
- evidencia requerida,
- validaciones esperadas,
- checkpoint de partida,
- riesgos conocidos,
- criterios de cierre.

La directiva se persiste en disco para auditoria.

### 15.8 Ejecucion del worker

El executor lanza un worker nuevo. El worker ejecuta una sola tarea. No deberia asumir que una sesion anterior sigue viva ni guardar memoria fuera del runtime.

La ejecucion produce:

- stdout/stderr,
- codigo de salida,
- duracion,
- archivos creados,
- archivos modificados,
- validaciones ejecutadas,
- blockers.

### 15.9 Validacion

El verification plane contrasta el resultado contra la tarea:

- existen los archivos esperados,
- se ejecutaron los comandos,
- pasaron las validaciones,
- el resultado estructurado cumple contrato.

Si la validacion falla, no se puede marcar progreso como real.

### 15.10 Persistencia de resultado

Cada resultado se registra en:

- `task_history.jsonl`
- `failures.jsonl` si aplica,
- checkpoints,
- project_state,
- task_queue.

La evidencia se vuelve reanudable.

### 15.11 Recuperacion ante fallo

Si una tarea falla:

1. Se registra el fallo con causa.
2. Se evalua retry por tarea.
3. Se incrementa contador de intentos.
4. Se puede generar accion de recovery.
5. Si el problema persiste, la tarea puede bloquearse.
6. Si el estado se considera critico, se activa protocolo de blanqueo.

El blanqueo nunca debe ser destructivo sin backup y decision auditable. En `medium` y `long-run`, un blanqueo total requiere confirmacion humana.

### 15.12 Avance de cola

Cuando una tarea pasa, se marca `completed`, se actualiza `completed_tasks`, se libera la siguiente tarea lista y el ciclo se repite. Una sesion puede contener multiples tareas, especialmente en `build`, `medium` y `long-run`.

### 15.13 Cierre tecnico

Cuando la cola termina, el proyecto no deberia cerrarse solo porque las tareas terminaron. Debe ejecutarse cierre tecnico:

- writer final,
- scanner final,
- reporte de integridad,
- sandbox real,
- healthcheck positivo,
- URL embebible,
- checkpoint final.

La politica indica que `completed` exige evidencia. Si falta scanner, el sistema debe quedar en verificacion. Si falta sandbox, tambien.

### 15.14 Observacion final

El Observer cruza:

- `project_state.json`,
- `final_code_scanner_report.json`,
- `final_typewriter_report.json`,
- `sandbox.json`,
- integridad,
- grafo,
- lint,
- sesiones.

Si detecta inconsistencia, emite evento con razon, evidencia y accion visual.

### 15.15 Revision humana HAR

Despues de un cierre tecnico correcto, el sistema debe abrir o reutilizar una Human Alignment Review:

```text
runtime/human_alignment_reviews/
```

HAR no modifica codigo al abrirse. Primero resume:

- que se construyo,
- stack tecnico,
- decisiones detectadas,
- evidencia de cierre,
- opciones de direccion humana.

Luego espera feedback humano. Si el humano pide cambios de direccion, HAR crea tareas controladas que regresan al control plane normal.

### 15.16 Cierre de informacion

El cierre de informacion ocurre cuando:

- la cola esta completada o explicitamente bloqueada,
- los artefactos finales existen,
- el sandbox responde,
- el Observer no reporta gates faltantes,
- HAR queda abierto o resuelto segun politica,
- todo esta registrado en disco.

En ese punto el sistema puede afirmar avance con base material, no con memoria conversacional.

### 15.17 Ejemplo operacional: de una solicitud humana a un cierre verificable

Para entender por que este sistema no es solamente un editor de codigo, conviene observar un ciclo hipotetico pero coherente con la arquitectura real del repositorio.

Supongamos que el humano solicita:

```text
Crear una aplicacion web de inventario para un taller, con tabla de productos,
formulario de entrada, busqueda, persistencia local, vista responsive y sandbox
embebido para probarla al final.
```

En un editor asistido tradicional, la interaccion principal seria abrir archivos, pedir cambios al agente, revisar el diff y ejecutar manualmente pruebas. En este sistema, la solicitud se transforma primero en informacion operacional persistida.

#### 15.17.1 Entrada inicial

La entrada humana no se trata como una conversacion libre infinita. El backend recibe el requerimiento, lo asocia a un proyecto y a un modo explicito, por ejemplo `build` o `medium`.

La primera transformacion es conceptual:

```text
intencion humana -> HABLA/LACE -> proyecto ejecutable -> runtime persistente
```

En este punto aparece el corazon HABLA. La intencion no deberia ir directamente al worker. Primero debe pasar por una lectura procedural: que se pide realmente, que tipo de conocimiento o accion requiere, que evidencia sera necesaria, que riesgos existen, que capas HABLA deben activarse y que puerta LACE impedira cerrar sin ciclos o evidencia suficiente.

El sistema crea o reutiliza:

```text
workspace/projects/taller-inventario/
workspace/projects/taller-inventario/runtime/
```

Y registra estado inicial en:

```text
runtime/project_state.json
runtime/task_queue.json
runtime/task_history.jsonl
runtime/failures.jsonl
runtime/checkpoints/
runtime/directives/
```

#### 15.17.2 Planificacion de trabajo

El planner divide la solicitud en tareas pequenas. Una salida posible seria:

```text
TASK-001 Crear estructura base de la app
TASK-002 Implementar modelo de productos y persistencia local
TASK-003 Construir formulario de entrada y validacion
TASK-004 Construir tabla, busqueda y filtros
TASK-005 Agregar estilos responsive
TASK-006 Crear pruebas o validaciones basicas
TASK-007 Ejecutar cierre final con scanner, sandbox y HAR
```

Cada tarea tiene archivos esperados, comandos de validacion, timeout, dependencias y maximo de reintentos. La informacion ya no esta solo en el prompt; queda convertida en cola verificable.

#### 15.17.3 Generacion de directiva para el worker

Para `TASK-003`, por ejemplo, el sistema no deberia enviar al agente una instruccion generica como "haz el formulario". Debe generar una directiva derivada de:

- `AGENTS.md`,
- `PLANS.md`,
- matriz HABLA V5 + LACE,
- `project_state.json`,
- `task_queue.json`,
- historial previo,
- fallos previos,
- checkpoint activo,
- evidencia de archivos existentes,
- guia procedural HABLA.

La directiva resultante puede decir, de forma estructurada:

```text
Tarea: TASK-003
Objetivo: construir formulario de entrada y validacion.
Raiz obligatoria: workspace/projects/taller-inventario/
Archivos esperados: frontend/src/components/ProductForm.jsx
Validacion esperada: npm test o npm run build
Restricciones: no tocar runtime interno, no declarar exito sin evidencia.
HABLA: interpretar, clasificar, planificar, actuar, observar, validar y registrar memoria.
LACE: no cerrar si falta mejora objetiva o evidencia de ciclo.
Cierre: devolver TaskResult con archivos creados/modificados y validacion.
```

El punto importante es que la instruccion del worker es un artefacto auditable. Si el proceso se interrumpe, otra corrida puede leer la directiva y continuar.

#### 15.17.4 Ejecucion aislada

El executor lanza un worker nuevo para esa tarea. El worker no "posee" todo el proyecto; solo ejecuta una unidad acotada. Si se queda colgado, el sistema aplica timeout, `terminate()` y luego `kill()` si hace falta.

Al terminar, el worker devuelve un resultado estructurado:

```json
{
  "task_id": "TASK-003",
  "completed": true,
  "files_created": ["frontend/src/components/ProductForm.jsx"],
  "files_modified": ["frontend/src/App.jsx"],
  "validation_ran": ["npm run build"],
  "validation_passed": true,
  "blockers": [],
  "next_recommendation": "Continuar con tabla y busqueda."
}
```

Ese resultado no vale por declaracion. El verification plane revisa que los archivos existan y que la validacion indicada realmente haya corrido.

#### 15.17.5 Procesamiento de informacion

Durante el ciclo, la informacion fluye asi:

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

Cada flecha produce o consume evidencia. El sistema procesa informacion humana, informacion tecnica e informacion de runtime al mismo tiempo:

| Tipo de informacion | Donde entra | Como se procesa | Donde queda evidencia |
| --- | --- | --- | --- |
| Intencion humana | UI/API | Se transforma en objetivo y modo | `project_state.json`, metadata del proyecto |
| Razonamiento HABLA | Motor HABLA / adaptador | Interpreta, clasifica, planifica, triangula y exige evidencia | directivas, logs, checkpoints |
| Politica LACE | `LACE.md` / contexto HABLA | Bloquea cierre prematuro y exige ciclos de mejora | `LACE_LOG.md`, estado de cierre, checkpoints |
| Plan tecnico | Planner | Se divide en tareas | `task_queue.json` |
| Politica del sistema | `AGENTS.md` y `PLANS.md` | Se incorpora a directivas | `runtime/directives/` |
| Trabajo del worker | Proceso aislado | Se convierte en `TaskResult` | `task_history.jsonl` |
| Fallos | Worker/validator | Se clasifican para retry o bloqueo | `failures.jsonl` |
| Evidencia de codigo | Disco del proyecto | Se valida por archivos y comandos | checkpoints y reportes |
| Evidencia visual/runtime | Scanner, sandbox, Observer | Se cruza contra estado final | `artifacts/`, `sandbox.json`, findings |
| Preferencia humana | HAR | Se transforma en tareas nuevas | `human_alignment_reviews/` |

Esta tabla muestra la diferencia esencial: el sistema no solo ayuda a escribir codigo; convierte informacion en estado operacional verificable.

#### 15.17.6 Manejo de fallo

Si `TASK-004` falla porque la tabla no compila, el sistema no deberia reiniciar todo el proyecto ni asumir que "algo salio mal" de forma vaga. Debe registrar:

```text
task_id: TASK-004
causa: npm run build fallo por import inexistente ProductTable
intento: 1 de 3
accion: retry de la misma tarea con directiva corregida
```

El fallo queda en `failures.jsonl` y el retry queda asociado a la tarea. Si falla tres veces, el sistema puede bloquearla o activar recuperacion. Si el estado se vuelve irrecuperable, entra la politica de blanqueo con backup y confirmacion humana cuando corresponda.

#### 15.17.7 Cierre tecnico del ejemplo

Cuando todas las tareas terminan, el resultado esperado no es solamente "hay archivos". El cierre correcto exige:

- build o validacion aprobada,
- scanner final leyendo archivos hasta la ultima linea,
- reporte de typewriter final,
- integridad sin manipulacion externa,
- sandbox local corriendo,
- URL HTTP embebible,
- iframe interno en la UI,
- Observer sin alarmas de scanner o sandbox faltante,
- checkpoint final,
- HAR abierto para revision humana.

El resultado obtenido por el sistema seria un paquete de ejecucion auditable:

```text
Aplicacion creada:
  workspace/projects/taller-inventario/

Estado:
  runtime/project_state.json -> completed o human_alignment_pending

Cola:
  runtime/task_queue.json -> tareas completadas con dependencias resueltas

Historial:
  runtime/task_history.jsonl -> eventos de ejecucion y validacion

Evidencia:
  runtime/artifacts/final_code_scanner_report.json
  runtime/artifacts/final_typewriter_report.json
  runtime/sandbox.json
  runtime/checkpoints/<checkpoint-final>.json
  runtime/human_alignment_reviews/<review>.json
```

El humano no recibe solo codigo. Recibe codigo, trazabilidad, validacion, contexto de recuperacion, evidencia de cierre y una ruta formal para pedir ajustes.

#### 15.17.8 Resultado intelectual del ciclo

El resultado final no es simplemente una carpeta con una aplicacion. Es una unidad de conocimiento ejecutable:

- se sabe que pidio el humano,
- se sabe como se dividio,
- se sabe que worker hizo cada tarea,
- se sabe que archivos cambiaron,
- se sabe que pruebas o validaciones corrieron,
- se sabe donde fallo si fallo,
- se sabe que checkpoint permite reanudar,
- se sabe si la app arranco en sandbox,
- se sabe si el Observer encontro contradicciones,
- se sabe que queda pendiente de alineacion humana.

Esta es la razon por la que el proyecto debe entenderse como un orquestador autonomo. El codigo es solo una parte del resultado; la otra parte es la historia verificable de como ese codigo llego a existir.

## 16. Modelo de datos minimo

El modelo minimo de tarea es:

```json
{
  "id": "TASK-001",
  "title": "Crear estructura base del proyecto",
  "goal": "Inicializar carpetas y archivos base",
  "status": "pending",
  "priority": 10,
  "dependencies": [],
  "expected_files": ["README.md", "src/__init__.py"],
  "validation_commands": ["pytest -q", "ruff check ."],
  "timeout_seconds": 900,
  "max_retries": 3,
  "mode": "build",
  "checkpoint_key": null
}
```

El modelo minimo de resultado es:

```json
{
  "task_id": "TASK-001",
  "completed": false,
  "files_created": [],
  "files_modified": [],
  "validation_ran": [],
  "validation_passed": false,
  "blockers": [],
  "next_recommendation": ""
}
```

Estos modelos son importantes porque convierten una accion de IA en un contrato verificable.

## 17. Estado empirico observado

En la revision previa persistida se observo un proyecto activo:

```text
workspace/projects/sesion-20260518014728-jeego-en-3d
```

Su estado reportado era:

- `project_state.status`: `completed`
- `current_task_id`: `null`
- tareas completadas: 76
- tareas en `task_queue.json`: 76
- todas las tareas: `completed`

Tambien se validaron pruebas y compilacion de componentes principales durante la revision arquitectonica anterior. Para este documento, la evidencia relevante es documental y se registra en el checkpoint creado junto a este paper.

## 18. Discusion: que es realmente este proyecto

Este proyecto es mejor entendido como una plataforma de ejecucion autonoma con trazabilidad, no como una app web tradicional. React y Flask son la superficie de interaccion; el nucleo conceptual inmediato es el runtime persistente y verificable. Pero su nucleo de origen, su inspiracion y su gramatica cognitiva vienen de HABLA Agentic Engine V5 + LACE.

HABLA es el corazon de la idea porque introduce la tesis previa: un LLM no debe responder ni actuar libremente; debe ser controlado por un runtime metacognitivo que interpreta, clasifica, busca evidencia, observa, triangula, mide confianza, se autocritica, registra memoria y solo entonces genera accion. El orquestador de este repositorio toma ese principio y lo lleva a proyectos completos. Donde HABLA produce una directiva razonada, este sistema produce tareas, workers, validaciones, checkpoints, scanner, sandbox y revision humana.

Su valor diferencial esta en cinco decisiones:

1. **Separar intencion humana de ejecucion de tarea.** El humano expresa objetivo; el sistema lo convierte en tareas.
2. **Separar worker de memoria.** El worker ejecuta; la memoria vive en disco.
3. **Separar finalizacion de evidencia.** Una tarea no termina porque el agente lo diga; termina cuando hay archivos y validacion.
4. **Separar cierre tecnico de alineacion humana.** Un proyecto puede compilar y aun asi necesitar ajuste de direccion.
5. **Agregar observacion transversal.** Observer IA no solo mira la UI; cruza runtime, sandbox, scanner, integridad y grafo.

En este sentido, el proyecto intenta crear una "infraestructura de verdad operacional" para agentes de software.

La forma mas precisa de nombrarlo seria: una materializacion visual y persistente de HABLA para ejecucion de proyectos. HABLA aporta la disciplina cognitiva; LACE aporta la puerta de ciclos y cierre; el orquestador aporta memoria de proyecto, workers, verificacion, UI, Observer y sandbox.

### 18.1 Por que no es solamente un editor de codigo tipo Cursor

Cursor y herramientas similares son valiosas como editores asistidos por IA: aceleran navegacion, escritura, refactorizacion y explicacion de codigo dentro de una experiencia centrada en archivos. El proyecto analizado apunta a una categoria distinta. Su pregunta principal no es "como edito este archivo mas rapido", sino "como ejecuto un proyecto completo sin perder estado, evidencia, validacion, recuperacion ni cierre".

La diferencia puede resumirse asi:

| Dimension | Editor asistido tipo Cursor | Este repositorio |
| --- | --- | --- |
| Unidad principal | Archivo, diff, conversacion o sesion de edicion | Tarea verificable dentro de un proyecto persistente |
| Inspiracion cognitiva | Asistencia contextual dentro del editor | HABLA V5 + LACE como motor procedimental y puerta de cierre |
| Memoria | Historial de chat, contexto del editor, archivos abiertos | `project_state`, `task_queue`, `task_history`, `failures`, checkpoints |
| Agente | Asistente integrado al editor | Worker reemplazable ejecutando una tarea acotada |
| Progreso | Cambios de codigo y respuestas del asistente | Evidencia en disco, validaciones, checkpoints y reportes |
| Fallo | El usuario o agente corrige manualmente | Recovery por tarea, retry con causa, bloqueo o blanqueo controlado |
| Cierre | El usuario decide si termino | Scanner final, typewriter, sandbox real, Observer y HAR |
| Observacion | Principalmente el codigo visible | Runtime, UI, sandbox, integridad, grafo, sesiones y artefactos |
| Resultado | Codigo editado | Proyecto ejecutado con trazabilidad operacional |

Por eso reducir este sistema a "editor de codigo" seria perder su tesis. El editor es solo una interfaz posible. La identidad real esta en el control plane y en la memoria persistida: el sistema intenta saber que paso, por que paso, que evidencia lo demuestra, que falta, como se reintenta y como se cierra.

En una herramienta centrada en edicion, el humano suele sostener mentalmente el proyecto: recuerda que se hizo, que falta, que fallo y que hay que probar. En este repositorio, esa carga se desplaza hacia el runtime. El sistema debe recordar en disco, decidir desde contratos, observar evidencia y dejar una ruta de reanudacion. Esa es la diferencia entre un editor inteligente y un sistema operativo de ejecucion de proyectos.

## 19. Limitaciones y deuda tecnica observada

La arquitectura ya expresa una direccion fuerte, pero existen riesgos actuales.

### 19.1 Drift entre contratos Python y schemas JSON

`orchestrator/contracts.py` permite `human_alignment_pending` y `pending_human_alignment_tasks`, pero la revision previa encontro que `schemas/project_state.schema.json` no reflejaba completamente esos campos. Esto puede hacer que validadores externos rechacen estados validos para Python.

### 19.2 Ambiguedad entre runtime raiz y runtime por proyecto

`StateStore()` por defecto apunta a `runtime/`, pero el runtime funcional de sesiones vive bajo `workspace/projects/<slug>/runtime/`. Si una herramienta instancia `StateStore()` sin especificar runtime, puede leer un plano equivocado.

### 19.3 Backend monolitico

`backend/app.py` integra muchos dominios: rutas, sockets, scanner, integridad, sandbox, editor, Observer, repair, reset, blanqueo y HAR. Esto aumenta el costo de cambio.

### 19.4 Doble ruta de worker

Coexisten el control plane por tareas y una ruta legacy Codex CLI/PTY. La direccion futura deberia formalizar un `WorkerAdapter` para que Codex sea una implementacion, no una dependencia conceptual.

### 19.5 Frontend con componentes grandes

`App.jsx`, `CodeWorkbench.jsx` y `AgentStudio.jsx` concentran muchas responsabilidades. La extraccion de hooks por dominio ayudaria a hacer mas legible el control de runtime, Observer, sandbox, sesiones y HAR.

### 19.6 Frontera de seguridad de validaciones

Algunas validaciones ejecutan comandos declarados. Esto debe permanecer ligado a politica de seguridad, aprobacion o confianza explicita.

## 20. Trabajo futuro recomendado

La siguiente etapa de madurez deberia priorizar:

1. Sincronizar `schemas/project_state.schema.json` con `orchestrator/contracts.py`.
2. Definir explicitamente runtime raiz versus runtime por proyecto.
3. Extraer servicios de `backend/app.py`.
4. Formalizar `WorkerAdapter`.
5. Crear hooks frontend por dominio.
6. Fortalecer validacion de comandos con `security_policy.py`.
7. Asegurar que cada cierre `completed` pase por scanner, typewriter, sandbox e integridad.
8. Consolidar benchmarks obligatorios como puerta de despliegue.
9. Formalizar en la documentacion y en el codigo que HABLA V5 + LACE es el motor de origen: las directivas del worker deben conservar capas HABLA, ciclo LACE y evidencia de cierre.

## 21. Conclusiones

El repositorio `architecture-react-three-flask-socketio` no debe ser leido solamente como una aplicacion React-Flask-Socket.IO. Esa descripcion cubre su tecnologia visible, pero no su identidad real. Tampoco debe entenderse como una invencion aislada: nace de HABLA Agentic Engine V5 + LACE. HABLA es el corazon conceptual que introduce el razonamiento por capas, la evidencia, la triangulacion, la confianza, la autocritica, la memoria episodica y la puerta contra cierres falsos.

El proyecto actual es un intento de llevar ese corazon HABLA a una escala mayor: construir un orquestador autonomo de proyectos donde los agentes son reemplazables, las tareas son pequenas, la memoria es persistente, la validacion es obligatoria y el cierre exige evidencia.

Su arquitectura actual ya contiene los elementos principales de ese sistema operativo de ejecucion:

- HABLA V5 + LACE como matriz cognitiva de origen,
- control plane,
- worker plane,
- verification plane,
- memory plane,
- Observer IA,
- scanner final,
- sandbox real,
- HAR,
- integridad forense,
- blanqueo controlado,
- benchmarks.

La contribucion mas importante del proyecto es epistemica: propone que el avance de un agente no se crea por declaracion, sino por evidencia persistida, verificable y reanudable. En otras palabras, el sistema intenta transformar una conversacion de IA en un proceso de ejecucion auditable.

## Apendice A. Mapa resumido de carpetas

```text
backend/
  app.py                         # API, Socket.IO, scanner, sandbox, integridad, Observer, HAR
  agent_runtime.py               # sesiones, proyectos, control plane, Codex CLI, eventos
  project_graph.py               # grafo del proyecto
  map_lint.py                    # lint visual/arquitectonico
  architecture_ir.py             # representacion intermedia
  ir_adapters/                   # adaptadores Python, JS, HTML/CSS
  human_alignment_review.py      # HAR
  workspace_blanqueo.py          # politica de limpieza/destruccion controlada

frontend/
  src/App.jsx                    # cabina principal UI
  src/components/AgentStudio.jsx # sesiones y experiencia agente
  src/components/CodeWorkbench.jsx
  src/components/ArchitectureCanvas.jsx
  src/components/AlgorithmFlow.jsx

orchestrator/
  contracts.py                   # contratos de Task, TaskResult, ProjectState
  planner.py                     # planificacion en tareas
  task_queue.py                  # cola y dependencias
  executor.py                    # lanza workers por tarea
  validator.py                   # validacion de resultados
  recovery.py                    # retry y recuperacion
  state_store.py                 # memoria persistente
  directive_context.py           # ensamble de contexto
  directive_generator.py         # directivas por tarea
  habla_adapter.py               # capa procedural HABLA
  observer_plane.py              # Observer IA
  security_policy.py             # decisiones de seguridad

workers/
  codex_worker.py                # worker acotado por tarea

runtime/
  artifacts/
  checkpoints/
  directives/
  logs/
  failures.jsonl
  task_history.jsonl

workspace/projects/<slug>/runtime/
  project_state.json
  task_queue.json
  task_history.jsonl
  failures.jsonl
  artifacts/
  checkpoints/
  human_alignment_reviews/
  sandbox.json

microservice-js/
  src/server.js                  # health y sync
  src/catalogService.js
  src/architectureBridge.js
```

## Apendice B. Criterio de cierre auditable

Un cierre completo debe demostrar, como minimo:

- tareas completadas con evidencia,
- historial persistido,
- fallos registrados o ausencia explicita de fallos,
- checkpoint final,
- scanner final valido,
- typewriter final persistido,
- sandbox local corriendo,
- healthcheck HTTP positivo,
- URL embebible en iframe,
- Observer sin gates pendientes,
- HAR creado o reutilizado para revision humana.

Sin esos elementos, el estado correcto no deberia ser "terminado sin reservas", sino "en verificacion", "bloqueado" o "pendiente de alineacion humana", segun la evidencia real.

## Apendice C. Mapa del motor de origen HABLA V5 + LACE

```text
/home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual/
  README.md                     # presenta HABLA Agentic Engine V5 + LACE
  LACE.md                       # politica de arranque y 10 ciclos obligatorios
  LACE_LOG.md                   # evidencia de ciclos cuando se ejecuta

  runtime/
    engine.py                   # HablaEngineV5
    lace.py                     # LacePolicy, LaceRuntime, LaceGate, LaceVisualModel
    classifier.py               # clasificacion semantica
    planner.py                  # orquestador de subtareas
    tools.py                    # herramientas reales e inyectables
    triangulation.py            # triangulacion
    confidence.py               # confianza por componente
    constitutional.py           # chequeo constitucional
    memory.py                   # memoria episodica
    prompt_converter.py         # convierte pregunta a protocolo HABLA

  memory/
    episodic_memory.jsonl       # memoria de preguntas, herramientas, fuentes y confianza

  docs/
    PAPER_HABLA_BILINGUE.md     # definicion conceptual de HABLA
    GUIA_LACE_V5.md             # uso de HABLA + LACE con Codex/Ollama/LLM
    CHANGELOG_V5_1.md           # LACE visual y politica ejecutable
    GUIA_LACE_VISUAL_V5_1.md    # inspeccion visual del estado LACE

  connectors/
    codex_cli_connector.py      # puente hacia Codex CLI
    ollama_connector.py         # puente hacia Ollama
    echo_connector.py           # proveedor de prueba
```

Este apendice importa porque muestra que el orquestador actual no surge de la nada. Surge de una evolucion previa donde HABLA ya habia definido el principio central: la IA debe actuar bajo un procedimiento externo, con memoria, evidencia, confianza y cierre bloqueado si no hay mejora objetiva.
