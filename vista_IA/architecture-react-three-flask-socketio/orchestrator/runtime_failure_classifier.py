"""Classify runtime failures that retries cannot fix.

These helpers are intentionally small and dependency-free so worker, recovery
and Prompt Flight code can agree on infrastructure failures without importing
large runtime modules.
"""

from __future__ import annotations

from typing import Any

INFRASTRUCTURE_FAILURE_MARKERS = (
    "bwrap: loopback",
    "failed rtm_newaddr",
    "operation not permitted",
    "codex's linux sandbox uses bubblewrap",
    "bubblewrap",
    "user namespaces",
    "failed to write file /tmp/codex_write_probe",
    "failed to write file",
    "apply_patch no pudo escribir",
    "todos los comandos locales fallan",
)

FATAL_INFRASTRUCTURE_MARKERS = (
    "bwrap: loopback",
    "failed rtm_newaddr",
    "codex's linux sandbox uses bubblewrap",
    "user namespaces",
    "failed to write file /tmp/codex_write_probe",
    "todos los comandos locales fallan",
)


def runtime_failure_signal_lines(text: str) -> list[str]:
    """Return only lines that look like fresh runtime failure signals.

    Worker stdout/stderr can contain generated Markdown, context summaries and
    diffs from files such as recuperacioncontexto.md. Those documents may quote
    old bwrap failures. A quoted historical marker is not evidence that the
    current child process failed.
    """

    signals: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if not any(marker in lowered for marker in INFRASTRUCTURE_FAILURE_MARKERS):
            continue
        if _is_diff_or_context_line(lowered):
            continue
        if _looks_like_runtime_signal(lowered):
            signals.append(line)
    return signals


def runtime_failure_text(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            parts.extend(_walk_strings(value))
        elif isinstance(value, list):
            parts.extend(_walk_strings(value))
        else:
            parts.append(str(value))
    signal_parts: list[str] = []
    for part in parts:
        signal_parts.extend(runtime_failure_signal_lines(part))
    return " ".join(part for part in signal_parts if part).lower()


def classify_runtime_failure(*values: Any) -> dict[str, Any]:
    text = runtime_failure_text(*values)
    markers = [marker for marker in INFRASTRUCTURE_FAILURE_MARKERS if marker in text]
    fatal_markers = [marker for marker in FATAL_INFRASTRUCTURE_MARKERS if marker in text]
    return {
        "infrastructureFailure": bool(markers),
        "fatalInfrastructureFailure": bool(fatal_markers),
        "markers": markers,
        "fatalMarkers": fatal_markers,
    }


def _walk_strings(value: Any) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        items.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            items.extend(_walk_strings(item))
    elif isinstance(value, list):
        for item in value:
            items.extend(_walk_strings(item))
    return items


def _is_diff_or_context_line(line: str) -> bool:
    stripped = line.lstrip()
    if stripped.startswith(("+++", "---", "@@", "diff --git ", "index ")):
        return True
    if stripped.startswith(("+", "-")):
        body = stripped[1:].strip()
        # Diff/context lines commonly quote old diagnostics inside docs,
        # markdown bullets or JSON snippets. Actual process stderr does not
        # need a diff prefix to be classified.
        if body.startswith(("*", "-", "`", '"')) or " bwrap" in body or "bwrap:" in body:
            return True
    historical_terms = (
        "visto en",
        "fallo anterior",
        "falla anterior",
        "historial",
        "contexto",
        "recuperacioncontexto",
        "ultimo contexto",
        "quoted",
        "example",
    )
    return any(term in stripped for term in historical_terms)


def _looks_like_runtime_signal(line: str) -> bool:
    if line.startswith("bwrap:"):
        return True
    strong_fragments = (
        "failed rtm_newaddr",
        "operation not permitted",
        "exec_command failed",
        "every exec_command failed",
        "worker infrastructure failure",
        "codex's linux sandbox uses bubblewrap",
        "failed to write file /tmp/codex_write_probe",
        "apply_patch no pudo escribir",
        "todos los comandos locales fallan",
    )
    return any(fragment in line for fragment in strong_fragments)
