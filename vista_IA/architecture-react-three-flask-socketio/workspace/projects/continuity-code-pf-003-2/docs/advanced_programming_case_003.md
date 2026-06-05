# Estrategia de pruebas para una API REST

## Objetivo

Definir una estrategia pequena y ejecutable para validar una API REST cubriendo respuestas `200`, `400`, `404` y `500`. La estrategia asume pruebas automatizadas con `pytest` y un cliente HTTP de test del framework usado por la API.

## Alcance minimo

- Probar al menos un endpoint representativo de lectura o consulta.
- Validar contrato de respuesta: codigo HTTP, tipo de contenido y estructura JSON.
- Separar datos validos, datos invalidos, recurso inexistente y fallo interno simulado.
- Evitar dependencias externas reales en pruebas de error: usar fixtures, doubles o monkeypatch.

## Matriz de casos

| Caso | Escenario | Preparacion | Aserciones obligatorias |
| --- | --- | --- | --- |
| `200 OK` | Solicitud valida sobre un recurso existente | Fixture con datos validos | `status_code == 200`, JSON con campos esperados, sin campo `error` |
| `400 Bad Request` | Payload, query param o path param invalido | Enviar campo requerido ausente o tipo incorrecto | `status_code == 400`, mensaje de validacion estable, no modifica estado |
| `404 Not Found` | Recurso inexistente pero request bien formada | Usar identificador valido que no exista | `status_code == 404`, error claro, no filtra detalles internos |
| `500 Internal Server Error` | Excepcion inesperada controlada por middleware | Monkeypatch del servicio/repositorio para lanzar excepcion | `status_code == 500`, respuesta generica, excepcion registrada por logs/handler |

## Diseno recomendado de pruebas

1. Crear fixtures para cliente HTTP, datos validos y datos invalidos.
2. Usar factories o fixtures de base de datos aislada si la API persiste datos.
3. Para `500`, no romper infraestructura real: simular el fallo en una dependencia del endpoint.
4. Mantener los asserts enfocados en el contrato publico, no en detalles privados de implementacion.
5. Ejecutar cada prueba de forma independiente, sin depender del orden.

## Esqueleto pytest

```python
def test_get_resource_returns_200(client, existing_resource):
    response = client.get(f"/resources/{existing_resource['id']}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == existing_resource["id"]
    assert "error" not in body


def test_get_resource_rejects_invalid_id_with_400(client):
    response = client.get("/resources/not-a-valid-id")

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "validation_error"


def test_get_resource_returns_404_for_missing_resource(client):
    response = client.get("/resources/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    body = response.get_json()
    assert body["error"]["code"] == "not_found"


def test_get_resource_returns_500_on_unexpected_service_error(client, monkeypatch):
    def raise_unexpected_error(*_args, **_kwargs):
        raise RuntimeError("forced test failure")

    monkeypatch.setattr("app.services.resources.get_resource", raise_unexpected_error)

    response = client.get("/resources/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 500
    body = response.get_json()
    assert body["error"]["code"] == "internal_error"
    assert "forced test failure" not in body["error"].get("message", "")
```

## Criterios de cierre

- Las cuatro rutas de estado (`200`, `400`, `404`, `500`) tienen pruebas automatizadas.
- Las respuestas de error comparten una forma JSON consistente.
- El caso `500` prueba el handler de errores sin depender de un fallo real de red, base de datos o servicio externo.
- La validacion ejecuta `pytest` y deja evidencia del resultado.
