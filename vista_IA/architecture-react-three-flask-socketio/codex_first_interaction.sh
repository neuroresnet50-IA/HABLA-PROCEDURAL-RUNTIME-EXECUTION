#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

/home/neurodriver/ferrari_env/bin/python -m orchestrator.first_interaction --workspace .
