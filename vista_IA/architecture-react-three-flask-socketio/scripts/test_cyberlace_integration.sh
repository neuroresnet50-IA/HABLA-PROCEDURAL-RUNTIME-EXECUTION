#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${WORKSPACE_ROOT}"

export PYTHONPATH="${WORKSPACE_ROOT}/backend:${WORKSPACE_ROOT}:${PYTHONPATH:-}"

python3 -B -m py_compile   backend/cyberlace_integration.py   backend/cyberlace_routes.py   backend/cyberlace_policy_bridge.py   backend/agent_runtime.py   backend/cyberlace/supervisor/lace_security_supervisor.py

python3 -m unittest   backend.test_cyberlace_integration   backend.test_cyberlace_routes   backend.test_cyberlace_agent_runtime_hooks

python3 -m unittest   backend.test_security_policy   backend.test_validator_security   backend.test_runtime_boundary   backend.test_agent_runtime_habla
