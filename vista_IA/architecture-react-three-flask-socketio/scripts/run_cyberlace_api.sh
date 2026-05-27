#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${WORKSPACE_ROOT}/backend"
PORT="${CYBERLACE_PORT:-8088}"
HOST="${CYBERLACE_HOST:-127.0.0.1}"

if [[ -d "${WORKSPACE_ROOT}/.venv" ]]; then
  # shellcheck disable=SC1091
  source "${WORKSPACE_ROOT}/.venv/bin/activate"
elif [[ -d "${WORKSPACE_ROOT}/venv" ]]; then
  # shellcheck disable=SC1091
  source "${WORKSPACE_ROOT}/venv/bin/activate"
fi

export PYTHONPATH="${BACKEND_DIR}:${WORKSPACE_ROOT}:${PYTHONPATH:-}"
export CYBERLACE_CONFIG_PATH="${CYBERLACE_CONFIG_PATH:-${BACKEND_DIR}/cyberlace_config.yaml}"

exec python3 -m uvicorn cyberlace.api.app:app --host "${HOST}" --port "${PORT}"
