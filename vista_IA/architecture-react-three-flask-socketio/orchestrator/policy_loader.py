"""Load AGENTS.md as structured repository policy for the control plane."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


POLICY_FILE = "AGENTS.md"


class PolicyLoadError(RuntimeError):
    """Raised when the policy document cannot be loaded or parsed."""

    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path
        self.message = message

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "path": self.path}


def load_policy(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Load and normalize AGENTS.md from the real repository root."""

    root = _repo_root(repo_root)
    path = root / POLICY_FILE
    text = _read_markdown(path)
    sections = _parse_sections(text)

    policy = {
        "source_path": str(path),
        "document": POLICY_FILE,
        "repository_purpose": _section_text(sections, "Propósito del repositorio"),
        "central_thesis": _section_text(sections, "Tesis central"),
        "system_identity": _section_text(sections, "Identidad del sistema"),
        "master_rules": _section_list(sections, "Reglas maestras"),
        "runtime_hard_rules": _section_list(sections, "Reglas duras del runtime"),
        "directive_policy": _section_list(sections, "Política de directivas operativas"),
        "expected_project_structure": _section_code_block(
            sections,
            "Estructura esperada del proyecto",
        ),
        "mandatory_benchmarks": _section_list(sections, "Benchmarks obligatorios"),
        "implementation_policy": _section_list(sections, "Política de implementación"),
        "sprint_delivery_policy": _section_list(sections, "Política de entrega por sprint"),
        "sections": sections,
    }
    _validate_policy(policy, path)
    return policy


def current_policy(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Return the current repository policy."""

    return load_policy(repo_root)


def get_policy_section(policy: dict[str, Any], key: str) -> Any:
    """Return a normalized policy field by key."""

    if key not in policy:
        raise PolicyLoadError("missing_policy_key", f"Policy key not found: {key}")
    return policy[key]


def _repo_root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]


def _read_markdown(path: Path) -> str:
    if not path.exists():
        raise PolicyLoadError("missing_policy_file", f"Policy file does not exist: {path}", path=str(path))
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise PolicyLoadError("empty_policy_file", f"Policy file is empty: {path}", path=str(path))
    return text


def _parse_sections(text: str) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    current_title: str | None = None
    current_level: int | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        match = re.match(r"^(#{2,3})\s+(.+?)\s*$", line)
        if match:
            if current_title is not None:
                sections[current_title] = _normalize_section(current_title, current_level or 0, current_lines)
            current_level = len(match.group(1))
            current_title = match.group(2).strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections[current_title] = _normalize_section(current_title, current_level or 0, current_lines)
    if not sections:
        raise PolicyLoadError("malformed_policy_file", "Policy file has no markdown sections")
    return sections


def _normalize_section(title: str, level: int, lines: list[str]) -> dict[str, Any]:
    body = "\n".join(lines).strip()
    return {
        "title": title,
        "level": level,
        "text": _strip_code_blocks(body).strip(),
        "items": _extract_list_items(lines),
        "code_blocks": _extract_code_blocks(body),
    }


def _section_text(sections: dict[str, dict[str, Any]], title: str) -> str:
    section = _require_section(sections, title)
    return section["text"]


def _section_list(sections: dict[str, dict[str, Any]], title: str) -> list[str]:
    section = _require_section(sections, title)
    return section["items"]


def _section_code_block(sections: dict[str, dict[str, Any]], title: str) -> str:
    section = _require_section(sections, title)
    blocks = section["code_blocks"]
    return blocks[0] if blocks else ""


def _require_section(sections: dict[str, dict[str, Any]], title: str) -> dict[str, Any]:
    if title not in sections:
        raise PolicyLoadError("missing_policy_section", f"Policy section not found: {title}")
    return sections[title]


def _extract_list_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.+?)\s*$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def _extract_code_blocks(body: str) -> list[str]:
    return [match.group(1).strip("\n") for match in re.finditer(r"```(?:\w+)?\n(.*?)```", body, re.S)]


def _strip_code_blocks(body: str) -> str:
    return re.sub(r"```(?:\w+)?\n.*?```", "", body, flags=re.S)


def _validate_policy(policy: dict[str, Any], path: Path) -> None:
    if not policy["repository_purpose"]:
        raise PolicyLoadError("invalid_policy", "Repository purpose is empty", path=str(path))
    if not policy["central_thesis"]:
        raise PolicyLoadError("invalid_policy", "Central thesis is empty", path=str(path))
    if not policy["master_rules"]:
        raise PolicyLoadError("invalid_policy", "Master rules are missing", path=str(path))
    if not policy["runtime_hard_rules"]:
        raise PolicyLoadError("invalid_policy", "Runtime hard rules are missing", path=str(path))
    if not policy["mandatory_benchmarks"]:
        raise PolicyLoadError("invalid_policy", "Mandatory benchmarks are missing", path=str(path))
