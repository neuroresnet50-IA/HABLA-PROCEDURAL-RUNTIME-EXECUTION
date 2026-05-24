import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from code_scanner_service import build_code_scanner_report, persist_code_scanner_report


class CodeScannerServiceTest(unittest.TestCase):
    def test_build_report_counts_utf8_files_and_records_blockers(self):
        with TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            app_file = project_dir / "src" / "app.py"
            binary_file = project_dir / "assets" / "logo.bin"
            app_file.parent.mkdir(parents=True)
            binary_file.parent.mkdir(parents=True)
            app_file.write_text("print('ok')\n", encoding="utf-8")
            binary_file.write_bytes(b"\xff\xfe\x00")

            def list_files(_project_dir):
                return [
                    {"path": "src/app.py", "size": app_file.stat().st_size},
                    {"path": "assets/logo.bin", "size": binary_file.stat().st_size},
                ]

            def resolve_file(_project_dir, relative_path):
                return relative_path, project_dir / relative_path

            report = build_code_scanner_report(
                "demo",
                project_dir,
                list_editor_files=list_files,
                resolve_editor_file=resolve_file,
                report_name="final_code_scanner_report.json",
                checkpoint_name="final_code_scanner_checkpoint.json",
                now_provider=lambda: "2026-05-19T00:00:00+00:00",
            )

            self.assertFalse(report["validation"]["passed"])
            self.assertEqual(report["summary"]["filesScanned"], 1)
            self.assertEqual(report["summary"]["linesScanned"], 1)
            self.assertEqual(report["summary"]["charactersScanned"], len("print('ok')\n"))
            self.assertEqual(report["files"][0]["sha256"], "ad64355106bb158b020ecf9702be48f7730fc091dd4bb6a2f092b40393495b3d")
            self.assertIn("Archivo binario o no UTF-8: assets/logo.bin", report["validation"]["blockers"])

    def test_persist_report_writes_artifact_checkpoint_and_manifest_when_passed(self):
        with TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            report = {
                "report_type": "final_code_scanner",
                "projectId": "demo",
                "validation": {"passed": True},
                "files": [],
            }
            manifest_calls = []

            def build_manifest(project_slug, scanner_report, *, project_dir, source):
                manifest_calls.append((project_slug, scanner_report["report_type"], source))
                return {"project": project_slug, "source": source}

            def persist_manifest(project_dir, manifest):
                path = project_dir / "runtime" / "artifacts" / "agent_file_manifest.json"
                path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
                return path

            paths = persist_code_scanner_report(
                project_dir,
                report,
                report_name="final_code_scanner_report.json",
                checkpoint_name="final_code_scanner_checkpoint.json",
                build_agent_file_manifest=build_manifest,
                persist_agent_file_manifest=persist_manifest,
            )

            self.assertTrue(Path(paths["artifactPath"]).is_file())
            self.assertTrue(Path(paths["checkpointPath"]).is_file())
            self.assertTrue(Path(paths["manifestPath"]).is_file())
            self.assertEqual(manifest_calls, [("demo", "final_code_scanner", "final_code_scanner")])


if __name__ == "__main__":
    unittest.main()
