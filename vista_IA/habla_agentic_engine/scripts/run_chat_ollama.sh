#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
MODEL="${1:-gemma:2b}"
python -m chat.chat_cli --provider ollama --model "$MODEL" --show-debug
