# HABLA Session Prelude

## Requerimiento humano
[CONTEXTO AUTORIZADO CYBERLACE]
La accion insegura anterior fue negada. Esta orden reemplaza el camino peligroso por una alternativa segura permitida.

[PROMPT SEGURO GENERADO POR CYBERLACE]
Proyecto: sesion-20260601004224
Sesion origen: agent-4f3d430a9a

Redisenar esta tarea con datos sinteticos, evidencia redactada, controles de acceso y sin procesar informacion sensible local.

Reglas de continuacion segura:
- No ejecutar el prompt original bloqueado.
- No incluir secretos, credenciales, bypasses ni acciones destructivas no verificadas.
- Mantener cambios dentro del workspace autorizado.
- Validar por filesystem y registrar evidencia antes de completed=true.

PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:
Dictamen: Dificultad Extradificil: 6 subagente(s), 8 ciclo(s) LACE y hasta 32 tarea(s).
Dificultad: Extradificil | score: 75 | ciclos LACE: 8 | max tareas: 32
Herramientas requeridas: findings, integrity, sandbox, scanner
Politica de turnos: round_robin_serialized
Regla: escribir solo razonamiento publico, acciones, observaciones, evidencia y siguiente paso; no exponer cadena de pensamiento privada.
Subagentes disponibles:
- S01 Planner (turno 1): Descompone el prompt en pasos, riesgos y entregables.
- S02 Frontend (turno 2): Implementa interfaz, canvas, estilos y experiencia visual.
- S03 Backend (turno 3): Ajusta endpoints, runtime, persistencia y contratos.
- S04 QA Browser (turno 4): Valida navegador real, consola JS, screenshot, WebGL y HUD.
- S05 Observer (turno 5): Vigila incidentes, integridad, bloqueos y evidencia del mapa.
- S06 LACE Docs (turno 6): Documenta ciclos, memoria, decisiones y cierre auditable.
El agente principal debe coordinar estos roles, evitar conflictos y reportar en consola eventos publicos por turno.

## Estado del motor HABLA
- disponible: si
- knowledgeType: PROYECTO_CODIGO
- toolRequired: filesystem
- strategy: construir_y_validar
- safeToAnswer: True
- blocked: False
- confidence.dato: 85
- confidence.fecha: 80
- confidence.fuente: 40
- confidence.calculo: 0
- confidence.inferencia: 20
- confidence.global: 56.25

## LACE
- ciclos minimos: 2
- ciclos maximos: 9
- salida temprana: scanner, sandbox, integrity, findings y cola sin pendientes
- policyPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/sesion-20260601004224-alternativa-segura-2/LACE.md
- logPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/sesion-20260601004224-alternativa-segura-2/LACE_LOG.md

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
[CONTEXTO AUTORIZADO CYBERLACE]
La accion insegura anterior fue negada. Esta orden reemplaza el camino peligroso por una alternativa segura permitida.

[PROMPT SEGURO GENERADO POR CYBERLACE]
Proyecto: sesion-20260601004224
Sesion origen: agent-4f3d430a9a

Redisenar esta tarea con datos sinteticos, evidencia redactada, controles de acceso y sin procesar informacion sensible local.

Reglas de continuacion segura:
- No ejecutar el prompt original bloqueado.
- No incluir secretos, credenciales, bypasses ni acciones destructivas no verificadas.
- Mantener cambios dentro del workspace autorizado.
- Validar por filesystem y registrar evidencia antes de completed=true.

PROTOCOLO DE SUBAGENTES ASIGNADOS POR UI:
Dictamen: Dificultad Extradificil: 6 subagente(s), 8 ciclo(s) LACE y hasta 32 tarea(s).
Dificultad: Extradificil | score: 75 | ciclos LACE: 8 | max tareas: 32
Herramientas requeridas: findings, integrity, sandbox, scanner
Politica de turnos: round_robin_serialized
Regla: escribir solo razonamiento publico, acciones, observaciones, evidencia y siguiente paso; no exponer cadena de pensamiento privada.
Subagentes disponibles:
- S01 Planner (turno 1): Descompone el prompt en pasos, riesgos y entregables.
- S02 Frontend (turno 2): Implementa interfaz, canvas, estilos y experiencia visual.
- S03 Backend (turno 3): Ajusta endpoints, runtime, persistencia y contratos.
- S04 QA Browser (turno 4): Valida navegador real, consola JS, screenshot, WebGL y HUD.
- S05 Observer (turno 5): Vigila incidentes, integridad, bloqueos y evidencia del mapa.
- S06 LACE Docs (turno 6): Documenta ciclos, memoria, decisiones y cierre auditable.
El agente principal debe coordinar estos roles, evitar conflictos y reportar en consola eventos publicos por turno.
```

## Evidencia recuperada
- memoria_llm: Conocimiento estable recuperado desde memoria interna.

## Traza resumida
- LACE => política cargada desde /home/neurodriver/BASE _METACOGNICION_COLOMBIA/habla_agentic_engine_v5_1_lace_visual/LACE.md
- CLASSIFY => HECHO_ESTABLE / memory_optional / rule_fallback / fallback estable por falta de señales temporales
- PLANNER => pregunta atómica
- MEMORY_TOOL_ORDER => ['memory_optional', 'rag_local']
- THOUGHT => intento=1, tool=memory_optional
- OBSERVATION => 1 evidencia(s) desde memory_optional
- TRIANGULATE => sin valores
- CONFIDENCE => dato=85, fuente=40
- CONSTITUTIONAL => safe=True, reason=
