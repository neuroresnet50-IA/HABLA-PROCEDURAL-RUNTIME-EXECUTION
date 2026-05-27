# Architecture View: React + Three.js + Flask-SocketIO

Prototipo funcional de un mapa conceptual donde cada archivo generado por un agente aparece como un módulo conectado.

## Ejecutar aplicacion local

```bash
./start.sh start
```

Backend y frontend bundle: http://localhost:5001

## Acceso de validacion

Para validar el proyecto desde una instalacion local o clon de GitHub, el backend siembra un usuario por defecto cuando PostgreSQL esta disponible:

```text
usuario: admin
contrasena: admin
```

Se puede desactivar con `HABLA_DEFAULT_ADMIN_ENABLED=0` o cambiar con `HABLA_DEFAULT_ADMIN_USER` y `HABLA_DEFAULT_ADMIN_PASSWORD`.

## Frontend en modo desarrollo

```bash
./start.sh dev
```

Frontend dev: http://localhost:5173

## Enviar un grafo nuevo

```bash
curl -X POST http://localhost:5001/api/architecture \
  -H 'Content-Type: application/json' \
  -d '{"nodes":[],"edges":[],"metadata":{"projectName":"Nuevo turno"}}'
```
