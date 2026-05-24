# Integracion PostgreSQL local - evidencia y guia de transferencia

Fecha: 2026-05-21
Proyecto: HABLA Observer IA / architecture-react-three-flask-socketio
Alcance: dejar PostgreSQL funcionando para el backend local y documentar como se conecto.

## Objetivo

El objetivo fue dejar una base de datos PostgreSQL usable por la aplicacion local, con evidencia real de instalacion, conexion, esquema y healthcheck. La solicitud original fue instalar PostgreSQL en este entorno; al verificar el sistema se encontro que PostgreSQL ya estaba instalado, pero no estaba preparado para este proyecto con un rol/base administrable por el usuario actual.

Este documento explica exactamente que se hizo, por que se hizo asi, que archivos cambiaron y como un ingeniero humano puede repetir el proceso.

## Resultado final

PostgreSQL quedo disponible para el proyecto en una instancia Docker local persistente:

```text
Contenedor: habla-postgres
Imagen: postgres:16-alpine
Host local: 127.0.0.1
Puerto local: 55432
Base de datos: habla_observer
Usuario: habla_user
Password de desarrollo local: habla_change_me
URL local: postgresql://habla_user:habla_change_me@127.0.0.1:55432/habla_observer
```

El backend queda conectado porque `start.sh` carga `backend/.env` antes de iniciar Flask. Cuando Flask arranca, `backend/auth_routes.py` lee `DATABASE_URL` y abre la conexion con `psycopg`.

## Estado inicial encontrado

Se verifico el sistema antes de crear nada:

```bash
psql --version
```

Resultado real:

```text
psql (PostgreSQL) 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
```

Tambien se verifico el cluster del sistema:

```bash
pg_lsclusters
systemctl is-active postgresql
pg_isready
```

Resultado relevante:

```text
16 main 5432 online postgres /var/lib/postgresql/16/main
active
/var/run/postgresql:5432 - accepting connections
```

Conclusion: PostgreSQL del sistema ya existia y estaba activo en el puerto `5432`.

## Por que no se uso el PostgreSQL del sistema

Para crear la base `habla_observer` y el rol `habla_user` en el PostgreSQL del sistema era necesario administrar el cluster como usuario `postgres`. Se probaron las dos vias locales razonables:

```bash
sudo -n -u postgres psql -tAc "SELECT 1"
runuser -u postgres -- psql -tAc "SELECT 1"
```

Resultados reales:

```text
sudo: a password is required
runuser: may not be used by non-root users
```

Decision tecnica: no bloquear la integracion esperando privilegios de sistema. Se creo una instancia PostgreSQL aislada para este proyecto mediante Docker, usando un puerto distinto (`55432`) para no chocar con el PostgreSQL del sistema en `5432`.

Esta decision deja tres beneficios:

- No requiere tocar el cluster global de Ubuntu.
- Es reproducible y reversible para desarrollo local.
- Mantiene datos persistentes en el volumen Docker `habla_postgres_data`.

## Archivos tocados

Se crearon o modificaron estos archivos:

```text
backend/.env
.gitignore
start.sh
docs/integracion_postgresql_local_2026-05-21.md
runtime/checkpoints/postgresql-setup-20260521T091317-0700.json
runtime/task_history.jsonl
recuperacioncontexto.md
ULTIMO_CONTEXTO_CODEX.md
```

## 1. Contenedor PostgreSQL creado

Se uso la imagen local disponible `postgres:16-alpine` y se creo el contenedor `habla-postgres`.

Comando ejecutado:

```bash
docker run -d \
  --name habla-postgres \
  --restart unless-stopped \
  -e POSTGRES_DB=habla_observer \
  -e POSTGRES_USER=habla_user \
  -e POSTGRES_PASSWORD=habla_change_me \
  -p 127.0.0.1:55432:5432 \
  -v habla_postgres_data:/var/lib/postgresql/data \
  -v "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio/backend/postgresql_schema.sql:/docker-entrypoint-initdb.d/001_schema.sql:ro" \
  postgres:16-alpine
```

Detalles importantes del comando:

- `--name habla-postgres`: nombre estable para poder usar `docker start habla-postgres` despues.
- `--restart unless-stopped`: Docker intenta mantenerlo vivo despues de reinicios del servicio Docker.
- `POSTGRES_DB=habla_observer`: crea la base de datos inicial.
- `POSTGRES_USER=habla_user`: crea el usuario de aplicacion.
- `POSTGRES_PASSWORD=habla_change_me`: password local de desarrollo.
- `127.0.0.1:55432:5432`: expone PostgreSQL solo en localhost, puerto local 55432.
- `habla_postgres_data:/var/lib/postgresql/data`: guarda datos de forma persistente.
- `backend/postgresql_schema.sql:/docker-entrypoint-initdb.d/001_schema.sql:ro`: carga el esquema inicial al crear por primera vez el volumen.

## 2. Esquema cargado

El archivo usado para inicializar tablas fue `backend/postgresql_schema.sql`.

Tablas definidas por el esquema:

```text
users
user_profiles
payment_methods
sessions
```

Indices definidos:

```text
sessions_token_hash_idx
sessions_user_id_idx
user_profiles_user_id_idx
payment_methods_user_id_idx
```

Docker ejecuto ese SQL durante la primera inicializacion del contenedor. La evidencia del log mostro:

```text
/docker-entrypoint-initdb.d/001_schema.sql
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
```

## 3. Configuracion del backend

Se creo `backend/.env` con la configuracion local de PostgreSQL:

```dotenv
DATABASE_URL=postgresql://habla_user:habla_change_me@127.0.0.1:55432/habla_observer

POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=55432
POSTGRES_DB=habla_observer
POSTGRES_USER=habla_user
POSTGRES_PASSWORD=habla_change_me

HABLA_AUTH_SESSION_HOURS=24
POSTGRES_CONNECT_TIMEOUT=4
```

La variable principal es `DATABASE_URL`. Las variables `POSTGRES_*` quedan como alternativa porque `backend/auth_routes.py` soporta ambos formatos.

Nota de seguridad: este `.env` es para desarrollo local. No debe usarse como secreto productivo. Por eso `.gitignore` excluye `backend/.env`.

## 4. Driver Python usado por Flask

El backend ya tenia el driver PostgreSQL declarado en `backend/requirements.txt`:

```text
psycopg[binary]
```

Se valido que el Python usado por `start.sh` lo puede importar:

```bash
/home/neurodriver/ferrari_env/bin/python -c "import psycopg; print('ferrari psycopg ok', psycopg.__version__)"
```

Resultado real:

```text
ferrari psycopg ok 3.3.4
```

## 5. Como se conecto Flask con PostgreSQL

El backend ya tenia la logica de conexion en `backend/auth_routes.py`.

La funcion `_database_configured()` considera que PostgreSQL esta configurado si existe `DATABASE_URL` o si existen `POSTGRES_HOST`, `POSTGRES_DB` y `POSTGRES_USER`.

La funcion `_connect_db()` hace esto:

```text
1. Verifica que psycopg este instalado.
2. Verifica que exista configuracion de PostgreSQL.
3. Si existe DATABASE_URL, conecta con psycopg.connect(DATABASE_URL).
4. Si no existe DATABASE_URL, conecta con host, port, dbname, user y password.
5. Usa connect_timeout y row_factory=dict_row.
```

Por eso la integracion real no necesito reescribir el backend: habia que darle variables de entorno correctas antes de iniciar Flask.

## 6. Cambio hecho en start.sh

Antes, `start.sh` no cargaba `backend/.env`. Se agrego un cargador de variables al inicio del script:

```bash
BACKEND_ENV_FILE="$BACKEND_DIR/.env"

load_backend_env() {
  if [[ -f "$BACKEND_ENV_FILE" ]]; then
    set -a
    source "$BACKEND_ENV_FILE"
    set +a
  fi
}

load_backend_env
```

Por que esto conecta la aplicacion:

- `set -a` hace que las variables leidas desde `backend/.env` se exporten al ambiente.
- Luego `start.sh` lanza el backend con `setsid "$PYTHON_BIN" "$BACKEND_DIR/app.py"`.
- Ese proceso Python hereda `DATABASE_URL`, `POSTGRES_HOST`, `POSTGRES_PORT`, etc.
- `auth_routes.py` las lee con `os.environ` y abre la conexion PostgreSQL.

## 7. .gitignore agregado

Se creo `.gitignore` para evitar que secretos locales y dependencias generadas entren en versionamiento futuro.

Contenido relevante:

```gitignore
.env
.env.*
!.env.example
backend/.env
backend/.env.*
!backend/.env.example
frontend/.env
frontend/.env.*
!frontend/.env.example
.venv/
.installer-venv/
frontend/node_modules/
.runtime/
```

Se corrigio explicitamente para no ignorar `runtime/`, porque este repositorio usa `runtime/` como memoria auditable de checkpoints, historial y evidencias.

## 8. Evidencia de contenedor vivo

Comando:

```bash
docker ps --filter name=habla-postgres --format "{{.Names}} {{.Image}} {{.Status}} {{.Ports}}"
```

Resultado real:

```text
habla-postgres postgres:16-alpine Up ... 127.0.0.1:55432->5432/tcp
```

## 9. Evidencia de PostgreSQL respondiendo

Comando:

```bash
pg_isready -h 127.0.0.1 -p 55432 -U habla_user -d habla_observer
```

Resultado real:

```text
127.0.0.1:55432 - accepting connections
```

## 10. Evidencia de tablas creadas

Comando usado para comprobar que el esquema existe:

```bash
psql postgresql://habla_user:habla_change_me@127.0.0.1:55432/habla_observer   -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('users','user_profiles','payment_methods','sessions')"
```

Resultado real:

```text
4
```

Interpretacion: las cuatro tablas esperadas para autenticacion existen en la base `habla_observer`.

## 11. Evidencia de healthcheck Flask

Se probo `/api/health` usando `Flask.test_client()` con las variables de `backend/.env` cargadas.

Comando resumido:

```bash
/home/neurodriver/ferrari_env/bin/python - <<'PY'
import json
import os
import sys
from pathlib import Path
root = Path.cwd()
for line in (root / 'backend' / '.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        os.environ[key] = value
sys.path.insert(0, str(root / 'backend'))
from app import app
payload = app.test_client().get('/api/health').get_json()
print(json.dumps(payload.get('auth', {}).get('postgres', {}), sort_keys=True))
PY
```

Resultado real con `Flask.test_client()`:

```json
{"configured": true, "driver": "psycopg", "ready": true}
```

Tambien se hizo una validacion HTTP real. Como el puerto `5000` estaba ocupado por otra aplicacion externa en este entorno (`/home/neurodriver/Downloads/habla_voxel_face_3d(1)/habla_voxel_face_3d/app.py`), no se uso ese puerto para validar el health de este backend. Se levanto una instancia temporal en `5051`, con `PYTHONPATH=$PWD`, y se apago al terminar:

```bash
set -a
. backend/.env
set +a
PYTHONPATH="$PWD" HOST=127.0.0.1 PORT=5051 /home/neurodriver/ferrari_env/bin/python backend/app.py
curl -sS http://127.0.0.1:5051/api/health
```

Resultado HTTP real:

```json
{"auth":{"postgres":{"configured":true,"driver":"psycopg","ready":true}},"ok":true,"service":"HABLA Observer IA"}
```

Interpretacion:

- `configured=true`: Flask vio las variables de entorno.
- `driver=psycopg`: el driver Python esta instalado.
- `ready=true`: Flask abrio conexion y ejecuto `SELECT 1` correctamente.

## 12. Como arrancar la aplicacion ahora

Para levantar la app con PostgreSQL conectado:

```bash
./start.sh start
```

`start.sh` cargara `backend/.env`, compilara/servira segun su modo y arrancara Flask. En un entorno sin conflicto, el backend queda en:

```text
http://127.0.0.1:5000/
```

En este equipo, al momento de esta documentacion, el puerto `5000` estaba ocupado por otra app Flask externa. Por eso la evidencia HTTP de PostgreSQL se tomo con una instancia temporal en `5051`. Si un ingeniero necesita validar HTTP en este mismo equipo, debe liberar el puerto `5000` o arrancar este backend en otro puerto.

Para consultar solo el estado de PostgreSQL:

```bash
pg_isready -h 127.0.0.1 -p 55432 -U habla_user -d habla_observer
```

Para entrar a la base manualmente:

```bash
PGPASSWORD=habla_change_me psql -h 127.0.0.1 -p 55432 -U habla_user -d habla_observer
```

Dentro de `psql`, comandos utiles:

```sql
\dt
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM sessions;
```

## 13. Como detener o reiniciar PostgreSQL

Detener el contenedor sin borrar datos:

```bash
docker stop habla-postgres
```

Volver a iniciarlo:

```bash
docker start habla-postgres
```

Ver logs:

```bash
docker logs --tail 80 habla-postgres
```

Ver estado:

```bash
docker ps --filter name=habla-postgres
```

## 14. Como reproducir desde cero en otra maquina

Prerequisitos:

```text
Docker instalado
psql/pg_isready recomendados para validar
Python con psycopg instalado para el backend
```

Pasos:

```bash
cd "/home/neurodriver/BASE _METACOGNICION_COLOMBIA/vista_IA/architecture-react-three-flask-socketio"

docker run -d \
  --name habla-postgres \
  --restart unless-stopped \
  -e POSTGRES_DB=habla_observer \
  -e POSTGRES_USER=habla_user \
  -e POSTGRES_PASSWORD=habla_change_me \
  -p 127.0.0.1:55432:5432 \
  -v habla_postgres_data:/var/lib/postgresql/data \
  -v "$PWD/backend/postgresql_schema.sql:/docker-entrypoint-initdb.d/001_schema.sql:ro" \
  postgres:16-alpine
```

Despues crear `backend/.env` con este contenido:

```dotenv
DATABASE_URL=postgresql://habla_user:habla_change_me@127.0.0.1:55432/habla_observer
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=55432
POSTGRES_DB=habla_observer
POSTGRES_USER=habla_user
POSTGRES_PASSWORD=habla_change_me
HABLA_AUTH_SESSION_HOURS=24
POSTGRES_CONNECT_TIMEOUT=4
```

Luego validar y arrancar:

```bash
chmod 600 backend/.env
pg_isready -h 127.0.0.1 -p 55432 -U habla_user -d habla_observer
./start.sh start
```

Si `start.sh` no carga `.env` en otra copia del proyecto, agregar el bloque `load_backend_env` mostrado en la seccion 6.

## 15. Si se quiere usar PostgreSQL del sistema en puerto 5432

Esta integracion uso Docker porque no habia permiso para administrar el cluster del sistema. Si un administrador humano quiere usar el PostgreSQL del sistema, debe crear rol y base con privilegios sudo:

```bash
sudo -u postgres psql <<'SQL'
CREATE USER habla_user WITH PASSWORD 'habla_change_me';
CREATE DATABASE habla_observer OWNER habla_user;
GRANT ALL PRIVILEGES ON DATABASE habla_observer TO habla_user;
SQL

PGPASSWORD=habla_change_me psql -h 127.0.0.1 -p 5432 -U habla_user -d habla_observer -f backend/postgresql_schema.sql
```

Luego debe cambiar `backend/.env` a puerto `5432`:

```dotenv
DATABASE_URL=postgresql://habla_user:habla_change_me@127.0.0.1:5432/habla_observer
POSTGRES_PORT=5432
```

No se ejecuto esta ruta porque la sesion actual no tenia permiso sudo.

## 16. Incidentes y blockers registrados

Durante la integracion y documentacion quedaron estos blockers reales:

```text
Sandbox Codex: bwrap: loopback: Failed RTM_NEWADDR
sudo postgres: sudo: a password is required
runuser postgres: runuser may not be used by non-root users
agent_tools health: backend local respondio 404 para esa herramienta interna
git status: la carpeta no se comporta como repo Git valido aunque existe .git
puerto 5000: ocupado por una app Flask externa en Downloads, por eso /api/health se valido en 5051
primer arranque temporal en 5051: fallo sin PYTHONPATH porque no encontraba orchestrator; se corrigio con PYTHONPATH=$PWD
primer intento de escribir este MD: fallo por choque de delimitador heredoc; no se creo archivo parcial
```

El primer intento de escribir este documento fallo porque el contenido incluia un bloque de ejemplo con una linea `PY`, que coincidio con el delimitador del script usado para escribir el archivo. Se corrigio usando un delimitador unico y se verifico que no existia un archivo parcial antes de reescribir.

## 17. Riesgos y decisiones pendientes

Riesgos conocidos:

- `backend/.env` contiene credenciales locales de desarrollo. No debe subirse ni reutilizarse en produccion.
- El puerto del proyecto es `55432`, no `5432`, para evitar conflicto con el PostgreSQL del sistema.
- Si se elimina el volumen Docker `habla_postgres_data`, se pierde la base local.
- Si se recrea el contenedor con un volumen ya existente, los scripts de `/docker-entrypoint-initdb.d/` no se vuelven a ejecutar automaticamente.

Buenas practicas recomendadas:

- Cambiar password si este entorno se comparte.
- Usar secretos reales fuera del repositorio para produccion.
- Mantener `backend/.env.example` como plantilla publica y `backend/.env` como archivo local privado.
- Hacer backup del volumen si la base empieza a contener datos importantes.

## 18. Artefactos de auditoria

Checkpoint principal de la integracion:

```text
runtime/checkpoints/postgresql-setup-20260521T091317-0700.json
```

Memoria persistida actualizada:

```text
recuperacioncontexto.md
ULTIMO_CONTEXTO_CODEX.md
runtime/task_history.jsonl
```

Este documento es la evidencia humana complementaria para que un ingeniero pueda entender y repetir la integracion sin depender de memoria implicita de la sesion.

## Checklist rapido para el ingeniero

```text
[ ] docker ps muestra habla-postgres vivo
[ ] pg_isready responde en 127.0.0.1:55432
[ ] backend/.env existe y apunta a 55432
[ ] start.sh carga backend/.env antes de iniciar Flask
[ ] /api/health devuelve auth.postgres.ready=true en el puerto donde este corriendo este backend
[ ] si 5000 devuelve otra app, liberar 5000 o validar temporalmente en otro puerto como 5051
[ ] psql muestra las tablas users, user_profiles, payment_methods y sessions
```
