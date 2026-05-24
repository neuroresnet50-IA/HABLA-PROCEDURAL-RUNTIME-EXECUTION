# AGENTS.md

## Propósito del repositorio
Este repositorio debe evolucionar hacia un **orquestador autónomo de proyectos**.
No debe comportarse como una sola sesión larga de chat.
Debe comportarse como una máquina de ejecución de proyectos cortos, medianos y largos, con agentes reemplazables.

## Tesis central
Nunca tratar un proyecto largo como una sola sesión larga.
Todo proyecto debe dividirse en tareas pequeñas, verificables, persistentes y reanudables.

## Identidad del sistema
El producto final no es “un chat que programa”.
El producto final es “un sistema operativo de ejecución de proyectos con agentes reemplazables”.

## Reglas maestras
1. No depender de la memoria implícita de una sola corrida.
2. Persistir siempre el estado real en disco.
3. No contar progreso sin evidencia real en disco.
4. Toda tarea debe ser verificable.
5. Toda tarea debe ser reanudable.
6. Todo fallo debe dejar traza.
7. Todo retry debe tener causa registrada.
8. Toda validación debe quedar en historial.
9. Todo cambio importante debe generar checkpoint.
10. No acoplar fuertemente el sistema a Codex; Codex es solo un worker.
11. Toda directiva operativa del worker debe generarse desde política, plan, estado y checkpoint; no debe depender de prompts manuales permanentes.

## Arquitectura objetivo
El sistema debe dividirse en cuatro planos:

### 1. Control plane
Python decide el estado real.
Mantiene backlog, prioridades, budgets, checkpoints y retries.

### 2. Worker plane
Cada worker ejecuta una sola tarea acotada.
Una tarea puede ser:
- crear archivo,
- refactorizar módulo,
- escribir pruebas,
- corregir un fallo puntual.

### 3. Verification plane
Después de cada tarea se debe validar:
- archivos creados,
- archivos modificados,
- tests,
- lint,
- estructura,
- comandos de validación declarados.

### 4. Memory plane
Persistir todo en disco:
- project_state,
- task_queue,
- task_history,
- failures,
- checkpoints,
- artifacts.

## Reglas duras del runtime
1. El modo smoke no puede inferirse por palabras sueltas.
2. El modo smoke solo puede venir de una señal explícita de configuración.
3. Deben existir modos explícitos:
   - smoke
   - build
   - medium
   - long-run
4. Una sesión debe contener múltiples tareas.
5. Cada tarea debe lanzar un worker propio.
6. Cada tarea debe tener timeout propio.
7. El retry debe ser por tarea, no por sesión completa.
8. Si un proceso no cierra con terminate(), debe cerrarse con kill().
9. long-run no puede comportarse igual que smoke.
10. El progreso solo vale si existe evidencia real.
11. Las instrucciones del worker deben derivarse de `AGENTS.md`, `PLANS.md`, el estado persistido y HABLA BASIC.
12. `PROMPT_SPRINT_*.txt` solo puede existir como artefacto humano o bootstrap; el sistema final debe generar directivas por tarea.

## Politica de cierre visual y sandbox real
Estas reglas son obligatorias cuando una integracion, reparacion o proyecto pasa a `completed`.

1. **Scanner final completo.** El scanner visual debe recorrer cada archivo visible desde la linea 1 hasta la ultima linea real. La lupa debe seguir la linea activa del editor, sincronizada con la guia roja de numeros, y no puede limitarse a una pagina parcial o a un rango fijo de pixeles.
2. **Reporte auditable del scanner.** El backend debe persistir `runtime/artifacts/final_code_scanner_report.json` y checkpoint final declarando `magnifier_line_by_line_to_last_line`, total de lineas, caracteres y archivos leidos.
3. **Sandbox real post-integracion.** Despues de scanner aprobado, el sistema debe arrancar la aplicacion creada en un sandbox local real. Para web/static/node/python web, debe existir un proceso servidor vivo, puerto local, URL HTTP y healthcheck positivo antes de marcarlo `running`.
4. **Modal interno obligatorio.** Si la app expone preview web, la UI debe abrir un modal interno con iframe apuntando a `embedUrl`; no basta con dejar solo un link externo ni un estado dummy.
5. **Evidencia antes de cierre.** La secuencia final solo se considera completa si writer final, scanner final y sandbox real quedan con evidencia persistida. Si el sandbox no puede responder HTTP, el cierre debe quedar bloqueado o con advertencia visible.

## Politica HABLA Observer IA
El diferenciador del sistema es observar evidencia que otros agentes no ven. El Observer no debe limitarse a mirar sesiones activas o puntos rojos del mapa; debe cruzar estado persistido, scanner, sandbox, runtime y UI.

1. **Evidencia runtime obligatoria.** El snapshot del Observer debe incluir `runtime/project_state.json`, `runtime/artifacts/final_code_scanner_report.json`, `runtime/artifacts/final_typewriter_report.json` y `runtime/sandbox.json` del proyecto activo cuando existan.
2. **Alarma por scanner faltante.** Si un proyecto esta `completed` pero no existe scanner final valido, o el reporte no certifica `magnifier_line_by_line_to_last_line` y `scrolls_to_last_line`, el Observer debe emitir estado `verifying_scanner` antes de hacer observaciones genericas de mapa/flujo.
3. **Alarma por sandbox incompleto.** Si el scanner final esta aprobado pero el sandbox no tiene `running=true`, `ready=true` y URL embebible, el Observer debe emitir estado `verifying_sandbox`.
4. **Observacion explicable.** Cada evento del Observer debe traer `reason`, `evidence`, `snapshotSummary`, `projectSlug` y accion visual (`uiAction`) para que el humano vea por que el sistema esta mirando esa zona.
5. **No accion destructiva.** El Observer puede proponer acciones seguras o pedir autorizacion, pero no ejecuta reparaciones destructivas ni blanqueos sin cumplir las reglas de seguridad.

## Politica de herramientas internas para agentes
Los agentes Codex pueden usar herramientas internas del sistema, pero solo por contrato ejecutable y con evidencia persistida. La instruccion escrita no basta: el agente debe invocar la herramienta real y leer su salida.

Interfaz canonica:

```text
python3 orchestrator/agent_tools.py health
python3 orchestrator/agent_tools.py observer-status
python3 orchestrator/agent_tools.py observe
python3 orchestrator/agent_tools.py scanner <projectSlug>
python3 orchestrator/agent_tools.py integrity <projectSlug>
python3 orchestrator/agent_tools.py findings <projectSlug>
python3 orchestrator/agent_tools.py sniper <projectSlug> --dry-run
python3 orchestrator/agent_tools.py sniper <projectSlug> --confirm FROZEN_SNIPER
```

Reglas de uso:
1. `observer-status` es lectura de estado; no debe iniciar misiones ni mantener vivo el Observer.
2. `observe` solo se usa cuando el agente necesita una observacion puntual con razon de tarea.
3. `scanner` debe usarse antes de aceptar cierre tecnico, despues de cambios importantes o cuando el humano pida scanner.
4. `integrity` debe usarse para detectar cambios externos, codigo borrado, sobrescrituras fuera del ledger o divergencias de baseline.
5. `findings` debe leerse antes de reportar que no hay problemas forenses.
6. `sniper --dry-run` es permitido para diagnostico y propuesta de recuperacion.
7. `sniper --confirm FROZEN_SNIPER` solo puede ejecutarse con confirmacion humana o politica explicita de recovery; debe quedar registrado en historial.
8. Ningun agente puede inventar que una herramienta paso: debe citar `statusCode`, `ok`, `reportPath`, `artifactPath` o el blocker real.
9. La salida por defecto del CLI debe ser compacta (`outputMode=compact`) para no consumir tokens con evidencia masiva; `--full` solo se usa cuando una tarea acotada necesita el payload completo.
10. Si el backend local no responde, el agente debe registrar el blocker y usar validaciones locales alternativas; no debe simular salida de Observer.
11. Las salidas de herramientas quedan auditadas en `runtime/agent_tool_invocations.jsonl`.

Activacion correcta:
- Al iniciar o continuar un proyecto, el runtime puede activar Observer en modo mision.
- Al oprimir Scanner, Observer administra la revision como herramienta.
- Al oprimir Sniper, Observer administra la recuperacion como herramienta.
- Con la UI abierta sin tarea, Observer no debe trabajar autonomamente.
- Con polling, reconnect o consulta de status, Observer no debe abrir incidente nuevo.

Contrato de responsabilidad:
- Worker plane ejecuta cambios acotados.
- Observer coordina evidencia y herramientas.
- Scanner inspecciona codigo y genera reporte.
- Integrity scan compara contra baseline/ledger.
- Sniper recupera solo bajo reglas de seguridad.
- Control plane decide tareas, retries y cierre con evidencia.

## Politica general de destruccion / blanqueo
Estas reglas son obligatorias para cualquier agente, worker, endpoint o boton que tenga permiso de ejecutar `Blanquear Workspace` o cualquier accion destructiva masiva.

1. **Blanqueo por fallo critico de compilacion.** Si el software no compila end-to-end despues de 3 intentos de reparacion consecutivos, o se detecta un estado irrecuperable, el agente debe iniciar protocolo de blanqueo. Antes de blanquear debe crear backup de bases de datos, archivos importantes, runtime e historial; registrar el motivo exacto en `runtime/failures.jsonl` y `runtime/task_history.jsonl`; y solo despues ejecutar la accion destructiva aprobada.
2. **Confirmacion humana obligatoria.** Ningun blanqueo total puede ejecutarse de forma 100% autonoma en modo `medium` o `long-run`. El agente debe mostrar el resumen de decision y pedir: `CONFIRMAR BLANQUEO TOTAL DEL WORKSPACE? (si/confirmar)`. Solo una respuesta afirmativa permite proceder. En modo `smoke` o pruebas controladas se permite blanqueo autonomo con registro.
3. **Backup siempre antes de destruir.** Nunca se blanquea sin backup previo. Todo blanqueo debe generar backup de codigo fuente del workspace, bases de datos si existen, `runtime/`, configuraciones y `.env*`. Los backups deben guardarse en `backups/blanqueo/YYYYMMDD.../` con `manifest.json`.
4. **Blanqueo selectivo inteligente primero.** Antes de un blanqueo total se debe intentar blanqueo selectivo: eliminar carpetas generadas (`__pycache__`, `node_modules`, `build`, `dist`, `venv`, `.venv`, caches), temporales y logs pesados; resetear estado transitorio manteniendo historial base. Solo si el problema persiste o el estado es irrecuperable se escala a blanqueo total.
5. **Post-blanqueo y aprendizaje.** Despues de cualquier blanqueo se debe crear la tarea `POST-BLANQUEO-RECOVERY`, analizar causa raiz, y actualizar `lessons_learned/blanqueo-YYYY-MM-DD.md` o `AGENTS.md` con causa raiz, que fallo y que debe prevenirse.
6. **Justificacion obligatoria y transparente.** Antes de cualquier blanqueo total o parcial, el agente debe generar una decision auditable con causa raiz, intentos previos, evidencia de irrecuperabilidad o degradacion, riesgos de no blanquear, beneficios esperados, que se elimina, que se preserva y donde quedara el backup. Esa decision debe registrarse como `BLANQUEO_DECISION` en `runtime/failures.jsonl`, en `runtime/task_history.jsonl` y en `runtime/logs/blanqueo_decision_[TIMESTAMP].md`.

Formato visible obligatorio antes de proceder:

```text
=== DECISION DE BLANQUEO ===
Tarea: ...
Decision: Blanqueo Total / Selectivo
Motivo principal: ...
Intentos fallidos: X
Archivos/Carpetas a eliminar: ...
Backups creados en: ...
Proceder: si / no, requiere confirmacion humana en modo seguro
```

## Politica Human Alignment Review (HAR)
HAR es el ciclo formal de alineacion humana despues de un cierre tecnico correcto. Un proyecto puede compilar, validar y quedar `completed`, pero aun necesitar cambios de preferencia humana o direccion de diseno.

1. **Activacion automatica.** Al cerrar una tarea grande o proyecto completo con `status=completed`, el control plane debe crear o reutilizar una revision `HUMAN_ALIGNMENT_REVIEW-*` en `runtime/human_alignment_reviews/`.
2. **Activacion manual.** Si el humano indica "quiero cambiar X", "no me gusto que usara Y" o una preferencia equivalente, se debe abrir HAR para el proyecto actual.
3. **No tocar codigo al abrir HAR.** La creacion de HAR solo resume lo construido, decisiones detectadas, stack tecnico y evidencias. No puede modificar archivos de producto.
4. **Feedback primero.** El agente debe esperar feedback humano explicito antes de convertir preferencias en tareas. Ejemplo: cambiar PostgreSQL por SQL Server es ajuste de direccion, no fallo tecnico.
5. **Tareas controladas.** Despues del feedback, HAR debe crear tareas prioritarias `HUMAN_ALIGNMENT_REVIEW-*-NNN` con dependencias, archivos esperados y validaciones. Esas tareas se ejecutan por el control plane normal, no por edicion oculta.
6. **Stack auditable.** HAR debe exponer opciones de lenguajes, bases de datos, backend, frontend, visualizacion, realtime, mobile, devops, IA/ML, librerias, embebidos, testing y otros frameworks para capturar preferencias humanas.
7. **Trazabilidad.** Cada HAR debe persistir JSON, Markdown, evento en `runtime/task_history.jsonl` y evento HAR en `runtime/human_alignment_reviews/events.jsonl`.
8. **Estado posterior.** Cuando el humano envia ajustes, `project_state.status` puede pasar a `human_alignment_pending` hasta que las tareas HAR se ejecuten y validen.

## Política de directivas operativas
1. El runtime debe cargar `AGENTS.md` como constitución del repositorio.
2. El runtime debe cargar `PLANS.md` como roadmap ejecutable.
3. El runtime debe combinar política, plan, estado, historial y checkpoint para construir la directiva de la tarea actual.
4. HABLA BASIC debe actuar como capa procedural para esa directiva, no como texto decorativo.
5. Cada directiva generada para un worker debe persistirse en disco para auditoría y reanudación.

## Estructura esperada del proyecto
```text
runtime/
  project_state.json
  task_queue.json
  task_history.jsonl
  failures.jsonl
  artifacts/
  checkpoints/
  directives/
  logs/

orchestrator/
  planner.py
  task_queue.py
  executor.py
  validator.py
  recovery.py
  state_store.py
  contracts.py
  policy_loader.py
  plan_loader.py
  directive_context.py
  habla_adapter.py
  directive_generator.py
  benchmark.py

workers/
  codex_worker.py

schemas/
  task.schema.json
  task_result.schema.json
  project_state.schema.json

tests/
  test_smoke_mode.py
  test_retry_recovery.py
  test_task_queue.py
  test_resume_checkpoint.py
  test_long_project_flow.py
```

## Modelo mínimo de Task
```json
{
  "id": "TASK-001",
  "title": "Crear estructura base del proyecto",
  "goal": "Inicializar carpetas y archivos base",
  "status": "pending",
  "priority": 10,
  "dependencies": [],
  "expected_files": ["README.md", "src/__init__.py"],
  "validation_commands": ["pytest -q", "ruff check ."],
  "timeout_seconds": 900,
  "max_retries": 3,
  "mode": "build",
  "checkpoint_key": null
}
```

## Modelo mínimo de TaskResult
```json
{
  "task_id": "TASK-001",
  "completed": false,
  "files_created": [],
  "files_modified": [],
  "validation_ran": [],
  "validation_passed": false,
  "blockers": [],
  "next_recommendation": ""
}
```

## Contrato de salida obligatorio
Cada tarea debe devolver:
- objetivo cumplido o no,
- archivos creados,
- archivos modificados,
- validaciones ejecutadas,
- resultado de validación,
- blockers reales,
- recomendación siguiente.

## Política de implementación
Cuando implementes:
- prioriza claridad y trazabilidad,
- deja comentarios útiles solo donde agreguen valor,
- no inventes éxito si no hay validación,
- no cierres una tarea como completa sin evidencia real,
- si falta algo, deja el estado explícito en archivos de runtime.

## Política de recuperación de contexto
Debe mantenerse `recuperacioncontexto.md` en la raíz del repositorio.

Cada terminal de Codex que trabaje en este repositorio debe tratar la memoria en disco como obligatoria, no opcional.

Al iniciar una intervención de trabajo debe leer, como mínimo:
- `ULTIMO_CONTEXTO_CODEX.md`, si existe,
- las entradas recientes de `recuperacioncontexto.md`,
- `PLANS.md` y esta política cuando el usuario pregunte por planes, arquitectura o continuidad.

Cada respuesta de trabajo debe actualizar `recuperacioncontexto.md` antes del cierre final con:
- solicitud recibida,
- acciones realizadas,
- archivos creados o modificados,
- validación corta ejecutada,
- resultado real de la validación,
- blockers o riesgos,
- punto de reanudación.

Cada respuesta de trabajo también debe actualizar `ULTIMO_CONTEXTO_CODEX.md` con un resumen corto y sobrescribible del estado actual:
- fecha/hora,
- última solicitud del usuario,
- estado real,
- archivos tocados,
- validación ejecutada,
- siguiente paso exacto.

Regla de cierre: no se debe enviar una respuesta final de trabajo sin dejar esos dos rastros actualizados. Si una validación no pudo ejecutarse, debe quedar escrito el motivo exacto.

No se debe basar el estado actual solo en benchmarks viejos. Después de cada cambio se debe ejecutar una validación corta enfocada en los archivos más recientes o relacionados con el cambio.

## Política de entrega por sprint
Cada sprint debe:
1. modificar solo el alcance asignado,
2. dejar artefactos persistidos,
3. dejar tests o validaciones asociadas,
4. registrar riesgos o pendientes,
5. no invadir sprints futuros salvo stubs mínimos necesarios.

## Benchmarks obligatorios
El sistema final debe soportar:
- smoke-01
- crud-ui-02
- refactor-mid-03
- long-project-04
- recovery-05

Si una versión no pasa todos los benchmarks, no se despliega.
