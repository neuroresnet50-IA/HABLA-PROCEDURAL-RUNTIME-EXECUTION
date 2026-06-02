import json
from pathlib import Path


def test_rest_api_strategy_covers_required_status_codes():
    artifact = Path("runtime/complexity_estimate.json")
    data = json.loads(artifact.read_text(encoding="utf-8"))

    strategy = data["rest_api_test_strategy"]
    status_codes = {case["status"] for case in strategy["status_code_cases"]}

    assert status_codes == {200, 400, 404, 500}
    assert strategy["pytest_plan"]["commands"]
    assert all(case["assertions"] for case in strategy["status_code_cases"])


def test_500_case_requires_controlled_fault_injection():
    data = json.loads(Path("runtime/complexity_estimate.json").read_text(encoding="utf-8"))
    cases = data["rest_api_test_strategy"]["status_code_cases"]
    internal_error = next(case for case in cases if case["status"] == 500)

    assert "excepcion controlada" in internal_error["example"]
    assert any("no expone stack trace" in assertion for assertion in internal_error["assertions"])
