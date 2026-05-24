# HABLA Observer Engine - Algoritmo funcional v1

## Proposito

Observer Engine no es un worker, no es un chat y no es un scanner infinito.
Observer Engine es un motor de procesamiento de evidencia que abre incidentes
finitos, mira el estado real, clasifica lo que ocurre, propone una accion y
cierra con una razon auditable.

La forma canonica del ciclo es:

```text
trigger -> incidente -> snapshot -> clasificacion -> inspeccion -> decision -> evidencia -> cierre
```

## Regla principal

Observer nunca debe quedarse trabajando sin una pregunta activa.

Si no hay incidente abierto, debe estar en `idle`.
Si hay incidente abierto, debe tener presupuesto, deadline y condicion de cierre.
Si encontro un problema, debe dejar evidencia y parar en `waiting_human`,
`blocked`, `completed` o `expired`.

## Separacion de responsabilidades

### Observer Engine

- Abre incidentes.
- Lee evidencia persistida.
- Cruza runtime, scanner, sandbox, typewriter, integridad, logs y UI.
- Clasifica causa raiz.
- Emite una observacion explicable.
- Propone acciones seguras.
- Cierra el incidente con `stopReason`.

### Scanner visual

- Solo muestra animacion acotada en la UI.
- No decide estado del proyecto.
- No mantiene vivo al Observer.
- Siempre termina por exito, error, cancelacion o watchdog.

### UI polling

- Solo refresca pantallas.
- No abre incidentes por si mismo.
- No renueva deadlines.
- No reactiva modo autonomo.

### Worker

- Ejecuta una tarea acotada.
- Devuelve resultado estructurado.
- No controla el ciclo de vida del Observer.

## Entradas del motor

Observer acepta solo estas entradas:

- `agent_started`
- `agent_closed`
- `observe_now`
- `final_sequence_started`
- `final_sequence_closed`
- `integrity_scan_requested`
- `scanner_requested`
- `sandbox_check_requested`
- `runtime_contradiction_detected`
- `human_pinned_observer`

Estas senales no abren incidentes:

- `GET /api/observer/status`
- `GET /api/projects/*/files`
- `GET /api/agent/projects`
- `socket.io` heartbeat
- reviewer polling
- navegador abierto
- refresco automatico de UI

## Datos que debe leer por snapshot

Cada tick de Observer debe construir un snapshot con timeout:

```text
runtime/project_state.json
runtime/task_queue.json
runtime/task_history.jsonl
runtime/failures.jsonl
runtime/artifacts/final_code_scanner_report.json
runtime/artifacts/final_typewriter_report.json
runtime/artifacts/file_integrity_report.json
runtime/artifacts/observer_findings.json
runtime/sandbox.json
.runtime/observer/manual_pin.json
.runtime/observer/memory.json
.runtime/observer/timeline.jsonl
backend log tail
active agent sessions
active browser/UI state, solo como contexto
```

Regla: si una fuente no responde en `endpointTimeoutSeconds`, se registra
timeout y el ciclo sigue en modo degradado. No puede bloquear todo el Observer.

## Modelo de incidente

Cada observacion real debe vivir en un incidente:

```json
{
  "incidentId": "OBS-YYYYMMDD-HHMMSS-001",
  "projectSlug": "sesion-...",
  "trigger": "agent_closed",
  "status": "open",
  "phase": "snapshotting",
  "createdAt": "2026-05-19T00:00:00Z",
  "updatedAt": "2026-05-19T00:00:00Z",
  "deadlineAt": "2026-05-19T00:03:00Z",
  "budgets": {
    "maxRuntimeSeconds": 180,
    "maxTicks": 30,
    "maxRepeatedEvents": 3,
    "endpointTimeoutSeconds": 3,
    "maxFindingsPerTick": 20,
    "maxVisualFiles": 3,
    "maxVisualLinesPerFile": 200
  },
  "counters": {
    "ticks": 0,
    "repeatedEvents": 0,
    "timeouts": 0
  },
  "fingerprintsSeen": {},
  "rootCause": "",
  "evidencePaths": [],
  "proposedActions": [],
  "stopReason": ""
}
```

Ubicacion persistente:

```text
.runtime/observer/incidents/<incidentId>.json
.runtime/observer/timeline.jsonl
runtime/artifacts/observer_findings.json
runtime/checkpoints/
```

## Estados finitos

```text
idle
gate_trigger
incident_opened
snapshotting
normalizing
classifying
prioritizing
inspecting
deciding
emitting
waiting_human
cooling_down
completed
blocked
expired
cancelled
```

Estados terminales:

```text
completed
blocked
expired
cancelled
waiting_human
```

Un incidente en estado terminal no puede seguir emitiendo "barriendo lineas".

## Presupuestos obligatorios

Valores por defecto:

```json
{
  "maxRuntimeSeconds": 180,
  "maxTicks": 30,
  "maxRepeatedEvents": 3,
  "endpointTimeoutSeconds": 3,
  "cooldownSeconds": 60,
  "maxFindingsPerTick": 20,
  "maxVisualFiles": 3,
  "maxVisualLinesPerFile": 200,
  "statusEndpointMaxSeconds": 3
}
```

Reglas:

- Ningun incidente puede vivir sin `deadlineAt`.
- Ningun tick puede leer endpoints sin timeout.
- Ningun hallazgo repetido puede emitirse indefinidamente.
- Ninguna animacion visual puede representar todo el proyecto durante horas.
- El reporte persistente puede ser completo, pero la UI visual debe ser acotada.

## Fingerprint de observacion

Cada evento se deduplica con una firma estable:

```text
sha256(
  projectSlug
  + state
  + behavior
  + source
  + findingType
  + focusPath
  + evidenceHash
)
```

Si la misma firma aparece mas de `maxRepeatedEvents`, Observer:

1. registra `observer_repeated_finding_suppressed`,
2. actualiza `occurrenceCount`,
3. deja de mover la UI al mismo punto,
4. pasa el incidente a `waiting_human` o `completed_with_findings`.

## Clasificador de causa raiz

El clasificador debe producir una sola causa principal por tick.

Prioridad:

1. `active_worker_running`
2. `project_completed_without_scanner`
3. `project_completed_without_sandbox`
4. `typewriter_failed_binary_file`
5. `integrity_failed_external_change`
6. `integrity_failed_registered_internal_change`
7. `sandbox_unhealthy`
8. `lint_blocker`
9. `ui_polling_only`
10. `no_new_evidence`

Regla: si no hay worker activo y solo hay polling, la causa es
`ui_polling_only` y el incidente debe cerrar.

## Rutina completa

### 1. Gate de trigger

```text
recibir evento
si evento no esta en triggers permitidos -> ignorar
si evento es polling UI -> no abrir incidente
si ya existe incidente abierto con mismo fingerprint -> reusar o suprimir
si no existe -> abrir incidente
```

### 2. Apertura de incidente

```text
crear incidentId
calcular deadlineAt
persistir archivo de incidente
emitir evento observer_incident_opened
```

### 3. Snapshot

```text
leer project_state con timeout
leer queue/history/failures con timeout
leer scanner/typewriter/sandbox/integrity con timeout
leer estado de sesiones activas
leer manual_pin
leer log tail acotado
registrar fuentes faltantes como degraded, no como bloqueo global
```

### 4. Normalizacion

```text
normalizar status
normalizar projectSlug
normalizar activeSessionCount
normalizar validation.passed
normalizar findings por fingerprint
normalizar paths relativos
```

### 5. Clasificacion

```text
si activeSessionCount > 0 -> active_worker_running
si project_state.status == completed y scanner invalido -> project_completed_without_scanner
si scanner valido y sandbox no listo -> project_completed_without_sandbox
si typewriter falla por archivo binario -> typewriter_failed_binary_file
si integrity tiene hallazgos externos -> integrity_failed_external_change
si solo hay polling de UI -> ui_polling_only
si no cambio evidencia -> no_new_evidence
```

### 6. Priorizacion

```text
crear cola de hallazgos
ordenar por severidad y politica:
  integridad externa
  scanner final
  sandbox real
  typewriter final
  lint
  mapa/flujo
tomar maxFindingsPerTick
```

### 7. Inspeccion acotada

```text
leer solo archivos necesarios
para UI visual tomar maxVisualFiles y maxVisualLinesPerFile
para reporte persistente referenciar artefactos completos
no repetir foco si el fingerprint ya fue suprimido
```

### 8. Decision

Observer decide una de estas salidas:

```text
close_clean
close_with_findings
wait_human
propose_repair_task
propose_integrity_acceptance
propose_sandbox_restart
propose_typewriter_binary_fix
expire_incident
cancel_incident
```

Observer no ejecuta reparaciones destructivas.
Observer no hace blanqueo.
Observer no acepta nueva baseline sin decision humana.

### 9. Emision visual

La UI debe recibir un evento claro:

```json
{
  "op": "observer_action",
  "incidentId": "OBS-...",
  "state": "waiting_human",
  "message": "Observer encontro integridad fallida y detuvo el barrido.",
  "reason": "No hay tarea activa; el hallazgo ya fue reportado y requiere decision humana.",
  "uiAction": {
    "type": "show-observer-summary",
    "targetId": "observer-panel"
  },
  "stopReason": "waiting_human_after_repeated_finding"
}
```

Regla visual: despues de `waiting_human`, `blocked`, `completed` o `expired`,
no se muestra "escaneando lineas" para ese incidente.

### 10. Cierre

```text
si decision terminal -> cerrar incidente
persistir stopReason
persistir resumen
emitir observer_incident_closed
cancelar scanner visual asociado
entrar a cooling_down por fingerprint
volver a idle
```

## Pseudocodigo canonico

```python
def handle_observer_event(event):
    if not is_allowed_trigger(event):
        return ignored("not_observer_trigger")

    fingerprint = trigger_fingerprint(event)
    if is_in_cooldown(fingerprint):
        return suppressed("cooldown_active")

    incident = load_or_create_incident(event, fingerprint)

    while not incident.is_terminal:
        if budget_expired(incident):
            close_incident(incident, status="expired", stop_reason="budget_expired")
            break

        snapshot = build_snapshot(timeout_seconds=incident.budgets.endpointTimeoutSeconds)
        classification = classify_snapshot(snapshot)

        if classification.root_cause == "ui_polling_only":
            close_incident(incident, status="completed", stop_reason="ui_polling_only")
            break

        findings = prioritize_findings(snapshot, classification)
        observation = inspect_findings(findings, incident.budgets)
        signature = observation_signature(observation)

        if incident.repeated(signature) >= incident.budgets.maxRepeatedEvents:
            persist_suppression(incident, signature)
            close_incident(
                incident,
                status="waiting_human",
                stop_reason="repeated_finding_suppressed",
            )
            break

        decision = decide_next_action(snapshot, classification, observation)
        emit_observer_event(incident, classification, observation, decision)

        if decision.is_terminal:
            close_incident(incident, status=decision.status, stop_reason=decision.reason)
            break

        incident.counters.ticks += 1
        persist_incident(incident)
        sleep_until_next_tick(incident)

    cancel_visual_scanner_if_owned_by(incident)
    enter_cooldown(fingerprint)
    return incident.result()
```

## Aplicacion al caso actual: pantalla negra

Trigger original:

```text
usuario: verificar por que el juego renderiza pantalla negra
```

Flujo correcto:

1. Abrir incidente `black_screen_render_check`.
2. Tomar snapshot de sandbox, screenshots, logs y agent session.
3. Confirmar si el worker reparo `frontend/index.html` y `frontend/app.js`.
4. Validar screenshot o health del sandbox.
5. Si el render queda visible, cerrar incidente de pantalla negra como
   `completed`.
6. Si aparecen hallazgos nuevos de integridad/typewriter, abrir incidentes
   separados:
   - `integrity_after_render_fix`
   - `typewriter_binary_png_failure`
   - `scanner_report_outdated`
7. No mantener el incidente original barriendo lineas durante horas.
8. Mostrar al humano:

```text
Render negro: atendido.
Cierre limpio: bloqueado por integridad/typewriter.
Observer: detenido, esperando decision humana.
```

## Contrato de salida

Cada incidente debe devolver:

```json
{
  "incidentId": "OBS-YYYYMMDD-HHMMSS-001",
  "projectSlug": "sesion-...",
  "trigger": "agent_closed",
  "completed": true,
  "status": "waiting_human",
  "rootCause": "typewriter_failed_binary_file",
  "evidencePaths": [
    "runtime/artifacts/final_typewriter_report.json",
    "runtime/artifacts/file_integrity_report.json"
  ],
  "actionsProposed": [
    "OBSERVER-LIFECYCLE-005"
  ],
  "actionsExecuted": [],
  "stopReason": "decision_required_after_evidence",
  "validation": {
    "snapshotLoaded": true,
    "timeouts": [],
    "findingsCount": 238
  }
}
```

## Respuestas visuales obligatorias

La UI debe distinguir cuatro situaciones:

```text
Observer idle
Observer investigando incidente OBS-...
Observer bloqueado esperando humano
UI refrescando estado
```

Nunca debe mostrar "Sistema escaneando" si solo hay polling.
Nunca debe mostrar "barriendo lineas" despues del cierre terminal del incidente.

## Pruebas obligatorias

1. `test_observer_ignores_ui_polling`
   - Dado Chrome abierto y sin tarea activa, no se abre incidente.

2. `test_observer_closes_when_no_active_task`
   - Dado `current_task_id=null`, Observer cierra con `ui_polling_only` si no hay evidencia nueva.

3. `test_observer_suppresses_repeated_fingerprint`
   - El mismo hallazgo no se emite mas de 3 veces.

4. `test_observer_status_timeout_degraded`
   - Si status/snapshot tarda mas de 3 segundos, devuelve estado degradado.

5. `test_manual_pin_expires`
   - El pin humano expira y no mantiene Observer infinito.

6. `test_visual_scanner_budget`
   - La animacion visual respeta maximo de archivos/lineas y watchdog.

7. `test_typewriter_ignores_binary_png`
   - PNG no se procesa como texto y no bloquea por UTF-8.

8. `test_completed_project_with_findings_waits_human`
   - Proyecto completed con hallazgos activos pasa a `waiting_human`, no a barrido infinito.

## Tareas de implementacion

```text
OBSERVER-LIFECYCLE-001  Incident store + finite state loop + stopReason
OBSERVER-LIFECYCLE-002  Expiring manual pin
OBSERVER-LIFECYCLE-003  Fingerprint dedupe + repeated finding suppression
OBSERVER-LIFECYCLE-004  Split visual scanner from Observer lifecycle
OBSERVER-LIFECYCLE-005  Binary-safe typewriter and image file handling
OBSERVER-LIFECYCLE-006  Observer status degraded response with timeout
OBSERVER-LIFECYCLE-007  UI labels for idle/investigating/waiting/polling
```

## Criterio final

Observer demuestra inteligencia cuando sabe cuando parar.

El resultado esperado no es mirar mas tiempo.
El resultado esperado es mirar mejor, explicar la evidencia, proponer el
siguiente paso correcto y cerrar el ciclo.
