# Evidencia Tecnica: CyberLACE, Falsos Positivos y Harness End-to-End

Fecha: 2026-05-25
Sistema: HABLA / Codex runtime
Repositorio: `architecture-react-three-flask-socketio`

## Resumen Ejecutivo

Se reparo el runtime HABLA/Codex sin crear proyecto nuevo, sin borrar los proyectos protegidos y sin activar `CyberLACE enforce` global. CyberLACE permanece en modo `monitor`, pero se agrego un hard-gate obligatorio para documentos sensibles antes de lanzar Codex.

El sistema ahora bloquea el runtime si una orden, tarea, directiva, documento referenciado, workspace o worker contiene o intenta procesar credenciales, claves, PIN, CVV, tokens o rutas externas sensibles. El bloqueo ocurre antes de crear un proceso Codex real.

Validacion clave:

- `/api/agent/session` con fixture sensible respondio en `1.828s`.
- Estado final: `blocked`.
- `pid=null`.
- `command=[]`.
- `returncode=126`.
- `runtimeAction=QUARANTINE`.
- Evidencia sanitizada con `sample="[REDACTED]"`.
- No se imprimieron ni persistieron valores secretos nuevos.

## Problema Original

Durante pruebas de seguridad se detecto que una orden podia referenciar un archivo local con datos delicados. El sistema estaba en `CyberLACE mode=monitor`, por lo que podia registrar o recomendar acciones, pero no bloqueaba necesariamente la ejecucion.

La brecha importante era esta:

- CyberLACE monitoreaba prompts, herramientas, memoria y salida instrumentada.
- Pero no interceptaba automaticamente cada `read file` interno de un proceso Codex ya lanzado.
- Si Codex arrancaba con acceso al workspace, podia leer un archivo sensible antes de que el backend lo detectara.

Por eso la solucion correcta no fue confiar en un hook posterior, sino impedir el arranque cuando el alcance del runtime no es seguro.

## Solucion Implementada

### 1. Hard-Gate de Documentos

Archivo principal:

`backend/cyberlace_document_guard.py`

Responsabilidad:

- Escanea texto de `requirement`.
- Escanea tareas del control-plane.
- Escanea directivas generadas antes de persistirlas/ejecutarlas.
- Extrae rutas locales referenciadas.
- Lee documentos de texto permitidos bajo repo/workspace.
- Escanea documentos del workspace antes de lanzar Codex.
- Niega rutas externas sensibles como home, SSH, `/etc`, etc.
- Falla cerrado cuando un documento no puede ser inspeccionado de forma segura.

Patrones de bloqueo:

- `password`
- `api_key`
- `private_key`
- `pin`
- `cvv`
- `bank_account`
- tarjetas con contexto financiero
- rutas externas sensibles
- documentos demasiado grandes o no escaneables cuando forman parte del alcance

Resultado cuando bloquea:

```json
{
  "runtimeAction": "QUARANTINE",
  "blocked": true,
  "blocksRuntime": true,
  "severity": "CRITICAL"
}
```

La evidencia se guarda sanitizada:

```json
{
  "sample": "[REDACTED]"
}
```

### 2. Integracion con Runtime

Archivo:

`backend/agent_runtime.py`

Cambios principales:

- Se invoca el hard-gate antes de iniciar una sesion Codex.
- Se invoca antes de preparar directiva del control-plane.
- Se invoca antes de construir el comando del worker.
- Se agrego estado `blocked` para bloqueo CyberLACE.
- El bloqueo deja `pid=null` y `command=[]`.
- Se registra failure y checkpoint.
- Los eventos visuales del bloqueo se emiten en background para no retrasar `/api/agent/session`.

Comportamiento esperado:

- `running` solo se usa con PID real o worker activo.
- `preparing` se usa para trabajo previo.
- Si CyberLACE bloquea, nunca se crea proceso Codex.

### 3. Guard Interno del Worker

Archivo:

`workers/codex_worker.py`

Se agrego una segunda defensa:

- El worker vuelve a ejecutar el scanner antes de crear el proceso hijo.
- Si detecta secreto en workspace, no crea child process.
- Resultado validado:

```json
{
  "completed": false,
  "childPid": null,
  "returncode": 126,
  "blocked": true,
  "resultFileExists": false
}
```

### 4. Entorno Seguro para Procesos Hijo

Archivo:

`orchestrator/safe_process_env.py`

Objetivo:

- No heredar el entorno completo del backend.
- Filtrar variables con nombres tipo `PASSWORD`, `TOKEN`, `API_KEY`, `SECRET`, `CREDENTIAL`, `DATABASE_URL`, `GITHUB`, `SSH`, etc.
- Permitir solo variables necesarias y metadatos `VISTA_AGENT_*`.

### 5. Sandbox Codex Seguro por Defecto

Antes:

- Default interno: `danger-full-access`.

Despues:

- Default interno: `workspace-write`.
- `danger-full-access` y `full-auto` se degradan salvo que existan flags explicitos de autorizacion.

Esto evita que Codex tenga acceso amplio por defecto.

### 6. Modal Visual de Bloqueo

Archivos:

- `frontend/src/App.jsx`
- `frontend/src/App.css`

Se agrego modal rojo critico para eventos CyberLACE:

- `cyberlace_document_blocked`
- `session_blocked`
- decisiones `BLOCK`, `QUARANTINE` o `HUMAN_REVIEW`

El modal informa que la accion fue negada y que Codex no se ejecutara aunque el usuario quiera continuar.

## Falsos Positivos Detectados

### Falso Positivo 1: `/BASE`

Durante la validacion amplia, el scanner interpreto una cadena como `/BASE` dentro de una directiva como si fuera una ruta absoluta externa.

Efecto:

- Bloqueaba pruebas internas del control-plane.
- Marcaba evidencia como:

```json
{
  "path": "external:BASE",
  "pattern": "external_path"
}
```

Causa:

- El regex de rutas detectaba `/BASE` como ruta absoluta.
- El repo contiene un path real con espacio: `BASE _METACOGNICION_COLOMBIA`.
- Al aparecer en texto renderizado, la ruta quedaba truncada y el guard la trataba como externa peligrosa.

Solucion:

- Se ajusto la heuristica de rutas externas.
- Ahora no bloquea prefijos truncados del repo como `/home/neurodriver/BASE _...`.
- Sigue bloqueando rutas realmente sensibles como:
  - `/home/neurodriver/.ssh/id_rsa`
  - `/etc/passwd`
  - archivos referenciados con credenciales

Validacion:

```json
[
  {
    "case": "ruta repo truncada con espacio",
    "blocked": false
  },
  {
    "case": "/home/neurodriver/.ssh/id_rsa",
    "blocked": true
  },
  {
    "case": "runtime/cyberlace/test_fixtures/fake_git_credentials.txt",
    "blocked": true
  }
]
```

### Falso Positivo 2: Artefacto Grande de Runtime

El scanner inicialmente bloqueo un artefacto historico de runtime porque superaba el limite de lectura, no porque se hubiera confirmado un secreto.

Causa:

- `MAX_DOCUMENT_SCAN_BYTES` era demasiado bajo para ciertos artefactos JSON/logs de runtime.

Solucion:

- Se elevo el limite controlado a `2_000_000` bytes.
- El archivo pudo escanearse realmente.
- Resultado posterior: no habia secreto confirmado, por lo tanto no bloqueo.

### Falso Positivo 3: Tests Obsoletos

La suite interna tenia expectativas antiguas:

- Esperaba `danger-full-access`.
- Esperaba estado `running` antes de PID real.
- Esperaba directivas/prompt listos sin esperar background.

Eso ya no es correcto con la reparacion.

Nuevo comportamiento seguro:

- Codex default: `workspace-write`.
- Estado previo: `preparing`.
- `running` solo con PID real.
- Sesion async puede tener `prompt=""` y `command=[]` mientras prepara.

Se actualizaron tests para validar la politica segura actual, no el comportamiento inseguro anterior.

## Harness End-to-End

Script:

`orchestrator/e2e_gate_harness.py`

### Que Es

Es el script interno de validacion end-to-end por proyecto. No crea proyectos nuevos. Toma un proyecto existente bajo `workspace/projects/<slug>` y cruza varios gates del ecosistema.

Comando tipico:

```bash
python3 -B orchestrator/e2e_gate_harness.py \
  --workspace . \
  --project sesion-20260518014728-jeego-en-3d \
  --base-url http://127.0.0.1:5001 \
  --cycles 1 \
  --verbose
```

### Que Comprueba

Nodos principales:

1. `pytest_available`
   - Confirma que pytest existe.

2. `pytest_lace_unit`
   - Corre pruebas unitarias de LACE.

3. `pytest_lace_control_gate`
   - Verifica que el gate LACE solo permite cierre con ciclos validos.

4. `lace_log_readonly`
   - Lee `LACE_LOG.md`.
   - Valida ciclos LACE requeridos.

5. `runtime_state_after_gate`
   - Revisa `project_state.json`.
   - Revisa `task_queue.json`.

6. `backend_health`
   - Llama al backend por HTTP.

7. `scanner_gate`
   - Ejecuta scanner interno via `orchestrator/agent_tools.py`.

8. `scanner_artifact_gate`
   - Verifica el artefacto generado por scanner.

9. `integrity_gate`
   - Ejecuta integridad de archivos.

10. `integrity_artifact_gate`
   - Verifica que el reporte de integridad no tenga findings.

11. `findings_gate`
   - Ejecuta observer/findings.

12. `findings_artifact_gate`
   - Comprueba que no queden findings activos.

13. `sandbox_http_gate`
   - Lee `runtime/sandbox.json`.
   - Hace HTTP real al sandbox.

14. `no_pytest_process_left`
   - Confirma que no quedan procesos pytest colgados.

15. `pytest_cache_cleanup`
   - Limpia `.pytest_cache`.

### Como Mide

Cada nodo registra:

- comando ejecutado
- hora de entrada
- hora de salida
- duracion
- timeout
- exit code
- stdout
- stderr
- evidencia parseada
- estado `ok`

El resultado final contiene:

```json
{
  "nodesTotal": 15,
  "nodesPassed": 15,
  "nodesFailed": 0,
  "timedOut": 0,
  "passed": true
}
```

### Reportes

Genera:

`runtime/e2e_gate_harness/latest.json`

Y reporte timestamp:

`runtime/e2e_gate_harness/e2e-gate-harness-<proyecto>-<fecha>.json`

## Resultado del Harness

Primera corrida:

- `13/15`
- Fallaron:
  - `findings_artifact_gate`
  - `sandbox_http_gate`

Causa:

- El sandbox del proyecto default estaba apagado.
- Observer tenia un finding activo: "Sandbox real incompleto despues de scanner aprobado."

Correccion:

- Se arranco sandbox del proyecto default.
- Se repitio el harness.

Resultado final:

- `15/15 OK`
- `nodesFailed=0`
- `timedOut=0`

Reporte final:

`runtime/e2e_gate_harness/e2e-gate-harness-sesion-20260518014728-jeego-en-3d-20260525T032247Z.json`

## Proyectos Protegidos

Proyectos:

- `workspace/projects/sesion-20260524210420`
- `workspace/projects/sesion-20260524233805`

Ambos fueron revisados por API:

- aparecen en `/api/agent/projects`
- abren archivos por `/api/projects/<slug>/file`
- `runtime-truth` responde
- no tienen worker vivo sin PID
- no requieren release zombie

Tambien se intento correr el harness contra ambos.

Resultado:

- Ambos paran en `lace_log_readonly`.
- Causa: `0/10` ciclos LACE validos.
- Esto no es caida de backend ni de runtime.
- Es una condicion de madurez/cierre LACE del proyecto.

## Validaciones Ejecutadas

Validaciones principales:

```bash
python3 -B -m py_compile backend/app.py backend/agent_runtime.py backend/cyberlace_document_guard.py orchestrator/*.py workers/codex_worker.py
npm --prefix frontend run build
OPEN_BROWSER=0 ./start.sh restart
python3 -B -m pytest backend/test_cyberlace_integration.py backend/test_cyberlace_routes.py backend/test_cyberlace_agent_runtime_hooks.py backend/test_runtime_boundary.py backend/test_runtime_sandbox.py backend/test_tool_invocation_policy.py backend/test_agent_runtime_habla.py backend/test_agent_runtime_lace.py backend/test_control_plane_visual_bridge.py -q
python3 -B orchestrator/e2e_gate_harness.py --workspace . --base-url http://127.0.0.1:5001 --cycles 1 --verbose
```

Resultados:

- Pytest runtime/seguridad: `97 passed`.
- Harness default: `15/15 OK`.
- Build frontend: OK.
- Backend health: OK.
- CyberLACE health: OK, `mode=monitor`.
- Socket.IO polling: OK, `upgrades=[]`.

## Checkpoints y Reportes Relacionados

Reparacion runtime:

- `runtime/artifacts/habla_runtime_repair_report_20260525T011758Z.md`
- `runtime/checkpoints/habla-runtime-repair-final-20260525T011758Z.json`

Hard gate CyberLACE:

- `runtime/artifacts/cyberlace_document_hard_gate_report_20260525T024358Z.md`
- `runtime/checkpoints/cyberlace-document-hard-gate-final-20260525T024358Z.json`

Harness/integridad:

- `runtime/artifacts/internal_harness_integrity_final_20260525T032417Z.md`
- `runtime/checkpoints/internal-harness-integrity-final-20260525T032417Z.json`
- `runtime/e2e_gate_harness/latest.json`

Redaccion de evidencia historica:

- `runtime/checkpoints/cyberlace-evidence-redaction-20260525T015742Z.json`
- `runtime/backups/cyberlace_redaction/20260525T015742Z`

## Estado Final

Estado final validado:

- UI carga.
- Backend responde.
- Socket.IO usa polling controlado.
- No hay WebSocket 500.
- `/api/agent/session` responde en menos de 5 segundos.
- CyberLACE global sigue en `monitor`.
- Hard-gate de documentos bloquea siempre ante secreto.
- Codex no arranca si hay secreto.
- `running` solo ocurre con PID real.
- No quedan zombis.
- Entorno del worker queda filtrado.
- Sandbox interno Codex por defecto es `workspace-write`.
- Modal rojo de CyberLACE queda integrado.

## Conclusión

La reparacion no reemplazo arquitectura ni activo `enforce` global. Se agrego una puerta obligatoria de seguridad para documentos y workspace antes de lanzar Codex. Esto cierra el caso critico donde un archivo sensible podia ser procesado por un worker ya arrancado.

Los falsos positivos encontrados fueron documentados y corregidos sin debilitar la proteccion real. El harness interno end-to-end fue ejecutado, corregido y validado con `15/15` nodos OK en el proyecto default. La suite interna de runtime/seguridad quedo en `97 passed`.
