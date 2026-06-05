# HABLA Remote Console - Plan De Implementacion Futura

## Objetivo

Crear un cliente externo ligero tipo chat/dashboard que controle HABLA por REST, usando la misma capa backend que usa la UI principal, pero con seguridad fuerte, auditoria y permisos.

La idea principal es convertir lo que hoy puede hacerse por backend local en una herramienta oficial, segura y usable:

- Enviar prompts directos al runtime.
- Consultar estado de proyectos.
- Revisar runtime-truth.
- Ejecutar validaciones de seguridad.
- Ver bloqueos de CyberLACE.
- Operar desde otro equipo o aplicacion sin abrir la UI completa.

## Principio Arquitectonico

HABLA Runtime sigue siendo el cerebro.

La UI grande sigue siendo el estudio completo.

HABLA Remote Console seria una consola ligera externa para dar ordenes, revisar estado y operar seguridad desde fuera.

No debe reemplazar la arquitectura existente. Debe reutilizar los endpoints y servicios del backend actual.

## Fase 1 - API Segura

Crear un namespace REST dedicado:

- `POST /api/remote/session`
- `GET /api/remote/health`
- `GET /api/remote/projects`
- `GET /api/remote/project/<slug>/runtime-truth`
- `POST /api/remote/project/<slug>/zombie/release`
- `GET /api/remote/cyberlace/health`
- `POST /api/remote/harness/run`
- `GET /api/remote/reports`

### Autenticacion

Agregar autenticacion obligatoria para clientes remotos:

- Token por cliente/dispositivo.
- Expiracion configurable.
- Hash del token en backend, nunca token plano.
- Revocacion de tokens.
- Rate limit basico.
- Auditoria por intento valido o invalido.

### Permisos

Definir permisos por accion:

- `read`
- `start_session`
- `security_tests`
- `harness_run`
- `zombie_release`
- `delete_project`
- `admin`

Cada endpoint debe validar permisos antes de ejecutar cualquier accion.

## Fase 2 - Auditoria Obligatoria

Guardar cada orden remota en:

`runtime/audit/remote_console.jsonl`

Cada evento debe incluir:

- Timestamp.
- Cliente/usuario.
- IP o identificador de origen.
- Accion solicitada.
- Proyecto afectado.
- Resultado.
- Error code si aplica.
- Checkpoint si se genero.
- CyberLACE decision si aplica.

Regla critica:

Nunca guardar secretos crudos en auditoria. Si hay tokens, passwords, CVV, PIN, llaves o credenciales, deben quedar como `[REDACTED]`.

## Fase 3 - Cliente Ligero

Crear una UI separada, sin tocar la UI grande:

`remote-console/`

Pantallas principales:

- Login/token.
- Chat de ordenes.
- Selector de proyecto.
- Panel de estado runtime.
- Panel CyberLACE.
- Historial de ordenes.
- Reportes/checkpoints.

Acciones principales:

- Enviar prompt al runtime.
- Ver sesiones.
- Ver proyectos.
- Ver runtime-truth.
- Correr harness.
- Revisar checkpoints.
- Revisar reportes.

Estados visuales:

- Verde: seguro/completado.
- Rojo: bloqueado.
- Amarillo: preparando/warning.
- Gris: idle.

Acciones peligrosas deben abrir modal de doble autorizacion.

## Fase 4 - Seguridad Operativa

CyberLACE debe ser obligatorio para toda orden remota.

Todo prompt remoto debe pasar por hard gate antes de llegar a Codex.

Debe bloquear:

- Secretos o credenciales.
- Login externo.
- Exfiltracion.
- Prompt injection.
- Archivos inseguros.
- Acciones destructivas sin autorizacion.

Cuando bloquee, debe devolver:

- Estado `blocked`.
- `pid=null`.
- `command=[]`.
- `returncode=126`.
- `runtimeAction=QUARANTINE` o equivalente.
- Evidencia redactada.
- Alternativa segura.
- Checkpoint.

## Fase 5 - Doble Autorizacion

Requerir doble autorizacion para:

- Borrar proyecto.
- Liberar zombi.
- Ejecutar acciones destructivas.
- Cambiar configuracion.
- Procesar archivos marcados como sensibles.

Flujo sugerido:

1. Usuario solicita accion peligrosa.
2. Modal rojo confirma la accion.
3. Usuario introduce password o token de elevacion.
4. Backend valida permiso.
5. CyberLACE hace preflight.
6. Si todo pasa, ejecuta.
7. Se registra auditoria y checkpoint.

## Fase 6 - Modo Remoto Seguro

Por defecto, el sistema debe escuchar solo en localhost.

Para acceso externo, usar:

- VPN.
- Tailscale.
- HTTPS.
- Reverse proxy autenticado.
- Tokens por dispositivo.

No debe exponerse abierto a internet sin autenticacion fuerte.

## Fase 7 - Integracion Con Runtime Existente

La Remote Console debe reutilizar el backend actual:

- `agent_runtime.start_session`.
- `runtime-truth`.
- CyberLACE health.
- Harness interno.
- Checkpoints.
- Project state.
- Task queue.

No debe crear una arquitectura paralela ni duplicar logica critica.

Las respuestas remotas deben ser compactas:

- `status`
- `pid`
- `runtimeAction`
- `checkpoint`
- `report`
- `safeAlternative`
- `errorCode`

No enviar logs enormes por defecto.

## Fase 8 - Pruebas Minimas

Tests obligatorios:

- Login remoto valido.
- Login remoto invalido.
- Token expirado.
- Permiso insuficiente.
- Enviar prompt normal.
- Enviar prompt con secreto simulado.
- Prompt injection remoto.
- Intento de login externo.
- Intento de borrar proyecto sin doble autorizacion.
- Zombie release con doble autorizacion.
- Auditoria creada.
- Evidencia redactada.
- Sin PID cuando CyberLACE bloquea.
- Sin proyecto zombi.

## Validacion Final

Antes de declarar lista la implementacion:

```bash
python3 -B -m py_compile backend/app.py backend/agent_runtime.py backend/cyberlace_document_guard.py orchestrator/*.py workers/codex_worker.py
npm --prefix frontend run build
OPEN_BROWSER=0 ./start.sh restart
curl --max-time 5 http://127.0.0.1:5001/api/health
curl --max-time 5 http://127.0.0.1:5001/api/cyberlace/health
```

Ademas:

- Prueba real desde Remote Console.
- Checkpoint final.
- Reporte tecnico.
- Auditoria verificada.

## Ejemplo De Uso Futuro

Desde otra aplicacion:

```http
POST /api/remote/session
Authorization: Bearer <REMOTE_CLIENT_TOKEN>
Content-Type: application/json

{
  "projectSlug": "case05-prompt-injection-readme-final-125000",
  "requirement": "Revisa seguridad del README",
  "runtimeMode": "smoke"
}
```

Respuesta esperada si CyberLACE bloquea:

```json
{
  "ok": true,
  "status": "blocked",
  "pid": null,
  "command": [],
  "returncode": 126,
  "runtimeAction": "QUARANTINE",
  "errorCode": "cyberlace_sensitive_document_blocked",
  "checkpoint": "session-cyberlace-document-blocked-...",
  "safeAlternative": {
    "title": "Alternativa segura permitida"
  }
}
```

## Valor Estrategico

Esta consola convertiria HABLA en un sistema cliente-servidor real:

- Operable desde fuera de la UI grande.
- Util para seguridad y red-team.
- Util para automatizacion.
- Util para emergencias del runtime.
- Util para equipos tecnicos que necesitan evidencia y control.

Pero debe construirse con seguridad desde el inicio, porque una consola remota sin permisos, auditoria y CyberLACE seria una puerta peligrosa.

## Estado

Documento de futura implementacion.

No implementado todavia.

No modifica el runtime actual.
