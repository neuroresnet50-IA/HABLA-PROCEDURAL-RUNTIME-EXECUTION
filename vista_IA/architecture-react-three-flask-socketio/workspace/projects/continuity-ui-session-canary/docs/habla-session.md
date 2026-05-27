# HABLA Session Prelude

## Requerimiento humano
Crear una tarea real pequeña desde la ruta normal de la UI y medir toda la transaccion interna del servidor.

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
- ciclos maximos: 3
- salida temprana: scanner, sandbox, integrity, findings y cola sin pendientes
- policyPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/continuity-ui-session-canary/LACE.md
- logPath: /home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/workspace/projects/continuity-ui-session-canary/LACE_LOG.md

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
Crear una tarea real pequeña desde la ruta normal de la UI y medir toda la transaccion interna del servidor.
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
