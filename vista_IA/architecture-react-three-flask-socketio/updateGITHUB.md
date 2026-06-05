# updateGITHUB.md

Guia de relevo para reiniciar el PC y permitir que otro agente retome sin empezar desde cero.

## Estado de publicacion

- Repositorio local: `/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio`
- Remote GitHub: `https://github.com/neuroresnet50-IA/HABLA-PROCEDURAL-RUNTIME-EXECUTION.git`
- Repo GitHub: `https://github.com/neuroresnet50-IA/HABLA-PROCEDURAL-RUNTIME-EXECUTION`
- PR de publicacion: `https://github.com/neuroresnet50-IA/HABLA-PROCEDURAL-RUNTIME-EXECUTION/pull/1`
- Rama de trabajo: `codex/publish-complete-runtime-project`
- Base del PR: `main`
- Ultimo commit ya empujado antes de este relevo: `e36fc25b` (`Publish latest harness engineering updates`)
- Repositorio verificado como publico: `visibility=PUBLIC`, `isPrivate=false`

## Objetivo actual

Subir a GitHub el segundo corte de cambios que aparecio despues del commit `e36fc25b`, incluyendo modificaciones del harness engineering interno, backend, frontend, orchestrator, runtime y evidencias generadas por el sistema vivo.

Este archivo es el punto de arranque para el siguiente agente despues de reiniciar el PC.

## Abrir el repo despues de reiniciar

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"
git status --short --branch
git branch --show-current
git remote -v
```

El resultado esperado es estar en:

```text
codex/publish-complete-runtime-project
```

con remote:

```text
origin https://github.com/neuroresnet50-IA/HABLA-PROCEDURAL-RUNTIME-EXECUTION.git
```

## Archivos de contexto obligatorios

Antes de tocar codigo o subir cambios, leer:

```bash
sed -n '1,240p' AGENTS.md
sed -n '1,240p' updateGITHUB.md
sed -n '1,220p' ULTIMO_CONTEXTO_CODEX.md
tail -n 180 recuperacioncontexto.md
sed -n '1,220p' PLANS.md
```

Si falta alguno, registrar el blocker en `recuperacioncontexto.md`.

## Metricas y validaciones ya ejecutadas en este corte

Herramienta interna:

```text
python3 orchestrator/agent_tools.py health
statusCode=200
ok=true
service=HABLA Observer IA
```

Python:

```text
find backend orchestrator workers tools -name '*.py' -print | sort | xargs python3 -B -m py_compile
resultado=OK
```

Pytest enfocado backend/harness:

```text
python3 -m pytest backend/test_complexity_audit_kernel.py backend/test_agent_runtime_habla.py backend/test_control_plane_visual_bridge.py backend/test_cyberlace_agent_runtime_hooks.py backend/test_cyberlace_routes.py backend/test_lace_automejora_kernel.py backend/test_app_lint.py -q
resultado=123 passed in 5.71s
```

Frontend build:

```text
cd frontend
npm run build
resultado=OK
nota=Vite warning conocido: chunk mayor a 500 kB
assets observados=index-DCoz45xZ.css, index-DYP9buiQ.js
```

Frontend test:

```text
cd frontend
npm test
resultado=OK
salida=agentClosureCertificate tests passed
```

Escaneo de archivos grandes:

```text
find . -path ./.git -prune -o -path ./.venv -prune -o -path ./frontend/node_modules -prune -o -path ./backups -prune -o -type f -size +95M -print
resultado=OK, sin salida
```

Escaneo estricto de secretos:

```text
rg --pcre2 -n "((?<![A-Za-z0-9])sk-(?:proj-)?[A-Za-z0-9_-]{32,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)" . -g '!/.git/**' -g '!/.venv/**' -g '!frontend/node_modules/**' -g '!backups/**' -g '!runtime/*.pid' -g '!=*'
resultado=OK, sin coincidencias
nota=exit code 1 de rg significa sin matches
```

## Cambios locales pendientes observados

Despues del push `e36fc25b`, el runtime/desarrollo genero nuevo delta en estas zonas:

- `backend/agent_runtime.py`
- `backend/app.py`
- `backend/cyberlace_document_guard.py`
- `backend/editor_state.json`
- `backend/test_app_lint.py`
- `backend/test_control_plane_visual_bridge.py`
- `backend/test_cyberlace_agent_runtime_hooks.py`
- `frontend/src/App.css`
- `frontend/src/App.jsx`
- `frontend/src/components/AgentStudio.jsx`
- `frontend/src/components/RuntimeDashboardSidebar.jsx`
- `frontend/src/components/agentClosureCertificate.js`
- `frontend/src/components/agentClosureCertificate.test.js`
- `orchestrator/recovery.py`
- `orchestrator/runtime_task_cleaner.py`
- `runtime/continuity_probe/...`
- `workspace/projects/continuity-code-pf-001-2/...`
- `workspace/projects/sesion-20260604162627/...`
- `recuperacioncontexto.md`
- `ULTIMO_CONTEXTO_CODEX.md`
- `runtime/task_history.jsonl`
- `updateGITHUB.md`

Hay muchos artefactos runtime/checkpoints/directives/logs nuevos de LACE, CyberLACE, closure repair, baseline vault, broom, tool invocations y continuity probe.

## Rutas que NO se deben subir desde este subrepo

Si aparece esto como untracked, dejarlo fuera:

```text
../../conector MCP/
```

Motivo: esta fuera del subrepo de publicacion.

Tambien deben quedar fuera por `.gitignore` o por politica:

```text
.runtime/
.venv/
frontend/node_modules/
backups/
runtime/*.pid
=*
```

## Problema de sandbox local

En esta maquina varios comandos fallaron con:

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

Cuando eso ocurra, repetir el comando con permiso escalado puntual. No inventar resultados. Registrar el blocker si no se puede validar.

## Flujo exacto para terminar el push

Desde la raiz del subrepo:

```bash
git add -A .
git diff --cached --check
```

Si `git diff --cached --check` falla por whitespace en artefactos generados, normalizar texto staged y repetir el check. No tocar binarios.

Verificar que no entren exclusiones:

```bash
git diff --cached --name-only --relative | rg -n '^(backups/|\.runtime/|frontend/node_modules/|\.venv/|runtime/.*\.pid$|=)'
```

Si `rg` no imprime nada, esta OK.

Contar archivos staged:

```bash
git diff --cached --name-only --relative | wc -l
```

Actualizar antes del commit:

```text
recuperacioncontexto.md
ULTIMO_CONTEXTO_CODEX.md
runtime/task_history.jsonl
updateGITHUB.md
```

Commit recomendado:

```bash
git commit -m "Publish latest live harness follow-up"
git push origin codex/publish-complete-runtime-project
```

Verificar despues del push:

```bash
gh pr view 1 --json number,state,isDraft,headRefName,baseRefName,url,commits
gh repo view neuroresnet50-IA/HABLA-PROCEDURAL-RUNTIME-EXECUTION --json nameWithOwner,visibility,isPrivate,defaultBranchRef,pushedAt,url
git rev-parse --short HEAD
git status --short --branch
```

## Regla de cierre para el siguiente agente

No enviar respuesta final sin actualizar:

- `recuperacioncontexto.md`
- `ULTIMO_CONTEXTO_CODEX.md`
- `runtime/task_history.jsonl`
- `updateGITHUB.md` si cambia el estado de publicacion

La respuesta final debe decir:

- commit final subido,
- PR actualizado,
- repo publico confirmado o blocker real,
- validaciones reales ejecutadas,
- si quedo delta posterior generado por runtime.

## Verificacion post-push 2026-06-05T13:31:10-07:00

Estado verificado:

- Commit de corte completo subido: `24d0081c` (`24d0081c4e39618b873917ac55225c0f42e76860`)
- Mensaje: `Publish latest live harness follow-up`
- Rama: `codex/publish-complete-runtime-project`
- PR: `https://github.com/neuroresnet50-IA/HABLA-PROCEDURAL-RUNTIME-EXECUTION/pull/1`
- PR #1: `OPEN`, `isDraft=true`, base `main`, head `codex/publish-complete-runtime-project`
- Repo GitHub: `neuroresnet50-IA/HABLA-PROCEDURAL-RUNTIME-EXECUTION`
- Visibilidad GitHub: `PUBLIC`
- `isPrivate=false`
- `pushedAt=2026-06-05T20:30:52Z`

Validaciones reales usadas para este corte:

- `python3 orchestrator/agent_tools.py health`: OK, `statusCode=200`, `ok=true`
- Python py_compile backend/orchestrator/workers/tools: OK
- Pytest enfocado backend/harness: OK, `123 passed in 5.71s`
- `npm run build` en `frontend/`: OK, warning conocido de chunk grande
- `npm test` en `frontend/`: OK, `agentClosureCertificate tests passed`
- `git diff --cached --check`: OK antes del commit
- Rutas excluidas staged: OK, sin coincidencias
- Escaneo exacto de secretos reales: OK, sin coincidencias
- Escaneo de archivos mayores a 95 MB: OK, sin salida

Delta posterior al push:

Despues de subir `24d0081c`, el runtime vivo genero cambios nuevos locales. No fueron revertidos. El siguiente agente debe decidir si hace otro corte o los deja como runtime en curso.

Rutas principales observadas:

- `backend/editor_state.json`
- `workspace/projects/continuity-code-pf-002-2/` con artefactos, checkpoints, baseline vault y logs nuevos
- `workspace/projects/continuity-code-pf-002/runtime/artifacts/observer_findings.json`
- `../../conector MCP/` sigue fuera del subrepo y no debe agregarse desde aqui

Punto exacto de reanudacion:

1. Abrir este repo con `cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"`.
2. Leer `AGENTS.md`, `updateGITHUB.md`, `ULTIMO_CONTEXTO_CODEX.md` y `recuperacioncontexto.md`.
3. Ejecutar `git status --short --branch`.
4. Si se quiere subir el delta posterior, validar de nuevo y hacer un nuevo commit sobre `codex/publish-complete-runtime-project`.
