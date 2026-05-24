#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALLER_VENV="${APP_ROOT}/.installer-venv"
PAUSE_ON_EXIT="${HABLA_INSTALLER_NO_PAUSE:-0}"

pause_if_needed() {
  if [[ "${PAUSE_ON_EXIT}" != "1" && -t 0 ]]; then
    printf "\nPresiona Enter para cerrar el instalador..."
    read -r _ || true
  fi
}

fail() {
  local exit_code=$?
  echo
  echo "HABLA installer fallo con codigo ${exit_code}."
  echo "Revisa installer/logs/ o copia este mensaje para diagnostico."
  pause_if_needed
  exit "${exit_code}"
}

trap fail ERR

cd "${APP_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required before running the HABLA installer."
  exit 1
fi

python3 -m venv "${INSTALLER_VENV}"
"${INSTALLER_VENV}/bin/python" -m pip install --upgrade pip --quiet
"${INSTALLER_VENV}/bin/python" -m pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet

ARGS=("$@")
has_arg() {
  local wanted="$1"
  for arg in "${ARGS[@]}"; do
    [[ "${arg}" == "${wanted}" || "${arg}" == "${wanted}="* ]] && return 0
  done
  return 1
}

has_smart_input=0
if has_arg "--requirement" || has_arg "--from-requirement" || has_arg "--recipe" || has_arg "--ask"; then
  has_smart_input=1
fi

if [[ "${#ARGS[@]}" == "0" ]]; then
  ARGS=("--ask" "--execute" "--allow-system")
  has_smart_input=1
fi
if [[ "${has_smart_input}" == "0" ]] && ! has_arg "--profile" && ! has_arg "--execute"; then
  ARGS=("--ask" "--execute" "--allow-system" "${ARGS[@]}")
  has_smart_input=1
fi
if [[ "${has_smart_input}" == "1" ]] && ! has_arg "--execute"; then
  ARGS=("--execute" "${ARGS[@]}")
fi
if [[ "${has_smart_input}" == "1" ]] && ! has_arg "--allow-system"; then
  ARGS=("--allow-system" "${ARGS[@]}")
fi
if [[ "${HABLA_INSTALLER_NO_PAUSE:-0}" != "1" ]]; then
  ARGS+=("--pause")
fi

"${INSTALLER_VENV}/bin/python" "${SCRIPT_DIR}/habla_observer_installer.py" "${ARGS[@]}"
