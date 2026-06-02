# Plan HABLA Visual IA Autonoma 2026-06-02

## Proposito
Convertir HABLA en una interfaz visual de IA autonoma que no parezca un editor de codigo tradicional, sino un sistema operativo de ejecucion de proyectos con evidencia viva.

La diferencia con herramientas tipo Cursor debe ser visible desde el primer minuto:

- Cursor muestra archivos y chat.
- HABLA debe mostrar runtime, workers, seguridad, validacion, LACE, scanner, sandbox y cierre canonico como un organismo operativo.

## Regla suprema visual
Ningun efecto visual puede simular progreso.

Cada animacion, pulso, color, transicion, compuerta o alerta debe venir de evidencia real:

- evento `agent:visual`,
- `project_state.json`,
- `task_queue.json`,
- `task_history.jsonl`,
- `failures.jsonl`,
- `runtime/checkpoints/`,
- `runtime/artifacts/final_code_scanner_report.json`,
- `runtime/artifacts/file_integrity_report.json`,
- `runtime/artifacts/observer_findings.json`,
- `runtime/sandbox.json`,
- `LACE_LOG.md`,
- `docs/lace_cycles/ciclo-*.md`,
- eventos CyberLACE.

Si no hay evidencia, la UI debe decir `sin evidencia` o `pendiente`, no animar exito.

## Precondicion runtime detectada
Antes de cerrar este paquete como completo, hay que corregir o visualizar de forma clara el fallo LACE actual:

```text
Control plane fallo durante la ejecucion de la tarea:
Task LACE-20260602-004 has unknown dependencies: ['LACE-20260602-003']
```

Este fallo no debe esconderse. La nueva UI debe mostrarlo como fallo de grafo de tareas LACE:

- nodo `LACE-20260602-004` en rojo,
- dependencia faltante `LACE-20260602-003` como nodo fantasma,
- recomendacion: `reparar cadena de dependencias LACE antes de cierre`,
- cierre canonico bloqueado.

## Paquete visual de 7 modulos



### 0. Mouse Operativo Real

#### Objetivo
Convertir el mouse simulado en un actor operativo real de la interfaz. El cursor visual no debe moverse por decoracion: debe representar una accion real decidida por el runtime, con objetivo, boton destino, resultado y evidencia.

El mouse debe dejar de ser `movimiento bonito` y convertirse en `mano visible del runtime`.

#### Principio central
No hay accion real, no hay movimiento de mouse.

Cada movimiento debe tener:

- `intentId`,
- `source`: runtime, worker, CyberLACE, LACE, scanner, usuario o Observer,
- `targetTool`,
- `targetSelector`,
- `action`: click, open_modal, close_modal, toggle, submit, search, scan, sweep, typewrite,
- `reason`,
- `evidenceBefore`,
- `evidenceAfter`,
- `result`.

#### Diferencia esperada
Antes:

```text
mouse se mueve sin objetivo -> parece demo decorativa
```

Despues:

```text
runtime necesita scanner -> mouse viaja al boton Scanner -> click real -> modal abre -> endpoint real corre -> artifact aparece -> mouse marca evidencia
```

#### Arquitectura propuesta
Crear un plano separado de accion visual:

```text
Runtime Event
  -> Mouse Action Planner
  -> Mouse Action Queue
  -> UI Action Executor
  -> Modal / Tool Button
  -> Endpoint real / Tool real
  -> Evidence Result
  -> Visual confirmation
```

Este plano debe trabajar en hilo/logica independiente para no bloquear el worker principal.

#### Backend / runtime sugerido
Endpoint o socket de cola:

```text
GET /api/ui-actions/queue
POST /api/ui-actions/enqueue
POST /api/ui-actions/<action_id>/ack
POST /api/ui-actions/<action_id>/result
```

Evento socket sugerido:

```text
ui:mouse-action
```

Payload:

```json
{
  "actionId": "UI-ACTION-20260602-001",
  "projectId": "sesion-...",
  "source": "control_plane",
  "reason": "Scanner requerido antes de cierre canonico.",
  "targetTool": "scanner",
  "targetSelector": "[data-tool='scanner-final']",
  "action": "click",
  "requiresHuman": false,
  "safetyLevel": "safe",
  "expectedEvidence": "runtime/artifacts/final_code_scanner_report.json"
}
```

#### Frontend sugerido
Componentes:

- `OperationalMouseLayer.jsx`
- `MouseActionQueuePanel.jsx`
- `ToolCommandDock.jsx`
- `ToolModalShell.jsx`
- `mouseActionExecutor.js`

El cursor operativo debe:

- moverse hacia botones reales,
- hacer click real con `HTMLElement.click()` o dispatch controlado,
- abrir modales reales,
- esperar resultado,
- mostrar exito o bloqueo,
- registrar evidencia visual.

#### Botones y modales minimos
Crear minimo cinco herramientas con boton visible y modal real:

1. **Scanner Final**
   - Boton: `Scanner`
   - Modal: progreso del scanner cinematico.
   - Accion real: `POST /api/projects/<project>/code-scanner`.
   - Evidencia: `runtime/artifacts/final_code_scanner_report.json`.

2. **Escoba Runtime**
   - Boton: `Escoba`
   - Modal: residuos encontrados, acciones permitidas, reporte.
   - Accion real: `python3 orchestrator/agent_tools.py to-sweep-with-a-broom ...` o endpoint equivalente.
   - Evidencia: `runtime/artifacts/broom/*.json`.
   - Regla: no borrar historial, checkpoints, directives, logs ni producto.

3. **Web Research Blackboard**
   - Boton: `Research`
   - Modal: pizarra de investigacion con navegador/iframe sandbox o resultados curados.
   - Accion real: abrir busqueda externa segura o herramienta de investigacion autorizada.
   - Evidencia: consultas, fuentes, timestamps, resumen.
   - Regla: no enviar secretos locales a internet; no investigar prompts bloqueados por CyberLACE; usar P_safe o pregunta redactada.

4. **Typewriter Writer**
   - Boton: `Typewriter`
   - Modal: escritura final/linea por linea.
   - Accion real: secuencia writer final o typewriter report.
   - Evidencia: `runtime/artifacts/final_typewriter_report.json`.

5. **Integrity / Findings / Sniper**
   - Boton: `Integrity`
   - Modal: findings activos, baseline, sniper dry-run.
   - Accion real: `integrity`, `findings`, `sniper --dry-run`.
   - Evidencia: `file_integrity_report.json`, `observer_findings.json`, `frozen_sniper_report.json`.
   - Regla: `sniper --confirm` requiere confirmacion humana/politica explicita.

Opcionales futuros:

- Sandbox Preview,
- CyberLACE Rescue,
- LACE Closure Gate,
- Dependency Repair.

#### Web Research Blackboard
La pizarra de investigacion debe ser visual y real, pero segura.

Debe permitir:

- abrir una busqueda,
- mostrar paginas o resultados dentro de modal sandbox,
- extraer notas,
- guardar fuentes,
- conectar hallazgos al plan o tarea,
- generar evidencia persistida.

Debe bloquear:

- envio de secretos,
- cookies/sesiones locales,
- prompts en cuarentena,
- navegacion que intente ejecutar acciones destructivas.

Artifact sugerido:

```text
runtime/artifacts/web_research/<task_id>-research.json
```

#### Reglas de seguridad del mouse
El mouse puede hacer clicks autonomos solo si:

- la accion es no destructiva,
- el target esta registrado en `ToolCommandDock`,
- hay razon persistida,
- existe proyecto activo,
- CyberLACE no marco riesgo alto,
- la accion no requiere confirmacion humana.

El mouse no puede confirmar:

- borrar workspace,
- sniper destructivo,
- blanqueo,
- envio de secretos,
- aceptar baseline irreversible,
- bypass de CyberLACE.

En esos casos puede mover el foco y abrir el modal, pero debe detenerse en `requiere humano`.

#### Contrato visual
Cada accion del mouse debe verse asi:

```text
1. Intencion: "Necesito scanner antes de cierre"
2. Cursor viaja al boton Scanner
3. Click real
4. Modal Scanner abre
5. Endpoint real inicia
6. Resultado aparece
7. Artifact queda citado
8. Linea de Verdad Forense actualiza gate
```

#### Validacion
- Test: accion `scanner` abre modal real y llama endpoint real/mocked.
- Test: accion destructiva queda en `requiresHuman=true` y no ejecuta click final.
- Test: sin evidencia no se marca exito.
- Test: web research no recibe texto sensible sin redaccion.
- Test: cada accion queda en historial `runtime/ui_action_history.jsonl`.

---

### 1. Nucleo IA 3D Vivo

#### Objetivo
Mostrar un nucleo 3D que represente la inteligencia operativa de HABLA en tiempo real.

#### Experiencia visual
Un grafo 3D full-bleed o panel principal con nodos vivos:

- Control Plane,
- Worker Codex,
- HostWriteExecutor,
- Validator,
- CyberLACE,
- LACE,
- Scanner,
- Integrity,
- Sandbox,
- Observer,
- Task Queue,
- Checkpoints.

Las conexiones pulsan solo cuando hay evento real. Ejemplos:

- `worker_started` activa pulso Control Plane -> Worker.
- `validation_passed` activa Worker -> Validator.
- `cyberlace_blocked` activa Prompt -> CyberLACE en rojo.
- `scanner_complete` activa Scanner -> Closure Gate.
- `lace_cycles_missing` activa LACE -> Task Queue.

#### Estados visuales
- Verde: validado con evidencia.
- Azul: ejecutando.
- Amarillo: esperando evidencia.
- Rojo: bloqueado.
- Gris: no aplicable.
- Morado sobrio: automejora LACE activa.

#### Datos necesarios
Endpoint o socket derivado de:

- `/api/agent/sessions`,
- `/api/projects/<project>/runtime-truth`,
- `agent:visual`,
- `agent:session`,
- artifacts runtime.

#### Componentes frontend sugeridos
- `frontend/src/components/RuntimeBrain3D.jsx`
- `frontend/src/components/runtimeBrainUtils.js`
- estilos en `frontend/src/App.css` o modulo dedicado.

#### Validacion
- Si no hay eventos reales, los nodos quedan idle.
- Si hay session running, debe verse worker vivo con PID.
- Si hay blocked task, debe verse bloqueo en rojo.
- Test unitario de normalizacion de eventos.
- Screenshot Playwright o smoke visual para evitar canvas negro.

---

### 2. Linea de Verdad Forense

#### Objetivo
Mostrar al usuario por que una tarea puede o no puede cerrar.

#### Experiencia visual
Una linea horizontal o vertical de compuertas:

1. Prompt recibido.
2. CyberLACE aprobado o P_safe generado.
3. Worker lanzado.
4. Archivos esperados existen.
5. Validator OK.
6. Integrity OK.
7. Findings limpios.
8. Scanner OK.
9. Sandbox running.
10. LACE closure OK.
11. Canonical outcome completed.

Cada compuerta muestra:

- estado,
- evidencia,
- timestamp,
- archivo o artifact asociado,
- razon natural si falla.

#### Regla importante
`completed` no puede aparecer antes que LACE closure si LACE esta activo.

#### Datos necesarios
- `project_state.json`,
- `task_history.jsonl`,
- `file_integrity_report.json`,
- `observer_findings.json`,
- `final_code_scanner_report.json`,
- `sandbox.json`,
- LACE gate status.

#### Componentes frontend sugeridos
- `frontend/src/components/ForensicTruthRail.jsx`
- `frontend/src/components/forensicTruthUtils.js`

#### Backend sugerido
Crear endpoint compacto:

```text
GET /api/projects/<project_id>/closure-truth
```

Payload esperado:

```json
{
  "projectId": "...",
  "status": "running|blocked|completed",
  "gates": [
    {
      "id": "validator",
      "label": "Validator",
      "status": "ok|blocked|pending|not_applicable",
      "evidencePath": "runtime/task_history.jsonl",
      "reason": "...",
      "timestamp": "..."
    }
  ],
  "canonicalOutcome": {
    "completed": false,
    "reason": "blocked_lace_closure"
  }
}
```

#### Validacion
- Caso con LACE pendiente: rail muestra bloqueo antes de completed.
- Caso con CyberLACE block: rail muestra original bloqueado y P_safe si existe.
- Caso limpio: todas las compuertas abren con artifact real.

---

### 3. Scanner Cinematico Real

#### Objetivo
Hacer que el scanner final se vea como una revision real de codigo y no como un boton que devuelve JSON.

#### Experiencia visual
- Lupa visible recorriendo linea por linea.
- Guia roja sincronizada con numero de linea.
- Minimap lateral de archivos escaneados.
- Contadores vivos:
  - archivos,
  - lineas,
  - caracteres,
  - bytes,
  - porcentaje.
- Al finalizar, sello visual:
  `Scanner evidence persisted`.

#### Regla importante
La animacion debe estar acotada al reporte real. Si el reporte dice 3364 lineas, la UI no debe fingir 10000.

#### Datos necesarios
- `final_code_scanner_report.json`.
- `report.summary.filesScanned`.
- `report.summary.linesScanned`.
- `report.scanner.visual_playback`.
- `report.scanner.scrolls_to_last_line`.

#### Componentes existentes a aprovechar
- `CodeWorkbench.jsx` ya tiene scanner activo, lupa, timer y overlay.
- Extraer o reforzar:
  - `CodeScannerCinematicOverlay.jsx`,
  - `ScannerEvidenceSeal.jsx`,
  - `ScannerMiniMap.jsx`.

#### Validacion
- Scanner activo no debe correr si proyecto esta locked por worker activo.
- Si scanner devuelve `project_locked`, se muestra gate bloqueado, no animacion falsa.
- Si scanner OK, se persiste artifact y se muestra sello.

---

### 4. CyberLACE Rescue Visual

#### Objetivo
Convertir bloqueos CyberLACE en una experiencia clara, humana y accionable.

#### Experiencia visual
Mostrar dos rutas:

- Ruta roja: `P_original`, bloqueada.
- Ruta verde: `P_safe`, autorizada por PIN.

Flujo visual:

1. CyberLACE detecta riesgo.
2. Muestra vector de riesgo y razon natural.
3. Cuarentena el prompt original.
4. Genera P_safe.
5. Usuario ingresa PIN.
6. Control plane relanza proyecto existente con P_safe.
7. UI muestra `original sigue bloqueado; P_safe continua`.

#### Importante
El PIN no es bypass. Solo autoriza usar la version segura.

#### Datos necesarios
- `runtime/cyberlace/evidence/cyberlace_safe_rewrites.jsonl`,
- `/api/cyberlace/rescue/rewrite`,
- `/api/cyberlace/rescue/accept`,
- `/api/agent/projects/<project>/cyberlace-safe-continue`.

#### Componentes sugeridos
- `CyberLaceRescueFlow.jsx`
- `CyberLaceRiskBoard.jsx`
- `SafePromptDiffView.jsx`

#### Validacion
- PIN incorrecto no continua.
- PIN correcto continua solo con P_safe.
- Prompt original no vuelve a worker.
- Evento queda persistido.

---

### 5. Replay de Autonomia

#### Objetivo
Permitir ver la mision ejecutada por HABLA como una repeticion auditada.

#### Experiencia visual
Una linea de tiempo reproducible:

- tarea creada,
- directiva generada,
- worker lanzado,
- archivo sincronizado,
- validacion ejecutada,
- scanner ejecutado,
- LACE actualizado,
- checkpoint creado,
- outcome final.

El usuario puede pausar y revisar cada evento con evidencia.

#### Datos necesarios
- `runtime/logs/<session>-events.jsonl`,
- `runtime/logs/<session>-terminal.log`,
- `task_history.jsonl`,
- checkpoints,
- artifacts.

#### Componentes sugeridos
- `AutonomyReplayTimeline.jsx`
- `AutonomyEventCard.jsx`
- `RuntimeEvidenceDrawer.jsx`

#### Validacion
- No mostrar eventos no persistidos.
- Si falta artifact, evento aparece como incompleto.
- Replay debe sobrevivir recarga de pagina.

---

### 6. Teatro LACE de Automejora

#### Objetivo
Mostrar LACE como motor de automejora y cierre canonico, no como texto oculto en logs.

#### Experiencia visual
Panel de ciclos:

- ciclo actual,
- ciclos requeridos,
- ciclos validos,
- ciclos faltantes,
- score,
- threshold,
- early exit,
- checkpoint por ciclo,
- dependency graph LACE.

Cada ciclo tiene 3 columnas:

1. Problemas.
2. Mejora.
3. Validacion.

Si falta una dependencia, se muestra como ruptura del grafo.

Ejemplo actual que debe verse claramente:

```text
LACE-20260602-004 bloqueado
Dependencia faltante: LACE-20260602-003
Cierre canonico: bloqueado
```

#### Datos necesarios
- `LACE_LOG.md`,
- `docs/lace_cycles/ciclo-*.md`,
- `runtime/checkpoints/lace-cycle-*`,
- `runtime/checkpoints/lace-closure-gate-*`,
- `task_queue.json`,
- `task_history.jsonl`.

#### Componentes sugeridos
- `LaceAutomejoraTheater.jsx`
- `LaceCycleCard.jsx`
- `LaceDependencyGraph.jsx`
- `LaceClosureGateBadge.jsx`

#### Validacion
- LACE_LOG.md solo no cuenta como ciclo valido.
- Ciclo sin checkpoint aparece incompleto.
- Tarea LACE con dependencia faltante aparece bloqueada.
- Si LACE closure esta blocked, completed queda visualmente cerrado con candado.

## Arquitectura visual propuesta

### Capa 1: Event Normalization
Crear utilidades que conviertan eventos y artifacts en estado visual:

- `runtimeVisualState.js`
- entrada: sessions, runtime-truth, artifacts, queue, LACE, CyberLACE.
- salida: nodos, gates, timelines, warnings.

### Capa 2: Visual Components
Componentes React especializados:

- `RuntimeBrain3D.jsx`
- `ForensicTruthRail.jsx`
- `CodeScannerCinematicOverlay.jsx`
- `CyberLaceRescueFlow.jsx`
- `AutonomyReplayTimeline.jsx`
- `LaceAutomejoraTheater.jsx`

### Capa 3: Backend Truth Endpoints
Endpoints compactos para no obligar al frontend a parsear todo:

- `GET /api/projects/<project>/visual-runtime-state`
- `GET /api/projects/<project>/closure-truth`
- `GET /api/projects/<project>/lace-status`
- `GET /api/projects/<project>/autonomy-replay`

### Capa 4: Persistence
Cada modulo debe citar artifacts reales.

Ejemplo:

```json
{
  "gate": "scanner",
  "status": "ok",
  "artifactPath": "runtime/artifacts/final_code_scanner_report.json",
  "evidence": {
    "filesScanned": 18,
    "linesScanned": 3364
  }
}
```

## Roadmap de ejecucion

### Sprint Visual 0: Auditoria y contrato de verdad
Objetivo: definir payloads, acciones de mouse y evitar animacion falsa.

Entregables:
- `docs/plan_habla_visual_ia_autonoma_2026-06-02.md`
- contrato de `visual-runtime-state`
- contrato de `closure-truth`
- fixture de runtime running, blocked y completed.

Validacion:
- tests de normalizacion sin UI.



### Sprint Visual 0.5: Mouse Operativo Real y Tool Dock
Objetivo: dar vida real al mouse simulado con acciones verificables.

Entregables:
- `OperationalMouseLayer.jsx`,
- `ToolCommandDock.jsx`,
- `MouseActionQueuePanel.jsx`,
- contrato `ui:mouse-action`,
- historial `runtime/ui_action_history.jsonl`,
- cinco modales minimos: Scanner, Escoba, Research, Typewriter, Integrity.

Validacion:
- el mouse solo se mueve con accion real en cola.
- el click abre un modal real.
- scanner ejecuta endpoint o queda blocked con razon.
- acciones destructivas quedan esperando humano.
- web research usa prompt seguro/redactado y persiste fuentes.

### Sprint Visual 1: Linea de Verdad Forense
Objetivo: primero claridad, luego espectaculo.

Entregables:
- backend closure truth endpoint,
- `ForensicTruthRail.jsx`,
- tests para LACE pendiente y validator blocked.

Validacion:
- state_completed no tapa LACE pendiente.
- expected_file faltante bloquea completed.

### Sprint Visual 2: CyberLACE Rescue Visual
Objetivo: hacer que el bloqueo se sienta seguro, no abandono.

Entregables:
- `CyberLaceRescueFlow.jsx`,
- P_original redacted,
- P_safe route,
- PIN state,
- continuation state.

Validacion:
- PIN incorrecto bloquea.
- PIN correcto relanza P_safe.
- original nunca llega al worker.

### Sprint Visual 3: Teatro LACE
Objetivo: mostrar automejora como proceso canonico.

Entregables:
- `LaceAutomejoraTheater.jsx`,
- `lace-status` endpoint,
- grafo de dependencias.

Validacion:
- dependencia faltante aparece visible.
- ciclo sin checkpoint no cuenta.
- closure gate blocked se ve antes de completed.

### Sprint Visual 4: Scanner Cinematico
Objetivo: elevar la revision final a experiencia visual auditable.

Entregables:
- scanner overlay mejorado,
- minimap,
- sello de evidencia,
- contador real.

Validacion:
- scanner OK muestra artifact.
- project_locked no anima exito.

### Sprint Visual 5: Runtime Brain 3D
Objetivo: impacto visual fuerte.

Entregables:
- `RuntimeBrain3D.jsx`,
- nodos 3D por plano,
- conexiones por eventos,
- fallback 2D si WebGL no esta disponible.

Validacion:
- canvas no negro.
- nodos reflejan estado real.
- responsive desktop/mobile.

### Sprint Visual 6: Replay de Autonomia
Objetivo: que el usuario vea todo lo que hizo la IA.

Entregables:
- timeline reproducible,
- drawer de evidencia,
- filtro por worker, LACE, scanner, CyberLACE.

Validacion:
- replay persiste tras recarga.
- eventos sin artifact se marcan incompletos.

## Orden recomendado
1. Mouse Operativo Real y Tool Dock.
2. Linea de Verdad Forense.
3. CyberLACE Rescue Visual.
4. Teatro LACE.
5. Scanner Cinematico.
6. Runtime Brain 3D.
7. Replay de Autonomia.

Razon: primero se convierte el movimiento visual en accion real verificable; despues se arregla claridad y confianza; finalmente se agrega impacto visual 3D.

## Pruebas obligatorias

### Backend
- `python3 -B -m py_compile backend/app.py backend/agent_runtime.py`
- tests de endpoints nuevos.
- tests de LACE status.
- tests de closure truth.

### Frontend
- `npm run build`
- tests de normalizadores visuales.
- screenshot o smoke visual para canvas 3D.
- prueba responsive.

### Runtime real
- proyecto running muestra worker vivo.
- mouse operativo ejecuta clicks reales solo cuando hay accion en cola.
- proyecto blocked muestra razon natural.
- CyberLACE block muestra P_safe.
- LACE dependency missing muestra grafo roto.
- scanner OK muestra artifact.

## Criterio de exito
El paquete queda aprobado si un usuario puede mirar la UI y entender en menos de 10 segundos:

- que esta haciendo HABLA,
- por que el mouse se mueve y que accion real esta ejecutando,
- por que avanza,
- por que se bloquea,
- que evidencia existe,
- que falta para completed,
- que parte esta protegida por CyberLACE,
- como LACE gobierna la automejora.

## Criterio de rechazo
Rechazar cualquier implementacion que:

- anime progreso sin evidencia,
- mueva el mouse sin accion real o target verificable,
- declare completed sin validator/scanner/LACE,
- oculte bloqueos,
- use solo decoracion sin utilidad,
- degrade rendimiento del editor,
- vuelva ilegible la interfaz.
