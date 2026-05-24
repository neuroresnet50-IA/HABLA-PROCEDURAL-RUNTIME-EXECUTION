#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

export HABLA_INSTALLER_NO_PAUSE="${HABLA_INSTALLER_NO_PAUSE:-0}"

exec ./installer/install.sh --profile full --execute --allow-system "$@"
