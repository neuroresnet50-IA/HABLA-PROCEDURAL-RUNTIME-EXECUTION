# HABLA Session Prelude

## Requerimiento humano
MODO EJECUCION AGENTICA CONTROLADA.

Proyecto existente: continuity-code-pf-003.

No crear proyecto nuevo. No cambiar workspace. No blanquear el proyecto. Trabajar como refactor/continuacion sobre los archivos actuales.

Retomar la orden recuperada de la tarea RUNTIME-20260604020052-002. Relanzarla como ejecucion limpia de runtime, no como proyecto nuevo.

Orden original:
Escribe la solucion o plan en docs/advanced_programming_case_003.md, manten el cambio pequeno, registra evidencia y no modifiques archivos no relacionados.

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
- docs/advanced_programming_case_003.md

Validacion obligatoria:
- python3 -B -c "from pathlib import Path; missing=[p for p in ['docs/advanced_programming_case_003.md'] if not Path(p).is_file()]; assert not missing, missing"

PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:
Dictamen: Dificultad Facil: 1 subagente(s), 2 ciclo(s) LACE y hasta 3 tarea(s).
Dificultad: Facil | score: 15 | ciclos LACE: 2 | max tareas: 3
Herramientas requeridas: sandbox, scanner
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
- ciclos maximos: 7
- salida temprana: scanner, sandbox, integrity, findings y cola sin pendientes
- policyPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/continuity-code-pf-003/LACE.md
- logPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/continuity-code-pf-003/LACE_LOG.md

## Triangulacion
No hay valores numéricos para triangular.

## Respuesta tentativa del motor
No puedo responder con seguridad suficiente. Causa: No se obtuvo evidencia suficiente después de los intentos.

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

Proyecto existente: continuity-code-pf-003.

No crear proyecto nuevo. No cambiar workspace. No blanquear el proyecto. Trabajar como refactor/continuacion sobre los archivos actuales.

Retomar la orden recuperada de la tarea RUNTIME-20260604020052-002. Relanzarla como ejecucion limpia de runtime, no como proyecto nuevo.

Orden original:
Escribe la solucion o plan en docs/advanced_programming_case_003.md, manten el cambio pequeno, registra evidencia y no modifiques archivos no relacionados.

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
- docs/advanced_programming_case_003.md

Validacion obligatoria:
- python3 -B -c "from pathlib import Path; missing=[p for p in ['docs/advanced_programming_case_003.md'] if not Path(p).is_file()]; assert not missing, missing"

PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:
Dictamen: Dificultad Facil: 1 subagente(s), 2 ciclo(s) LACE y hasta 3 tarea(s).
Dificultad: Facil | score: 15 | ciclos LACE: 2 | max tareas: 3
Herramientas requeridas: sandbox, scanner
Politica de turnos: round_robin_serialized
Regla: escribir solo razonamiento publico, acciones, observaciones, evidencia y siguiente paso; no exponer cadena de pensamiento privada.
Subagentes disponibles:
- S01 Planner (turno 1): Descompone el prompt en pasos, riesgos y entregables.
El agente principal debe coordinar estos roles, evitar conflictos y reportar en consola eventos publicos por turno.
```

## Traza resumida
- PLANNER => pregunta atómica
- MEMORY_TOOL_ORDER => ['calculator']
- THOUGHT => intento=1, tool=calculator
- OBSERVATION => vacío con calculator
- THOUGHT => intento=2, tool=calculator
- OBSERVATION => vacío con calculator
- THOUGHT => intento=3, tool=calculator
- OBSERVATION => vacío con calculator
- THOUGHT => intento=4, tool=calculator
- OBSERVATION => vacío con calculator
- TRIANGULATE => sin valores
- CONFIDENCE => dato=99, fuente=100
