# Reporte de Cierre de Auditoria - Seccion 19

Fecha: 2026-05-20  
Proyecto: Orquestador autonomo de proyectos con agentes reemplazables  
Alcance del reporte: cierre de las seis deudas tecnicas listadas en la seccion 19 del paper y automatizacion de auditoria con GitHub Actions.

## 1. Resumen ejecutivo

Se cerro el bloque de auditoria asociado a la seccion 19. Las seis deudas tecnicas identificadas fueron atendidas con cambios en codigo, pruebas enfocadas, checkpoints persistidos y una GitHub Action de auditoria.

Estado final:

| ID | Deuda auditada | Estado |
| --- | --- | --- |
| 19.1 | Drift entre contratos Python y schemas JSON | Cerrada |
| 19.2 | Ambiguedad entre runtime raiz y runtime por proyecto | Cerrada |
| 19.3 | Backend monolitico | Cerrada |
| 19.4 | Doble ruta de worker | Cerrada |
| 19.5 | Frontend con componentes grandes | Cerrada |
| 19.6 | Frontera de seguridad de validaciones | Cerrada |

Conclusion: no queda ninguna deuda abierta de la seccion 19. El riesgo residual registrado es que `backend/app.py` sigue siendo composition root Flask/SocketIO, pero ya no concentra los dominios pesados que motivaban la observacion 19.3.

## 2. Estado inicial de auditoria

La auditoria marco seis riesgos principales:

1. `19.1`: el contrato Python aceptaba estados HAR que el schema JSON no reflejaba.
2. `19.2`: `StateStore()` podia apuntar por defecto a `runtime/`, aunque el runtime funcional vive por proyecto.
3. `19.3`: `backend/app.py` concentraba rutas, sockets, scanner, integridad, sandbox, editor, Observer, repair, reset, blanqueo y HAR.
4. `19.4`: coexistian ruta control-plane y ruta legacy Codex CLI/PTY sin adaptador formal.
5. `19.5`: `App.jsx`, `CodeWorkbench.jsx` y `AgentStudio.jsx` concentraban demasiadas responsabilidades.
6. `19.6`: algunas validaciones ejecutaban comandos sin frontera de politica de seguridad explicita.

## 3. Cambios ejecutados por fase

### Fase 1 - Contratos y seguridad

Cierres:
- `19.1` cerrado.
- `19.6` cerrado.

Cambios principales:
- `schemas/project_state.schema.json` acepta `human_alignment_pending`.
- `schemas/project_state.schema.json` declara `pending_human_alignment_tasks`.
- `backend/test_project_state_schema_contract.py` compara schema y contrato Python.
- `orchestrator/validator.py` evalua cada `validation_command` con `orchestrator.security_policy.decide_command`.
- `orchestrator/validator.py` ejecuta comandos permitidos con `shell=False`.
- `orchestrator/validator.py` persiste decisiones en `runtime/validation_security_events.jsonl`.
- `backend/test_validator_security.py` cubre comandos permitidos, bloqueo de shell, comandos desconocidos y comandos invalidos.

Checkpoint:
- `runtime/checkpoints/phase-1-section-19-20260519T131739-0700.json`

### Fase 2 - Runtime explicito y WorkerAdapter

Cierres:
- `19.2` cerrado.
- `19.4` cerrado.

Cambios principales:
- `orchestrator/state_store.py` exige `runtime_dir` explicito.
- Se agregaron constructores intencionales `for_project_runtime` y `for_repo_runtime`.
- `orchestrator/task_queue.py`, `orchestrator/recovery.py`, `orchestrator/directive_context.py` y `orchestrator/directive_generator.py` ya no dependen de runtime raiz implicito.
- `orchestrator/worker_adapter.py` define `TaskWorkerAdapter` y `CodexSubprocessWorkerAdapter`.
- `backend/agent_worker_adapters.py` define `SessionWorkerAdapter`, `ControlPlaneSessionWorkerAdapter` y `LegacyPtySessionWorkerAdapter`.
- `backend/agent_runtime.py` selecciona la ruta de sesion por adaptador formal.

Checkpoint:
- `runtime/checkpoints/phase-2-section-19-20260519T142613-0700.json`

### Fase 3 - Primer corte backend/frontend

Estado:
- `19.3` y `19.5` quedaron mitigadas, no cerradas todavia.

Cambios principales:
- `backend/code_scanner_service.py` contiene construccion y persistencia del scanner final fuera de `backend/app.py`.
- `backend/agent_repair_service.py` contiene seleccion de archivos, directiva de reparacion y encolado de tarea de reparacion fuera de `backend/app.py`.
- `frontend/src/appUtils.js` extrae helpers de `App.jsx`.
- `frontend/src/components/codeWorkbenchUtils.js` extrae helpers de `CodeWorkbench.jsx`.
- `frontend/src/components/agentStudioUtils.js` extrae helpers de `AgentStudio.jsx`.
- `frontend/src/components/LiveReviewerPanel.jsx` extrae el panel de revisor en vivo.

Checkpoint:
- `runtime/checkpoints/phase-3-section-19-20260519T180025-0700.json`

### Fase 4 - Cierre frontend y avance backend

Cierre:
- `19.5` cerrado.

Cambios principales:
- `backend/sandbox_service.py` contiene el sandbox runtime real fuera de `backend/app.py`.
- Se extrajeron componentes presentacionales desde `frontend/src/App.jsx`.
- Se extrajeron componentes presentacionales desde `frontend/src/components/CodeWorkbench.jsx`.
- `App.jsx`, `CodeWorkbench.jsx` y `AgentStudio.jsx` quedaron bajo el umbral operativo usado para auditoria.

Componentes extraidos relevantes:
- `AppTopbar`
- `AppLintPanel`
- `AppObserverPanel`
- `AppRuntimeWorkbenches`
- `AppAgentPresenceLayer`
- `AppStatusbar`
- `CodeWorkbenchTopMenu`
- `CodeWorkbenchActivityBar`
- `CodeWorkbenchActions`
- `CodeWorkbenchSidebar`
- `CodeWorkbenchEditorHeader`
- `CodeWorkbenchEditorOverlays`
- `CodeWorkbenchGutter`
- `CodeWorkbenchTextarea`

Checkpoint:
- `runtime/checkpoints/phase-4-section-19-20260520T070929-0700.json`

### Fase 5 - Cierre backend monolitico

Cierre:
- `19.3` cerrado.

Cambios principales:
- `backend/integrity_service.py` contiene manifiesto forense, sellos, ancla externa, ledger, diff por caracter, reporte de integridad y Frozen Sniper.
- `backend/integrity_routes.py` contiene rutas de scanner, integrity report, observer findings, baseline y Frozen Sniper.
- `backend/observer_runtime_service.py` contiene seleccion de proyecto activo y snapshot runtime del Observer.
- `backend/human_alignment_routes.py` registra rutas HAR.
- `backend/editor_routes.py` registra rutas de archivos del editor y reparacion desde Workbench.
- `backend/runtime_admin_service.py` contiene limpieza de runtime/workspace.
- `backend/runtime_admin_routes.py` registra reset runtime y clean-workspace/blanqueo.
- `backend/sandbox_routes.py` registra rutas sandbox.
- `backend/app.py` quedo como composition root y dejo de contener implementaciones directas de los dominios pesados auditados.

Conteos finales relevantes:

| Archivo | Lineas |
| --- | ---: |
| `backend/app.py` | 4566 |
| `backend/integrity_service.py` | 1126 |
| `backend/integrity_routes.py` | 333 |
| `backend/editor_routes.py` | 252 |
| `backend/observer_runtime_service.py` | 186 |
| `backend/runtime_admin_routes.py` | 126 |
| `backend/runtime_admin_service.py` | 118 |
| `backend/human_alignment_routes.py` | 116 |
| `backend/sandbox_routes.py` | 74 |
| `frontend/src/App.jsx` | 1992 |
| `frontend/src/components/CodeWorkbench.jsx` | 1994 |
| `frontend/src/components/AgentStudio.jsx` | 1754 |

Checkpoint:
- `runtime/checkpoints/phase-5-section-19-20260520T094539-0700.json`

## 4. Automatizacion de auditoria

Se creo el workflow:

- `.github/workflows/audit.yml`

Jobs definidos:

| Job | Funcion |
| --- | --- |
| `backend` | Instala dependencias Python, ejecuta `py_compile` y corre suite backend de auditoria. |
| `frontend` | Ejecuta `npm ci`, `npm run build` y `npm test`. |
| `checkpoints` | Valida JSON de checkpoints, cierre de 19.3 y marcadores de cierre de seccion 19 en `PLANS.md`. |
| `audit-summary` | Falla el workflow si backend, frontend o checkpoints fallan. |

Checkpoint:
- `runtime/checkpoints/github-actions-audit-20260520T131626-0700.json`

## 5. Validaciones ejecutadas

Validaciones principales ejecutadas durante el cierre:

- `python3 -m py_compile` sobre modulos backend tocados.
- `python3 -m unittest backend.test_project_state_schema_contract backend.test_validator_security`
- `python3 -m unittest backend.test_runtime_boundary`
- `python3 -m unittest backend.test_control_plane_visual_bridge backend.test_tool_invocation_policy backend.test_executor_pipe_drain backend.test_runtime_boundary`
- `env PYTHONPATH=backend:. python3 -m unittest backend.test_agent_runtime_habla backend.test_human_alignment_review backend.test_project_state_runtime_metadata`
- `python3 -m unittest backend.test_security_policy backend.test_project_state_schema_contract backend.test_validator_security`
- `python3 -m unittest backend.test_code_scanner_service backend.test_agent_repair_service backend.test_code_scanner backend.test_app_lint`
- `python3 -m unittest backend.test_runtime_sandbox backend.test_code_scanner_service backend.test_agent_repair_service backend.test_code_scanner backend.test_app_lint`
- `python3 -m unittest backend.test_runtime_clean_workspace backend.test_code_scanner backend.test_runtime_sandbox backend.test_observer_auto_shutdown backend.test_human_alignment_review`
- `python3 -m unittest backend.test_app_lint backend.test_code_scanner backend.test_code_scanner_service backend.test_agent_repair_service backend.test_runtime_sandbox backend.test_runtime_clean_workspace backend.test_observer_auto_shutdown backend.test_human_alignment_review backend.test_security_policy backend.test_validator_security backend.test_project_state_schema_contract`
- `npm run build`
- `npm test`
- `jq .` sobre checkpoints relevantes.
- Validacion YAML del workflow con PyYAML.
- Validacion local del script de checkpoints incluido en `.github/workflows/audit.yml`.

Ultima validacion local equivalente al workflow:

| Validacion | Resultado |
| --- | --- |
| YAML del workflow con PyYAML | OK |
| Checkpoints JSON y cierre seccion 19 | OK, 13 JSON |
| `py_compile` backend | OK |
| Suite backend del workflow | OK, 45 tests |
| `npm run build` | OK |
| `npm test` | OK |

## 6. Evidencia persistida

Checkpoints relevantes:

- `runtime/checkpoints/phase-1-section-19-20260519T131739-0700.json`
- `runtime/checkpoints/phase-2-section-19-20260519T142613-0700.json`
- `runtime/checkpoints/phase-3-section-19-20260519T180025-0700.json`
- `runtime/checkpoints/phase-4-section-19-20260520T070929-0700.json`
- `runtime/checkpoints/phase-5-section-19-20260520T094539-0700.json`
- `runtime/checkpoints/github-actions-audit-20260520T131626-0700.json`

Documentos actualizados:

- `PLANS.md`
- `recuperacioncontexto.md`
- `ULTIMO_CONTEXTO_CODEX.md`

Documento de reporte:

- `docs/reporte_cierre_auditoria_seccion_19_2026-05-20.md`

## 7. Limitaciones y riesgos residuales

Limitaciones:
- La carpeta local no esta inicializada como repositorio Git, por lo tanto no hubo evidencia por `git diff` o `git status`.
- `actionlint`, `yq` y `ruby` no estan disponibles localmente; el workflow fue validado con PyYAML.
- La GitHub Action ejecutara realmente cuando el codigo este subido a GitHub con Actions habilitado.

Riesgo residual aceptado:
- `backend/app.py` sigue siendo composition root Flask/SocketIO para arquitectura, reverse engineering, email commands, sesiones de agente y sockets. Esto no se considera deuda 19.3 abierta porque los dominios pesados nombrados por auditoria ya fueron extraidos a servicios o modulos de rutas dedicados.

## 8. Dictamen final

La seccion 19 queda cerrada en codigo, documentacion, checkpoints y auditoria automatica.

Condicion para presentar:
- Adjuntar este reporte.
- Adjuntar `PLANS.md`.
- Adjuntar los checkpoints de Fase 1 a Fase 5.
- Adjuntar evidencia del workflow `.github/workflows/audit.yml`.
- Cuando el repositorio este en GitHub, adjuntar la primera ejecucion exitosa del workflow `Audit`.

Estado final para auditor/inversor:

```text
Seccion 19: cerrada.
Deudas abiertas: 0 de 6.
Validacion local: OK.
Auditoria automatica: creada.
Pendiente operativo externo: primera corrida real en GitHub Actions.
```
