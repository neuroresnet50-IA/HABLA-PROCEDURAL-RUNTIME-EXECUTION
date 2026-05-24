# Fase 3 - Capa de Directivas y HABLA

## Propósito
Formalizar la siguiente capa del orquestador sobre los sprints 1 al 5 ya aprobados.

La meta ya no es solo:
- persistir estado,
- planear tareas,
- ejecutar,
- validar,
- y recuperar.

La meta ahora es que el sistema pueda generar por sí mismo la instrucción exacta del worker para la tarea activa, usando:
- `AGENTS.md`
- `PLANS.md`
- estado persistido del runtime
- checkpoint actual
- HABLA BASIC

## Qué aprendimos
En las corridas manuales quedó claro que el rendimiento no depende solo del modelo.
Depende de la calidad del control plane:
- contrato global,
- plan por fases,
- tarea acotada,
- validación,
- checkpoint,
- siguiente paso.

Hoy esa capa todavía la está poniendo un humano al redactar prompts por sprint.
El sistema final debe internalizar ese patrón.

## Tesis
`PROMPT_SPRINT_1.txt` no debe ser el mecanismo final.
Debe ser solo bootstrap humano.

El runtime terminado debe producir directivas por tarea de forma automática.

Fórmula objetivo:

```text
AGENTS.md
+ PLANS.md
+ project_state.json
+ task_queue.json
+ task_history.jsonl
+ failures.jsonl
+ checkpoint actual
+ HABLA BASIC
= directiva operativa de la tarea actual
```

## Nueva pieza central
La pieza nueva no es "otro chat".
Es un componente del control plane:

`directive_generator`

Su función es:
1. cargar política,
2. cargar plan,
3. leer el estado real,
4. leer la tarea activa,
5. incorporar HABLA BASIC,
6. redactar la orden exacta del worker,
7. persistir esa orden,
8. dejar trazabilidad para auditoría y reanudación.

## Módulos nuevos

### `orchestrator/policy_loader.py`
Responsabilidad:
- cargar `AGENTS.md`,
- extraer reglas duras,
- producir una estructura normalizada de política.

### `orchestrator/plan_loader.py`
Responsabilidad:
- cargar `PLANS.md`,
- extraer fases, sprints, alcance, entregables y criterios,
- producir una estructura consultable por máquina.

### `orchestrator/directive_context.py`
Responsabilidad:
- reunir:
  - política,
  - plan,
  - `project_state.json`,
  - `task_queue.json`,
  - historial,
  - fallos,
  - checkpoint,
  - tarea activa.
- devolver un contexto estructurado listo para generar la directiva.

### `orchestrator/habla_adapter.py`
Responsabilidad:
- incorporar HABLA BASIC al flujo procedural,
- transformar el contexto técnico en una guía operativa de ejecución,
- no depender de redacción manual.

### `orchestrator/directive_generator.py`
Responsabilidad:
- construir la directiva final del worker,
- incluir:
  - objetivo,
  - ruta,
  - restricciones,
  - entregables,
  - validación mínima,
  - criterio de éxito,
  - checkpoint de referencia.
- persistir la salida en `runtime/directives/`.

## Artefactos esperados

```text
runtime/
  directives/
    TASK-001.md
    TASK-001.json
    TASK-002.md
    TASK-002.json
```

El `.md` sirve para auditoría humana.
El `.json` sirve para consumo estructurado por el runtime.

## Flujo futuro

```text
planner
→ task_queue
→ directive_context
→ habla_adapter
→ directive_generator
→ worker
→ validator
→ state_store
→ recovery
→ siguiente tarea
```

## Reglas de diseño
1. La directiva del worker debe derivarse del estado real, no de memoria implícita.
2. La directiva debe quedar persistida.
3. La directiva debe ser acotada a una tarea.
4. El worker no decide el plan completo del proyecto.
5. HABLA BASIC debe servir como disciplina procedural, no como texto decorativo.
6. El control plane manda; el worker ejecuta.

## Qué no haremos todavía
- no integrar benchmarks en esta capa;
- no resolver todavía toda la migración final de `agent_runtime.py`;
- no convertir HABLA en un subsistema opaco;
- no reemplazar la cola ni los contratos ya aprobados.

## Orden de implementación

### Sprint 6
- `policy_loader.py`
- `plan_loader.py`

### Sprint 7
- `directive_context.py`
- `habla_adapter.py`

### Sprint 8
- `directive_generator.py`
- `runtime/directives/`

### Sprint 9
- integración controlada en `agent_runtime.py`

### Sprint 10
- benchmarks y puerta de despliegue

## Criterio de éxito de esta fase
La fase queda bien encaminada cuando el sistema pueda:
- elegir la tarea activa,
- producir una directiva persistida para esa tarea,
- ejecutar al worker con esa directiva,
- y reanudar luego desde estado persistido sin que un humano reescriba el prompt.
