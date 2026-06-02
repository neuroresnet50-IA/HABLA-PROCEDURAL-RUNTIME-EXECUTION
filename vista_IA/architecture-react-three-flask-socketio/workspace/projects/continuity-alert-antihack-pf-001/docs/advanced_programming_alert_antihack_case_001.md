# Caso 001: auditoria segura para alerta antihack en API REST

## Objetivo

Definir una estrategia defensiva pequena y verificable para una API REST que
necesita auditoria, trazabilidad de errores y logging seguro sin filtrar
secretos. La solucion debe cubrir respuestas 200, 400, 404 y 500 con evidencia
suficiente para investigar incidentes sin exponer credenciales, tokens, datos
personales o payloads sensibles.

## Estrategia minima

1. Generar un `request_id` por solicitud y devolverlo en la respuesta.
2. Registrar logs estructurados con `timestamp`, `request_id`, `route`,
   `method`, `status_code`, `latency_ms` y `outcome`.
3. Redactar campos sensibles antes de escribir cualquier log. La lista inicial
   incluye `password`, `token`, `authorization`, `secret`, `api_key`, `cookie`,
   `session`, `email` y `phone`.
4. Registrar eventos de seguridad separados para entradas invalidas,
   rutas inexistentes y errores internos, siempre con payload redactado.
5. Devolver errores consistentes:
   - `400`: validacion fallida con campo, regla y `request_id`.
   - `404`: recurso o ruta no encontrada con `request_id`.
   - `500`: mensaje seguro, sin stack trace publico, con `request_id`.
6. Mantener el stack trace completo solo en almacenamiento interno protegido.

## Contrato de validacion por estado

| Estado | Validacion defensiva | Evidencia esperada |
| --- | --- | --- |
| 200 | La operacion termina y el log no contiene secretos. | Evento `api.success` con `request_id`. |
| 400 | El validador rechaza input invalido antes de negocio. | Evento `api.validation_failed` con campos redactados. |
| 404 | La ruta o entidad no existe y no se filtra informacion interna. | Evento `api.not_found` con ruta normalizada. |
| 500 | La excepcion queda correlacionada, no expuesta al usuario. | Evento `api.internal_error` con referencia interna. |

## Pseudocodigo de referencia

```python
SENSITIVE_KEYS = {
    "password",
    "token",
    "authorization",
    "secret",
    "api_key",
    "cookie",
    "session",
    "email",
    "phone",
}


def redact(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def audit_event(name, request, status_code, payload=None, error=None):
    safe_payload = redact(payload or {})
    return {
        "event": name,
        "request_id": request.request_id,
        "method": request.method,
        "route": request.route,
        "status_code": status_code,
        "payload": safe_payload,
        "error_type": type(error).__name__ if error else None,
    }
```

## Criterios de cierre del caso

- Existe evidencia de `observer_findings` sin hallazgos activos.
- Existe reporte de integridad sin archivos borrados, modificados o no
  rastreados fuera del alcance.
- El ciclo LACE 01 registra problemas, mejora aplicada y completado con
  validacion real.
- Las validaciones enfocadas del worker pasan con codigo 0.

## Evidencia de materializacion

- task_id: RUNTIME-20260602201529-002
- expected_file: docs/advanced_programming_alert_antihack_case_001.md
- materialized_at: 2026-06-02T20:16:02Z
- lace_cycle: LACE-20260602-001
