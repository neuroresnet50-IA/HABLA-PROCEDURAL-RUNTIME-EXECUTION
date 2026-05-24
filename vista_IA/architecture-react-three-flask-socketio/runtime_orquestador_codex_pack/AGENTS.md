# AGENTS.md

## Propósito del repositorio
Este repositorio debe evolucionar hacia un **orquestador autónomo de proyectos**.
No debe comportarse como una sola sesión larga de chat.
Debe comportarse como una máquina de ejecución de proyectos cortos, medianos y largos, con agentes reemplazables.

## Tesis central
Nunca tratar un proyecto largo como una sola sesión larga.
Todo proyecto debe dividirse en tareas pequeñas, verificables, persistentes y reanudables.

## Identidad del sistema
El producto final no es “un chat que programa”.
El producto final es “un sistema operativo de ejecución de proyectos con agentes reemplazables”.

## Reglas maestras
1. No depender de la memoria implícita de una sola corrida.
2. Persistir siempre el estado real en disco.
3. No contar progreso sin evidencia real en disco.
4. Toda tarea debe ser verificable.
5. Toda tarea debe ser reanudable.
6. Todo fallo debe dejar traza.
7. Todo retry debe tener causa registrada.
8. Toda validación debe quedar en historial.
9. Todo cambio importante debe generar checkpoint.
10. No acoplar fuertemente el sistema a Codex; Codex es solo un worker.

## Arquitectura objetivo
El sistema debe dividirse en cuatro planos:

### 1. Control plane
Python decide el estado real.
Mantiene backlog, prioridades, budgets, checkpoints y retries.

### 2. Worker plane
Cada worker ejecuta una sola tarea acotada.
Una tarea puede ser:
- crear archivo,
- refactorizar módulo,
- escribir pruebas,
- corregir un fallo puntual.

### 3. Verification plane
Después de cada tarea se debe validar:
- archivos creados,
- archivos modificados,
- tests,
- lint,
- estructura,
- comandos de validación declarados.

### 4. Memory plane
Persistir todo en disco:
- project_state,
- task_queue,
- task_history,
- failures,
- checkpoints,
- artifacts.

## Reglas duras del runtime
1. El modo smoke no puede inferirse por palabras sueltas.
2. El modo smoke solo puede venir de una señal explícita de configuración.
3. Deben existir modos explícitos:
   - smoke
   - build
   - medium
   - long-run
4. Una sesión debe contener múltiples tareas.
5. Cada tarea debe lanzar un worker propio.
6. Cada tarea debe tener timeout propio.
7. El retry debe ser por tarea, no por sesión completa.
8. Si un proceso no cierra con terminate(), debe cerrarse con kill().
9. long-run no puede comportarse igual que smoke.
10. El progreso solo vale si existe evidencia real.

## Estructura esperada del proyecto
```text
runtime/
  project_state.json
  task_queue.json
  task_history.jsonl
  failures.jsonl
  artifacts/
  checkpoints/
  logs/

orchestrator/
  planner.py
  task_queue.py
  executor.py
  validator.py
  recovery.py
  state_store.py
  contracts.py
  benchmark.py

workers/
  codex_worker.py

schemas/
  task.schema.json
  task_result.schema.json
  project_state.schema.json

tests/
  test_smoke_mode.py
  test_retry_recovery.py
  test_task_queue.py
  test_resume_checkpoint.py
  test_long_project_flow.py
```

## Modelo mínimo de Task
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

## Modelo mínimo de TaskResult
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

## Contrato de salida obligatorio
Cada tarea debe devolver:
- objetivo cumplido o no,
- archivos creados,
- archivos modificados,
- validaciones ejecutadas,
- resultado de validación,
- blockers reales,
- recomendación siguiente.

## Política de implementación
Cuando implementes:
- prioriza claridad y trazabilidad,
- deja comentarios útiles solo donde agreguen valor,
- no inventes éxito si no hay validación,
- no cierres una tarea como completa sin evidencia real,
- si falta algo, deja el estado explícito en archivos de runtime.

## Política de entrega por sprint
Cada sprint debe:
1. modificar solo el alcance asignado,
2. dejar artefactos persistidos,
3. dejar tests o validaciones asociadas,
4. registrar riesgos o pendientes,
5. no invadir sprints futuros salvo stubs mínimos necesarios.

## Benchmarks obligatorios
El sistema final debe soportar:
- smoke-01
- crud-ui-02
- refactor-mid-03
- long-project-04
- recovery-05

Si una versión no pasa todos los benchmarks, no se despliega.
