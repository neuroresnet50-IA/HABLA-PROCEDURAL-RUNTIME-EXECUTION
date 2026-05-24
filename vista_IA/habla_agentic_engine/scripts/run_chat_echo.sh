#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python -m chat.chat_cli --provider echo --show-debug
