import cmath
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = PROJECT_ROOT / "runtime" / "complexity_estimate.json"


def _load_resolution():
    with ARTIFACT_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["task_resolution"]


def _as_complex(value):
    if isinstance(value, dict):
        return complex(value["real"], value["imag"])
    return complex(value, 0)


def test_resolution_artifact_documents_quadratic_formula():
    resolution = _load_resolution()

    assert resolution["equation"] == "a*x^2 + b*x + c = 0, a != 0"
    assert resolution["discriminant"]["formula"] == "b^2 - 4*a*c"
    assert resolution["roots"] == [
        "x1 = (-b + sqrt(Delta)) / (2*a)",
        "x2 = (-b - sqrt(Delta)) / (2*a)",
    ]
    assert "docs/mathematics_case_005.md" in resolution["artifact_files"]


def test_documented_roots_annul_their_polynomial():
    resolution = _load_resolution()

    for example in resolution["examples"]:
        coefficients = example["coefficients"]
        a = coefficients["a"]
        b = coefficients["b"]
        c = coefficients["c"]
        delta = (b * b) - (4 * a * c)
        expected_roots = [
            (-b + cmath.sqrt(delta)) / (2 * a),
            (-b - cmath.sqrt(delta)) / (2 * a),
        ]

        assert delta == example["discriminant"]
        for root_value in example["roots"]:
            root = _as_complex(root_value)
            assert any(abs(root - expected) < 1e-9 for expected in expected_roots)
            assert abs((a * root * root) + (b * root) + c) < 1e-9
