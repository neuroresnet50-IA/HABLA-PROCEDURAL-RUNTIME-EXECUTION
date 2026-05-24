# Fase 2 - Guard Rails Del Runtime

Estado: implementada

Documento base:

- `protocolo Arquitectonico.md`
- `Fase 1 - Contrato Formal.md`

## Objetivo

Cerrar el runtime agentic para que no existan sesiones mudas o ambiguas.

## Alcance Implementado

Se implementaron estos guard rails:

1. `timeout` del primer evento visual
2. `heartbeat` de sesion en ejecucion
3. error explicito si el agente no entra al bridge visual
4. error explicito si la sesion queda en silencio demasiado tiempo
5. estado explicito de sesion detenida por usuario

## Parametros Activos

Valores por defecto actuales:

- `AGENT_FIRST_VISUAL_TIMEOUT_SECONDS = 300`
- `AGENT_HEARTBEAT_INTERVAL_SECONDS = 5`
- `AGENT_SESSION_IDLE_TIMEOUT_SECONDS = 120`

## Comportamiento Esperado

Una sesion agentic valida ahora debe:

1. arrancar
2. emitir `session_start`
3. producir el primer evento visual util dentro del tiempo permitido
4. emitir `heartbeat` mientras siga viva
5. fallar explicitamente si no entra al bridge

Adicionalmente, la sesion debe exponer estado de avance visible:

- `progressPercent`
- `progressLabel`
- `firstOutputAt`
- `terminalLogPath`

## Eventos De Runtime Introducidos O Endurecidos

- `session_start`
- `heartbeat`
- `session_failed`
- `session_stopped`
- `session_complete`

## Errores Explicitados

- `bridge_timeout`
- `session_idle_timeout`
- `no_visual_events`
- `process_exit_nonzero`
- `codex_command_not_found`
- `codex_launch_error`

## Resultado Arquitectonico

Con esta fase:

- una sesion ya no puede quedar "pensando" sin explicacion
- la UI puede distinguir entre sesion viva, sesion muda, sesion fallida y sesion detenida
- la UI puede mostrar porcentaje y etapa aunque Codex aun no haya dibujado nodos
- el runtime ya tiene una primera capa real de contrato operativo

## Verificacion Ejecutada

- compilacion Python del backend
- build del frontend con Vite
- verificacion de exposicion de timeouts y nuevos campos de sesion
