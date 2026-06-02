import json
from pathlib import Path


def test_complexity_estimate_contains_rest_testing_strategy():
    estimate_path = Path("runtime/complexity_estimate.json")
    strategy_path = Path("docs/advanced_programming_case_003.md")

    data = json.loads(estimate_path.read_text(encoding="utf-8"))

    assert strategy_path.is_file()
    assert data["strategy_artifact"] == str(strategy_path)
    assert set(data["covered_status_codes"]) == {200, 400, 404, 500}
    assert {case["status_code"] for case in data["testing_strategy"]["cases"]} == {
        200,
        400,
        404,
        500,
    }
