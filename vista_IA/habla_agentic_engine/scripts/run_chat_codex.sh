#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
CODEX_CMD="${1:-codex}"
python -m chat.chat_cli --provider codex --codex-cmd "$CODEX_CMD" --show-debug
