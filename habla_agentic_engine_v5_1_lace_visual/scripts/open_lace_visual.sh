#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HTML="$ROOT/docs/visual/lace_system_diagram.html"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$HTML"
elif command -v open >/dev/null 2>&1; then
  open "$HTML"
else
  echo "Abre manualmente: $HTML"
fi
