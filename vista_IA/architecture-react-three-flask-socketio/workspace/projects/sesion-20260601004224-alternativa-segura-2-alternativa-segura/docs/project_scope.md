# Project Scope

## Resumen

Alternativa Segura 2 evolucionara hacia un orquestador autonomo de proyectos con agentes reemplazables. El sistema debe convertir solicitudes amplias en tareas pequenas, verificables, persistentes y reanudables, con evidencia real en disco antes de declarar avance.

Esta tarea solo define el shell documental inicial. La implementacion de modulos, esquemas, workers, endpoints, UI, benchmarks y sandbox real queda para tareas posteriores controladas por el backlog.

## Problema a resolver

Un proyecto largo tratado como una unica conversacion acumula memoria implicita, decisiones no auditables y cierres dificiles de validar. El sistema objetivo debe operar como una maquina de ejecucion que pueda pausar, reanudar, auditar y reemplazar workers sin perder el estado real del proyecto.

## Objetivo funcional

Construir un runtime que:

- lea politica, plan, estado, historial y checkpoints;
- genere directivas por tarea;
- lance workers acotados;
- valide cada resultado;
- registre fallos y retries por tarea;
- mantenga evidencia persistida;
- bloquee cierres sin scanner, sandbox o validaciones cuando sean aplicables.

## Usuarios previstos

- Humano operador: define direccion, revisa evidencia, autoriza acciones destructivas y corrige preferencias mediante HAR.
- Control plane: decide cola, prioridades, presupuestos, retries y cierre.
- Worker reemplazable: ejecuta una tarea delimitada y devuelve un TaskResult.
- Observer: cruza runtime, scanner, sandbox, findings, UI y estado persistido para explicar observaciones.

## Arquitectura objetivo

### Control plane

Responsable de la verdad operacional. Debe mantener backlog, estados, dependencias, budgets, retries, checkpoints y decision de cierre.

### Worker plane

Responsable de ejecucion acotada. Cada worker recibe una sola tarea con expected files, validaciones, timeout, modo y limites de escritura.

### Verification plane

Responsable de aceptar o rechazar evidencia. Debe ejecutar validaciones declaradas, scanner, integrity, findings y sandbox segun el tipo de proyecto y la fase.

### Memory plane

Responsable de persistencia. Debe mantener estado, cola, historial, fallos, artefactos, checkpoints, logs, directivas y reportes de recuperacion.

## Contratos minimos

### Task

Cada tarea debe declarar id, titulo, objetivo, estado, prioridad, dependencias, archivos esperados, comandos de validacion, timeout, retries, modo y checkpoint asociado.

### TaskResult

Cada worker debe devolver:

- si el objetivo se cumplio;
- archivos creados;
- archivos modificados;
- validaciones ejecutadas;
- resultado de validacion;
- blockers reales;
- recomendacion siguiente.

## Reglas operativas que deben preservarse

- El modo `smoke` solo puede venir de configuracion explicita.
- Los modos validos son `smoke`, `build`, `medium` y `long-run`.
- Una sesion debe contener multiples tareas.
- Cada tarea debe lanzar un worker propio.
- Cada tarea debe tener timeout propio.
- El retry debe ser por tarea, no por sesion completa.
- Si un proceso no cierra con `terminate()`, debe cerrarse con `kill()`.
- El progreso solo cuenta con evidencia real en disco.
- Las directivas deben derivarse de `AGENTS.md`, `PLANS.md`, estado persistido, checkpoint y HABLA BASIC.
- `PROMPT_SPRINT_*.txt` solo puede ser artefacto humano o bootstrap, no el mecanismo final de directivas.

## Seguridad y continuacion segura

El proyecto debe mantenerse dentro del workspace autorizado. Los ejemplos deben usar datos sinteticos o evidencia redactada. No se deben procesar secretos, credenciales, bypasses, informacion sensible local ni acciones destructivas no verificadas.

Las acciones destructivas masivas requieren decision auditable, backup previo y confirmacion humana cuando aplique. El blanqueo selectivo debe intentarse antes de un blanqueo total.

## Evidencia de cierre

Un cierre tecnico solo puede aceptarse cuando existan evidencias persistidas correspondientes al tipo de tarea:

- writer o artefacto final cuando aplique;
- scanner final con lectura linea por linea hasta la ultima linea real;
- integrity scan sin divergencias criticas;
- findings revisados;
- sandbox local real si la app expone preview web;
- validaciones declaradas con codigo de salida 0.

Para esta tarea documental, la evidencia obligatoria es la existencia de `README.md` y `docs/project_scope.md` bajo el root del proyecto.

## No alcance de esta tarea

Esta tarea no crea:

- modulos de `orchestrator/`;
- implementacion de workers;
- esquemas JSON;
- endpoints backend;
- frontend o preview web;
- benchmarks;
- sandbox ejecutable;
- cambios en archivos internos de control plane.

## Notas de implementacion para tareas futuras

1. Crear estructura base solo cuando el backlog asigne esa tarea.
2. Implementar loaders de politica y plan antes de generar directivas.
3. Persistir cada directiva de worker en disco para auditoria y reanudacion.
4. Separar validacion local corta de validacion de cierre completo.
5. Registrar fallos y retries por tarea con causa concreta.
6. Mantener HAR como revision humana posterior al cierre tecnico, sin modificar producto hasta recibir feedback explicito.

## Criterio de aceptacion de esta tarea

La tarea se considera tecnicamente lista para validacion del control plane si:

- existe `README.md`;
- existe `docs/project_scope.md`;
- el comando de validacion declarado pasa con codigo 0;
- LACE_LOG registra el ciclo acotado de esta tarea;
- el bridge visual sincronizo los archivos modificados;
- no se editaron archivos internos de control plane restringidos.
