# Prompts de validacion GitHub - Juego 3D de drones

Fecha UTC: 2026-05-24T19:11:28Z
Proyecto objetivo: `workspace/projects/sesion-20260518014728-jeego-en-3d`
Objetivo: ejecutar tres pruebas publicables sobre el juego 3D, en dificultad medio, dificil y extradificil, dejando evidencia persistente en disco para README, release notes o PR de GitHub.

## Instrucciones comunes para los tres prompts

Usar siempre el proyecto existente `sesion-20260518014728-jeego-en-3d`. No crear un proyecto nuevo. No tratar esto como una sola sesion larga: cada prompt debe ejecutarse como una tarea independiente, verificable y reanudable.

Cada ejecucion debe dejar evidencia en:

```text
workspace/projects/sesion-20260518014728-jeego-en-3d/runtime/task_history.jsonl
workspace/projects/sesion-20260518014728-jeego-en-3d/runtime/checkpoints/
workspace/projects/sesion-20260518014728-jeego-en-3d/runtime/artifacts/github_validation/<case-id>/
```

Evidencia minima por caso:

```text
prompt.txt
implementation_summary.md
task_result.json
validation_commands.txt
browser_render_smoke.json
browser_render_smoke.png
files_touched.txt
```

Validaciones minimas obligatorias por caso:

```bash
node --check workspace/projects/sesion-20260518014728-jeego-en-3d/frontend/app.js
python3 -B backend/browser_render_smoke.py --workspace workspace/projects/sesion-20260518014728-jeego-en-3d --frontend frontend --mode smoke --light day
python3 orchestrator/agent_tools.py --base-url http://127.0.0.1:5001 --timeout-seconds 8 health
```

Si se ejecuta scanner/integrity desde herramientas internas, registrar `statusCode`, `ok`, `reportPath` o el blocker real. No inventar cierre si una validacion falla.

---

## PROMPT 1 - MODO MEDIO

```text
MODO MEDIO - VALIDACION GITHUB JUEGO 3D DRONES

Proyecto existente: workspace/projects/sesion-20260518014728-jeego-en-3d
No crear proyecto nuevo. Ejecutar como una sola tarea acotada, verificable y reanudable.

Objetivo:
Mejorar el juego 3D de drones con una mision media de patrullaje verificable: el dron policia azul debe recorrer 3 checkpoints urbanos visibles, mantener el HUD existente y publicar evidencia clara de progreso sin cambiar la arquitectura del runtime ni tocar el control-plane.

Alcance permitido:
- frontend/index.html
- frontend/styles.css
- frontend/app.js
- docs/github_validation/CASE-MEDIO.md o runtime/artifacts/github_validation/CASE-MEDIO/*

Requisitos funcionales:
1. Agregar 3 checkpoints visibles en la ciudad 3D con estados pendiente, activo y completado.
2. El HUD debe mostrar: checkpoint actual, total completados, distancia al checkpoint y estado de patrulla.
3. Al completar los 3 checkpoints, mostrar una senal visible: "validacion medio completada".
4. Mantener la senal existente "patrulla lista".
5. No romper DQN, ciudad procedural, rockets, combate, briefing tactico ni modo smoke explicito.
6. El modo smoke no puede inferirse por palabras sueltas; toda validacion debe usar configuracion explicita.

Evidencia obligatoria:
- Crear carpeta `runtime/artifacts/github_validation/CASE-MEDIO/` dentro del proyecto.
- Guardar `prompt.txt` con este prompt.
- Guardar `implementation_summary.md` con cambios reales y archivos tocados.
- Guardar `task_result.json` con completed, files_created, files_modified, validation_ran, validation_passed, blockers y next_recommendation.
- Ejecutar browser smoke y conservar `browser_render_smoke.json` y `browser_render_smoke.png`.

Validaciones obligatorias:
- node --check frontend/app.js
- python3 -B ../../../../backend/browser_render_smoke.py --workspace . --frontend frontend --mode smoke --light day
- Verificar por busqueda textual que existen las senales: "validacion medio completada", "checkpoint", "patrulla lista".

Contrato de salida:
Devolver TaskResult estricto: objetivo cumplido o no, archivos creados, archivos modificados, validaciones ejecutadas, resultado real, blockers y recomendacion siguiente.
```

---

## PROMPT 2 - MODO DIFICIL

```text
MODO DIFICIL - VALIDACION GITHUB JUEGO 3D DRONES

Proyecto existente: workspace/projects/sesion-20260518014728-jeego-en-3d
No crear proyecto nuevo. Ejecutar como tarea independiente; no continuar desde memoria implicita de otra corrida.

Objetivo:
Agregar una mision dificil de persecucion tactica al juego 3D: el dron policia azul debe identificar una placa objetivo, mantener seguimiento visual, sobrevivir a amenaza del dron rojo y registrar evidencia de captura o perdida sin alterar el control-plane.

Alcance permitido:
- frontend/index.html
- frontend/styles.css
- frontend/app.js
- docs/github_validation/CASE-DIFICIL.md o runtime/artifacts/github_validation/CASE-DIFICIL/*

Requisitos funcionales:
1. Agregar un objetivo de persecucion asociado a la placa buscada existente del juego.
2. Mostrar en el HUD o panel tactico: placa objetivo, nivel de amenaza, lock visual, distancia y estado persecucion.
3. El dron rojo debe aumentar presion visual o tactica durante la persecucion sin romper el render WebGL.
4. Agregar estados claros: "buscando", "lock activo", "captura confirmada", "objetivo perdido".
5. Al completar la persecucion, publicar senal visible: "validacion dificil completada".
6. Mantener evidencia existente de patrulla, combate, briefing, DQN y modo smoke explicito.
7. No editar runtime/project_state.json, task_queue.json ni historial salvo artefactos de evidencia de esta tarea.

Evidencia obligatoria:
- Crear carpeta `runtime/artifacts/github_validation/CASE-DIFICIL/` dentro del proyecto.
- Guardar `prompt.txt`, `implementation_summary.md`, `task_result.json`, `validation_commands.txt`, `files_touched.txt`.
- Guardar captura y JSON de browser smoke.
- Registrar un mini reporte Markdown que explique que se ve en pantalla y como comprobarlo desde GitHub.

Validaciones obligatorias:
- node --check frontend/app.js
- python3 -B ../../../../backend/browser_render_smoke.py --workspace . --frontend frontend --mode smoke --light day
- Busqueda textual de: "validacion dificil completada", "lock activo", "captura confirmada", "objetivo perdido".
- Si algun endpoint interno falla por timeout, registrar el blocker real y no marcar scanner/integrity como aprobado.

Contrato de salida:
Devolver TaskResult estricto con evidencia real. Si no hay captura o smoke OK, la tarea no puede cerrarse como completada.
```

---

## PROMPT 3 - MODO EXTRADIFICIL

```text
MODO EXTRADIFICIL - VALIDACION GITHUB JUEGO 3D DRONES

Proyecto existente: workspace/projects/sesion-20260518014728-jeego-en-3d
No crear proyecto nuevo. Ejecutar como tarea long-run dividida internamente en subtareas pequenas si el runtime lo permite. No depender de memoria de chat; todo avance debe quedar en disco.

Objetivo:
Crear una validacion extradificil de mision multi-fase en el juego 3D: patrulla, identificacion, persecucion, combate, rescate/evasion y cierre con reporte visual publicable. Debe probar que el juego soporta un flujo complejo sin romper WebGL, HUD, DQN, ciudad procedural, Observer, scanner ni sandbox.

Alcance permitido:
- frontend/index.html
- frontend/styles.css
- frontend/app.js
- docs/github_validation/CASE-EXTRADIFICIL.md
- runtime/artifacts/github_validation/CASE-EXTRADIFICIL/*

Requisitos funcionales:
1. Implementar una mision multi-fase con estas fases visibles: "patrulla", "identificacion", "persecucion", "combate", "rescate", "cierre".
2. Cada fase debe tener estado en DOM/HUD y evidencia legible para captura: fase actual, objetivo, amenaza, recompensa/penalidad y resultado.
3. Agregar un panel compacto de reporte final dentro del juego con: fases completadas, dano del dron policia, lock enemigo, captura/rescate y resultado final.
4. Al cerrar todas las fases, mostrar senal visible exacta: "validacion extradificil completada".
5. Mantener el render WebGL activo y no disminuir la escena a una pantalla estatica o mock.
6. No blanquear workspace, no crear proyecto nuevo, no eliminar artefactos previos, no sobrescribir evidencia de otros casos.
7. Si se modifica logica compartida, justificarlo en `implementation_summary.md` y dejar validacion especifica.

Evidencia obligatoria:
- Crear carpeta `runtime/artifacts/github_validation/CASE-EXTRADIFICIL/` dentro del proyecto.
- Persistir `prompt.txt`, `implementation_summary.md`, `task_result.json`, `validation_commands.txt`, `files_touched.txt`.
- Persistir `github_publish_summary.md` con un texto listo para pegar en README/PR: que se probo, como se probo, comandos y resultado.
- Persistir `browser_render_smoke.json` y `browser_render_smoke.png`.
- Si se puede, ejecutar scanner e integrity con herramientas internas y registrar salida compacta real. Si fallan, registrar statusCode/blocker.

Validaciones obligatorias:
- node --check frontend/app.js
- python3 -B ../../../../backend/browser_render_smoke.py --workspace . --frontend frontend --mode smoke --light day
- Verificar textual/DOM de: "patrulla", "identificacion", "persecucion", "combate", "rescate", "cierre", "validacion extradificil completada".
- python3 ../../../../orchestrator/agent_tools.py --base-url http://127.0.0.1:5001 --timeout-seconds 8 health

Criterio de cierre:
Solo marcar completed si hay evidencia en disco, captura smoke, validaciones ejecutadas y TaskResult persistido. Si una fase queda incompleta, declarar blocker y recomendacion siguiente.

Contrato de salida:
Devolver TaskResult estricto y un resumen publicable para GitHub con rutas de artefactos.
```
