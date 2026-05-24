# HABLA Session Prelude

## Requerimiento humano
PROMPT 2 - MEDIO / BUILD

  Resultado estimado: medio, 3 agentes, 4 ciclos LACE, 10 tareas máx.

  MODO MEDIO / BUILD.

  Proyecto objetivo existente y obligatorio:
  workspace/projects/sesion-20260518014728-jeego-en-3d

  Mantener el mismo slug. Si el sistema intenta abrir otro slug o crear otra carpeta de proyecto, detener.

  Mejorar el frontend del juego 3D de drones agregando un panel de briefing tactico conectado a datos existentes:

  - dron policia
  - dron azul
  - amenaza
  - placa buscada
  - rostro buscado

  El panel debe actualizarse desde app.js, tener estilos responsive y no alterar fisica, DQN ni combate.

  Validar:
  - HTML/CSS/JS existentes
  - node --check frontend/app.js
  - browser smoke

PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:
Dictamen: El orquestador recomienda 4 subagente(s) para esta tarea.
Politica de turnos: round_robin_serialized
Regla: escribir solo razonamiento publico, acciones, observaciones, evidencia y siguiente paso; no exponer cadena de pensamiento privada.
Subagentes disponibles:
- S01 Planner (turno 1): Descompone el prompt en pasos, riesgos y entregables.
- S02 Frontend (turno 2): Implementa interfaz, canvas, estilos y experiencia visual.
- S03 Backend (turno 3): Ajusta endpoints, runtime, persistencia y contratos.
- S04 QA Browser (turno 4): Valida navegador real, consola JS, screenshot, WebGL y HUD.
El agente principal debe coordinar estos roles, evitar conflictos y reportar en consola eventos publicos por turno.

## Estado del motor HABLA
- disponible: si
- knowledgeType: PROYECTO_CODIGO
- toolRequired: filesystem
- strategy: construir_y_validar
- safeToAnswer: True
- blocked: False
- confidence.dato: 60
- confidence.fecha: 60
- confidence.fuente: 40
- confidence.calculo: 0
- confidence.inferencia: 70
- confidence.global: 57.5

## LACE
- ciclos obligatorios: 10
- policyPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/sesion-20260518014728-jeego-en-3d/LACE.md
- logPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/sesion-20260518014728-jeego-en-3d/LACE_LOG.md

## Triangulacion
No hay valores numéricos para triangular.

## Respuesta tentativa del motor
Respuesta generada bajo control HABLA: separaré hecho, inferencia y límites de conocimiento.

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
PROMPT 2 - MEDIO / BUILD

  Resultado estimado: medio, 3 agentes, 4 ciclos LACE, 10 tareas máx.

  MODO MEDIO / BUILD.

  Proyecto objetivo existente y obligatorio:
  workspace/projects/sesion-20260518014728-jeego-en-3d

  Mantener el mismo slug. Si el sistema intenta abrir otro slug o crear otra carpeta de proyecto, detener.

  Mejorar el frontend del juego 3D de drones agregando un panel de briefing tactico conectado a datos existentes:

  - dron policia
  - dron azul
  - amenaza
  - placa buscada
  - rostro buscado

  El panel debe actualizarse desde app.js, tener estilos responsive y no alterar fisica, DQN ni combate.

  Validar:
  - HTML/CSS/JS existentes
  - node --check frontend/app.js
  - browser smoke

PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:
Dictamen: El orquestador recomienda 4 subagente(s) para esta tarea.
Politica de turnos: round_robin_serialized
Regla: escribir solo razonamiento publico, acciones, observaciones, evidencia y siguiente paso; no exponer cadena de pensamiento privada.
Subagentes disponibles:
- S01 Planner (turno 1): Descompone el prompt en pasos, riesgos y entregables.
- S02 Frontend (turno 2): Implementa interfaz, canvas, estilos y experiencia visual.
- S03 Backend (turno 3): Ajusta endpoints, runtime, persistencia y contratos.
- S04 QA Browser (turno 4): Valida navegador real, consola JS, screenshot, WebGL y HUD.
El agente principal debe coordinar estos roles, evitar conflictos y reportar en consola eventos publicos por turno.
```

## Evidencia recuperada
- memoria_llm: Conocimiento estable recuperado desde memoria interna.

## Traza resumida
- LACE => política cargada desde /home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual/LACE.md
- CLASSIFY => INFERENCIA_OPINION / llm_reasoning_declared / rule_fallback / patrones de opinión/inferencia
- PLANNER => pregunta atómica
- MEMORY_TOOL_ORDER => ['memory_optional', 'rag_local']
- THOUGHT => intento=1, tool=memory_optional
- OBSERVATION => 1 evidencia(s) desde memory_optional
- TRIANGULATE => sin valores
- CONFIDENCE => dato=60, fuente=40
- CONSTITUTIONAL => safe=True, reason=
