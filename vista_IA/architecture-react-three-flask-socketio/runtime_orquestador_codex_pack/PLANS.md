# PLANS.md

## Visión del proyecto
Rediseñar el runtime actual para convertirlo en un orquestador autónomo de proyectos cortos, medianos y largos.

## Problema actual
El sistema actual es frágil por diseño porque:
1. clasifica tareas grandes como smoke por heurísticas frágiles,
2. mata sesiones útiles por timeouts rígidos,
3. el retry puede quedar esperando indefinidamente al proceso anterior.

## Nueva tesis operativa
No tratar proyectos largos como una sola sesión larga.
Dividir el trabajo en tareas pequeñas, verificables, persistentes y reanudables.

## Resultado esperado
Un runtime que:
- divide proyectos grandes,
- ejecuta tarea por tarea,
- valida por evidencia real,
- crea checkpoints,
- se recupera de fallos,
- reanuda tras reinicios,
- desacopla el worker del sistema central.

---

# FASE 1 — Estabilización del runtime actual

## Objetivo
Quitar las fallas estructurales más peligrosas del runtime actual.

## Alcance
- eliminar smoke heurístico,
- introducir modos explícitos,
- separar lógica de sesión y tarea,
- endurecer cierre de procesos,
- preparar persistencia mínima.

## Criterios de aceptación
- un prompt grande no entra en smoke por palabras como “prueba”, “validación” o “mínima”;
- el runtime deja preparado el terreno para task runtime;
- existen estructuras persistentes base.

---

# FASE 2 — Orquestación por tareas

## Objetivo
Pasar de session runtime a task runtime.

## Alcance
- cola persistente,
- dependencias tipo DAG,
- contrato de salida por tarea,
- validación automática por paso,
- reanudación desde checkpoint.

## Criterios de aceptación
- el proyecto puede apagarse y retomarse;
- una tarea fallida no mata el proyecto completo;
- el sistema sigue desde el último estado persistido.

---

# FASE 3 — Autonomía larga

## Objetivo
Soportar proyectos cortos, medianos y largos con la misma base.

## Alcance
- planificación por etapas,
- budgets de tiempo por tarea,
- ciclos de corrección,
- batería de benchmarks,
- soporte para agentes reemplazables.

## Criterios de aceptación
- el runtime supera smoke, mediano, largo y recovery sin intervención manual continua.

---

# Arquitectura de módulos

## orchestrator/planner.py
Responsabilidad:
- dividir prompt grande en tareas,
- definir objetivo,
- definir archivos esperados,
- definir validaciones,
- definir dependencias,
- definir prioridad,
- definir timeout,
- definir modo.

## orchestrator/task_queue.py
Responsabilidad:
- cargar y guardar cola,
- ordenar por dependencias,
- ordenar por prioridad,
- seleccionar siguiente tarea ejecutable.

## orchestrator/executor.py
Responsabilidad:
- lanzar un worker por tarea,
- esperar resultado o timeout,
- devolver resultado estructurado.

## orchestrator/validator.py
Responsabilidad:
- validar evidencia real,
- ejecutar validation_commands,
- decidir si una tarea pasa o falla.

## orchestrator/recovery.py
Responsabilidad:
- registrar fallo,
- cerrar proceso,
- crear checkpoint,
- reintentar limpio,
- dividir tarea si es demasiado grande,
- bloquear tarea si supera reintentos.

## orchestrator/state_store.py
Responsabilidad:
- cargar/guardar estado,
- persistir queue,
- persistir historial,
- persistir failures,
- persistir checkpoints.

## orchestrator/contracts.py
Responsabilidad:
- validar Task,
- validar TaskResult,
- validar ProjectState.

## orchestrator/benchmark.py
Responsabilidad:
- ejecutar benchmarks oficiales,
- bloquear despliegue si fallan.

## workers/codex_worker.py
Responsabilidad:
- ejecutar una tarea acotada,
- devolver resultado estructurado.

---

# Cambios obligatorios en agent_runtime.py

## 1. Smoke mode
- eliminar detección heurística por palabras;
- soportar solo modo explícito:
  - smoke
  - build
  - medium
  - long-run

## 2. Session vs task
- reemplazar session runtime por task runtime;
- una sesión contiene muchas tareas;
- cada tarea tiene worker propio;
- cada tarea tiene timeout propio.

## 3. Retry fuerte
- registrar causa del fallo,
- cerrar proceso anterior,
- reintentar limpio,
- dividir tarea si era demasiado grande,
- nunca esperar que una sesión larga “reviva sola”.

## 4. Timeout contextual
- FIRST_SIGNAL_TIMEOUT depende del modo;
- FIRST_VISUAL_TIMEOUT depende del modo;
- SESSION_IDLE_TIMEOUT depende del modo y del tipo de tarea.

## 5. Cierre garantizado
- terminate()
- wait
- kill() si sigue vivo

---

# Flujo principal esperado

```text
Prompt grande
→ planner
→ división en tareas pequeñas
→ task_queue persistente
→ executor ejecuta una tarea
→ validator valida evidencia real
→ state_store guarda checkpoint
→ recovery actúa si falla
→ siguiente tarea
```

---

# Sprints

## Sprint 1
Objetivo:
Crear la base persistente del runtime y los contratos mínimos.

Entregables:
- `schemas/`
- `orchestrator/state_store.py`
- `orchestrator/contracts.py`
- `runtime/project_state.json`
- `runtime/task_queue.json`

Aceptación:
- existe persistencia base;
- existen contratos mínimos;
- la cola y el estado pueden cargarse y guardarse.

## Sprint 2
Objetivo:
Planificación y cola.

Entregables:
- `orchestrator/planner.py`
- `orchestrator/task_queue.py`

Aceptación:
- soporta prioridad;
- soporta dependencias.

## Sprint 3
Objetivo:
Ejecución acotada por tarea.

Entregables:
- `workers/codex_worker.py`
- `orchestrator/executor.py`

Aceptación:
- una tarea equivale a un proceso.

## Sprint 4
Objetivo:
Validación real.

Entregables:
- `orchestrator/validator.py`

Aceptación:
- ejecuta validaciones y exige evidencia real.

## Sprint 5
Objetivo:
Recovery robusto.

Entregables:
- `orchestrator/recovery.py`

Aceptación:
- terminate → wait → kill;
- divide tareas tras fallos repetidos.

## Sprint 6
Objetivo:
Modificar `agent_runtime.py`.

Entregables:
- modos explícitos,
- fin de smoke heurístico,
- timeout por tarea.

## Sprint 7
Objetivo:
Benchmarks y puerta de despliegue.

Entregables:
- `orchestrator/benchmark.py`

Aceptación:
- no se despliega si falla la batería oficial.

---

# Benchmarks oficiales
- smoke-01
- crud-ui-02
- refactor-mid-03
- long-project-04
- recovery-05

## Regla de despliegue
Si no pasan todos, no se despliega.
