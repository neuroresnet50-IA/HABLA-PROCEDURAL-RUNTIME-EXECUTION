#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


INSTALLER_ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG_PATH = INSTALLER_ROOT / "domain_profiles.json"


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog_path = path or DEFAULT_CATALOG_PATH
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9+#.\-/]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def ordered_groups(groups: list[str], catalog: dict[str, Any]) -> list[str]:
    order = list(catalog.get("groupOrder") or [])
    seen = set()
    result: list[str] = []
    for group in list(catalog.get("defaultGroups") or ["base"]) + groups:
        if group and group not in seen:
            seen.add(group)
    for group in order:
        if group in seen:
            result.append(group)
            seen.remove(group)
    result.extend(sorted(seen))
    return result


def match_keyword(normalized_requirement: str, normalized_keyword: str) -> bool:
    if not normalized_keyword:
        return False
    if " " in normalized_keyword or "/" in normalized_keyword or "-" in normalized_keyword:
        return normalized_keyword in normalized_requirement
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])", normalized_requirement) is not None


def plan_from_requirement(requirement: str = "", *, recipe: str = "", catalog_path: Path | None = None) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)
    groups: list[str] = []
    evidence: list[dict[str, Any]] = []
    description = "Perfil calculado por requerimiento de cliente."
    profile_label = "requirement-plan"

    recipe_name = normalize_text(recipe).replace(" ", "-") if recipe else ""
    if recipe_name:
        recipes = catalog.get("recipes") or {}
        selected = recipes.get(recipe_name)
        if not selected:
            available = ", ".join(sorted(recipes))
            raise ValueError(f"Receta desconocida: {recipe}. Recetas disponibles: {available}")
        groups.extend(selected.get("groups") or [])
        description = str(selected.get("description") or description)
        profile_label = f"recipe:{recipe_name}"
        evidence.append({"type": "recipe", "id": recipe_name, "groups": selected.get("groups") or []})

    normalized_requirement = normalize_text(requirement)
    for rule in catalog.get("keywordRules") or []:
        matched = []
        for keyword in rule.get("keywords") or []:
            normalized_keyword = normalize_text(str(keyword))
            if match_keyword(normalized_requirement, normalized_keyword):
                matched.append(keyword)
        if matched:
            rule_groups = list(rule.get("groups") or [])
            groups.extend(rule_groups)
            evidence.append({"type": "keyword-rule", "id": rule.get("id"), "matched": matched[:12], "groups": rule_groups})

    if not groups:
        groups.extend(catalog.get("defaultGroups") or ["base"])
        evidence.append({"type": "fallback", "id": "base", "groups": catalog.get("defaultGroups") or ["base"]})

    groups = ordered_groups(groups, catalog)
    return {
        "profile": profile_label,
        "description": description,
        "groups": groups,
        "evidence": evidence,
        "requirementPreview": requirement.strip()[:700],
    }


def read_requirement(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.from_requirement:
        chunks.append(Path(args.from_requirement).read_text(encoding="utf-8"))
    if args.requirement:
        chunks.append(args.requirement)
    if args.stdin:
        chunks.append(sys.stdin.read())
    return "\n".join(chunk for chunk in chunks if chunk)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HABLA installer requirement planner")
    parser.add_argument("--requirement", default="", help="Texto libre del requerimiento del cliente")
    parser.add_argument("--from-requirement", default="", help="Archivo de requerimiento del cliente")
    parser.add_argument("--recipe", default="", help="Receta predefinida, por ejemplo industrial-vision")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH), help="Catalogo JSON de dominios")
    parser.add_argument("--stdin", action="store_true", help="Leer requerimiento desde stdin")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = plan_from_requirement(read_requirement(args), recipe=args.recipe, catalog_path=Path(args.catalog))
    print(json.dumps(plan, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
