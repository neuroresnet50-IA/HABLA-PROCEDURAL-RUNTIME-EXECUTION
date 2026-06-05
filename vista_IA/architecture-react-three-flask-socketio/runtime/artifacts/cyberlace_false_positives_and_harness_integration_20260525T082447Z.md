# Evidencia tecnica: falsos positivos, CyberLACE y harness end-to-end

Fecha UTC: 2026-05-25T08:24:47.873123+00:00

## Resumen ejecutivo

Este documento registra la evidencia tecnica de la reparacion del runtime HABLA/Codex, el cierre del hueco de seguridad de CyberLACE, los falsos positivos encontrados durante la integracion y el uso del harness interno end-to-end.

El sistema quedo funcional end-to-end bajo las validaciones ejecutadas: backend activo, UI cargando, proyectos visibles, archivos accesibles, Socket.IO en polling controlado sin WebSocket 500, `/api/agent/session` respondiendo rapido, estados sin zombis, CyberLACE en `monitor` global y hard gate obligatorio bloqueando documentos sensibles antes de arrancar Codex.

## Contexto del incidente

La reparacion inicio con estas restricciones operativas:

- No crear proyecto nuevo.
- No borrar los proyectos protegidos:
  - `workspace/projects/sesion-20260524210420`
  - `workspace/projects/sesion-20260524233805`
- No borrar runtime sin backup.
- No reescribir `backend/app.py` completo.
- No reemplazar arquitectura.
- No activar CyberLACE enforce global.
- No declarar exito sin iniciar una sesion real o probar fallo limpio.
- Todo cambio debe dejar checkpoint.

Durante las pruebas posteriores se detecto un problema grave: CyberLACE estaba en modo `monitor`, por lo que auditaba y registraba riesgo, pero no bloqueaba la ejecucion. En ese estado, un archivo usado como fixture de seguridad con credenciales simuladas podia pasar por el flujo de agentes si el contenido llegaba al worker sin un bloqueo previo obligatorio.

La causa no era que CyberLACE no existiera, sino que el modo global `monitor` convertia decisiones de riesgo en `ALLOW` para el runtime. Ademas, el backend no tenia un hook que interceptara cada `read()` interno de un proceso Codex ya lanzado. La solucion aplicada fue impedir que Codex arranque si el alcance documental de la tarea no es seguro.

## Reparacion del runtime HABLA/Codex

Se aplicaron cambios acotados, sin reescribir la arquitectura:

- Socket.IO quedo forzado a polling controlado cuando se usa Werkzeug.
- La prueba de handshake devolvio `upgrades: []`, evitando el error original de WebSocket 500.
- `/api/agent/session` dejo de esperar trabajo pesado sincronico antes de responder.
- La preparacion de runtime, LACE, directiva y sincronizacion pesada se mueve a background.
- Se agrego estado `preparing`.
- `running` queda reservado para sesiones con PID real o worker activo.
- `pid=null` ya no puede representar una sesion `running`.
- `runtime-truth` detecta estados persistidos huerfanos: `running` en disco sin sesion activa ni PID vivo.
- La liberacion de zombi crea backup, reencola tareas activas a `pending`, registra failure y checkpoint.
- El preflight interno `observer-status` ya no bloquea el arranque; si vence el timeout queda como warning.

Evidencia de esta fase:

- Reporte: `runtime/artifacts/habla_runtime_repair_report_20260525T011758Z.md`
- Checkpoint: `runtime/checkpoints/habla-runtime-repair-final-20260525T011758Z.json`

## Cierre de seguridad CyberLACE

CyberLACE sigue en `monitor` global para no activar enforce global, cumpliendo la regla original. Pero se agrego una puerta obligatoria independiente del modo global.

La nueva politica efectiva es:

- CyberLACE global: `monitor`.
- Hard gate documental: siempre enforce.
- Si el hard gate detecta secreto, ruta externa sensible o documento no escaneable de forma segura, Codex no arranca.
- La decision se registra como bloqueo de runtime, no como advertencia ignorada.

Resultado esperado y validado cuando se referencia un documento sensible:

- `status=blocked`
- `pid=null`
- `command=[]`
- `returncode=126`
- `errorCode=cyberlace_sensitive_document_blocked`
- `runtimeAction=QUARANTINE`
- muestras en evidencia: `[REDACTED]`
- no se crea worker Codex
- no se crea proceso hijo

Archivos principales integrados:

- `backend/cyberlace_document_guard.py`
- `backend/agent_runtime.py`
- `orchestrator/safe_process_env.py`
- `orchestrator/worker_adapter.py`
- `workers/codex_worker.py`
- `frontend/src/App.jsx`
- `frontend/src/App.css`

## Como funciona el hard gate

El guard nuevo inspecciona antes de permitir el arranque:

- texto de la orden del usuario
- payload de la tarea
- directiva generada para el control plane
- rutas locales mencionadas en la tarea
- documentos de texto dentro del workspace del proyecto
- referencias externas sensibles como `.ssh`, claves privadas, `.env`, tokens o rutas criticas del sistema

Si encuentra patrones de riesgo, bloquea antes de lanzar Codex. Tambien repite el control dentro de `workers/codex_worker.py` justo antes de crear el proceso hijo. Esto cubre dos capas:

- backend/runtime antes de aceptar la ejecucion
- worker antes de invocar el binario Codex

Ademas se filtro el entorno del proceso hijo con `orchestrator/safe_process_env.py` para no heredar variables sensibles del backend, como passwords, tokens, API keys, DB URLs, credenciales cloud o claves SSH.

El default de Codex interno se endurecio de `danger-full-access` a `workspace-write`.

## Modal visual de bloqueo

Se agrego un modal global en frontend para eventos criticos de CyberLACE:

- aparece sobre la pantalla
- usa estilo rojo de warning
- informa que la accion fue negada
- no ofrece una ruta de override para ejecutar de todos modos

El modal es visual; la decision real vive en backend. Aunque el usuario cierre el modal, el runtime ya nego la accion.

## Falsos positivos encontrados

### Falso positivo 1: documento grande interpretado como inseguro

Durante el escaneo de workspace, `sesion-20260524210420` fue bloqueado inicialmente porque un artefacto historico grande superaba el limite de lectura del scanner. El bloqueo no se basaba en un secreto confirmado, sino en lectura incompleta.

Correccion aplicada:

- Se aumento el limite controlado de lectura de documentos de texto de runtime a `2_000_000` bytes.
- Se reescaneo el workspace.
- El proyecto dejo de bloquearse porque no habia evidencia real de secreto.

Evidencia:

- Checkpoint de redaccion sin cambios reales: `runtime/checkpoints/cyberlace-workspace-redaction-20260525T021448Z.json`
- Backup preparado: `runtime/backups/cyberlace_workspace_redaction/20260525T021448Z`
- Resultado: `redactedFiles=0`, `redactions=0`

### Falso positivo 2: `/BASE` detectado como ruta externa peligrosa

El repo vive bajo una ruta con espacios:

`/home/neurodriver/BASE _METACOGNICION_COLOMBIA/...`

El parser interpreto de forma incorrecta fragmentos como `/BASE` o `external:BASE` cuando una directiva mencionaba la ruta del repositorio. Eso generaba bloqueo aunque era una referencia normal al workspace.

Correccion aplicada:

- Se refino la heuristica de rutas absolutas externas en `backend/cyberlace_document_guard.py`.
- El guard ya no bloquea menciones a la raiz real del repo ni fragmentos truncados por espacios.
- Se mantuvo el bloqueo para rutas externas sensibles reales.

Casos validados:

- Mencion a `/home/neurodriver/BASE _METACOGNICION...`: no bloquea.
- Mencion a `/home/neurodriver/.ssh/id_rsa`: bloquea como `external:id_rsa`.
- Mencion a `/etc/passwd`: bloquea como ruta externa sensible.
- Mencion al fixture sensible: bloquea con evidencia redactada.

## Ajuste de pruebas internas

Al endurecer seguridad, algunas pruebas internas antiguas fallaron porque esperaban el comportamiento inseguro previo:

- `danger-full-access` por defecto.
- `running` inmediato antes de PID real.
- prompt/directiva disponible sincronica antes de la fase `preparing`.

Se actualizaron pruebas para validar el comportamiento seguro actual:

- sandbox por defecto `workspace-write`
- estado `preparing` antes de PID real
- `running` solo con worker real
- recuperacion de estados no-running cuando no hay PID vivo

Resultado final de suite runtime/seguridad:

`97 passed in 7.14s`

## Harness end-to-end

El script interno se llama:

`orchestrator/e2e_gate_harness.py`

Es un harness end-to-end por proyecto. No valida automaticamente todos los proyectos del workspace. Se ejecuta contra un proyecto concreto en `workspace/projects/<slug>`.

Comando tipico:

```bash
python3 -B orchestrator/e2e_gate_harness.py   --workspace .   --project <slug>   --base-url http://127.0.0.1:5001   --cycles 1   --verbose
```

Si no se pasa `--project`, usa el proyecto default configurado por el harness.

### Nodos que comprueba

El harness cruza el ecosistema por nodos. Cada nodo registra comando, tiempo, salida, codigo de salida y evidencia:

1. `pytest_available`: confirma que pytest existe.
2. `pytest_lace_unit`: corre pruebas unitarias LACE.
3. `pytest_lace_control_gate`: valida el gate LACE del control plane.
4. `lace_log_readonly`: lee `LACE_LOG.md` y valida ciclos LACE.
5. `runtime_state_after_gate`: revisa `project_state.json` y `task_queue.json`.
6. `backend_health`: llama el backend por HTTP.
7. `scanner_gate`: ejecuta scanner interno.
8. `scanner_artifact_gate`: valida artefacto del scanner.
9. `integrity_gate`: ejecuta integridad de archivos.
10. `integrity_artifact_gate`: valida artefacto de integridad.
11. `findings_gate`: ejecuta revision de findings/observer.
12. `findings_artifact_gate`: confirma que no queden findings activos.
13. `sandbox_http_gate`: comprueba `runtime/sandbox.json` y HTTP real al sandbox.
14. `no_pytest_process_left`: confirma que no quedan procesos pytest colgados.
15. `pytest_cache_cleanup`: limpia cache de pytest.

El resultado final se calcula con:

- `nodesTotal`
- `nodesPassed`
- `nodesFailed`
- `timedOut`
- `passed`

`passed=true` solo si todos los nodos pasan.

### Reportes del harness

El harness genera:

- `runtime/e2e_gate_harness/latest.json`
- `runtime/e2e_gate_harness/e2e-gate-harness-<proyecto>-<timestamp>.json`

### Resultado obtenido

Primera corrida sobre el proyecto default:

- `13/15` nodos OK.
- Fallaron `findings_artifact_gate` y `sandbox_http_gate`.
- Causa: sandbox del proyecto default apagado y finding activo asociado a sandbox incompleto.

Correccion:

- Se arranco el sandbox del proyecto default.
- Se repitio el harness.

Resultado final sobre proyecto default:

- `15/15 OK`
- `nodesFailed=0`
- `timedOut=0`

Reporte observado:

`runtime/e2e_gate_harness/e2e-gate-harness-sesion-20260518014728-jeego-en-3d-20260525T032247Z.json`

### Proyectos protegidos

Tambien se probo el harness contra:

- `sesion-20260524210420`
- `sesion-20260524233805`

Ambos fallaron en `lace_log_readonly` porque no tienen los 10 ciclos LACE validos que ese gate exige. Eso no fue una caida del runtime, sino una condicion de madurez/documentacion del proyecto.

Reportes de esas corridas:

- `runtime/e2e_gate_harness/e2e-gate-harness-sesion-20260524210420-20260525T025444Z.json`
- `runtime/e2e_gate_harness/e2e-gate-harness-sesion-20260524233805-20260525T025444Z.json`

## Validaciones finales ejecutadas

Validaciones generales:

```bash
python3 -B -m py_compile backend/app.py backend/agent_runtime.py backend/cyberlace_document_guard.py orchestrator/*.py workers/codex_worker.py
npm --prefix frontend run build
OPEN_BROWSER=0 ./start.sh restart
```

Resultado:

- Compilacion Python: OK.
- Build frontend: OK.
- Restart real: OK.
- Backend activo: OK.

Validaciones HTTP:

- `/api/health`: OK.
- `/api/agent/sessions`: OK.
- `/api/agent/projects`: OK.
- `/api/cyberlace/health`: OK, `mode=monitor`, `enabled=true`.
- `runtime-truth` de ambos proyectos protegidos: OK, `verdict=idle`, sin zombi.
- Socket.IO polling: HTTP 200 con `upgrades=[]`.

Validaciones de seguridad:

- Fixture sensible: bloqueado.
- Ruta externa `.ssh/id_rsa`: bloqueada.
- Ruta real del repo con espacios: no bloqueada.
- Worker con workspace sensible: no crea proceso hijo, `childPid=None`, `returncode=126`.
- Evidencia sensible: redactada.

Reporte y checkpoint de validacion ampliada:

- `runtime/artifacts/internal_harness_integrity_final_20260525T032417Z.md`
- `runtime/checkpoints/internal-harness-integrity-final-20260525T032417Z.json`

## Limitacion residual declarada

La reparacion no es un hook de syscall que intercepte cada `read()` interno de un Codex ya arrancado. En esta arquitectura, la mitigacion aplicada es impedir que Codex arranque si el alcance documental no es seguro y repetir el guard dentro del worker antes de crear el proceso hijo.

Esto es mas seguro para el modelo actual porque evita que el proceso tenga oportunidad de leer o subir documentos comprometidos.

## Estado final

Estado final validado:

- UI carga.
- Backend responde.
- Los dos proyectos protegidos aparecen.
- Los archivos se abren por API.
- No hay WebSocket 500.
- `/api/agent/session` responde rapido.
- No queda `running` con `pid=null`.
- No quedan zombis.
- CyberLACE permanece en `monitor` global.
- Hard gate documental bloquea siempre los documentos sensibles.
- Harness default end-to-end paso `15/15`.
- Suite interna runtime/seguridad paso `97 passed`.
- Se generaron reportes y checkpoints.

## Recomendacion operativa

Para declarar listo un proyecto despues de cambios relevantes, ejecutar como minimo:

```bash
python3 -B -m py_compile backend/app.py backend/agent_runtime.py backend/cyberlace_document_guard.py orchestrator/*.py workers/codex_worker.py
npm --prefix frontend run build
python3 -B orchestrator/e2e_gate_harness.py --workspace . --project <slug> --base-url http://127.0.0.1:5001 --cycles 1 --verbose
```

Y antes de cerrar una tarea grande:

- revisar `runtime/e2e_gate_harness/latest.json`
- revisar `/api/cyberlace/health`
- revisar `runtime-truth` del proyecto
- confirmar que no hay `running` sin PID real
- confirmar que CyberLACE bloquea fixtures sensibles con evidencia redactada
