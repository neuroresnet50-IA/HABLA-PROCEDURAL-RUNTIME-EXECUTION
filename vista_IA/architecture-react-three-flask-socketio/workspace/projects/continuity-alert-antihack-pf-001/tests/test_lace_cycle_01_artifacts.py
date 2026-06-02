import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_lace_cycle_01_artifacts_are_present_and_marked():
    case_doc = ROOT / "docs" / "advanced_programming_alert_antihack_case_001.md"
    cycle_doc = ROOT / "docs" / "lace_cycles" / "ciclo-01.md"
    lace_log = ROOT / "LACE_LOG.md"

    assert case_doc.is_file()
    assert cycle_doc.is_file()
    assert lace_log.is_file()

    cycle_text = cycle_doc.read_text(encoding="utf-8")
    assert "[CICLO-1 PROBLEMAS]" in cycle_text
    assert "[CICLO-1 MEJORA]" in cycle_text
    assert "[CICLO-1 COMPLETADO]" in cycle_text
    assert "Valido para cierre LACE: SI" in cycle_text


def test_lace_cycle_01_runtime_evidence_is_parseable():
    findings_path = ROOT / "runtime" / "artifacts" / "observer_findings.json"
    complexity_path = ROOT / "runtime" / "complexity_estimate.json"

    findings = json.loads(findings_path.read_text(encoding="utf-8"))
    complexity = json.loads(complexity_path.read_text(encoding="utf-8"))

    assert findings["summary"]["activeFindings"] == 0
    assert "findings" in complexity["required_tools"]
    assert "integrity" in complexity["required_tools"]
    assert "pytest" in complexity["required_tools"]
    assert "scanner" in complexity["required_tools"]
