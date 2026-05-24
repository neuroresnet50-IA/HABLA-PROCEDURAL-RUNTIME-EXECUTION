# Contexto de Continuidad

## Objetivo real del sistema

El programa no debe ser solo un editor visual ni un agente que escribe codigo.

Debe hacer esto:

1. Recibir un prompt humano normal.
2. Convertirlo a prompt HABLA procedural.
3. Ejecutar razonamiento HABLA real, no solo interpolacion de texto.
4. Orquestar LACE con 10 ciclos obligatorios.
5. Dibujar el mapa arquitectonico en vivo mientras el agente trabaja.
6. Dibujar los ciclos LACE en vivo, uno por uno.
7. Sincronizar codigo, flujo, mapa y `LACE_LOG.md` sin contradicciones.
8. Marcar desconexiones con lint visual y puntos rojos/parpadeantes.

## Lo que ya quedo hecho

### 1. Preflight HABLA real antes de lanzar Codex

- Archivo clave: `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/app.py`
- Funcion clave: `build_habla_payload()`

Ya no se usa solo `convert_to_habla()` como string.
Ahora se ejecuta `HablaEngineV4`, se serializa:

- `knowledgeType`
- `toolRequired`
- `strategy`
- `triangulatedText`
- `answerPreview`
- `directive`
- `confidence`
- `debug`
- `subTasks` si la pregunta es compuesta

### 2. Runtime visual de LACE en vivo

- Archivo clave: `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/agent_runtime.py`
- Funciones clave:
  - `_initialize_lace_cycle_visuals()`
  - `_sync_lace_runtime()`

Cuando arranca una sesion:

- reserva 10 nodos visuales en `docs/lace_cycles/`
- conecta esos nodos con `LACE_LOG.md`
- vuelve a leer `LACE_LOG.md` durante la sesion
- cambia cada ciclo entre `pending`, `analyzing`, `improving`, `completed` o `validated`
- sincroniza cada ciclo como markdown real al inspector

### 3. Estado de sesion enriquecido

La sesion expone:

- `habla`
- `laceCompletedCycles`
- `laceRequiredCycles`
- `laceCycles`

### 4. UI del agente mejorada

- Archivo clave: `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/frontend/src/components/AgentStudio.jsx`

La UI ya muestra:

- estado HABLA
- prompt procedural
- directiva HABLA
- debug resumido
- tarjetas de ciclos LACE
- subtareas compuestas

### 5. Lint visual reparado

- Archivo clave: `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/map_lint.py`

Se arreglo el bug de `known_paths` que estaba rompiendo la auditoria.
Sin eso, no aparecian hallazgos ni puntos rojos.

### 6. Motor HABLA local subido a un perfil mas completo

- Ruta:
  - `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/habla_agentic_engine/runtime/engine.py`
  - `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/habla_agentic_engine/runtime/planner.py`
  - `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/habla_agentic_engine/runtime/tools.py`
  - `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/habla_agentic_engine/runtime/memory.py`
  - `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/habla_agentic_engine/runtime/types.py`
  - `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/habla_agentic_engine/runtime/classifier.py`

Ahora incluye:

- planner compuesto
- memoria episodica activa
- orden de herramientas guiado por memoria
- mejor clasificador
- soporte para herramientas reales o inyectables
- confianza global corregida

## Verificaciones que ya pasaron

En el backend de `architecture-react-three-flask-socketio`:

```text
Ran 8 tests ... OK
```

En el demo generado:

```text
Ran 5 tests ... OK
```

## Ultima tirada observada

La ultima sesion vieja que si dejo archivos fue:

- `agent-b8c9c979cd`
- proyecto: `demo-agent-lab`

Esa tirada construyo la CLI Python y paso pruebas, pero fue anterior a la observacion final de la nueva instrumentacion profunda.

## Lo que todavia falta comprobar en una sesion nueva

Esto es lo importante para la siguiente ventana:

1. Lanzar la instancia parcheada en `5001`.
2. Abrir la UI y correr un prompt nuevo.
3. Ver si aparecen realmente:
   - `docs/habla-session.md`
   - `LACE_LOG.md`
   - `docs/lace_cycles/ciclo-01.md` ... `ciclo-10.md`
4. Confirmar si `LACE_LOG.md` mueve los ciclos visuales en vivo.
5. Confirmar si el agente realmente completa ciclos validos y no solo escribe placeholders.
6. Confirmar si el lint vuelve a prender puntos rojos cuando haya cableado roto.

## Criterio de exito de la siguiente sesion

La siguiente corrida se considera correcta solo si se ve esto:

1. El mapa se construye en vivo.
2. Los ciclos LACE cambian visualmente en vivo.
3. El panel HABLA muestra razonamiento real y no solo prompt.
4. `LACE_LOG.md` deja evidencia valida por ciclo.
5. El cierre se bloquea si no hay ciclos validos reales.
6. El sistema no se queda solo en arquitectura decorativa.

## Archivos mas importantes para seguir

- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/app.py`
- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/agent_runtime.py`
- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/map_lint.py`
- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/frontend/src/components/AgentStudio.jsx`
- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/frontend/src/App.css`
- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/habla_agentic_engine/runtime/engine.py`
- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/habla_agentic_engine/runtime/planner.py`
- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/test_agent_runtime_habla.py`
- `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/test_map_lint.py`

## Riesgo conocido

En esta shell no habia `node` ni `npm`, asi que aqui no se pudo compilar el frontend manualmente.
La logica ya quedo cambiada, pero la siguiente ventana debe relanzar la instancia real para verla en pantalla.
