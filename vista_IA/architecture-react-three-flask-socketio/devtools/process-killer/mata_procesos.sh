#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
PID_DIR="$RUNTIME_DIR/pids"

DEFAULT_PORTS=(5000 5173 4173)
KNOWN_PID_FILES=(
  "$PID_DIR/backend.pid"
  "$PID_DIR/frontend.pid"
)

HOLD_OPEN=0
DRY_RUN="${DRY_RUN:-0}"
PORTS=()

print_banner() {
  printf '\n%s\n' "Mata Procesos Vista IA"
  printf '%s\n\n' "root: $ROOT_DIR"
}

usage() {
  cat <<'EOF'
Uso:
  ./mata_procesos.sh
  ./mata_procesos.sh 5000 5173 8000
  ./mata_procesos.sh --hold
  DRY_RUN=1 ./mata_procesos.sh

Que hace:
  - intenta detener los PIDs conocidos del proyecto
  - libera puertos 5000, 5173 y 4173 por defecto
  - limpia archivos PID viejos en .runtime/pids

Opciones:
  --hold   deja la terminal abierta al terminar
  -h       muestra esta ayuda
EOF
}

pause_if_requested() {
  if [[ "$HOLD_OPEN" == "1" ]]; then
    printf '\n%s' "Presiona Enter para cerrar..."
    read -r _
  fi
}

is_pid_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid_file() {
  local file_path="$1"
  if [[ -f "$file_path" ]]; then
    tr -d '[:space:]' < "$file_path"
  fi
}

cleanup_pid_file() {
  local file_path="$1"
  if [[ -f "$file_path" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      printf '%s\n' "[dry-run] pid file quedaria limpiado: $file_path"
      return 0
    fi
    rm -f "$file_path"
    printf '%s\n' "pid file limpiado: $file_path"
  fi
}

signal_pid() {
  local pid="$1"
  local signal_name="$2"
  local signal_number="$3"

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '%s\n' "[dry-run] kill -$signal_name $pid"
    return 0
  fi

  kill "-$signal_number" "$pid" 2>/dev/null || true
}

wait_until_stopped() {
  local pid="$1"
  local seconds="${2:-3}"
  local step

  for ((step = 0; step < seconds; step++)); do
    if ! is_pid_running "$pid"; then
      return 0
    fi
    sleep 1
  done

  ! is_pid_running "$pid"
}

stop_pid() {
  local pid="$1"
  local source_label="$2"

  if ! is_pid_running "$pid"; then
    printf '%s\n' "$source_label: PID $pid ya no estaba activo"
    return 0
  fi

  printf '%s\n' "$source_label: enviando TERM a PID $pid"
  signal_pid "$pid" "TERM" 15
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '%s\n' "$source_label: simulacion completada"
    return 0
  fi
  if wait_until_stopped "$pid" 3; then
    printf '%s\n' "$source_label: PID $pid detenido"
    return 0
  fi

  printf '%s\n' "$source_label: enviando KILL a PID $pid"
  signal_pid "$pid" "KILL" 9
  if wait_until_stopped "$pid" 2; then
    printf '%s\n' "$source_label: PID $pid detenido por KILL"
    return 0
  fi

  printf '%s\n' "$source_label: no se pudo detener PID $pid"
  return 1
}

collect_port_pids_with_lsof() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

collect_port_pids_with_fuser() {
  local port="$1"
  fuser "${port}/tcp" 2>/dev/null | tr ' ' '\n' | sed '/^$/d' || true
}

collect_port_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    collect_port_pids_with_lsof "$port"
    return 0
  fi

  if command -v fuser >/dev/null 2>&1; then
    collect_port_pids_with_fuser "$port"
    return 0
  fi

  return 0
}

stop_known_pid_files() {
  local pid_file pid label
  for pid_file in "${KNOWN_PID_FILES[@]}"; do
    label="$(basename "$pid_file" .pid)"
    pid="$(read_pid_file "$pid_file")"

    if [[ -z "$pid" ]]; then
      cleanup_pid_file "$pid_file"
      continue
    fi

    stop_pid "$pid" "pid-file:$label" || true
    cleanup_pid_file "$pid_file"
  done
}

stop_listeners_by_port() {
  local port pid
  local -A seen=()
  local found_any=0

  for port in "${PORTS[@]}"; do
    mapfile -t port_pids < <(collect_port_pids "$port")
    if [[ "${#port_pids[@]}" -eq 0 ]]; then
      printf '%s\n' "puerto $port: libre"
      continue
    fi

    found_any=1
    printf '%s\n' "puerto $port: procesos detectados -> ${port_pids[*]}"
    for pid in "${port_pids[@]}"; do
      if [[ -z "$pid" || -n "${seen[$pid]:-}" ]]; then
        continue
      fi
      seen[$pid]=1
      stop_pid "$pid" "puerto:$port" || true
    done
  done

  if [[ "$found_any" == "0" ]]; then
    printf '%s\n' "no se detectaron listeners en los puertos objetivo"
  fi
}

parse_args() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --hold)
        HOLD_OPEN=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        PORTS+=("$1")
        ;;
    esac
    shift
  done

  if [[ "${#PORTS[@]}" -eq 0 ]]; then
    PORTS=("${DEFAULT_PORTS[@]}")
  fi
}

main() {
  parse_args "$@"
  print_banner
  printf '%s\n' "puertos objetivo: ${PORTS[*]}"
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '%s\n' "modo: dry-run"
  fi
  printf '\n'

  mkdir -p "$PID_DIR"
  stop_known_pid_files
  stop_listeners_by_port

  printf '\n%s\n' "limpieza finalizada"
  pause_if_requested
}

main "$@"
