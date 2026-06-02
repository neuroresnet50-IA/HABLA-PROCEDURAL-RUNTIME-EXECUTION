# Alternativa Segura 2

Shell inicial para un proyecto de orquestador autonomo de proyectos. Esta tarea define el alcance, la orientacion de implementacion y la evidencia documental minima; no implementa todavia el runtime completo.

## Proposito

El producto objetivo es un sistema operativo de ejecucion de proyectos con agentes reemplazables. No debe comportarse como una unica sesion larga de chat: cada proyecto se divide en tareas pequenas, verificables, persistentes y reanudables.

## Principios centrales

- Persistir el estado real en disco antes de contar progreso.
- Ejecutar cada tarea con un worker propio, timeout propio y retry propio.
- Separar control plane, worker plane, verification plane y memory plane.
- Generar directivas de worker desde politica, plan, estado persistido, checkpoint y HABLA BASIC.
- Mantener Codex como worker reemplazable, no como dependencia estructural del sistema.
- Usar solo datos sinteticos o evidencia redactada cuando se documenten ejemplos.

## Modos operativos

Los modos validos deben ser explicitos por configuracion:

- `smoke`: validacion corta y controlada.
- `build`: construccion incremental verificable.
- `medium`: ejecucion con mas tareas, presupuestos y control de retries.
- `long-run`: ejecucion prolongada con checkpoints, trazabilidad y reanudacion real.

El modo `smoke` no puede inferirse por palabras sueltas. `long-run` no puede degradarse al comportamiento de `smoke`.

## Planos del sistema

- Control plane: decide backlog, prioridades, budgets, checkpoints, retries y cierre.
- Worker plane: ejecuta una tarea acotada por vez y entrega resultados verificables.
- Verification plane: valida archivos, comandos, estructura, scanner, integrity, findings y sandbox cuando aplique.
- Memory plane: persiste estado, cola, historial, fallos, checkpoints, directivas y artefactos.

## Alcance de esta tarea

Entregables creados por esta tarea:

- `README.md`
- `docs/project_scope.md`

No se modifica `runtime/project_state.json`, `runtime/task_queue.json`, `runtime/task_history.jsonl`, `runtime/failures.jsonl`, `runtime/checkpoints/`, `runtime/directives/` ni `runtime/logs/`.

## Validacion esperada

```bash
python3 -B -c "from pathlib import Path; missing=[p for p in ['README.md', 'docs/project_scope.md'] if not Path(p).is_file()]; assert not missing, missing"
```

## Punto de partida

Leer primero `docs/project_scope.md` para entender los limites funcionales y tecnicos antes de crear nuevas tareas o implementar modulos.
