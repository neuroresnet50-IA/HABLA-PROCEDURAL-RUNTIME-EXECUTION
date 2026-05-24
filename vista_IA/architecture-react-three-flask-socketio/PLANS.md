# PLANS.md

## Visión del proyecto
Rediseñar el runtime actual para convertirlo en un orquestador autónomo de proyectos cortos, medianos y largos.

## Problema actual
El sistema actual es frágil por diseño porque:
1. clasifica tareas grandes como smoke por heurísticas frágiles,
2. mata sesiones útiles por timeouts rígidos,
3. el retry puede quedar esperando indefinidamente al proceso anterior.

## Nueva tesis operativa
No tratar proyectos largos como una sola sesión larga.
Dividir el trabajo en tareas pequeñas, verificables, persistentes y reanudables.

## Resultado esperado
Un runtime que:
- divide proyectos grandes,
- ejecuta tarea por tarea,
- valida por evidencia real,
- crea checkpoints,
- se recupera de fallos,
- reanuda tras reinicios,
- desacopla el worker del sistema central.

---

# PLAN FORENSE — HABLA Observer IA

## Objetivo
Volver al Observer más inteligente que un monitor genérico: debe detectar manipulación externa de archivos, cambios hechos por editores fuera del sistema, diferencias por línea/carácter y contradicciones entre UI, backend, runtime, scanner, sandbox y logs.

## Tesis
El sistema no puede confiar solo en que el worker diga "completado". Debe crear una baseline auditable, mirar el disco después, comparar hashes y texto, y explicar cualquier divergencia con evidencia verificable.

## Pasos

### 1. Baseline forense
- Crear un manifiesto de archivos generados por agentes después del scanner final.
- Persistir rutas, contenido base, métricas, SHA-256, fecha de baseline y origen.
- Guardar el artefacto como `runtime/artifacts/agent_file_manifest.json`.
- Sellar la baseline con `runtime/artifacts/agent_file_manifest.seal.json`.
- Guardar una copia de bóveda en `runtime/baseline_vault/<sha256>/agent_file_manifest.json`.
- Detectar `baseline_manifest_tampered`, `baseline_seal_tampered`, `baseline_unsealed` y `baseline_vault_tampered`.
- Anclar el sello fuera del árbol del proyecto en `.runtime/baseline_anchors/<project>/latest_anchor.json` o `HABLA_BASELINE_ANCHOR_ROOT`.
- Si existe `HABLA_BASELINE_SIGNING_KEY`, firmar el ancla con HMAC-SHA256.
- Detectar `baseline_external_anchor_missing`, `baseline_external_anchor_mismatch`, `baseline_external_anchor_tampered` y `baseline_external_anchor_vault_tampered`.

### 2. Registro de escrituras internas
- Registrar escrituras autorizadas desde el editor/API del sistema.
- Persistir antes/después, SHA-256 y razón en `runtime/file_write_ledger.jsonl`.
- Usar ese ledger para distinguir cambios internos legítimos de cambios externos.

### 3. Escaneo de integridad
- Comparar disco actual contra la baseline.
- Ignorar cambios internos registrados después de la baseline.
- Generar `runtime/artifacts/file_integrity_report.json`.

### 4. Tipos de hallazgo
- `file_modified`: archivo generado modificado externamente.
- `file_deleted`: archivo generado eliminado externamente.
- `untracked_file`: archivo nuevo no registrado en baseline.
- `char_replaced`: segmento o carácter reemplazado.
- `char_deleted`: segmento o carácter eliminado.
- `char_inserted`: segmento o carácter insertado.

### 5. Evidencia por carácter
Cada hallazgo debe incluir, cuando aplique:
- ruta relativa,
- línea,
- columna,
- longitud,
- texto esperado,
- texto actual,
- SHA-256 esperado,
- SHA-256 actual,
- mensaje explicable.

### 6. Prioridad en HABLA Observer IA
Antes de observaciones genéricas de mapa o flujo, el Observer debe emitir:
- `external_file_change_detected`,
- `external_file_deletion_detected`,
- `untracked_file_detected`,
- `char_level_tamper_detected`.

### 7. Evidencia visual en Workbench
- Mostrar alerta roja cuando existan cambios externos.
- Enfocar el primer hallazgo.
- Dibujar huellas rojas sobre líneas/caracteres afectados.
- Permitir aceptar una nueva baseline solo por decisión humana.

### 8. Observer findings persistente
- Crear una cola/reporte persistente `runtime/artifacts/observer_findings.json`.
- Integrar hallazgos de integridad, scanner, sandbox, lint y runtime.
- Asignar `observationScore`, severidad, fuente, fingerprint SHA-256, evidencia y acción recomendada.
- Mantener `firstSeenAt`, `lastSeenAt`, `occurrenceCount` y estado `active/resolved`.
- Hacer que el estado del Observer y futuras UI puedan leer esa evidencia sin depender de memoria de chat.

### 9. Frozen Sniper recovery
- Congelar evidencia antes de tocar archivos dañados.
- Restaurar archivos generados modificados o eliminados usando `agent_file_manifest.json`.
- Mover archivos no registrados a `runtime/frozen_sniper/<run>/quarantine/`, sin borrarlos.
- Persistir `runtime/artifacts/frozen_sniper_recovery_report.json`.
- Exigir confirmación humana `FROZEN_SNIPER` antes de restaurar o cuarentenar.
- Exponer la acción desde el Workbench cuando existan hallazgos rojos de integridad.

## Criterios de aceptación
- Un cambio externo de archivo generado aparece en `file_integrity_report.json`.
- Un cambio por carácter reporta línea, columna y SHA-256.
- Una escritura hecha desde el editor del sistema no se marca como ataque externo si está en el ledger.
- El Observer prioriza integridad sobre mapa/flujo.
- `observer_findings.json` persiste hallazgos con score y fingerprint SHA-256.
- La UI muestra alerta/huella roja y permite revisar el primer hallazgo.
- Frozen Sniper restaura archivos dañados/eliminados desde baseline y cuarentena archivos no registrados sin destruir evidencia.
- La baseline queda protegida por sello SHA-256 y bóveda; si se altera, el scanner no debe confiar silenciosamente en ella.
- Si una IA reescribe manifiesto, sello y bóveda dentro del proyecto, el ancla externa debe delatar la divergencia.

---

# CONTRATO DE HERRAMIENTAS INTERNAS PARA AGENTES

Documento canonico: `docs/agent_internal_tools_contract.md`.

Objetivo:
- permitir que agentes Codex usen herramientas internas reales;
- exponer Scanner, Integrity, Observer y Sniper por CLI/API auditable;
- evitar que Observer trabaje sin mision o por polling;
- exigir evidencia JSON antes de declarar exito.

Comando canonico:

```text
python3 orchestrator/agent_tools.py <command>
```

Criterios de aceptacion:
- cada invocacion queda en `runtime/agent_tool_invocations.jsonl` o en el log automatico `runtime/tool_invocation_policy.jsonl` del proyecto;
- `observer-status` no activa misiones;
- `scanner`, `integrity` y `sniper` devuelven reportes reales;
- el CLI devuelve salida compacta por defecto y exige `--full` para payload completo;
- `sniper --confirm FROZEN_SNIPER` queda restringido por politica de seguridad;
- `sniper` automatico solo corre en `--dry-run` durante `recovery_preview`;
- `AGENTS.md` contiene reglas obligatorias de uso.

Estado de implementacion 2026-05-19:
- Implementado `orchestrator/tool_invocation_policy.py`.
- `AgentRuntime` ejecuta preflight, postflight, task completion gate, recovery preview y project completion gate.
- Los artefactos de la politica quedan bajo `runtime/artifacts/tool_invocations/` y no cuentan como evidencia de producto.
- Checkpoint: `runtime/checkpoints/tool-invocation-policy-20260519T122321-0700.json`.

---

# PLAN DE CICLO DE VIDA FINITO — OBSERVER ENGINE

## Problema detectado
El Observer actual puede quedarse emitiendo actividad durante horas porque combina tres cosas distintas en un mismo flujo:
- vigilancia forense,
- animacion visual de scanner,
- polling de UI/reviewer/sandbox.

Eso crea una señal falsa para el humano: parece que el motor sigue trabajando en el incidente, aunque no exista una tarea activa y el proyecto ya tenga `current_task_id=null`.

## Principio operativo
Observer no debe ser un worker permanente.
Observer debe actuar como un ciclo finito de diagnostico por incidente:

```text
trigger -> snapshot -> clasificacion -> inspeccion acotada -> decision -> evidencia -> cierre
```

Si necesita seguir mirando, debe abrir un nuevo incidente con nueva causa, no permanecer indefinidamente en el mismo barrido.

## Definicion de incidente Observer
Un incidente Observer es una unidad reanudable y persistente con:
- `incidentId`,
- `projectSlug`,
- `trigger`,
- `startedAt`,
- `deadlineAt`,
- `maxTicks`,
- `status`,
- `currentPhase`,
- `fingerprintsSeen`,
- `evidencePaths`,
- `decision`,
- `stopReason`.

Debe persistirse en:

```text
.runtime/observer/incidents/<incidentId>.json
.runtime/observer/timeline.jsonl
runtime/artifacts/observer_findings.json
runtime/checkpoints/
```

## Triggers permitidos
Observer solo puede iniciar un incidente por una senal explicita:
- sesion de agente iniciada,
- sesion de agente cerrada,
- scanner final solicitado,
- integridad solicitada,
- sandbox solicitado,
- usuario presiona "Observar ahora",
- usuario activa modo autonomo con pin humano,
- runtime detecta contradiccion entre `completed` y evidencia fallida.

No debe iniciar un incidente por:
- polling normal de UI,
- refresco de archivos,
- socket heartbeat,
- lectura de status,
- el simple hecho de que Chrome este abierto.

## Estados finitos
Estados obligatorios del ciclo:

```text
idle
incident_opened
snapshotting
classifying
scanning_integrity
checking_scanner
checking_sandbox
checking_typewriter
checking_runtime
proposing_action
waiting_human
cooling_down
completed
blocked
expired
```

Reglas:
- `idle` no emite scanner visual.
- `completed`, `blocked` y `expired` son estados terminales del incidente.
- Un estado terminal debe apagar el bucle del incidente.
- El proceso global puede quedar vivo como servicio, pero sin barrido ni mensajes repetidos.

## Presupuestos obligatorios
Cada incidente debe tener limites duros:
- `maxRuntimeSeconds`: por defecto 180 segundos.
- `maxTicks`: por defecto 30 ticks.
- `maxRepeatedEvents`: por defecto 3 eventos con la misma firma.
- `maxFilesForVisualScan`: por defecto 3 archivos en UI.
- `maxLinesForVisualScan`: por defecto 200 lineas por archivo en UI.
- `endpointTimeoutSeconds`: por defecto 3 segundos para status/snapshot.
- `cooldownSeconds`: por defecto 60 segundos antes de reabrir el mismo fingerprint.

El scanner persistente puede leer todo el proyecto si la politica lo exige, pero la animacion visual no puede intentar representar indefinidamente todo el workspace.

## Firma de repeticion
Cada observacion debe calcular una firma estable:

```text
projectSlug + state + behavior + focusPath + findingFingerprint + evidenceHash
```

Si la misma firma se repite mas de `maxRepeatedEvents`, el Observer debe:
1. dejar un evento `observer_repeated_finding_suppressed`,
2. pasar el incidente a `waiting_human` o `completed_with_findings`,
3. dejar de emitir el mismo mensaje visual.

## Algoritmo funcional
Documento canonico del algoritmo detallado: `docs/observer_engine_algorithm.md`.

1. Recibir trigger explicito.
2. Crear `incidentId` y checkpoint inicial.
3. Tomar snapshot con timeout:
   - `project_state.json`,
   - `task_queue.json`,
   - `task_history.jsonl` reciente,
   - `final_code_scanner_report.json`,
   - `final_typewriter_report.json`,
   - `sandbox.json`,
   - `file_integrity_report.json`,
   - `observer_findings.json`.
4. Clasificar causa raiz:
   - agente activo,
   - cierre incompleto,
   - scanner faltante,
   - sandbox faltante,
   - typewriter fallido,
   - integridad fallida,
   - UI polling solamente,
   - sin evidencia nueva.
5. Si solo hay polling de UI y no hay agente activo, cerrar como `completed` con `stopReason=ui_polling_only`.
6. Si hay hallazgo real, inspeccionar solo el primer grupo prioritario:
   - integridad,
   - scanner,
   - sandbox,
   - typewriter,
   - lint,
   - runtime.
7. Persistir reporte y evento con evidencia.
8. Proponer una accion segura o pedir confirmacion humana.
9. Detener el incidente cuando se cumpla una condicion terminal.

## Condiciones de parada
Observer debe parar el incidente cuando ocurra cualquiera de estas condiciones:
- no hay tarea activa y no hay evidencia nueva,
- el mismo fingerprint ya fue reportado el maximo permitido,
- se alcanzo `maxRuntimeSeconds`,
- se alcanzo `maxTicks`,
- el usuario desactivo modo autonomo,
- el incidente llego a `waiting_human`,
- el incidente ya genero una recomendacion accionable,
- el backend no responde a snapshot dentro de timeout,
- el scanner visual completo su presupuesto,
- el cierre final queda bloqueado con evidencia persistida.

## Contrato de salida del incidente
Todo incidente debe devolver:

```json
{
  "incidentId": "OBS-YYYYMMDD-HHMMSS-001",
  "projectSlug": "sesion-...",
  "completed": true,
  "status": "completed|blocked|expired|waiting_human",
  "trigger": "agent_closed|observe_now|integrity_failed|...",
  "rootCause": "ui_polling_only|integrity_failed|typewriter_binary_file|...",
  "evidencePaths": [],
  "actionsProposed": [],
  "actionsExecuted": [],
  "stopReason": "max_ticks|waiting_human|no_new_evidence|...",
  "validation": {
    "snapshotLoaded": true,
    "timeouts": [],
    "findingsCount": 0
  }
}
```

## Separacion obligatoria entre Observer y scanner visual
Observer:
- decide donde mirar,
- resume evidencia,
- propone acciones,
- registra incidentes.

Scanner visual:
- muestra una reproduccion acotada,
- tiene boton detener,
- tiene watchdog,
- no decide estado del proyecto,
- no mantiene vivo el Observer.

Polling de UI:
- refresca estado,
- no debe iniciar incidentes,
- no debe extender deadlines,
- no debe reactivar modo autonomo.

## Reglas para modo autonomo humano
El pin humano debe tener expiracion:
- `humanPinned=true` debe guardar `expiresAt`.
- Por defecto expira en 15 minutos.
- La UI debe mostrar tiempo restante.
- Al expirar, Observer pasa a `idle` y emite `observer_manual_pin_expired`.
- Si el humano quiere mas tiempo, debe renovar explicitamente.

## Reparacion especifica del caso actual
El incidente actual debe cerrarse asi:
1. Reconocer que no hay tarea activa: `current_task_id=null`.
2. Clasificar actividad como `ui_polling_plus_stale_findings`.
3. Registrar que el render negro ya fue atendido por el agente.
4. Bloquear cierre limpio por:
   - integridad fallida,
   - typewriter fallido por PNG binario,
   - scanner previo desactualizado.
5. Detener mensajes repetidos de "barriendo lineas y rutas".
6. Crear tareas nuevas, separadas:
   - `OBSERVER-LIFECYCLE-001`: incidentes finitos y budgets.
   - `OBSERVER-LIFECYCLE-002`: expiracion de pin humano.
   - `OBSERVER-LIFECYCLE-003`: deduplicacion y supresion de firmas repetidas.
   - `OBSERVER-LIFECYCLE-004`: separar scanner visual de Observer.
   - `OBSERVER-LIFECYCLE-005`: corregir PNG/typewriter/binarios.

## Criterios de aceptacion
- Con proyecto `completed` y `current_task_id=null`, Observer no emite barrido infinito.
- Un mismo hallazgo no aparece mas de 3 veces como mensaje visual continuo.
- `/api/observer/status` responde en menos de 3 segundos o devuelve estado degradado.
- Desactivar modo autonomo detiene incidentes abiertos y cancela animacion visual asociada.
- El scanner visual termina por exito, error o watchdog, nunca queda activo horas.
- Los PNG no se tratan como texto en typewriter ni endpoint de archivo textual.
- `observer_findings.json` puede conservar hallazgos activos sin mantener animacion infinita.
- Cada incidente deja `stopReason` auditable.
- La UI distingue claramente:
  - "Observer idle",
  - "Incidente bloqueado esperando humano",
  - "Scanner visual detenido",
  - "Polling de UI activo".

---

# FASE 1 — Estabilización del runtime actual

## Objetivo
Quitar las fallas estructurales más peligrosas del runtime actual.

## Alcance
- eliminar smoke heurístico,
- introducir modos explícitos,
- separar lógica de sesión y tarea,
- endurecer cierre de procesos,
- preparar persistencia mínima.

## Criterios de aceptación
- un prompt grande no entra en smoke por palabras como “prueba”, “validación” o “mínima”;
- el runtime deja preparado el terreno para task runtime;
- existen estructuras persistentes base.

---

# FASE 2 — Orquestación por tareas

## Objetivo
Pasar de session runtime a task runtime.

## Alcance
- cola persistente,
- dependencias tipo DAG,
- contrato de salida por tarea,
- validación automática por paso,
- reanudación desde checkpoint.

## Criterios de aceptación
- el proyecto puede apagarse y retomarse;
- una tarea fallida no mata el proyecto completo;
- el sistema sigue desde el último estado persistido.

---

# FASE 3 — Autonomía larga

## Objetivo
Soportar proyectos cortos, medianos y largos con la misma base.

## Alcance
- planificación por etapas,
- budgets de tiempo por tarea,
- ciclos de corrección,
- batería de benchmarks,
- soporte para agentes reemplazables.

## Criterios de aceptación
- el runtime supera smoke, mediano, largo y recovery sin intervención manual continua.

---

# Arquitectura de módulos

## orchestrator/planner.py
Responsabilidad:
- dividir prompt grande en tareas,
- definir objetivo,
- definir archivos esperados,
- definir validaciones,
- definir dependencias,
- definir prioridad,
- definir timeout,
- definir modo.

## orchestrator/task_queue.py
Responsabilidad:
- cargar y guardar cola,
- ordenar por dependencias,
- ordenar por prioridad,
- seleccionar siguiente tarea ejecutable.

## orchestrator/executor.py
Responsabilidad:
- lanzar un worker por tarea,
- esperar resultado o timeout,
- devolver resultado estructurado.

## orchestrator/validator.py
Responsabilidad:
- validar evidencia real,
- ejecutar validation_commands,
- decidir si una tarea pasa o falla.

## orchestrator/recovery.py
Responsabilidad:
- registrar fallo,
- cerrar proceso,
- crear checkpoint,
- reintentar limpio,
- dividir tarea si es demasiado grande,
- bloquear tarea si supera reintentos.

## orchestrator/state_store.py
Responsabilidad:
- cargar/guardar estado,
- persistir queue,
- persistir historial,
- persistir failures,
- persistir checkpoints.

## orchestrator/contracts.py
Responsabilidad:
- validar Task,
- validar TaskResult,
- validar ProjectState.

## orchestrator/policy_loader.py
Responsabilidad:
- cargar y normalizar `AGENTS.md`,
- exponer reglas duras del repositorio al control plane.

## orchestrator/plan_loader.py
Responsabilidad:
- cargar y normalizar `PLANS.md`,
- exponer fases, sprints, alcance y criterios de aceptación consumibles por máquina.

## orchestrator/directive_context.py
Responsabilidad:
- reunir política, plan, estado, cola, historial, fallos y checkpoint actual,
- producir el contexto estructurado de la tarea activa.

## orchestrator/habla_adapter.py
Responsabilidad:
- incorporar HABLA BASIC como capa procedural reusable,
- transformar el contexto de tarea en guía operativa compatible con el generador de directivas.

## orchestrator/directive_generator.py
Responsabilidad:
- construir la instrucción exacta del worker para la tarea actual,
- persistir la directiva en disco,
- evitar prompts manuales permanentes como mecanismo final del runtime.

## orchestrator/benchmark.py
Responsabilidad:
- ejecutar benchmarks oficiales,
- bloquear despliegue si fallan.

## workers/codex_worker.py
Responsabilidad:
- ejecutar una tarea acotada,
- devolver resultado estructurado.

---

# Cambios obligatorios en agent_runtime.py

## 1. Smoke mode
- eliminar detección heurística por palabras;
- soportar solo modo explícito:
  - smoke
  - build
  - medium
  - long-run

## 2. Session vs task
- reemplazar session runtime por task runtime;
- una sesión contiene muchas tareas;
- cada tarea tiene worker propio;
- cada tarea tiene timeout propio.

## 3. Retry fuerte
- registrar causa del fallo,
- cerrar proceso anterior,
- reintentar limpio,
- dividir tarea si era demasiado grande,
- nunca esperar que una sesión larga “reviva sola”.

## 4. Timeout contextual
- FIRST_SIGNAL_TIMEOUT depende del modo;
- FIRST_VISUAL_TIMEOUT depende del modo;
- SESSION_IDLE_TIMEOUT depende del modo y del tipo de tarea.

## 5. Cierre garantizado
- terminate()
- wait
- kill() si sigue vivo

---

# Flujo principal esperado

```text
Prompt grande
→ planner
→ división en tareas pequeñas
→ task_queue persistente
→ executor ejecuta una tarea
→ validator valida evidencia real
→ state_store guarda checkpoint
→ recovery actúa si falla
→ siguiente tarea
```

---

# Sprints

## Sprint 1
Objetivo:
Crear la base persistente del runtime y los contratos mínimos.

Entregables:
- `schemas/`
- `orchestrator/state_store.py`
- `orchestrator/contracts.py`
- `runtime/project_state.json`
- `runtime/task_queue.json`

Aceptación:
- existe persistencia base;
- existen contratos mínimos;
- la cola y el estado pueden cargarse y guardarse.

## Sprint 2
Objetivo:
Planificación y cola.

Entregables:
- `orchestrator/planner.py`
- `orchestrator/task_queue.py`

Aceptación:
- soporta prioridad;
- soporta dependencias.

## Sprint 3
Objetivo:
Ejecución acotada por tarea.

Entregables:
- `workers/codex_worker.py`
- `orchestrator/executor.py`

Aceptación:
- una tarea equivale a un proceso.

## Sprint 4
Objetivo:
Validación real.

Entregables:
- `orchestrator/validator.py`

Aceptación:
- ejecuta validaciones y exige evidencia real.

## Sprint 5
Objetivo:
Recovery robusto.

Entregables:
- `orchestrator/recovery.py`

Aceptación:
- terminate → wait → kill;
- divide tareas tras fallos repetidos.

## Sprint 6
Objetivo:
Integrar política y plan como entradas permanentes del control plane.

Entregables:
- `orchestrator/policy_loader.py`
- `orchestrator/plan_loader.py`

Aceptación:
- `AGENTS.md` se carga como política del repositorio;
- `PLANS.md` se carga como roadmap ejecutable;
- el runtime puede consultar reglas y alcance sin intervención manual.

## Sprint 7
Objetivo:
Construir el contexto procedural de tarea con HABLA BASIC.

Entregables:
- `orchestrator/directive_context.py`
- `orchestrator/habla_adapter.py`

Aceptación:
- el sistema puede reunir política, plan, estado, cola, historial y checkpoint;
- HABLA BASIC queda integrado como capa procedural reusable.

## Sprint 8
Objetivo:
Generar directivas operativas por tarea.

Entregables:
- `orchestrator/directive_generator.py`
- `runtime/directives/`

Aceptación:
- cada tarea puede producir una directiva persistida en disco;
- el worker deja de depender de prompts manuales permanentes.

## Sprint 9
Objetivo:
Integrar el runtime existente con el nuevo control plane por tareas y directivas.

Entregables:
- modificación acotada de `agent_runtime.py`
- modos explícitos,
- fin de smoke heurístico,
- timeout por tarea,
- consumo de directivas generadas.

Aceptación:
- `agent_runtime.py` deja de operar como sesión monolítica;
- la tarea activa se ejecuta con una directiva generada por el control plane.

## Sprint 10
Objetivo:
Benchmarks y puerta de despliegue.

Entregables:
- `orchestrator/benchmark.py`

Aceptación:
- no se despliega si falla la batería oficial.

---

# Benchmarks oficiales
- smoke-01
- crud-ui-02
- refactor-mid-03
- long-project-04
- recovery-05

## Regla de despliegue
Si no pasan todos, no se despliega.

---

# Cierre de deuda tecnica seccion 19

## Estado 2026-05-20
Fase 1 y Fase 2 cerradas con codigo, tests y checkpoint.
Fase 3 ejecutada como mitigacion estructural verificable para 19.3 y 19.5.
Fase 4 ejecutada: 19.5 queda cerrada; 19.3 queda avanzada pero no cerrada totalmente.
Fase 5 ejecutada: 19.3 queda cerrada por descomposicion backend verificable.
GitHub Actions de auditoria creada para automatizar validaciones backend, frontend y checkpoints.

Deudas cerradas:
- 19.1 Drift entre contratos Python y schemas JSON.
- 19.2 Ambiguedad entre runtime raiz y runtime por proyecto.
- 19.3 Backend monolitico.
- 19.4 Doble ruta de worker.
- 19.5 Frontend con componentes grandes.
- 19.6 Frontera de seguridad de validaciones.

Deudas todavia abiertas:
- Ninguna de las seis deudas de la seccion 19 queda abierta despues de Fase 5.
- Riesgo residual: `backend/app.py` sigue siendo composition root de Flask/SocketIO para arquitectura, reverse engineering, email commands, sesiones de agente y sockets. La deuda 19.3 se considera cerrada porque los dominios pesados nombrados en auditoria fueron extraidos a servicios/rutas dedicadas.

Evidencia:
- `schemas/project_state.schema.json` acepta `human_alignment_pending`.
- `schemas/project_state.schema.json` declara `pending_human_alignment_tasks`.
- `backend/test_project_state_schema_contract.py` compara schema y contrato Python.
- `orchestrator/state_store.py` exige `runtime_dir` explicito y provee constructores intencionales `for_project_runtime` / `for_repo_runtime`.
- `orchestrator/task_queue.py` y `orchestrator/recovery.py` exigen `StateStore` explicito.
- `orchestrator/directive_context.py` y `orchestrator/directive_generator.py` exigen runtime explicito para contexto/directivas.
- `orchestrator/worker_adapter.py` define `TaskWorkerAdapter` y `CodexSubprocessWorkerAdapter`.
- `backend/agent_worker_adapters.py` define `SessionWorkerAdapter`, `ControlPlaneSessionWorkerAdapter` y `LegacyPtySessionWorkerAdapter`.
- `backend/agent_runtime.py` selecciona ruta de sesion por adaptador formal.
- `orchestrator/validator.py` evalua cada `validation_command` con `orchestrator.security_policy.decide_command` antes de ejecutar.
- `orchestrator/validator.py` ejecuta comandos permitidos con `shell=False`.
- `orchestrator/validator.py` persiste decisiones en `runtime/validation_security_events.jsonl`.
- `backend/test_validator_security.py` prueba comandos permitidos, bloqueo de shell, denegacion de desconocidos y comandos invalidos.
- `backend/test_runtime_boundary.py` prueba runtime explicito, adaptadores de worker y persistencia de directivas bajo runtime activo.
- `backend/code_scanner_service.py` contiene la construccion/persistencia del scanner final fuera de `backend/app.py`.
- `backend/test_code_scanner_service.py` prueba el scanner final como servicio unitario.
- `backend/agent_repair_service.py` contiene seleccion de archivos, directiva de reparacion y encolado de tarea de reparacion fuera de `backend/app.py`.
- `backend/test_agent_repair_service.py` prueba la logica de reparacion como servicio unitario.
- `frontend/src/appUtils.js` contiene helpers, constantes y layout/graph utils extraidos de `App.jsx`.
- `frontend/src/components/codeWorkbenchUtils.js` contiene helpers de scanner visual, integridad y reparacion extraidos de `CodeWorkbench.jsx`.
- `frontend/src/components/agentStudioUtils.js` contiene helpers de runtime/agentes/HAR extraidos de `AgentStudio.jsx`.
- `frontend/src/components/LiveReviewerPanel.jsx` contiene el panel de revisor en vivo extraido de `AgentStudio.jsx`.
- `backend/sandbox_service.py` contiene el sandbox runtime real fuera de `backend/app.py`.
- `backend/integrity_service.py` contiene manifiesto forense, sellos, ancla externa, diff por caracter, reporte de integridad y Frozen Sniper fuera de `backend/app.py`.
- `backend/integrity_routes.py` contiene rutas de scanner, integrity report, observer findings, baseline y Frozen Sniper fuera de `backend/app.py`.
- `backend/observer_runtime_service.py` contiene seleccion de proyecto activo y snapshot runtime del Observer fuera de `backend/app.py`.
- `backend/human_alignment_routes.py` registra rutas HAR fuera de `backend/app.py`.
- `backend/editor_routes.py` registra rutas de archivos del editor y reparacion desde Workbench fuera de `backend/app.py`.
- `backend/runtime_admin_service.py` contiene limpieza de runtime/workspace fuera de `backend/app.py`.
- `backend/runtime_admin_routes.py` registra reset runtime y clean-workspace/blanqueo fuera de `backend/app.py`.
- `backend/sandbox_routes.py` registra rutas sandbox fuera de `backend/app.py`.
- `backend/app.py` bajo a 4566 lineas despues de Fase 5.
- `.github/workflows/audit.yml` automatiza py_compile, unittests backend, build/test frontend y validacion JSON de checkpoints.
- `docs/reporte_cierre_auditoria_seccion_19_2026-05-20.md` consolida el reporte humano de cierre para auditoria/inversor.
- `frontend/src/App.jsx` bajo a 1992 lineas.
- `frontend/src/components/CodeWorkbench.jsx` bajo a 1994 lineas.
- `frontend/src/components/AgentStudio.jsx` queda en 1754 lineas.
- Componentes frontend extraidos en Fase 4: `AppTopbar`, `AppLintPanel`, `AppObserverPanel`, `AppRuntimeWorkbenches`, `AppAgentPresenceLayer`, `AppStatusbar`, `CodeWorkbenchTopMenu`, `CodeWorkbenchActivityBar`, `CodeWorkbenchActions`, `CodeWorkbenchSidebar`, `CodeWorkbenchEditorHeader`, `CodeWorkbenchEditorOverlays`, `CodeWorkbenchGutter`, `CodeWorkbenchTextarea`.
- Checkpoint: `runtime/checkpoints/phase-1-section-19-20260519T131739-0700.json`.
- Checkpoint: `runtime/checkpoints/phase-2-section-19-20260519T142613-0700.json`.
- Checkpoint: `runtime/checkpoints/phase-3-section-19-20260519T180025-0700.json`.
- Checkpoint: `runtime/checkpoints/phase-4-section-19-20260520T070929-0700.json`.
- Checkpoint: `runtime/checkpoints/phase-5-section-19-20260520T094539-0700.json`.
- Checkpoint: `runtime/checkpoints/github-actions-audit-20260520T131626-0700.json`.
- Checkpoint: `runtime/checkpoints/audit-report-section-19-20260520T140040-0700.json`.

Validaciones ejecutadas:
- `python3 -m py_compile orchestrator/validator.py orchestrator/security_policy.py backend/test_project_state_schema_contract.py backend/test_validator_security.py`
- `python3 -m unittest backend.test_project_state_schema_contract backend.test_validator_security`
- `python3 -m unittest backend.test_security_policy backend.test_human_alignment_review backend.test_project_state_runtime_metadata`
- `python3 -m unittest backend.test_tool_invocation_policy backend.test_control_plane_visual_bridge`
- `jq . schemas/project_state.schema.json`
- `env PYTHONPATH=backend:. python3 -m unittest backend.test_agent_runtime_habla backend.test_executor_pipe_drain`
- `python3 -m py_compile orchestrator/state_store.py orchestrator/task_queue.py orchestrator/recovery.py orchestrator/directive_context.py orchestrator/directive_generator.py orchestrator/worker_adapter.py orchestrator/executor.py backend/agent_worker_adapters.py backend/agent_runtime.py backend/test_runtime_boundary.py`
- `python3 -m unittest backend.test_runtime_boundary`
- `python3 -m unittest backend.test_control_plane_visual_bridge backend.test_tool_invocation_policy backend.test_executor_pipe_drain backend.test_runtime_boundary`
- `env PYTHONPATH=backend:. python3 -m unittest backend.test_agent_runtime_habla backend.test_human_alignment_review backend.test_project_state_runtime_metadata`
- `python3 -m unittest backend.test_security_policy backend.test_project_state_schema_contract backend.test_validator_security`
- `jq . runtime/checkpoints/phase-2-section-19-20260519T142613-0700.json`
- `python3 -m py_compile backend/app.py backend/code_scanner_service.py backend/agent_repair_service.py backend/test_code_scanner_service.py backend/test_agent_repair_service.py`
- `python3 -m unittest backend.test_code_scanner_service backend.test_agent_repair_service backend.test_code_scanner backend.test_app_lint`
- `python3 -m py_compile backend/app.py backend/sandbox_service.py backend/code_scanner_service.py backend/agent_repair_service.py`
- `python3 -m unittest backend.test_runtime_sandbox backend.test_code_scanner_service backend.test_agent_repair_service backend.test_code_scanner backend.test_app_lint`
- `python3 -m py_compile backend/app.py backend/editor_routes.py backend/integrity_routes.py backend/human_alignment_routes.py backend/observer_runtime_service.py backend/integrity_service.py backend/runtime_admin_routes.py backend/runtime_admin_service.py backend/sandbox_routes.py backend/sandbox_service.py backend/code_scanner_service.py backend/agent_repair_service.py`
- `python3 -m unittest backend.test_code_scanner`
- `python3 -m unittest backend.test_runtime_clean_workspace backend.test_code_scanner backend.test_runtime_sandbox backend.test_observer_auto_shutdown backend.test_human_alignment_review`
- `python3 -m unittest backend.test_app_lint backend.test_code_scanner backend.test_code_scanner_service backend.test_agent_repair_service backend.test_runtime_sandbox backend.test_runtime_clean_workspace backend.test_observer_auto_shutdown backend.test_human_alignment_review backend.test_security_policy backend.test_validator_security backend.test_project_state_schema_contract`
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/audit.yml', encoding='utf-8')); print('workflow yaml ok')"`
- Validacion local del script de checkpoints embebido en `.github/workflows/audit.yml`.
- `npm run build`
- `npm test`

Siguiente fase:
- Subir el repositorio a GitHub y verificar la primera ejecucion real del workflow `Audit`.
