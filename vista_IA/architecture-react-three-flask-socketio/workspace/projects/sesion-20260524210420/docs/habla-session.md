# HABLA Session Prelude

## Requerimiento humano
MODO EJECUCION AGENTICA CONTROLADA.

Proyecto existente: sesion-20260524210420.

No crear proyecto nuevo. No cambiar workspace. No blanquear el proyecto. Trabajar como refactor/continuacion sobre los archivos actuales.

Retomar la orden recuperada de la tarea RUNTIME-20260525010939-001. Relanzarla como ejecucion limpia de runtime, no como proyecto nuevo.

Orden original:
Validacion smoke de runtime HABLA/Codex: inspecciona LACE.md, LACE_LOG.md y docs/habla-session.md; no modifiques archivos, emite evidencia breve y termina.

Regla de cierre obligatoria:
No marcar completado solo porque existen archivos. Antes de cerrar debe pasar prueba real de navegador:
- abrir el juego en navegador o sandbox
- comprobar que existe canvas
- comprobar WebGL activo o fallback funcional
- consola JS sin excepciones
- screenshot no negro
- HUD o telemetria actualiza
- si falla, dejar tarea blocked con evidencia, no completed

Entregables esperados:
- runtime/backups/habla_runtime_repair/20260525T005750Z/project_state.before.json
- runtime/backups/habla_runtime_repair/20260525T005750Z/task_queue.before.json
- runtime/complexity_estimate.json

Validacion obligatoria:
- python3 -B -c "from pathlib import Path; missing=[p for p in ['runtime/backups/habla_runtime_repair/20260525T005750Z/project_state.before.json', 'runtime/backups/habla_runtime_repair/20260525T005750Z/task_queue.before.json', 'runtime/complexity_estimate.json'] if not Path(p).is_file()]; assert not missing, missing"

PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:
Dictamen: Dificultad Facil: 1 subagente(s), 2 ciclo(s) LACE y hasta 3 tarea(s).
Dificultad: Facil | score: 8 | ciclos LACE: 2 | max tareas: 3
Herramientas requeridas: pytest
Politica de turnos: round_robin_serialized
Regla: escribir solo razonamiento publico, acciones, observaciones, evidencia y siguiente paso; no exponer cadena de pensamiento privada.
Subagentes disponibles:
- S01 Planner (turno 1): Descompone el prompt en pasos, riesgos y entregables.
El agente principal debe coordinar estos roles, evitar conflictos y reportar en consola eventos publicos por turno.

## Estado del motor HABLA
- disponible: si
- knowledgeType: PROYECTO_CODIGO
- toolRequired: filesystem
- strategy: construir_y_validar
- safeToAnswer: True
- blocked: False
- confidence.dato: 99
- confidence.fecha: 100
- confidence.fuente: 100
- confidence.calculo: 99
- confidence.inferencia: 0
- confidence.global: 99.5

## LACE
- ciclos minimos: 2
- ciclos maximos: 6
- salida temprana: scanner, sandbox, integrity, findings y cola sin pendientes
- policyPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/sesion-20260524210420/LACE.md
- logPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/sesion-20260524210420/LACE_LOG.md

## Triangulacion
Una sola fuente indica aproximadamente 20,260,524,210,420.

## Respuesta tentativa del motor
Resultado calculado: 20260524210420

## Directiva HABLA para Codex
```text
Esta sesion es de implementacion de codigo. Construye el proyecto solicitado en disco, valida con archivos y pruebas reales, y no trates la tarea como una pregunta teorica bloqueada.
```

## Prompt HABLA BASIC
```text
PROTOCOLO HABLA PARA EJECUCION DE PROYECTO DE CODIGO

OBJETIVO:
Construir y validar en disco el proyecto solicitado por el usuario, sin tratar la tarea como una pregunta teórica.

INSTRUCCIONES OPERATIVAS:
1. Interpreta el requerimiento como trabajo de implementacion real sobre archivos.
2. Usa el filesystem del proyecto como fuente primaria de evidencia.
3. Si falta contexto, crea una base minima coherente y luego iterala con validacion tecnica.
4. No bloquees la ejecucion por ausencia de evidencia externa; la evidencia debe surgir del codigo, pruebas y archivos creados.
5. Reporta limites reales del entorno solo despues de intentar validar.

REQUERIMIENTO HUMANO:
MODO EJECUCION AGENTICA CONTROLADA.

Proyecto existente: sesion-20260524210420.

No crear proyecto nuevo. No cambiar workspace. No blanquear el proyecto. Trabajar como refactor/continuacion sobre los archivos actuales.

Retomar la orden recuperada de la tarea RUNTIME-20260525010939-001. Relanzarla como ejecucion limpia de runtime, no como proyecto nuevo.

Orden original:
Validacion smoke de runtime HABLA/Codex: inspecciona LACE.md, LACE_LOG.md y docs/habla-session.md; no modifiques archivos, emite evidencia breve y termina.

Regla de cierre obligatoria:
No marcar completado solo porque existen archivos. Antes de cerrar debe pasar prueba real de navegador:
- abrir el juego en navegador o sandbox
- comprobar que existe canvas
- comprobar WebGL activo o fallback funcional
- consola JS sin excepciones
- screenshot no negro
- HUD o telemetria actualiza
- si falla, dejar tarea blocked con evidencia, no completed

Entregables esperados:
- runtime/backups/habla_runtime_repair/20260525T005750Z/project_state.before.json
- runtime/backups/habla_runtime_repair/20260525T005750Z/task_queue.before.json
- runtime/complexity_estimate.json

Validacion obligatoria:
- python3 -B -c "from pathlib import Path; missing=[p for p in ['runtime/backups/habla_runtime_repair/20260525T005750Z/project_state.before.json', 'runtime/backups/habla_runtime_repair/20260525T005750Z/task_queue.before.json', 'runtime/complexity_estimate.json'] if not Path(p).is_file()]; assert not missing, missing"

PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:
Dictamen: Dificultad Facil: 1 subagente(s), 2 ciclo(s) LACE y hasta 3 tarea(s).
Dificultad: Facil | score: 8 | ciclos LACE: 2 | max tareas: 3
Herramientas requeridas: pytest
Politica de turnos: round_robin_serialized
Regla: escribir solo razonamiento publico, acciones, observaciones, evidencia y siguiente paso; no exponer cadena de pensamiento privada.
Subagentes disponibles:
- S01 Planner (turno 1): Descompone el prompt en pasos, riesgos y entregables.
El agente principal debe coordinar estos roles, evitar conflictos y reportar en consola eventos publicos por turno.
```

## Evidencia recuperada
- calculadora: Resultado calculado: 20260524210420 (valor=20260524210420.0)

## Traza resumida
- LACE => política cargada desde /home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual/LACE.md
- CLASSIFY => CALCULO / calculator / rule_fallback / patrones de cálculo
- PLANNER => pregunta atómica
- MEMORY_TOOL_ORDER => ['calculator']
- THOUGHT => intento=1, tool=calculator
- OBSERVATION => 1 evidencia(s) desde calculator
- TRIANGULATE => una fuente
- CONFIDENCE => dato=99, fuente=100
- CONSTITUTIONAL => safe=True, reason=
- OVERRIDE => coding_task_bypass_habla_block
