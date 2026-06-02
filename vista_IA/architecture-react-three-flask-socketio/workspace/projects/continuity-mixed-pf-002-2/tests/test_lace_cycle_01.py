from pathlib import Path


def test_mathematics_induction_document_has_required_sections():
    text = Path("docs/mixed_science_programming_case_002_mathematics.md").read_text(
        encoding="utf-8"
    )
    lower = text.lower()

    assert "caso base" in lower
    assert "hipotesis inductiva" in lower
    assert "paso inductivo" in lower
    assert "conclusion" in lower
    assert "n(n + 1) / 2" in text


def test_lace_cycle_01_has_required_markers():
    text = Path("docs/lace_cycles/ciclo-01.md").read_text(encoding="utf-8")

    assert "[CICLO-1 PROBLEMAS]" in text
    assert "[CICLO-1 MEJORA]" in text
    assert "[CICLO-1 COMPLETADO]" in text
