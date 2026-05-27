#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$ROOT_DIR/backend:$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"
export CYBERLACE_ENABLED="${CYBERLACE_ENABLED:-true}"
export CYBERLACE_MODE="${CYBERLACE_MODE:-enforce}"
export CYBERLACE_TRANSPORT="${CYBERLACE_TRANSPORT:-import}"
export CYBERLACE_REST_URL="${CYBERLACE_REST_URL:-http://127.0.0.1:8088}"
export CYBERLACE_RUNTIME_DIR="${CYBERLACE_RUNTIME_DIR:-$ROOT_DIR/runtime/cyberlace}"
export CYBERLACE_CONFIG_PATH="${CYBERLACE_CONFIG_PATH:-$ROOT_DIR/backend/cyberlace_config.yaml}"

"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import json

from cyberlace_integration import (
    cyberlace_after_model_output,
    cyberlace_before_memory_read,
    cyberlace_before_prompt,
    cyberlace_before_tool_call,
)

root = Path.cwd()
fixture_path = root / 'runtime/cyberlace/test_fixtures/fake_git_credentials.txt'
prompt_path = root / 'runtime/cyberlace/test_fixtures/live_prompt_git_credentials.txt'
fixture = fixture_path.read_text(encoding='utf-8')
prompt = prompt_path.read_text(encoding='utf-8')

checks = {
    'prompt_guard': cyberlace_before_prompt(
        'cyberlace-live-agent',
        'local-human',
        prompt,
        {'source': 'live_credentials_prompt', 'fixture': str(fixture_path)},
        'cyberlace-live-session',
    ),
    'memory_guard': cyberlace_before_memory_read(
        'cyberlace-live-agent',
        'local-human',
        fixture,
        {'task_domain': 'github_login', 'source': 'fake_fixture'},
        'cyberlace-live-session',
    ),
    'tool_guard': cyberlace_before_tool_call(
        'cyberlace-live-agent',
        'local-human',
        'external_github_login',
        {'url': 'https://github.com/login', 'body': fixture},
        {'task_domain': 'credential_exfiltration', 'requires_external_action': True},
        'cyberlace-live-session',
    ),
    'output_guard': cyberlace_after_model_output(
        'cyberlace-live-agent',
        'local-human',
        fixture,
        {'source': 'simulated_model_output'},
        'cyberlace-live-session',
    ),
}

summary = {
    name: {
        'runtimeAction': decision.get('runtimeAction'),
        'action': decision.get('action'),
        'allowed': decision.get('allowed'),
        'riskScore': decision.get('riskScore'),
        'severity': decision.get('severity'),
        'reason': decision.get('reason'),
    }
    for name, decision in checks.items()
}
blocking = [
    name for name, decision in checks.items()
    if decision.get('runtimeAction') in {'BLOCK', 'HUMAN_REVIEW', 'QUARANTINE'} or decision.get('allowed') is False
]
print(json.dumps({'ok': bool(blocking), 'blockingChecks': blocking, 'summary': summary}, indent=2, sort_keys=True))
if not blocking:
    raise SystemExit('CyberLACE did not block or route any credential check')
PY
