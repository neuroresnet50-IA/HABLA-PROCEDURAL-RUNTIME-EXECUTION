# Runtime Forensic Investigation After CyberLACE

Fecha UTC: 2026-05-25T00:13:43.414507+00:00

## Alcance
Investigacion forense del runtime HABLA/Codex despues de reportes de UI bloqueada, botones inaccesibles, login/modal irregular, lentitud general y `agent_session_start_timeout`.

No se aplicaron reparaciones de codigo en esta fase. No se reinicio servidor y no se mataron procesos.

## Prompt Usado Para Agentes
```text
MODO FORENSE HABLA/CYBERLACE - NO EDITAR CODIGO

Objetivo: investigar por que el runtime HABLA/Codex quedo inestable tras la integracion CyberLACE: UI bloqueada, botones inaccesibles, login/modal irregular, slowness, agent_session_start_timeout y sesiones que quedan running sin PID.

Reglas:
- No modificar archivos.
- No crear proyecto nuevo.
- No reiniciar servidor.
- No matar procesos.
- Leer codigo, logs y runtime.
- Separar hechos, inferencias y sospechas.
- Citar archivos, funciones, endpoints, logs y comandos de verificacion.
- Identificar cambios relacionados con CyberLACE y cambios no relacionados que puedan haber roto runtime.
- Entregar: causa probable, evidencia, riesgo, validacion sugerida y reparacion minima no destructiva.
```

## Hallazgos Principales

### 1. socketio_websocket_werkzeug_regression
Severidad: critical
Tipo: confirmed_regression

Evidencia:
- frontend now requests transports [websocket, polling] in App.jsx and AgentStudio/CodeWorkbench paths.
- backend SocketIO was changed from polling-only/allow_upgrades=false to default upgrades.
- .runtime/logs/backend.log shows repeated GET /socket.io/?EIO=4&transport=websocket HTTP 500.
- Traceback: AssertionError: write() before start_response from werkzeug.serving.
- Manual curl to /socket.io/?EIO=4&transport=websocket returned Invalid websocket upgrade / HTTP 400.

Impacto: browser reconnect loops and failed websocket upgrades add backend load, create CLOSE-WAIT sockets and make critical HTTP endpoints slow or timeout.

Reparacion minima: Temporarily return backend/frontend Socket.IO to polling-only with controlled intervals, or switch backend to a WebSocket-capable async server before enabling websocket transport.

### 2. agent_session_start_sync_work_timeout
Severidad: critical
Tipo: confirmed_design_risk

Evidencia:
- frontend/src/components/AgentStudio.jsx aborts POST /api/agent/session after 45s and reports agent_session_start_timeout.
- backend/app.py POST /api/agent/session calls agent_runtime.start_session(), then sync_runtime_graph(save_state=True), then list_agent_projects_snapshot() before response.
- Subagent backend found start_session control-plane preparation includes complexity, HABLA/LACE, runtime/directive generation before thread response.
- Observed session agent-00257041a0 was created but UI saw timeout.

Impacto: a session can exist server-side while the browser thinks start failed, leaving the UI inconsistent and causing duplicate attempts.

Reparacion minima: Make POST /api/agent/session return fast with session=preparing; run graph sync, project snapshot refresh and heavy preparation in background or expose phase metrics.

### 3. control_plane_running_without_pid
Severidad: high
Tipo: confirmed_state_model_bug

Evidencia:
- backend/agent_runtime.py _run_control_plane_session sets session.status=running before any worker process starts.
- PID only attaches when execute_task_with_details invokes on_process_start.
- Observed session agent-00257041a0 status became failed with pid=null, returncode=123, errorCode=agent_start_timeout.
- terminal log only has [agent-guard] La sesion no produjo salida de terminal ni eventos reales del bridge en el tiempo esperado.

Impacto: UI and lock logic can treat a pre-worker phase as a live running agent even when there is no Codex process.

Reparacion minima: Use status=preparing until process starts; only expose running after pid/worker_started_at or first output/event.

### 4. zombie_project_state_locks_editor
Severidad: high
Tipo: confirmed_state_persistence_bug

Evidencia:
- workspace/projects/sesion-20260524233805/runtime/project_state.json has status=running and current_task_id.
- workspace/projects/sesion-20260524233805/runtime/task_queue.json still has the task status=pending.
- backend/app.py build_editor_lock_state locks editor for state_status in queued/starting/running even without live session.
- runtime-truth code can identify stale state as verdict=zombie, but lock path does not use it first.

Impacto: project/editor can remain blocked after session guard failure, making buttons/editor appear broken.

Reparacion minima: Add reconciliation for guard failure and startup failure; if runtime-truth says zombie, unlock editor and offer safe cleanup action.

### 5. internal_agent_tools_self_http_dependency
Severidad: high
Tipo: confirmed_bottleneck_risk

Evidencia:
- orchestrator/tool_invocation_policy.py run_preflight invokes observer-status over HTTP to the same backend.
- python3 orchestrator/agent_tools.py --base-url http://127.0.0.1:5001 --timeout-seconds 5 health returned 200.
- observer-status timed out after 5s during backend load.
- No tool_invocation_policy.jsonl was written for the failed session, suggesting preflight did not complete before guard timeout.

Impacto: control-plane worker startup depends on the same saturated HTTP server, so load can prevent the worker from reaching first output.

Reparacion minima: Preflight must be non-blocking/bounded and should emit terminal progress before self-HTTP calls; use direct service calls when in-process.

### 6. cyberlace_monitor_not_direct_blocker_enforce_risk
Severidad: medium
Tipo: confirmed_security_mode_risk

Evidencia:
- CyberLACE current mode reported as monitor; monitor maps runtimeAction to ALLOW.
- CyberLACE enforce hooks can block prompt/tool/output in agent_runtime before worker launch.
- read_recent_cyberlace_evidence reads full JSONL file via read_text().splitlines() before tailing; currently small but grows over time.
- CyberLACE detected timestamp-like slug 20260524233805 as credit_card_like in monitor evidence.

Impacto: monitor is not the direct blocker now, but enforce/global evidence reading/false positives can cause future startup or diagnostic confusion.

Reparacion minima: Keep global CYBERLACE_MODE=monitor for UI; run enforce only in dedicated script/task. Optimize evidence tail and exclude timestamps from financial pattern.

### 7. auth_login_separate_audit_needed
Severidad: medium
Tipo: separate_risk

Evidencia:
- WelcomeAuthGate DEFAULT_LOADING_MS is now 1200ms and not the current blocker.
- auth_routes.py has default admin/admin enabled by env defaults, a separate security and login behavior change.
- No direct CyberLACE hook was found in auth routes.

Impacto: login behavior may differ from the original system, but current runtime slowness is more strongly explained by socket/HTTP/control-plane issues.

Reparacion minima: Audit auth separately after runtime stability; disable default admin outside dev.

## Orden De Reparacion Recomendado
- 1. Immediate stabilization: revert Socket.IO to polling-only or configure WebSocket-capable server; stop 500 upgrade loop.
- 2. Make /api/agent/session respond fast; move sync_runtime_graph and project snapshot after response/background.
- 3. Add control-plane preparing/running separation and pid-aware session status.
- 4. Add zombie-state reconciliation: session guard failures must update project_state/task_queue/failures.
- 5. Make internal tool preflight non-blocking or direct in-process; emit progress before preflight.
- 6. Optimize CyberLACE evidence tail and keep enforce out of global UI mode.
- 7. Audit auth/default admin separately.

## Validaciones Ejecutadas
- `ps -eo ...`: backend PID 1955912 observed around 104% CPU; chrome/code processes also active
- `ss -tanp | grep :5001`: many CLOSE-WAIT and ESTABLISHED sockets on backend 5001
- `tail .runtime/logs/backend.log`: repeated websocket HTTP 500 with AssertionError write() before start_response
- `curl /api/agent/sessions`: session agent-00257041a0 failed with errorCode=agent_start_timeout, pid=null, returncode=123
- `python3 orchestrator/agent_tools.py health`: statusCode=200
- `python3 orchestrator/agent_tools.py observer-status --timeout 5`: TimeoutError
- `uniform endpoint probe timeout=3s`: health/observer/status/agent/projects/cyberlace health all timed out under load

## Conclusion
CyberLACE en modo `monitor` no aparece como bloqueador directo. El dano operativo actual se explica mejor por una cadena de regresiones y riesgos: WebSocket incompatible con Werkzeug, request de inicio de sesion demasiado pesado, estado persistido zombi, preflight interno por HTTP contra el mismo backend saturado y polling recurrente de UI.

La reparacion debe empezar por estabilizar transporte/socket y devolver rapido `/api/agent/session`; despues reconciliar estados zombis y endurecer CyberLACE sin poner `enforce` global.
