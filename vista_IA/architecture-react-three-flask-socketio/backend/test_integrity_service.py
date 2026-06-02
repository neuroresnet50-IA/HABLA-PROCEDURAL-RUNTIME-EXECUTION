from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from backend.integrity_service import IntegrityService


class IntegrityServiceTrustedControlDocsTest(unittest.TestCase):
    def make_service(self) -> IntegrityService:
        def list_editor_files(project_dir: Path) -> list[dict[str, Any]]:
            files: list[dict[str, Any]] = []
            for path in sorted(project_dir.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(project_dir).as_posix()
                if rel.startswith("runtime/"):
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = ""
                files.append({"path": rel, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
            return files

        def resolve_editor_file(project_dir: Path, relative_path: Any, **_: Any):
            path = project_dir / str(relative_path)
            if not path.exists() or not path.is_file():
                return None
            return str(relative_path), path

        def load_json_file(path: Path, fallback: Any) -> Any:
            if not path.exists():
                return fallback
            return json.loads(path.read_text(encoding="utf-8"))

        return IntegrityService(
            baseline_anchor_root=Path(tempfile.gettempdir()) / "integrity-anchor-test",
            agent_file_manifest_name="agent_file_manifest.json",
            agent_file_manifest_seal_name="agent_file_manifest.seal.json",
            agent_baseline_seal_ledger_name="agent_file_manifest.seals.jsonl",
            file_integrity_report_name="file_integrity_report.json",
            observer_findings_report_name="observer_findings.json",
            frozen_sniper_report_name="frozen_sniper.json",
            file_write_ledger_name="file_write_ledger.jsonl",
            list_editor_files=list_editor_files,
            resolve_editor_file=resolve_editor_file,
            load_json_file=load_json_file,
            normalize_relative_fragment=lambda value: str(value or ""),
            normalize_project_id=lambda value: str(value or ""),
            now_provider=lambda: "2026-06-02T15:05:00Z",
        )

    def test_habla_session_safe_prelude_does_not_create_integrity_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            doc = project_dir / "docs" / "habla-session.md"
            doc.parent.mkdir(parents=True)
            baseline = "[CONTEXTO AUTORIZADO CYBERLACE]\nPROMPT SEGURO P_safe\nversion 1\n"
            current = baseline + "runtime continuation evidence\n"
            doc.write_text(current, encoding="utf-8")

            service = self.make_service()
            service.persist_agent_file_manifest(
                project_dir,
                {
                    "projectId": "demo",
                    "createdAt": "2026-06-02T15:00:00Z",
                    "files": [
                        {
                            "path": "docs/habla-session.md",
                            "sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                            "content": baseline,
                        }
                    ],
                },
            )

            report = service.build_file_integrity_report("demo", project_dir)

            self.assertTrue(report["validation"]["passed"])
            self.assertEqual(report["summary"]["totalFindings"], 0)
            self.assertEqual(report["summary"]["trustedRuntimeControlFiles"], 1)

    def test_regular_file_still_creates_integrity_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            readme = project_dir / "README.md"
            readme.write_text("changed\n", encoding="utf-8")

            service = self.make_service()
            baseline = "baseline\n"
            service.persist_agent_file_manifest(
                project_dir,
                {
                    "projectId": "demo",
                    "createdAt": "2026-06-02T15:00:00Z",
                    "files": [
                        {
                            "path": "README.md",
                            "sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                            "content": baseline,
                        }
                    ],
                },
            )

            report = service.build_file_integrity_report("demo", project_dir)

            self.assertFalse(report["validation"]["passed"])
            self.assertGreater(report["summary"]["totalFindings"], 0)
            self.assertEqual(report["findings"][0]["path"], "README.md")


if __name__ == "__main__":
    unittest.main()
