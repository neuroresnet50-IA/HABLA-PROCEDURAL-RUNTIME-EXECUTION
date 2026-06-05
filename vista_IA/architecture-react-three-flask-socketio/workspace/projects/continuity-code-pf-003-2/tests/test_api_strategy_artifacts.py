import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_rest_strategy_artifacts_exist_and_are_valid_json():
    for relative_path in (
        "runtime/complexity_audit.json",
        "runtime/complexity_estimate.json",
    ):
        path = ROOT / relative_path
        assert path.is_file(), f"missing required artifact: {relative_path}"
        json.loads(path.read_text(encoding="utf-8"))


def test_rest_strategy_covers_required_http_statuses():
    strategy_path = ROOT / "docs/advanced_programming_case_003.md"

    assert strategy_path.is_file()
    content = strategy_path.read_text(encoding="utf-8")

    for status in ("200", "400", "404", "500"):
        assert status in content

    for concept in (
        "pytest",
        "monkeypatch",
        "internal_error",
        "validation_error",
        "not_found",
    ):
        assert concept in content
