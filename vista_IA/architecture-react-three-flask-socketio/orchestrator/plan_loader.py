"""Load PLANS.md as structured roadmap data for the control plane."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


PLAN_FILE = "PLANS.md"


class PlanLoadError(RuntimeError):
    """Raised when the roadmap document cannot be loaded or parsed."""

    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path
        self.message = message

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "path": self.path}


def load_plan(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Load and normalize PLANS.md from the real repository root."""

    root = _repo_root(repo_root)
    path = root / PLAN_FILE
    text = _read_markdown(path)
    sections = _parse_sections(text)
    plan = {
        "source_path": str(path),
        "document": PLAN_FILE,
        "project_vision": _section_text(sections, "Visión del proyecto"),
        "problem": _section_items_or_text(sections, "Problema actual"),
        "operational_thesis": _section_text(sections, "Nueva tesis operativa"),
        "expected_result": _section_items_or_text(sections, "Resultado esperado"),
        "phases": _parse_phases(text),
        "modules": _parse_modules(text),
        "sprints": _parse_sprints(text),
        "official_benchmarks": _section_list(sections, "Benchmarks oficiales"),
        "deployment_rule": _section_text(sections, "Regla de despliegue"),
        "sections": sections,
    }
    _validate_plan(plan, path)
    return plan


def current_plan(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Return the current roadmap."""

    return load_plan(repo_root)


def get_sprint(plan: dict[str, Any], sprint_number: int) -> dict[str, Any]:
    """Return one sprint by number."""

    key = str(sprint_number)
    sprints = plan.get("sprints", {})
    if key not in sprints:
        raise PlanLoadError("missing_sprint", f"Sprint not found: {sprint_number}")
    return sprints[key]


def get_sprint_deliverables(plan: dict[str, Any], sprint_number: int) -> list[str]:
    return list(get_sprint(plan, sprint_number)["deliverables"])


def get_sprint_acceptance(plan: dict[str, Any], sprint_number: int) -> list[str]:
    return list(get_sprint(plan, sprint_number)["acceptance"])


def get_next_sprint(
    plan: dict[str, Any],
    *,
    completed_sprints: list[int] | set[int] | None = None,
) -> dict[str, Any] | None:
    """Return the first sprint not listed in completed_sprints."""

    completed = {int(item) for item in (completed_sprints or [])}
    for number in sorted(int(key) for key in plan.get("sprints", {})):
        if number not in completed:
            return get_sprint(plan, number)
    return None


def sprint_scope(plan: dict[str, Any], sprint_number: int) -> dict[str, Any]:
    """Return objective, deliverables, acceptance, and out-of-scope hints."""

    sprint = get_sprint(plan, sprint_number)
    future_deliverables: list[str] = []
    for number, candidate in plan.get("sprints", {}).items():
        if int(number) > sprint_number:
            future_deliverables.extend(candidate["deliverables"])
    return {
        "number": sprint_number,
        "objective": sprint["objective"],
        "deliverables": sprint["deliverables"],
        "acceptance": sprint["acceptance"],
        "out_of_scope_deliverables": future_deliverables,
    }


def _repo_root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[1]


def _read_markdown(path: Path) -> str:
    if not path.exists():
        raise PlanLoadError("missing_plan_file", f"Plan file does not exist: {path}", path=str(path))
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise PlanLoadError("empty_plan_file", f"Plan file is empty: {path}", path=str(path))
    return text


def _parse_sections(text: str) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    current_title: str | None = None
    current_level: int | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        match = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
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
        raise PlanLoadError("malformed_plan_file", "Plan file has no markdown sections")
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


def _parse_phases(text: str) -> dict[str, dict[str, Any]]:
    phases: dict[str, dict[str, Any]] = {}
    for block in _heading_blocks(text):
        title = block["title"]
        match = re.match(r"FASE\s+(\d+)\s+—\s+(.+)", title)
        if not match:
            continue
        number = match.group(1)
        body = block["body"]
        phases[number] = {
            "number": int(number),
            "title": match.group(2).strip(),
            "objective": _markdown_subsection_text(body, "Objetivo"),
            "scope": _extract_list_items(_markdown_subsection_text(body, "Alcance").splitlines()),
            "acceptance": _extract_list_items(
                _markdown_subsection_text(body, "Criterios de aceptación").splitlines()
            ),
        }
    return phases


def _parse_modules(text: str) -> dict[str, dict[str, Any]]:
    modules: dict[str, dict[str, Any]] = {}
    for block in _heading_blocks(text):
        title = block["title"]
        if not title.startswith("orchestrator/") and not title.startswith("workers/"):
            continue
        body_sections = _subsections(_strip_code_blocks(block["body"]).strip())
        responsibilities = _items_after_label(body_sections, "Responsabilidad")
        modules[title] = {
            "path": title,
            "responsibilities": responsibilities,
        }
    return modules


def _parse_sprints(text: str) -> dict[str, dict[str, Any]]:
    sprints: dict[str, dict[str, Any]] = {}
    for block in _heading_blocks(text):
        title = block["title"]
        match = re.match(r"Sprint\s+(\d+)$", title)
        if not match:
            continue
        number = int(match.group(1))
        body_sections = _subsections(_strip_code_blocks(block["body"]).strip())
        sprints[str(number)] = {
            "number": number,
            "title": title,
            "objective": _text_after_label(body_sections, "Objetivo"),
            "deliverables": _items_after_label(body_sections, "Entregables"),
            "acceptance": _items_after_label(body_sections, "Aceptación"),
        }
    return sprints


def _heading_blocks(text: str) -> list[dict[str, Any]]:
    matches = list(re.finditer(r"^(#{1,3})\s+(.+?)\s*$", text, re.M))
    blocks: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        end = len(text)
        for candidate in matches[index + 1 :]:
            candidate_level = len(candidate.group(1))
            if candidate_level <= level:
                end = candidate.start()
                break
        blocks.append(
            {
                "level": level,
                "title": match.group(2).strip(),
                "body": text[match.end() : end].strip(),
            }
        )
    return blocks


def _markdown_subsection_text(body: str, title: str) -> str:
    matches = list(re.finditer(r"^(#{2,3})\s+(.+?)\s*$", body, re.M))
    for index, match in enumerate(matches):
        if match.group(2).strip() != title:
            continue
        level = len(match.group(1))
        end = len(body)
        for candidate in matches[index + 1 :]:
            if len(candidate.group(1)) <= level:
                end = candidate.start()
                break
        return _strip_code_blocks(body[match.end() : end]).strip()
    return ""


def _section_text(sections: dict[str, dict[str, Any]], title: str) -> str:
    section = _require_section(sections, title)
    return section["text"]


def _section_list(sections: dict[str, dict[str, Any]], title: str) -> list[str]:
    section = _require_section(sections, title)
    return section["items"]


def _section_items_or_text(sections: dict[str, dict[str, Any]], title: str) -> list[str] | str:
    section = _require_section(sections, title)
    return section["items"] or section["text"]


def _require_section(sections: dict[str, dict[str, Any]], title: str) -> dict[str, Any]:
    if title not in sections:
        raise PlanLoadError("missing_plan_section", f"Plan section not found: {title}")
    return sections[title]


def _subsections(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        label = line.strip().rstrip(":")
        if label in {"Objetivo", "Alcance", "Criterios de aceptación", "Entregables", "Aceptación", "Responsabilidad"}:
            current = label
            result[current] = []
            continue
        if current is not None:
            result[current].append(line)
    return result


def _text_after_label(subsections: dict[str, list[str]], label: str) -> str:
    return "\n".join(line for line in subsections.get(label, []) if line.strip()).strip()


def _items_after_label(subsections: dict[str, list[str]], label: str) -> list[str]:
    return _extract_list_items(subsections.get(label, []))


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


def _validate_plan(plan: dict[str, Any], path: Path) -> None:
    if not plan["project_vision"]:
        raise PlanLoadError("invalid_plan", "Project vision is empty", path=str(path))
    if not plan["phases"]:
        raise PlanLoadError("invalid_plan", "No phases parsed from plan", path=str(path))
    if not plan["modules"]:
        raise PlanLoadError("invalid_plan", "No modules parsed from plan", path=str(path))
    if not plan["sprints"]:
        raise PlanLoadError("invalid_plan", "No sprints parsed from plan", path=str(path))
    if not plan["official_benchmarks"]:
        raise PlanLoadError("invalid_plan", "Official benchmarks are missing", path=str(path))
