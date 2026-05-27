"""Small YAML fallback for CyberLACE configuration files.

PyYAML is preferred when available. The fallback intentionally supports only the
simple mapping/list/scalar YAML shape used by CyberLACE bundled policies.
"""

from __future__ import annotations

import ast
from typing import Any

try:  # pragma: no cover - exercised only when PyYAML is installed.
    import yaml as _pyyaml
except ImportError:  # pragma: no cover - active in the bundled backend venv.
    _pyyaml = None


def safe_load(stream: Any) -> Any:
    if _pyyaml is not None:
        return _pyyaml.safe_load(stream)
    text = stream.read() if hasattr(stream, 'read') else str(stream or '')
    return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> Any:
    rows: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith('#'):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(' '))
        rows.append((indent, raw_line.strip()))
    if not rows:
        return {}
    value, _ = _parse_block(rows, 0, rows[0][0])
    return value


def _parse_block(rows: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(rows):
        return {}, index
    if rows[index][0] == indent and rows[index][1].startswith('- '):
        values = []
        while index < len(rows) and rows[index][0] == indent and rows[index][1].startswith('- '):
            item = rows[index][1][2:].strip()
            values.append(_parse_scalar(item))
            index += 1
        return values, index

    result: dict[str, Any] = {}
    while index < len(rows):
        current_indent, current = rows[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            break
        if ':' not in current:
            index += 1
            continue
        key, raw_value = current.split(':', 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            result[key] = _parse_scalar(raw_value)
            index += 1
            continue
        next_index = index + 1
        if next_index < len(rows) and rows[next_index][0] > current_indent:
            result[key], index = _parse_block(rows, next_index, rows[next_index][0])
        else:
            result[key] = {}
            index = next_index
    return result, index


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    lower = value.lower()
    if lower in {'true', 'false'}:
        return lower == 'true'
    if lower in {'null', 'none', '~'}:
        return None
    if value and value[0] in {'"', "'"}:
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value.strip('"\'')
    try:
        if any(ch in value for ch in ('.', 'e', 'E')):
            return float(value)
        return int(value)
    except ValueError:
        return value
