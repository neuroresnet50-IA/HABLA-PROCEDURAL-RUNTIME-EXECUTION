#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BACKEND_DIR="$ROOT/backend"
BACKEND_ENV_FILE="$BACKEND_DIR/.env"
FRONTEND_DIR="$ROOT/frontend"
FRONTEND_DIST_INDEX="$FRONTEND_DIR/dist/index.html"

load_backend_env() {
  if [[ -f "$BACKEND_ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$BACKEND_ENV_FILE"
    set +a
  fi
}

load_backend_env

PORT="${PORT:-5001}"
HOST="${HOST:-0.0.0.0}"
HEALTH_HOST="${HEALTH_HOST:-127.0.0.1}"
HEALTH_URL="http://${HEALTH_HOST}:${PORT}/api/health"
LOG_DIR="$ROOT/runtime/logs"
PID_FILE="$ROOT/runtime/prompt_flight_backend.pid"
mkdir -p "$LOG_DIR"
PYTHONPATH_VALUE="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

if [[ -z "${BACKEND_PYTHON:-}" ]]; then
  if [[ -x "$HOME/ferrari_env/bin/python" ]]; then
    BACKEND_PYTHON="$HOME/ferrari_env/bin/python"
  else
    BACKEND_PYTHON="$(command -v python3)"
  fi
fi

if [[ -z "${TK_PYTHON:-}" ]]; then
  TK_PYTHON="$(command -v python3)"
fi

BACKEND_LOG="$LOG_DIR/prompt_flight_backend_$(date -u +%Y%m%dT%H%M%SZ).log"
FRONTEND_BUILD_LOG="$LOG_DIR/frontend_build_$(date -u +%Y%m%dT%H%M%SZ).log"
TK_LOG="$LOG_DIR/prompt_flight_tkinter_$(date -u +%Y%m%dT%H%M%SZ).log"
DEFAULT_PROMPT_SUITE="${HABLA_PROMPT_FLIGHT_DEFAULT_SUITE:-advanced_programming_alert_antihack}"
DEFAULT_PROMPT_MODE="${HABLA_PROMPT_FLIGHT_DEFAULT_MODE:-ui_session_rest}"

usage() {
  cat <<USAGE
Uso:
  ./start_prompt_flight_tkinter.sh              Reinicia backend, verifica health y abre Tkinter
  ./start_prompt_flight_tkinter.sh --backend-only  Solo reinicia backend y verifica health
  ./start_prompt_flight_tkinter.sh --tk-only       Solo abre Tkinter contra un backend ya activo
  ./start_prompt_flight_tkinter.sh --no-restart    Usa backend existente si responde; si no, arranca uno nuevo
  ./start_prompt_flight_tkinter.sh --local-worker-no-bwrap
                                                 Modo local confiable: evita bubblewrap para workers Codex internos
  ./start_prompt_flight_tkinter.sh --safe-worker-sandbox
                                                 Fuerza sandbox workspace-write para diagnostico/hosts compatibles
  ./start_prompt_flight_tkinter.sh --suite SUITE_ID
                                                 Suite Prompt Flight inicial en Tkinter
  ./start_prompt_flight_tkinter.sh --alert-antihack
                                                 Atajo para suite advanced_programming_alert_antihack
  ./start_prompt_flight_tkinter.sh --stop          Detiene backend/app.py y sale

Variables opcionales:
  PORT=5001
  backend/.env se carga automaticamente si existe
  HOST=0.0.0.0
  BACKEND_PYTHON=/ruta/python
  TK_PYTHON=/ruta/python3
  HABLA_PROMPT_FLIGHT_DEFAULT_SUITE=advanced_programming_alert_antihack
  HABLA_PROMPT_FLIGHT_DEFAULT_MODE=ui_session_rest
  VISTA_PROMPT_FLIGHT_LOCAL_NO_BWRAP_DEFAULT=1
  HABLA_SKIP_FRONTEND_BUILD=1 para omitir build automatico de frontend/dist
USAGE
}

frontend_needs_build() {
  if [[ ! -d "$FRONTEND_DIR" || ! -f "$FRONTEND_DIR/package.json" ]]; then
    return 1
  fi
  if [[ ! -f "$FRONTEND_DIST_INDEX" ]]; then
    return 0
  fi
  local newer
  newer="$(find "$FRONTEND_DIR/src" "$FRONTEND_DIR/index.html" "$FRONTEND_DIR/package.json" "$FRONTEND_DIR/vite.config.js" -newer "$FRONTEND_DIST_INDEX" -print -quit 2>/dev/null || true)"
  [[ -n "$newer" ]]
}

build_frontend_if_needed() {
  if [[ "${HABLA_SKIP_FRONTEND_BUILD:-0}" == "1" || "${VISTA_SKIP_FRONTEND_BUILD:-0}" == "1" ]]; then
    echo "[frontend] Build automatico omitido por variable de entorno."
    return 0
  fi
  if [[ ! -d "$FRONTEND_DIR" || ! -f "$FRONTEND_DIR/package.json" ]]; then
    echo "[frontend] No hay frontend/package.json; no se compila dist."
    return 0
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "[frontend] npm no disponible; no se puede compilar frontend/dist." >&2
    return 0
  fi
  if frontend_needs_build; then
    echo "[frontend] Cambios detectados; compilando frontend/dist antes de levantar backend."
    echo "[frontend] Log: $FRONTEND_BUILD_LOG"
    (cd "$FRONTEND_DIR" && npm run build >"$FRONTEND_BUILD_LOG" 2>&1)
    echo "[frontend] Build OK. UI servida por backend en http://127.0.0.1:${PORT}/"
  else
    echo "[frontend] dist actualizado; usando $FRONTEND_DIST_INDEX"
  fi
}

pid_file_backend_pid() {
  if [[ ! -f "$PID_FILE" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
    return 0
  fi

  local args
  args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  if [[ "$args" == *"$ROOT/backend/app.py"* ]]; then
    echo "$pid"
  fi
}

find_backend_pids() {
  {
    pgrep -f "$ROOT/backend/app.py" || true
    pid_file_backend_pid || true
  } | awk 'NF && !seen[$1]++ { print $1 }'
}

stop_backend() {
  local pids
  pids="$(find_backend_pids)"
  if [[ -z "$pids" ]]; then
    echo "[backend] No hay backend/app.py activo."
    rm -f "$PID_FILE"
    return 0
  fi

  echo "[backend] Deteniendo backend viejo: $pids"
  # shellcheck disable=SC2086
  kill -TERM $pids 2>/dev/null || true

  for _ in {1..20}; do
    sleep 0.5
    if [[ -z "$(find_backend_pids)" ]]; then
      echo "[backend] Backend viejo detenido."
      rm -f "$PID_FILE"
      return 0
    fi
  done

  pids="$(find_backend_pids)"
  if [[ -n "$pids" ]]; then
    echo "[backend] TERM no cerro todo; aplicando KILL: $pids"
    # shellcheck disable=SC2086
    kill -KILL $pids 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
}

healthcheck() {
  "$BACKEND_PYTHON" - "$HEALTH_URL" <<'PYHEALTH'
import json
import sys
import urllib.request
url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=3) as response:
        payload = json.loads(response.read().decode('utf-8'))
    ok = response.status == 200 and payload.get('ok') is True
    print(json.dumps({'statusCode': response.status, 'ok': ok, 'payload': payload}, ensure_ascii=True, sort_keys=True))
    raise SystemExit(0 if ok else 1)
except Exception as exc:
    print(json.dumps({'statusCode': 0, 'ok': False, 'error': repr(exc)}, ensure_ascii=True, sort_keys=True))
    raise SystemExit(1)
PYHEALTH
}

backend_get_json() {
  local url="$1"
  "$BACKEND_PYTHON" - "$url" <<'PYGET'
import json
import sys
import urllib.request

url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    raise SystemExit(0 if response.status == 200 else 1)
except Exception as exc:
    print(json.dumps({"ok": False, "error": repr(exc), "url": url}, ensure_ascii=True, sort_keys=True))
    raise SystemExit(1)
PYGET
}

verify_default_suite() {
  echo "[suite] Suite inicial solicitada: ${DEFAULT_PROMPT_SUITE}"
  PYTHONPATH="$PYTHONPATH_VALUE" "$TK_PYTHON" - "$DEFAULT_PROMPT_SUITE" <<'PYSUITE'
import json
import sys

from orchestrator.prompt_flight_batch import discover_prompt_flight_suites

target = sys.argv[1]
suites = discover_prompt_flight_suites(".")
for suite in suites:
    if target in {str(suite.get("suiteId") or ""), str(suite.get("title") or ""), str(suite.get("domain") or "")}:
        ok = suite.get("status") == "ok"
        print(json.dumps({
            "ok": ok,
            "suiteId": suite.get("suiteId"),
            "title": suite.get("title"),
            "caseCount": suite.get("caseCount"),
            "casePath": suite.get("casePath"),
            "status": suite.get("status"),
            "error": suite.get("error"),
        }, ensure_ascii=True, sort_keys=True))
        raise SystemExit(0 if ok else 1)
print(json.dumps({"ok": False, "error": "suite_not_found", "requestedSuite": target}, ensure_ascii=True, sort_keys=True))
raise SystemExit(1)
PYSUITE
}

print_backend_preflight() {
  echo "[preflight] Health:"
  backend_get_json "$HEALTH_URL" || true
  echo "[preflight] Worker diagnostics:"
  backend_get_json "http://${HEALTH_HOST}:${PORT}/api/continuity-probe/prompt-flight/worker-diagnostics" || true
  echo "[preflight] CyberLACE health:"
  backend_get_json "http://${HEALTH_HOST}:${PORT}/api/cyberlace/health" || true
}

wait_for_backend() {
  echo "[backend] Esperando health: $HEALTH_URL"
  for _ in {1..40}; do
    if healthcheck >/tmp/prompt_flight_healthcheck.json 2>/dev/null; then
      cat /tmp/prompt_flight_healthcheck.json
      rm -f /tmp/prompt_flight_healthcheck.json
      return 0
    fi
    sleep 0.5
  done
  echo "[backend] ERROR: backend no respondio healthcheck. Log: $BACKEND_LOG" >&2
  tail -n 80 "$BACKEND_LOG" >&2 || true
  return 1
}

reuse_existing_backend_if_healthy() {
  local attempts="${1:-20}"
  for _ in $(seq 1 "$attempts"); do
    if healthcheck >/tmp/prompt_flight_healthcheck.json 2>/dev/null; then
      echo "[backend] Backend existente responde; reutilizando http://127.0.0.1:${PORT}."
      cat /tmp/prompt_flight_healthcheck.json
      rm -f /tmp/prompt_flight_healthcheck.json
      return 0
    fi
    sleep 0.5
  done
  rm -f /tmp/prompt_flight_healthcheck.json
  return 1
}

backend_log_has_port_conflict() {
  [[ -f "$BACKEND_LOG" ]] && grep -Eq "Address already in use|Port ${PORT} is in use" "$BACKEND_LOG"
}

start_backend() {
  if reuse_existing_backend_if_healthy 1 >/tmp/prompt_flight_existing_backend.json 2>/dev/null; then
    cat /tmp/prompt_flight_existing_backend.json
    rm -f /tmp/prompt_flight_existing_backend.json
    return 0
  fi
  rm -f /tmp/prompt_flight_existing_backend.json

  echo "[backend] Python: $BACKEND_PYTHON"
  echo "[backend] Log: $BACKEND_LOG"
  if command -v setsid >/dev/null 2>&1; then
    PYTHONPATH="$PYTHONPATH_VALUE" PORT="$PORT" HOST="$HOST" VISTA_CONTROL_PLANE_ENABLED="${VISTA_CONTROL_PLANE_ENABLED:-1}" \
      setsid "$BACKEND_PYTHON" "$ROOT/backend/app.py" >"$BACKEND_LOG" 2>&1 < /dev/null &
  else
    PYTHONPATH="$PYTHONPATH_VALUE" PORT="$PORT" HOST="$HOST" VISTA_CONTROL_PLANE_ENABLED="${VISTA_CONTROL_PLANE_ENABLED:-1}" \
      nohup "$BACKEND_PYTHON" "$ROOT/backend/app.py" >"$BACKEND_LOG" 2>&1 < /dev/null &
  fi
  local pid=$!
  disown "$pid" 2>/dev/null || true
  echo "$pid" > "$PID_FILE"
  echo "[backend] PID nuevo: $pid"
  if wait_for_backend; then
    return 0
  fi

  if backend_log_has_port_conflict; then
    echo "[backend] Puerto ${PORT} ocupado durante el arranque; intentando reutilizar backend sano." >&2
    if reuse_existing_backend_if_healthy 20; then
      return 0
    fi
    echo "[backend] ERROR: el puerto ${PORT} esta ocupado, pero no hay healthcheck sano en ${HEALTH_URL}." >&2
  fi

  return 1
}

launch_tkinter() {
  echo "[tkinter] Python: $TK_PYTHON"
  echo "[tkinter] Backend esperado: http://127.0.0.1:${PORT}"
  echo "[tkinter] Suite inicial: ${DEFAULT_PROMPT_SUITE}"
  echo "[tkinter] Flight mode inicial: ${DEFAULT_PROMPT_MODE}"
  echo "[tkinter] Log: $TK_LOG"
  if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    echo "[tkinter] ADVERTENCIA: no se detecta DISPLAY ni WAYLAND_DISPLAY; si estas por SSH/headless, la ventana no podra abrir." >&2
  fi
  PYTHONPATH="$PYTHONPATH_VALUE" HABLA_PROMPT_FLIGHT_DEFAULT_SUITE="$DEFAULT_PROMPT_SUITE" HABLA_PROMPT_FLIGHT_DEFAULT_MODE="$DEFAULT_PROMPT_MODE" \
    "$TK_PYTHON" "$ROOT/tools/habla_circuit_probe_tk.py" >>"$TK_LOG" 2>&1
  local status=$?
  if [[ "$status" -ne 0 ]]; then
    echo "[tkinter] ERROR: Tkinter cerro con codigo $status. Ultimas lineas del log:" >&2
    tail -n 80 "$TK_LOG" >&2 || true
  fi
  return "$status"
}

MODE="full"
RESTART="1"
LOCAL_WORKER_NO_BWRAP="${VISTA_PROMPT_FLIGHT_LOCAL_NO_BWRAP_DEFAULT:-1}"
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --backend-only)
      MODE="backend-only"
      ;;
    --tk-only)
      MODE="tk-only"
      RESTART="0"
      ;;
    --no-restart)
      RESTART="0"
      ;;
    --local-worker-no-bwrap)
      LOCAL_WORKER_NO_BWRAP="1"
      ;;
    --safe-worker-sandbox)
      LOCAL_WORKER_NO_BWRAP="0"
      export VISTA_CODEX_EXEC_SANDBOX_MODE="${VISTA_CODEX_EXEC_SANDBOX_MODE:-workspace-write}"
      export VISTA_CODEX_EXEC_APPROVAL_POLICY="${VISTA_CODEX_EXEC_APPROVAL_POLICY:-never}"
      unset VISTA_ALLOW_DANGER_FULL_ACCESS_CODEX
      ;;
    --suite)
      shift
      if [[ "$#" -eq 0 || -z "${1:-}" ]]; then
        echo "Falta SUITE_ID despues de --suite" >&2
        usage >&2
        exit 2
      fi
      DEFAULT_PROMPT_SUITE="$1"
      ;;
    --alert-antihack)
      DEFAULT_PROMPT_SUITE="advanced_programming_alert_antihack"
      ;;
    --stop)
      stop_backend
      exit 0
      ;;
    *)
      echo "Argumento desconocido: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$LOCAL_WORKER_NO_BWRAP" == "1" ]]; then
  export VISTA_ALLOW_DANGER_FULL_ACCESS_CODEX=1
  export VISTA_CODEX_EXEC_SANDBOX_MODE=danger-full-access
  export VISTA_CODEX_EXEC_APPROVAL_POLICY=never
  echo "[codex-worker] ADVERTENCIA: modo local confiable sin bubblewrap activo para workers Codex internos."
  echo "[codex-worker] VISTA_CODEX_EXEC_SANDBOX_MODE=danger-full-access, approval=never. No usar en entornos no confiables."
else
  echo "[codex-worker] Modo sandbox seguro solicitado: VISTA_CODEX_EXEC_SANDBOX_MODE=${VISTA_CODEX_EXEC_SANDBOX_MODE:-workspace-write}, approval=${VISTA_CODEX_EXEC_APPROVAL_POLICY:-never}."
fi

export HABLA_PROMPT_FLIGHT_DEFAULT_SUITE="$DEFAULT_PROMPT_SUITE"
export HABLA_PROMPT_FLIGHT_DEFAULT_MODE="$DEFAULT_PROMPT_MODE"

if [[ "$MODE" == "tk-only" ]]; then
  verify_default_suite || true
  print_backend_preflight || true
  launch_tkinter
  exit $?
fi

if [[ "$RESTART" == "1" ]]; then
  stop_backend
  build_frontend_if_needed
else
  if healthcheck >/tmp/prompt_flight_healthcheck.json 2>/dev/null; then
    echo "[backend] Backend existente responde; no se reinicia."
    cat /tmp/prompt_flight_healthcheck.json
    rm -f /tmp/prompt_flight_healthcheck.json
  else
    echo "[backend] No responde backend existente; arrancando uno nuevo."
    build_frontend_if_needed
    start_backend
  fi
fi

if [[ "$RESTART" == "1" ]]; then
  start_backend
fi

verify_default_suite || true
print_backend_preflight || true

if [[ "$MODE" == "backend-only" ]]; then
  echo "[ok] Backend listo en http://127.0.0.1:${PORT}"
  echo "[ok] UI nueva servida por backend: http://127.0.0.1:${PORT}/"
  echo "[nota] Si 5173 muestra otra app, no es esta UI del repo."
  exit 0
fi

launch_tkinter
