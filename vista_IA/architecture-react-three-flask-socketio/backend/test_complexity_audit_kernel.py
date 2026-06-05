from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
for item in (ROOT, BACKEND_DIR):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from orchestrator.complexity_audit_kernel import (
    audit_complexity,
    resolve_lace_budget_from_sources,
)
from orchestrator.complexity_estimator import estimate_complexity


class ComplexityAuditKernelTest(unittest.TestCase):
    def test_easy_task_budget(self) -> None:
        audit = audit_complexity(
            "Crear docs/faro.txt con contenido exacto FARO_OK.",
            runtime_mode="build",
            project_file_count=2,
            task={"expected_files": ["docs/faro.txt"], "validation_commands": ["test -f docs/faro.txt"]},
        )

        self.assertEqual(audit["difficulty"], "facil")
        self.assertEqual(audit["lace_min_cycles"], 0)
        self.assertEqual(audit["lace_target_cycles"], 1)
        self.assertLessEqual(audit["lace_max_cycles"], 2)

    def test_medium_estimate_four_not_inflated_to_ten(self) -> None:
        budget = resolve_lace_budget_from_sources(
            runtime_mode="build",
            complexity_estimate={
                "difficulty": "medio",
                "recommended_lace_cycles": 4,
                "confidence": 88,
            },
            lace_policy_text="CICLOS 1 AL 10\nNo declarar completo hasta automejora canonica.",
        )

        self.assertEqual(budget["min_cycles"], 2)
        self.assertEqual(budget["target_cycles"], 3)
        self.assertEqual(budget["max_cycles"], 4)
        self.assertEqual(budget["policy_ceiling"], 10)
        self.assertNotEqual(budget["max_cycles"], 10)

    def test_lace_md_ten_is_ceiling_not_required(self) -> None:
        audit = {
            "audit_version": "complexity-audit-kernel-v1",
            "difficulty": "medio",
            "confidence": 88,
            "lace_min_cycles": 2,
            "lace_target_cycles": 3,
            "lace_max_cycles": 4,
            "early_exit_allowed": True,
        }

        budget = resolve_lace_budget_from_sources(
            runtime_mode="medium",
            complexity_audit=audit,
            lace_policy_text="Toda tarea no puede superar CICLOS 1 AL 10.",
        )

        self.assertEqual(budget["source"], "complexity-audit-kernel-v1")
        self.assertEqual(budget["max_cycles"], 4)
        self.assertEqual(budget["policy_ceiling"], 10)

    def test_no_fallback_to_ten(self) -> None:
        budget = resolve_lace_budget_from_sources(
            runtime_mode="build",
            complexity_estimate=None,
            complexity_audit=None,
            lace_policy_text="",
        )

        self.assertEqual(budget["source"], "safe_fallback")
        self.assertLessEqual(budget["target_cycles"], 2)
        self.assertLessEqual(budget["max_cycles"], 3)
        self.assertNotEqual(budget["max_cycles"], 10)

    def test_estimator_persists_audit_fields_without_breaking_legacy_recommendation(self) -> None:
        estimate = estimate_complexity(
            "Ajustar modal visual y runtime con scanner e integridad.",
            runtime_mode="build",
            project_file_count=40,
        )

        self.assertIn("complexity_audit", estimate)
        self.assertIn("recommended_lace_cycles", estimate)
        self.assertIn("lace_target_cycles", estimate)
        self.assertLessEqual(estimate["complexity_audit"]["lace_max_cycles"], 4)

    def test_project_root_history_layer_increases_margin_without_forcing_ten(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            runtime = project / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "failures.jsonl").write_text(
                json.dumps({"failure_type": "bwrap", "status": "paused_infrastructure_failures"}) + "\n",
                encoding="utf-8",
            )
            audit = audit_complexity(
                "Reparar flujo frontend con scanner y sandbox.",
                project_root=project,
                runtime_mode="build",
                project_file_count=30,
            )
            budget = resolve_lace_budget_from_sources(
                runtime_mode="build",
                complexity_audit=audit,
                lace_policy_text="maximo 10 ciclos",
            )

        self.assertLessEqual(budget["max_cycles"], 7)
        self.assertNotEqual(budget["max_cycles"], 10)


if __name__ == "__main__":
    unittest.main()
