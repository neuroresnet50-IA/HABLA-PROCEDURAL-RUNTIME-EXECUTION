import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from workspace_blanqueo import (  # noqa: E402
    apply_total_blanqueo,
    apply_selective_blanqueo,
    create_blanqueo_backup,
    create_post_blanqueo_recovery,
    decidir_y_justificar_blanqueo,
    record_blanqueo_decision,
)


class WorkspaceBlanqueoPolicyTest(unittest.TestCase):
    def test_medium_total_requires_human_confirmation(self):
        decision = decidir_y_justificar_blanqueo(
            task_id="TASK-1",
            mode="medium",
            requested_scope="total",
            repair_attempts=3,
            compile_failed=True,
            root_cause="no compila end-to-end",
        )

        self.assertEqual(decision["scope"], "total")
        self.assertFalse(decision["allowed"])
        self.assertTrue(decision["requires_confirmation"])
        self.assertIn("CONFIRMAR BLANQUEO TOTAL", decision["confirmation_prompt"])

    def test_medium_total_accepts_confirmation_phrase(self):
        decision = decidir_y_justificar_blanqueo(
            task_id="TASK-1",
            mode="medium",
            requested_scope="total",
            repair_attempts=3,
            compile_failed=True,
            confirmation_phrase="confirmar",
        )

        self.assertTrue(decision["allowed"])
        self.assertFalse(decision["requires_confirmation"])

    def test_records_decision_in_required_audit_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "runtime"
            decision = decidir_y_justificar_blanqueo(
                task_id="TASK-AUDIT",
                requested_scope="selective",
                root_cause="limpieza preventiva",
            )

            audit = record_blanqueo_decision(decision, runtime)

            self.assertTrue(Path(audit["failure_log"]).is_file())
            self.assertTrue(Path(audit["task_history"]).is_file())
            self.assertTrue(Path(audit["decision_markdown"]).is_file())
            self.assertIn("BLANQUEO_DECISION", Path(audit["failure_log"]).read_text(encoding="utf-8"))
            self.assertIn("=== DECISION DE BLANQUEO ===", Path(audit["decision_markdown"]).read_text(encoding="utf-8"))

    def test_backup_manifest_and_selective_cleanup_preserve_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            runtime = root / "runtime"
            (workspace / "projects" / "demo" / "src").mkdir(parents=True)
            (workspace / "projects" / "demo" / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (workspace / "projects" / "demo" / "node_modules").mkdir()
            (workspace / "projects" / "demo" / "node_modules" / "x.js").write_text("x", encoding="utf-8")
            (workspace / "projects" / "demo" / "__pycache__").mkdir()
            (workspace / "projects" / "demo" / "__pycache__" / "app.pyc").write_bytes(b"x")
            (runtime / "task_history.jsonl").parent.mkdir(parents=True)
            (runtime / "task_history.jsonl").write_text("", encoding="utf-8")
            decision = decidir_y_justificar_blanqueo(
                task_id="TASK-BACKUP",
                requested_scope="selective",
                root_cause="artefactos generados rotos",
            )

            backup = create_blanqueo_backup(
                project_root=root,
                workspace_root=workspace,
                runtime_dirs=[runtime],
                backup_base=root / "backups" / "blanqueo",
                decision=decision,
            )
            cleanup = apply_selective_blanqueo(workspace, runtime_dirs=[runtime])

            manifest = json.loads(Path(backup["manifest"]).read_text(encoding="utf-8"))
            self.assertGreaterEqual(backup["files"], 1)
            self.assertTrue(any(item["target"].endswith("src/app.py") for item in manifest["files"]))
            self.assertFalse((workspace / "projects" / "demo" / "node_modules").exists())
            self.assertFalse((workspace / "projects" / "demo" / "__pycache__").exists())
            self.assertTrue((workspace / "projects" / "demo" / "src" / "app.py").exists())
            self.assertGreaterEqual(cleanup["removedCount"], 2)

    def test_post_blanqueo_recovery_creates_task_and_lesson(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "runtime"
            decision = decidir_y_justificar_blanqueo(task_id="TASK-POST", root_cause="fallo recuperado")
            recovery = create_post_blanqueo_recovery(
                runtime_dir=runtime,
                decision=decision,
                backup={"backup_dir": "backups/blanqueo/test"},
            )

            queue = json.loads(Path(recovery["queue_path"]).read_text(encoding="utf-8"))
            self.assertEqual(queue[-1]["id"], "POST-BLANQUEO-RECOVERY")
            self.assertTrue(Path(recovery["lesson_path"]).is_file())

    def test_total_blanqueo_preserves_runtime_and_audit_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            (workspace / "frontend").mkdir(parents=True)
            (workspace / "runtime").mkdir()
            (workspace / "backups").mkdir()
            (workspace / "lessons_learned").mkdir()
            (workspace / "frontend" / "app.js").write_text("broken", encoding="utf-8")
            (workspace / "runtime" / "task_history.jsonl").write_text("", encoding="utf-8")

            cleanup = apply_total_blanqueo(workspace)

            self.assertFalse((workspace / "frontend").exists())
            self.assertTrue((workspace / "runtime").exists())
            self.assertTrue((workspace / "backups").exists())
            self.assertTrue((workspace / "lessons_learned").exists())
            self.assertEqual(cleanup["scope"], "total")
            self.assertEqual(cleanup["removedCount"], 1)


if __name__ == "__main__":
    unittest.main()
