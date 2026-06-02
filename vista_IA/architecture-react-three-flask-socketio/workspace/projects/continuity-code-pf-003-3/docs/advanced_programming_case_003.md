# Estrategia de pruebas para API REST

## Objetivo

Validar que una API REST responde de forma consistente ante flujos exitosos,
errores de entrada, recursos inexistentes y fallos internos. La estrategia cubre
los codigos HTTP 200, 400, 404 y 500 con evidencia automatizable y repetible.

## Alcance

- Endpoints REST expuestos por el servicio bajo prueba.
- Contratos de request y response en formato JSON.
- Validacion de status code, cuerpo de respuesta, headers relevantes y trazas de error.
- Pruebas automatizadas ejecutables en CI o en validacion local.

Fuera de alcance para esta tarea: pruebas de carga, seguridad profunda,
compatibilidad entre versiones y contratos con consumidores externos.

## Matriz de casos

| Codigo | Escenario | Entrada | Evidencia esperada |
| --- | --- | --- | --- |
| 200 | Operacion valida completada | Request con parametros y payload validos | Status 200, JSON con datos esperados, esquema valido y sin campo `error` |
| 400 | Request invalido | Payload incompleto, tipos incorrectos o parametros fuera de rango | Status 400, mensaje claro de validacion, lista de campos invalidos cuando aplique |
| 404 | Recurso inexistente | Identificador valido en formato pero no existente | Status 404, mensaje estable de recurso no encontrado y sin datos parciales |
| 500 | Fallo interno controlado | Error simulado en dependencia, base de datos o servicio interno | Status 500, respuesta generica segura, correlacion/log interno y sin filtrar stack trace |

## Diseno de pruebas

1. Preparar fixtures deterministas para recursos existentes y no existentes.
2. Ejecutar cada endpoint con cliente HTTP de prueba o test client del framework.
3. Validar siempre status code, `Content-Type`, estructura JSON y campos obligatorios.
4. Separar pruebas por tipo de resultado: `test_success_200`,
   `test_validation_error_400`, `test_not_found_404` y `test_internal_error_500`.
5. Simular el caso 500 con monkeypatch, mock de repositorio o dependencia fallida,
   evitando inducir fallos reales en infraestructura.

## Criterios de aceptacion

- Cada endpoint critico tiene al menos un caso 200 y un caso negativo relevante.
- Los errores 400 y 404 son reproducibles sin depender de orden de ejecucion.
- El caso 500 esta cubierto por simulacion controlada y verifica que no se expone
  informacion sensible.
- La suite puede ejecutarse con `pytest` y falla si cambia el contrato publico de
  respuesta.
- Los nombres de prueba describen el comportamiento esperado, no la implementacion.

## Riesgos y mitigacion

- Datos compartidos entre pruebas: usar fixtures aisladas o reset por prueba.
- Errores 500 dificiles de reproducir: inyectar dependencia mockeable.
- Mensajes de error inestables: validar codigo, campo de error y categoria antes
  que texto exacto cuando el texto sea de presentacion.
- Contratos no documentados: convertir expectativas repetidas en helpers o schemas
  reutilizables.

## Evidencia minima por ejecucion

- Comando ejecutado.
- Resultado de `pytest`.
- Endpoint probado.
- Status code observado.
- Resumen de asserts por caso.
- Registro de cualquier fallo con causa y siguiente accion.
