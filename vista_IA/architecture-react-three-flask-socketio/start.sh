#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"
RUNTIME_DIR="$ROOT_DIR/.runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_DIR="$RUNTIME_DIR/pids"
BACKEND_ENV_FILE="$BACKEND_DIR/.env"
export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

load_backend_env() {
  if [[ -f "$BACKEND_ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$BACKEND_ENV_FILE"
    set +a
  fi
}

load_backend_env

PYTHON_BIN="${PYTHON_BIN:-/home/neurodriver/ferrari_env/bin/python}"
DEFAULT_NODE_BIN_DIR="/home/neurodriver/Downloads/node-v24.14.1-linux-x64/bin"
if [[ ! -x "$DEFAULT_NODE_BIN_DIR/npm" ]]; then
  DEFAULT_NODE_BIN_DIR="$(dirname "$(command -v npm 2>/dev/null || printf "/usr/local/bin/npm")")"
fi
NODE_BIN_DIR="${NODE_BIN_DIR:-$DEFAULT_NODE_BIN_DIR}"
NPM_BIN="${NPM_BIN:-$NODE_BIN_DIR/npm}"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

BACKEND_HOST="${BACKEND_HOST:-${HOST:-0.0.0.0}}"
BACKEND_PORT="${BACKEND_PORT:-${PORT:-5001}}"
APP_URL="${APP_URL:-http://127.0.0.1:${BACKEND_PORT}/}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:${BACKEND_PORT}/api/architecture}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173/}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
SERVE_MODE="${SERVE_MODE:-bundle}"

mkdir -p "$LOG_DIR" "$PID_DIR"

print_banner() {
  printf '\n%s\n' "Vista IA Launcher"
  printf '%s\n\n' "root: $ROOT_DIR"
}

is_pid_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
  local file_path="$1"
  if [[ -f "$file_path" ]]; then
    tr -d '[:space:]' < "$file_path"
  fi
}

cleanup_pid_file() {
  local file_path="$1"
  if [[ -f "$file_path" ]]; then
    rm -f "$file_path"
  fi
}

pid_cmdline() {
  local pid="${1:-}"
  if [[ -n "$pid" && -r "/proc/$pid/cmdline" ]]; then
    tr '\0' ' ' < "/proc/$pid/cmdline"
  fi
}

is_our_backend_pid() {
  local pid="${1:-}" cmdline
  is_pid_running "$pid" || return 1
  cmdline="$(pid_cmdline "$pid")"
  [[ "$cmdline" == *"$BACKEND_DIR/app.py"* || "$cmdline" == *"backend/app.py"* ]]
}

find_listening_pid() {
  local port="$1" line
  if command -v ss >/dev/null 2>&1; then
    line="$(ss -ltnp "sport = :$port" 2>/dev/null | awk 'NR > 1 {print; exit}')"
    if [[ "$line" =~ pid=([0-9]+) ]]; then
      printf '%s\n' "${BASH_REMATCH[1]}"
      return
    fi
  fi

  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1
  fi
}

reattach_backend_if_running() {
  local current_pid port_pid
  current_pid="$(read_pid "$BACKEND_PID_FILE")"
  if is_our_backend_pid "$current_pid"; then
    printf '%s\n' "$current_pid"
    return 0
  fi

  port_pid="$(find_listening_pid "$BACKEND_PORT")"
  if is_our_backend_pid "$port_pid"; then
    printf '%s\n' "$port_pid" > "$BACKEND_PID_FILE"
    printf '%s\n' "$port_pid"
    return 0
  fi

  return 1
}

start_backend() {
  local current_pid port_pid
  if current_pid="$(reattach_backend_if_running)"; then
    printf '%s\n' "backend ya esta corriendo con PID $current_pid"
    return
  fi

  cleanup_pid_file "$BACKEND_PID_FILE"
  : > "$BACKEND_LOG"
  (
    cd "$ROOT_DIR"
    PATH="$NODE_BIN_DIR:$PATH" NODE_BIN="$NODE_BIN_DIR/node" HOST="$BACKEND_HOST" PORT="$BACKEND_PORT" \
      NEURO_LACE_SOCKET_ASYNC_MODE="${NEURO_LACE_SOCKET_ASYNC_MODE:-threading}" \
      NEURO_LACE_SOCKET_POLLING_ONLY="${NEURO_LACE_SOCKET_POLLING_ONLY:-1}" \
      setsid "$PYTHON_BIN" "$BACKEND_DIR/app.py" >> "$BACKEND_LOG" 2>&1 < /dev/null &
    echo $! > "$BACKEND_PID_FILE"
  )
  sleep 2
  current_pid="$(read_pid "$BACKEND_PID_FILE")"
  if is_pid_running "$current_pid"; then
    printf '%s\n' "backend iniciado con PID $current_pid"
  else
    port_pid="$(find_listening_pid "$BACKEND_PORT")"
    if [[ -n "$port_pid" ]]; then
      printf '%s\n' "backend no pudo iniciar porque el puerto $BACKEND_PORT esta ocupado por PID $port_pid. Revisa $BACKEND_LOG"
      exit 1
    fi
    printf '%s\n' "backend no pudo iniciar. Revisa $BACKEND_LOG"
    exit 1
  fi
}

build_frontend_bundle() {
  : > "$FRONTEND_LOG"
  (
    cd "$FRONTEND_DIR"
    PATH="$NODE_BIN_DIR:$PATH" "$NPM_BIN" run build >> "$FRONTEND_LOG" 2>&1
  )
  if [[ -f "$FRONTEND_DIR/dist/index.html" ]]; then
    printf '%s\n' "frontend compilado en $FRONTEND_DIR/dist"
  else
    printf '%s\n' "frontend no pudo compilar. Revisa $FRONTEND_LOG"
    exit 1
  fi
}

start_frontend_dev() {
  local current_pid
  current_pid="$(read_pid "$FRONTEND_PID_FILE")"
  if is_pid_running "$current_pid"; then
    printf '%s\n' "frontend ya esta corriendo con PID $current_pid"
    return
  fi

  cleanup_pid_file "$FRONTEND_PID_FILE"
  : > "$FRONTEND_LOG"
  (
    cd "$FRONTEND_DIR"
    VITE_SOCKET_URL="${VITE_SOCKET_URL:-http://127.0.0.1:${BACKEND_PORT}}" \
      PATH="$NODE_BIN_DIR:$PATH" \
      nohup "$NPM_BIN" run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" >> "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )
  sleep 2
  current_pid="$(read_pid "$FRONTEND_PID_FILE")"
  if is_pid_running "$current_pid"; then
    printf '%s\n' "frontend iniciado con PID $current_pid"
  else
    printf '%s\n' "frontend no pudo iniciar. Revisa $FRONTEND_LOG"
    exit 1
  fi
}

stop_process() {
  local name="$1"
  local pid_file="$2"
  local current_pid
  current_pid="$(read_pid "$pid_file")"

  if ! is_pid_running "$current_pid"; then
    cleanup_pid_file "$pid_file"
    printf '%s\n' "$name ya estaba detenido"
    return
  fi

  kill "$current_pid" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    if ! is_pid_running "$current_pid"; then
      break
    fi
    sleep 1
  done

  if is_pid_running "$current_pid"; then
    kill -9 "$current_pid" 2>/dev/null || true
  fi

  cleanup_pid_file "$pid_file"
  printf '%s\n' "$name detenido"
}

stop_backend() {
  local current_pid
  if current_pid="$(reattach_backend_if_running)"; then
    printf '%s\n' "backend detectado con PID $current_pid"
  fi
  stop_process "backend" "$BACKEND_PID_FILE"
}

show_status() {
  local backend_pid frontend_pid
  backend_pid="$(read_pid "$BACKEND_PID_FILE")"
  if ! is_our_backend_pid "$backend_pid"; then
    backend_pid="$(reattach_backend_if_running || true)"
  fi
  frontend_pid="$(read_pid "$FRONTEND_PID_FILE")"

  if is_our_backend_pid "$backend_pid"; then
    printf '%s\n' "backend: activo (PID $backend_pid)"
  else
    printf '%s\n' "backend: detenido"
  fi

  if [[ "$SERVE_MODE" == "bundle" ]]; then
    if [[ -f "$FRONTEND_DIR/dist/index.html" ]]; then
      printf '%s\n' "frontend: compilado y servido por backend"
    else
      printf '%s\n' "frontend: dist ausente"
    fi
  elif is_pid_running "$frontend_pid"; then
    printf '%s\n' "frontend: activo (PID $frontend_pid)"
  else
    printf '%s\n' "frontend: detenido"
  fi

  printf '\n%s\n' "urls:"
  printf '  - %s\n' "$APP_URL"
  printf '  - %s\n' "$BACKEND_URL"
  if [[ "$SERVE_MODE" == "dev" ]]; then
    printf '  - %s\n' "$FRONTEND_URL"
  fi
  printf '\n%s\n' "logs:"
  printf '  - %s\n' "$BACKEND_LOG"
  printf '  - %s\n' "$FRONTEND_LOG"
}

show_logs() {
  touch "$BACKEND_LOG" "$FRONTEND_LOG"
  tail -n 80 -f "$BACKEND_LOG" "$FRONTEND_LOG"
}

open_browser() {
  if [[ "$OPEN_BROWSER" != "1" ]]; then
    printf '%s\n' "apertura automatica del navegador desactivada"
    return
  fi

  sleep 2

  if command -v xdg-open >/dev/null 2>&1; then
    nohup xdg-open "$APP_URL" >/dev/null 2>&1 &
    printf '%s\n' "abriendo navegador en $APP_URL"
    return
  fi

  if command -v gio >/dev/null 2>&1; then
    nohup gio open "$APP_URL" >/dev/null 2>&1 &
    printf '%s\n' "abriendo navegador en $APP_URL"
    return
  fi

  if command -v sensible-browser >/dev/null 2>&1; then
    nohup sensible-browser "$APP_URL" >/dev/null 2>&1 &
    printf '%s\n' "abriendo navegador en $APP_URL"
    return
  fi

  printf '%s\n' "no encontre un abridor grafico automatico. Abre manualmente: $APP_URL"
}

start_all() {
  print_banner
  if [[ "$SERVE_MODE" == "bundle" ]]; then
    stop_process "frontend" "$FRONTEND_PID_FILE"
    build_frontend_bundle
  fi
  start_backend
  if [[ "$SERVE_MODE" == "dev" ]]; then
    start_frontend_dev
  fi
  open_browser
  printf '\n%s\n' "sistema listo"
  show_status
}

stop_all() {
  print_banner
  stop_process "frontend" "$FRONTEND_PID_FILE"
  stop_backend
}

restart_all() {
  stop_all
  start_all
}

usage() {
  cat <<'EOF'
Uso:
  ./start.sh start
  ./start.sh stop
  ./start.sh restart
  ./start.sh status
  ./start.sh logs
  ./start.sh dev

Variables opcionales:
  PYTHON_BIN=/ruta/python
  NODE_BIN_DIR=/ruta/node/bin
  NPM_BIN=/ruta/npm
  APP_URL=http://127.0.0.1:5001/
  BACKEND_HOST=0.0.0.0
  BACKEND_PORT=5001
  FRONTEND_HOST=127.0.0.1
  FRONTEND_PORT=5173
  OPEN_BROWSER=0
  SERVE_MODE=bundle
EOF
}

case "${1:-start}" in
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    restart_all
    ;;
  status)
    print_banner
    show_status
    ;;
  logs)
    show_logs
    ;;
  dev)
    SERVE_MODE="dev"
    start_all
    ;;
  *)
    usage
    exit 1
    ;;
esac
