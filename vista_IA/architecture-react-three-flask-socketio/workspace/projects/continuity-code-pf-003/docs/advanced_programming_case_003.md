# Advanced Programming Case 003

## Objetivo
Definir una estrategia de pruebas para una API REST que cubra respuestas 200,
400, 404 y 500 con casos pequenos, reproducibles y faciles de automatizar.

## Alcance
- Validar un recurso REST representativo, por ejemplo `GET /api/items/{id}` y
  `POST /api/items`.
- Mantener fixtures controlados para evitar dependencia de datos externos.
- Separar pruebas de contrato HTTP de pruebas unitarias de reglas internas.
- Registrar evidencia con comando ejecutado, salida y archivo esperado.

## Matriz minima de casos

| Codigo | Caso | Preparacion | Aserciones esperadas |
| --- | --- | --- | --- |
| 200 | Recurso existente o payload valido | Fixture con item `id=1` o payload completo | `status_code == 200`, JSON con campos obligatorios y tipos esperados |
| 400 | Payload invalido | Enviar body sin campo requerido o tipo incorrecto | `status_code == 400`, error de validacion estable y sin stack trace |
| 404 | Recurso inexistente | Consultar `id` que no existe en fixtures | `status_code == 404`, mensaje controlado y sin crear datos |
| 500 | Fallo interno controlado | Mockear dependencia para lanzar excepcion | `status_code == 500`, respuesta generica y log interno auditable |

## Plan de implementacion de tests
1. Crear cliente de prueba del framework usado por la API.
2. Cargar fixtures deterministas antes de cada test.
3. Escribir un test por codigo HTTP para mantener diagnostico simple.
4. En el caso 500, usar mock de repositorio/servicio; no provocar fallos reales
   de infraestructura.
5. Ejecutar una validacion corta en cada cambio: `pytest -q` si existe suite,
   o una validacion de archivo cuando esta tarea solo entrega documentacion.

## Riesgos y controles
- Riesgo: aceptar cualquier 4xx como equivalente. Control: asercion exacta del
  codigo y estructura de error.
- Riesgo: test 500 fragil por depender de base de datos real. Control: mock de
  dependencia y verificacion de log/respuesta generica.
- Riesgo: fixtures compartidos entre pruebas. Control: reset por test o factory
  aislada.

## Evidencia de esta micro-tarea
- Archivo esperado presente: `docs/advanced_programming_case_003.md`.
- Integridad actualizada: `runtime/artifacts/file_integrity_report.json`.
- Hallazgos Observer actualizados: `runtime/artifacts/observer_findings.json`.
- Cierre LACE 01 documentado en `docs/lace_cycles/ciclo-01.md` y `LACE_LOG.md`.
