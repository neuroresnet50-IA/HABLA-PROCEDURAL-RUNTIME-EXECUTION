# HABLA Session Prelude

## Requerimiento humano
sesion-20260518014728 JEEGO EN 3D
workspace/projects/sesion-20260518014728-jeego-en-3d
296 archivos detectados en el proyecto seleccionado perfecto  si arranca  pero estamos teniendo problemas  con la pantalla negra no se muestra el render  de la animacion 3d  verifique todo el programa  y por favor lances el juego y tomen screens  tomas de pantalla para que se den cuanta  de la falla

## Estado del motor HABLA
- disponible: si
- knowledgeType: HECHO_ESTABLE
- toolRequired: memory_optional
- strategy: memoria_con_verificacion_opcional
- safeToAnswer: True
- blocked: False
- confidence.dato: 85
- confidence.fecha: 80
- confidence.fuente: 40
- confidence.calculo: 0
- confidence.inferencia: 20
- confidence.global: 56.25

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
LACE v2.0 ESTA ACTIVO Y FUE LEIDO ANTES DE ARRANCAR EL AGENTE.
REGLA ABSOLUTA: no declares proyecto terminado hasta completar 10 ciclos documentados en LACE_LOG.md.
Cada ciclo debe usar HABLA por capas: interpretación, clasificación, planificación, ReAct, evidencia, triangulación, confianza, autocrítica, memoria y acción final.
Antes de modificar código, escribe THOUGHT/ACTION/OBSERVATION en LACE_LOG.md.
Antes de cerrar, verifica la puerta de cierre LACE.

PROTOCOLO DE RESPUESTA CONTROLADA POR HABLA V5.0 + LACE

PREGUNTA HUMANA:
sesion-20260518014728 JEEGO EN 3D
workspace/projects/sesion-20260518014728-jeego-en-3d
296 archivos detectados en el proyecto seleccionado perfecto  si arranca  pero estamos teniendo problemas  con la pantalla negra no se muestra el render  de la animacion 3d  verifique todo el programa  y por favor lances el juego y tomen screens  tomas de pantalla para que se den cuanta  de la falla

TIPO DE CONOCIMIENTO:
HECHO_ESTABLE

EVIDENCIA:
- memoria_llm: Conocimiento estable recuperado desde memoria interna. (valor=None)

SUBTAREAS COMPUESTAS:
- No aplica.

TRIANGULACION:
No hay valores numéricos para triangular.

CONFIANZA POR COMPONENTE:
- dato: 85
- fecha: 80
- fuente: 40
- calculo: 0
- inferencia: 20
- global: 56.2

REGLAS OBLIGATORIAS:
1. No inventes datos.
2. No ocultes incertidumbre.
3. Separa hecho, cálculo e inferencia.
4. Si es estimación, dilo explícitamente.
5. Si la evidencia es insuficiente, declara el límite.

ESTADO CONSTITUCIONAL:
- safe_to_answer: True
- blocked: False
- block_reason: 

INSTRUCCION:
Responde al usuario en español, como chat natural, pero respetando todas las reglas anteriores.
```

## Prompt HABLA BASIC
```text
PROTOCOLO habla_reasoning_agent_v4:

OBJETIVO:
Resolver la pregunta humana sin inventar información, usando clasificación semántica, ReAct, RAG, triangulación, confianza por componente, verificación constitucional y memoria episódica.

ENTRADA:
-> DEFINE pregunta_usuario COMO "sesion-20260518014728 JEEGO EN 3D
workspace/projects/sesion-20260518014728-jeego-en-3d
296 archivos detectados en el proyecto seleccionado perfecto  si arranca  pero estamos teniendo problemas  con la pantalla negra no se muestra el render  de la animacion 3d  verifique todo el programa  y por favor lances el juego y tomen screens  tomas de pantalla para que se den cuanta  de la falla"
-> VERIFICA pregunta_usuario ≠ ""

FASE 0: SEMANTIC_CLASSIFIER
-> ANALIZA pregunta_usuario por significado
-> CLASIFICA como HECHO_TEMPORAL, CALCULO, HECHO_ESTABLE o INFERENCIA_OPINION

FASE 1: THOUGHT
-> DEFINE estrategia según clasificación

FASE 2: ACTION
-> USA herramienta obligatoria si aplica

FASE 3: OBSERVATION
-> SI no hay evidencia, cambia estrategia y reintenta

FASE 4: RAG_RECUPERATION
-> RECUPERA fragmentos candidatos sin validarlos todavía

FASE 5: TRIANGULATE
-> COMPARA fuentes y detecta consistencia, contradicción o evidencia limitada

FASE 6: CONFIDENCE_PER_COMPONENT
-> ASIGNA confianza a dato, fecha, fuente, cálculo e inferencia

FASE 7: CONSTITUTIONAL_CHECK
-> NO inventar
-> NO ocultar incertidumbre
-> SEPARAR hecho, cálculo e inferencia
-> BLOQUEAR si evidencia insuficiente

FASE 8: ANSWER
-> RESPONDE con dato, margen, confianza y límites

FASE 9: EPISODIC_MEMORY_UPDATE
-> GUARDA tipo, herramienta, resultado y confianza
FIN PROTOCOLO
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
