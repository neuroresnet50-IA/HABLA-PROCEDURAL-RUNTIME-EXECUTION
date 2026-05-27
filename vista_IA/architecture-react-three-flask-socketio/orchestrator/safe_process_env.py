"""Safe environment builder for child agent processes.

The runtime must not pass backend credentials, API keys, database URLs, cookies,
or operator approval secrets into Codex workers. This module keeps only a small
allowlist plus explicit non-secret VISTA_AGENT metadata.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

DEFAULT_SAFE_ENV_KEYS = {
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM", "COLORTERM",
    "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "TMPDIR", "TEMP", "TMP",
    "NO_COLOR", "FORCE_COLOR", "CODEX_HOME",
}
EXPLICIT_SAFE_KEYS = {
    "VISTA_AGENT_SESSION_ID",
    "VISTA_AGENT_PROJECT_SLUG",
    "VISTA_AGENT_PROJECT_DIR",
    "VISTA_AGENT_EVENT_FILE",
    "VISTA_AGENT_BRIDGE",
    "VISTA_CONTROL_PLANE_RUNTIME_DIR",
    "VISTA_CODEX_SAFE_ENV_ALLOWLIST",
}
SAFE_PREFIXES = ("VISTA_AGENT_",)
SENSITIVE_ENV_RE = re.compile(
    r"(PASSWORD|PASSWD|SECRET|TOKEN|API[_-]?KEY|PRIVATE[_-]?KEY|CREDENTIAL|AUTH|COOKIE|JWT|DATABASE[_-]?URL|POSTGRES|MYSQL|REDIS|AWS_|AZURE_|GCP_|GOOGLE_|GITHUB|GITLAB|NPM[_-]?TOKEN|SLACK|STRIPE|PAYPAL|TWILIO|SENDGRID|SMTP|SSH)",
    re.IGNORECASE,
)


def is_sensitive_env_name(name: str) -> bool:
    if name in EXPLICIT_SAFE_KEYS or any(name.startswith(prefix) for prefix in SAFE_PREFIXES):
        return False
    return bool(SENSITIVE_ENV_RE.search(name))


def _configured_allowlist(base: Mapping[str, str]) -> set[str]:
    raw = str(base.get("VISTA_CODEX_SAFE_ENV_ALLOWLIST") or os.environ.get("VISTA_CODEX_SAFE_ENV_ALLOWLIST") or "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def safe_child_process_env(
    base: Mapping[str, str] | None = None,
    *,
    extra: Mapping[str, str] | None = None,
    allowlist: set[str] | None = None,
) -> dict[str, str]:
    """Return an allowlisted environment with sensitive variable names removed."""

    source = dict(os.environ if base is None else base)
    allowed = set(DEFAULT_SAFE_ENV_KEYS)
    allowed.update(EXPLICIT_SAFE_KEYS)
    allowed.update(_configured_allowlist(source))
    if allowlist:
        allowed.update(allowlist)

    env: dict[str, str] = {}
    for raw_key, raw_value in source.items():
        key = str(raw_key)
        if key not in allowed and not any(key.startswith(prefix) for prefix in SAFE_PREFIXES):
            continue
        if is_sensitive_env_name(key):
            continue
        env[key] = str(raw_value)

    if extra:
        for raw_key, raw_value in extra.items():
            key = str(raw_key)
            if is_sensitive_env_name(key):
                continue
            env[key] = str(raw_value)
    return env
