# Ciclo 04

- Estado: completed
- Foco: documentación
- Valido para cierre LACE: no
- Problemas registrados: si
- Mejora registrada: si
- Validacion registrada: si

## Resumen
Ciclo 04 cerró observaciones pero todavía no supera toda la validación LACE.

[CICLO-4 PROBLEMAS]
- Ver docs/lace_cycles/ciclo-04.md para diagnostico completo.

[CICLO-4 MEJORA]
- Director de dificultad observable conectado a amenaza, energia y progreso.

[CICLO-4 COMPLETADO]
- Documento canonico creado y validado; node --check OK, pytest OK 2 passed, browser_render_smoke OK con render_mode=webgl y central_non_dark_ratio=0.9999.

[CICLO-5 - RUNTIME-20260602144656-001]
THOUGHT: Revalidar la app estatica runnable y los contratos minimos existentes sin editar archivos de producto ni archivos internos propiedad del control plane.
ACTION: Ejecutar validaciones de filesystem, sintaxis, contratos, pytest, browser smoke, sandbox HTTP, findings y scanner canonico.
OBSERVATION real: Los entregables frontend existen, node --check OK, py_compile OK, StateStore lee runtime/project_state.json y runtime/task_queue.json sin modificarlos, pytest OK 2 passed, browser_render_smoke OK con render_mode=webgl, distance_text="3 m", speed_text="4.8 m/s", central_non_dark_ratio=0.9999 y sandbox HTTP 200 en http://127.0.0.1:5603/.
Coincide con OBSERVATION esperada: SI para producto runnable y contratos locales.
Evidencia forense: integrity devolvio ok=false por timeout; findings devolvio statusCode=200 ok=true reportPath=runtime/artifacts/observer_findings.json con activeFindings=63 de fuente integrity en docs/habla-session.md; scanner devolvio statusCode=423 ok=false error=project_locked, sin reportPath nuevo.
Pendiente control-plane: liberar lock del scanner, resolver o aceptar la divergencia de docs/habla-session.md en baseline/ledger y relanzar scanner canonico antes de cierre completed=true.

[REVALIDACION ACOTADA - RUNTIME-20260602152017-001]
THOUGHT: Ejecutar la tarea acotada como worker sobre el proyecto existente, sin reconstruir prompts bloqueados, sin blanquear y sin editar archivos control-plane.
ACTION: Leer memoria, registrar mapa visual con bridge, verificar frontend/contratos existentes, ejecutar validaciones locales, browser smoke, sandbox HTTP y herramientas internas.
OBSERVATION real: No se modificaron archivos de producto porque los entregables ya existen y cumplen la orden runnable. Existencia de frontend OK; existencia de schemas/orchestrator/runtime state OK en modo lectura; node --check OK; py_compile OK; schemas JSON OK; StateStore leyo runtime/project_state.json y runtime/task_queue.json sin guardarlos; pytest OK 2 passed; browser_render_smoke OK con render_mode=webgl, distance_text="3 m", speed_text="4.8 m/s", event_text="salto predictivo ante riesgo", central_non_dark_ratio=0.9999 y screenshot no negro.
Evidencia runtime: sandbox.json reporto running=true, ready=true, embedUrl=http://127.0.0.1:5603/ y HTTP 200. health OK statusCode=200. observer-status OK state=waiting_worker. broom before_task OK reportPath=runtime/artifacts/broom/20260602T152624.452086Z-RUNTIME-20260602152017-001-before_task.json. broom after_task OK reportPath=runtime/artifacts/broom/20260602T153354.846089Z-RUNTIME-20260602152017-001-after_task.json.
Evidencia forense: integrity devolvio statusCode=0 ok=false error=timeout report=null; findings devolvio statusCode=200 ok=true reportPath=runtime/artifacts/observer_findings.json con activeFindings=0; scanner devolvio statusCode=423 ok=false error=project_locked report=null.
Pendiente control-plane: no declarar completed=true hasta resolver scanner project_locked y decidir si el timeout de integrity es aceptable o requiere retry de herramienta. No se editaron runtime/project_state.json, runtime/task_queue.json, runtime/task_history.jsonl, runtime/failures.jsonl, runtime/checkpoints/, runtime/directives/ ni runtime/logs/.

[AJUSTE VISUAL ACOTADO - RUNTIME-20260602160033-001]
THOUGHT: El corredor avanza sobre el eje X y el actor 3D esta modelado mirando hacia +Z; por eso se ve de frente en vez de correr de perfil por la ruta.
ACTION: Fijar una rotacion base de 90 grados en Y para que el rostro del actor apunte al eje del corredor y mantener solo una oscilacion pequena de carrera.
OBSERVATION esperada: El smoke browser debe seguir renderizando WebGL y el actor debe quedar de perfil alineado con el corredor real.
OBSERVATION real: `frontend/app.js` define `HERO_CORRIDOR_YAW = Math.PI * 0.5` y usa esa base en `this.player.rotation.y`. Browser smoke paso con `ok=true`, `render_mode=webgl`, `distance_text="2 m"`, `speed_text="4.8 m/s"`, `event_text="salto predictivo ante riesgo"` y `central_non_dark_ratio=0.9997`. La captura `runtime/artifacts/browser_render_smoke.png` muestra el actor en perfil sobre el corredor.
Coincide con OBSERVATION esperada: SI para producto visual y sandbox.
Problemas resueltos: el actor 3D ya no queda mirando de frente a la pantalla; el perfil queda alineado al eje X del corredor.
Validaciones ejecutadas: existencia de frontend OK; `node --check frontend/app.js` OK; `python3 -m pytest -q` OK 2 passed; browser smoke OK; comprobacion estatica de `HERO_CORRIDOR_YAW` OK; sandbox HTTP OK 200 en `http://127.0.0.1:5603/`; health OK; observer-status OK; broom before_task OK; broom after_task OK.
Evidencia forense: `integrity` post-cambio devolvio `statusCode=0`, `ok=false`, `error=timeout`, `report=null`. `findings` devolvio `statusCode=200`, `activeFindings=3`: dos sobre `frontend/app.js` por escritura no registrada en baseline/ledger y uno previo sobre `docs/habla-session.md`. El intento seguro de registrar `frontend/app.js` por `/api/projects/sesion-20260601004224/file` devolvio `statusCode=423`, `error=project_locked`, `reason=agent_session_active`, `sessionId=agent-74f6120cb7`. `scanner` devolvio `statusCode=423`, `error=project_locked`, `report=null`.
MEMORIA EPISODICA: funciono corregir la orientacion con una constante de yaw verificable sin rehacer la escena. No funciono registrar la escritura por endpoint mientras el proyecto estaba bloqueado por la sesion activa. Evitar declarar cierre completed=true cuando scanner/integrity/findings no quedan limpios.
Pendiente control-plane: liberar lock de la sesion, reintentar registro/ledger o aceptar la escritura esperada de `frontend/app.js`, relanzar `integrity`, `findings` y `scanner`; solo entonces cerrar sin blockers.
