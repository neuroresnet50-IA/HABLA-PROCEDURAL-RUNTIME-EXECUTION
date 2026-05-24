import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as backend_app


class CodeScannerEndpointTest(unittest.TestCase):
    def test_scanner_persists_report_and_ignores_runtime_internal_files(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            (project_dir / "runtime").mkdir(parents=True, exist_ok=True)
            (project_dir / "frontend" / "app.js").write_text("export function initApp() {}\n", encoding="utf-8")
            (project_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
            (project_dir / "runtime" / "internal.json").write_text('{"status":"internal"}\n', encoding="utf-8")

            client = backend_app.app.test_client()
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                response = client.post("/api/projects/demo-app/code-scanner")

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            report = payload["report"]
            scanned_paths = {file["path"] for file in report["files"]}

            self.assertTrue(report["validation"]["passed"])
            self.assertIn("frontend/app.js", scanned_paths)
            self.assertIn("README.md", scanned_paths)
            self.assertNotIn("runtime/internal.json", scanned_paths)
            self.assertGreater(report["summary"]["charactersScanned"], 0)
            self.assertEqual(report["scanner"]["visual_playback"], "magnifier_line_by_line_to_last_line")
            self.assertTrue(report["scanner"]["scrolls_to_last_line"])

            artifact_path = Path(payload["artifactPath"])
            checkpoint_path = Path(payload["checkpointPath"])
            manifest_path = Path(payload["manifestPath"])
            self.assertTrue(artifact_path.is_file())
            self.assertTrue(checkpoint_path.is_file())
            self.assertTrue(manifest_path.is_file())
            persisted = json.loads(artifact_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["report_type"], "final_code_scanner")
            self.assertEqual(persisted["summary"]["filesScanned"], 2)
            self.assertEqual(manifest["report_type"], "agent_file_manifest")
            contents = "\n".join(file["content"] for file in manifest["files"])
            self.assertIn("export function initApp", contents)
            seal_path = manifest_path.with_name("agent_file_manifest.seal.json")
            self.assertTrue(seal_path.is_file())
            seal = json.loads(seal_path.read_text(encoding="utf-8"))
            self.assertEqual(seal["report_type"], "agent_file_manifest_seal")
            self.assertEqual(len(seal["manifestSha256"]), 64)
            self.assertTrue(Path(seal["vaultPath"]).is_file())
            self.assertTrue(Path(seal["externalAnchorPath"]).is_file())

    def test_integrity_scan_detects_external_character_replacement(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            app_file = project_dir / "frontend" / "app.js"
            app_file.write_text("const token = 'safe';\n", encoding="utf-8")

            client = backend_app.app.test_client()
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                baseline_response = client.post("/api/projects/demo-app/code-scanner")
                self.assertEqual(baseline_response.status_code, 200)
                app_file.write_text("const token = 'sxfe';\n", encoding="utf-8")
                response = client.post("/api/projects/demo-app/integrity/scan")

            self.assertEqual(response.status_code, 200)
            report = response.get_json()["report"]
            self.assertFalse(report["validation"]["passed"])
            self.assertGreater(report["summary"]["totalFindings"], 0)
            finding_types = {finding["type"] for finding in report["findings"]}
            self.assertTrue(any(finding_type.startswith("char_") for finding_type in finding_types))
            first = report["findings"][0]
            self.assertEqual(first["path"], "frontend/app.js")
            self.assertGreaterEqual(first["line"], 1)
            self.assertGreaterEqual(first["column"], 1)

    def test_integrity_scan_detects_external_file_deletion(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "src").mkdir(parents=True, exist_ok=True)
            app_file = project_dir / "src" / "main.py"
            app_file.write_text("print('safe')\n", encoding="utf-8")

            client = backend_app.app.test_client()
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                baseline_response = client.post("/api/projects/demo-app/code-scanner")
                self.assertEqual(baseline_response.status_code, 200)
                app_file.unlink()
                response = client.post("/api/projects/demo-app/integrity/scan")

            self.assertEqual(response.status_code, 200)
            report = response.get_json()["report"]
            self.assertFalse(report["validation"]["passed"])
            self.assertEqual(report["summary"]["deletedFiles"], 1)
            self.assertEqual(report["findings"][0]["type"], "file_deleted")

    def test_integrity_scan_ignores_registered_editor_write_after_baseline(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "src").mkdir(parents=True, exist_ok=True)
            (project_dir / "src" / "main.py").write_text("print('safe')\n", encoding="utf-8")

            client = backend_app.app.test_client()
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                baseline_response = client.post("/api/projects/demo-app/code-scanner")
                self.assertEqual(baseline_response.status_code, 200)
                save_response = client.put(
                    "/api/projects/demo-app/file",
                    json={"path": "src/main.py", "content": "print('changed from HABLA')\n"},
                )
                self.assertEqual(save_response.status_code, 200)
                response = client.post("/api/projects/demo-app/integrity/scan")

            report = response.get_json()["report"]
            self.assertTrue(report["validation"]["passed"])
            self.assertEqual(report["summary"]["registeredWrites"], 1)

    def test_integrity_scan_detects_tampered_baseline_and_frozen_sniper_restores_it(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            app_file = project_dir / "frontend" / "app.js"
            app_file.write_text("const token = 'safe';\n", encoding="utf-8")

            client = backend_app.app.test_client()
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                baseline_response = client.post("/api/projects/demo-app/code-scanner")
                self.assertEqual(baseline_response.status_code, 200)
                manifest_path = Path(baseline_response.get_json()["manifestPath"])
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["files"][0]["content"] = "const token = 'evil';\n"
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

                scan_response = client.post("/api/projects/demo-app/integrity/scan")
                recovery_response = client.post(
                    "/api/projects/demo-app/integrity/frozen-sniper",
                    json={"confirm": "FROZEN_SNIPER"},
                )

            report = scan_response.get_json()["report"]
            self.assertFalse(report["validation"]["passed"])
            self.assertEqual(report["summary"]["baselineFindings"], 1)
            self.assertEqual(report["findings"][0]["type"], "baseline_manifest_tampered")
            self.assertEqual(report["baselineProtection"]["effectiveSource"], "vault")

            recovery = recovery_response.get_json()["report"]
            self.assertTrue(recovery_response.get_json()["ok"])
            self.assertTrue(recovery["validation"]["passed"])
            self.assertEqual(recovery["summary"]["restoredBaselines"], 1)
            self.assertEqual(recovery["summary"]["remainingFindings"], 0)
            restored_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(restored_manifest["files"][0]["content"], "const token = 'safe';\n")

    def test_external_anchor_detects_coherent_agent_baseline_rewrite(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            app_file = project_dir / "frontend" / "app.js"
            safe_content = "const token = 'safe';\n"
            evil_content = "const token = 'evil';\n"
            app_file.write_text(safe_content, encoding="utf-8")

            client = backend_app.app.test_client()
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                baseline_response = client.post("/api/projects/demo-app/code-scanner")
                self.assertEqual(baseline_response.status_code, 200)
                manifest_path = Path(baseline_response.get_json()["manifestPath"])
                original_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                tampered_manifest = json.loads(json.dumps(original_manifest))
                tampered_manifest["files"][0]["content"] = evil_content
                tampered_manifest["files"][0]["sha256"] = hashlib.sha256(evil_content.encode("utf-8")).hexdigest()
                manifest_path.write_text(json.dumps(tampered_manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

                tampered_seal = backend_app.build_agent_file_manifest_seal(project_dir, tampered_manifest, manifest_path)
                seal_path = backend_app.agent_file_manifest_seal_path(project_dir)
                seal_path.write_text(json.dumps(tampered_seal, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
                tampered_vault = Path(tampered_seal["vaultPath"])
                tampered_vault.parent.mkdir(parents=True, exist_ok=True)
                tampered_vault.write_text(json.dumps(tampered_manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

                scan_response = client.post("/api/projects/demo-app/integrity/scan")
                recovery_response = client.post(
                    "/api/projects/demo-app/integrity/frozen-sniper",
                    json={"confirm": "FROZEN_SNIPER"},
                )

            report = scan_response.get_json()["report"]
            self.assertFalse(report["validation"]["passed"])
            self.assertEqual(report["findings"][0]["type"], "baseline_external_anchor_mismatch")
            self.assertEqual(report["baselineProtection"]["effectiveSource"], "external_anchor_vault")

            recovery = recovery_response.get_json()["report"]
            self.assertTrue(recovery["validation"]["passed"])
            self.assertEqual(recovery["summary"]["restoredBaselines"], 1)
            restored_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(restored_manifest["files"][0]["content"], safe_content)
            self.assertEqual(app_file.read_text(encoding="utf-8"), safe_content)

    def test_frozen_sniper_restores_and_quarantines_integrity_findings(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            (project_dir / "src").mkdir(parents=True, exist_ok=True)
            app_file = project_dir / "frontend" / "app.js"
            main_file = project_dir / "src" / "main.py"
            untracked_file = project_dir / "src" / "virus_payload.py"
            original_app = "const token = 'safe';\nexport function boot() { return token; }\n"
            original_main = "print('safe runtime')\n"
            app_file.write_text(original_app, encoding="utf-8")
            main_file.write_text(original_main, encoding="utf-8")

            client = backend_app.app.test_client()
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                baseline_response = client.post("/api/projects/demo-app/code-scanner")
                self.assertEqual(baseline_response.status_code, 200)
                app_file.write_text("const token = 'pwned';\nexport function boot() { return token; }\n", encoding="utf-8")
                main_file.unlink()
                untracked_file.write_text("print('simulated payload')\n", encoding="utf-8")

                rejected = client.post("/api/projects/demo-app/integrity/frozen-sniper", json={})
                self.assertEqual(rejected.status_code, 409)
                self.assertEqual(rejected.get_json()["requiredConfirmation"], "FROZEN_SNIPER")

                response = client.post(
                    "/api/projects/demo-app/integrity/frozen-sniper",
                    json={"confirm": "FROZEN_SNIPER"},
                )

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            report = payload["report"]
            self.assertTrue(payload["ok"])
            self.assertTrue(report["validation"]["passed"])
            self.assertEqual(report["summary"]["restoredFiles"], 2)
            self.assertEqual(report["summary"]["quarantinedFiles"], 1)
            self.assertEqual(report["summary"]["remainingFindings"], 0)
            self.assertEqual(app_file.read_text(encoding="utf-8"), original_app)
            self.assertEqual(main_file.read_text(encoding="utf-8"), original_main)
            self.assertFalse(untracked_file.exists())

            quarantine_paths = [
                action.get("quarantinePath", "")
                for action in report["actions"]
                if action.get("type") == "quarantine_untracked_file"
            ]
            self.assertEqual(len(quarantine_paths), 1)
            quarantined = project_dir / quarantine_paths[0]
            self.assertTrue(quarantined.is_file())
            self.assertIn("simulated payload", quarantined.read_text(encoding="utf-8"))

            report_path = Path(payload["reportPath"])
            self.assertTrue(report_path.is_file())
            self.assertEqual(json.loads(report_path.read_text(encoding="utf-8"))["report_type"], "frozen_sniper_recovery")

    def test_scanner_rejects_active_runtime(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "src").mkdir(parents=True, exist_ok=True)
            (project_dir / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")

            client = backend_app.app.test_client()
            with (
                patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root),
                patch.object(
                    backend_app,
                    "build_editor_lock_state",
                    return_value={"locked": True, "message": "runtime activo"},
                ),
            ):
                response = client.post("/api/projects/demo-app/code-scanner")

            self.assertEqual(response.status_code, 423)
            self.assertEqual(response.get_json()["error"], "project_locked")

    def test_typewriter_final_persists_checkpoint_after_playback(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            (project_dir / "frontend").mkdir(parents=True, exist_ok=True)
            (project_dir / "frontend" / "app.js").write_text("export function initApp() {}\n", encoding="utf-8")
            (project_dir / "README.md").write_text("# Demo\n", encoding="utf-8")

            client = backend_app.app.test_client()
            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                response = client.post(
                    "/api/projects/demo-app/typewriter-final",
                    json={"trigger": "session_stopped", "playedFiles": ["README.md", "frontend/app.js"]},
                )

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            report = payload["report"]
            played_paths = [file["path"] for file in report["files"]]

            self.assertTrue(report["validation"]["passed"])
            self.assertEqual(report["report_type"], "final_typewriter")
            self.assertEqual(played_paths, ["README.md", "frontend/app.js"])
            self.assertEqual(report["typewriter"]["starts_at_line"], 1)
            self.assertGreater(report["summary"]["charactersPlayed"], 0)
            self.assertTrue(Path(payload["artifactPath"]).is_file())
            self.assertTrue(Path(payload["checkpointPath"]).is_file())


if __name__ == "__main__":
    unittest.main()
