import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _normalize_units(units):
    return {unit: exponent for unit, exponent in units.items() if exponent != 0}


def _combine_units(factors):
    combined = {}
    for factor in factors:
        for unit, exponent in factor["base_units"].items():
            combined[unit] = combined.get(unit, 0) + exponent
    return _normalize_units(combined)


def test_force_formula_units_are_dimensionally_consistent():
    artifact_path = PROJECT_ROOT / "runtime" / "complexity_estimate.json"
    data = json.loads(artifact_path.read_text(encoding="utf-8"))

    consistency_test = data["physical_units_consistency_test"]
    left_units = _normalize_units(consistency_test["left_side"]["base_units"])
    declared_right_units = _normalize_units(
        consistency_test["right_side"]["combined_base_units"]
    )
    computed_right_units = _combine_units(consistency_test["right_side"]["factors"])

    assert consistency_test["formula"] == "F = m * a"
    assert consistency_test["expected_result"] == "consistent"
    assert declared_right_units == computed_right_units
    assert left_units == computed_right_units
