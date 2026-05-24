import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from orchestrator.observer_plane import ObserverConfig, ObserverPlane


def graph_snapshot():
    return {
        "graph": {
            "nodes": [
                {
                    "id": "workspace__projects__demo__src__app_py",
                    "name": "app.py",
                    "path": "workspace/projects/demo/src/app.py",
                    "workspaceProject": "demo",
                    "algorithm": {"steps": [{"id": "start"}, {"id": "end"}]},
                }
            ],
            "edges": [{"from": "workspace__projects__demo__src__app_py", "to": "workspace__projects__demo__src__app_py"}],
        },
        "lint": {"findings": []},
        "sessions": [],
        "active_project_slug": "demo",
    }


def scanner_passed_report():
    return {
        "scanner": {
            "visual_playback": "magnifier_line_by_line_to_last_line",
            "scrolls_to_last_line": True,
        },
        "validation": {
            "passed": True,
            "blockers": [],
        },
    }


class ObserverPlaneTest(unittest.TestCase):
    def test_detects_real_lint_issue_before_generic_map_scan(self):
        emitted = []
        snapshot = graph_snapshot()
        snapshot["lint"]["findings"] = [
            {
                "severity": "error",
                "code": "unresolved_import",
                "message": "Import roto",
                "path": "workspace/projects/demo/src/app.py",
                "nodeId": "workspace__projects__demo__src__app_py",
                "line": 7,
            }
        ]
        observer = ObserverPlane(snapshot_provider=lambda: snapshot, event_handler=emitted.append)

        event = observer.observe_once(force=True)

        self.assertEqual(event["state"], "detecting_issue")
        self.assertEqual(event["behavior"], "inspect_visual_issue")
        self.assertEqual(event["uiAction"]["type"], "map-click")
        self.assertEqual(event["focusNodeId"], "workspace__projects__demo__src__app_py")
        self.assertEqual(emitted[-1], event)

    def test_worker_session_moves_to_waiting_worker_state(self):
        snapshot = graph_snapshot()
        snapshot["sessions"] = [
            {"sessionId": "agent-1", "projectSlug": "demo", "status": "running", "currentTaskId": "TASK-001"}
        ]
        observer = ObserverPlane(snapshot_provider=lambda: snapshot)

        event = observer.observe_once(force=True)

        self.assertEqual(event["state"], "waiting_worker")
        self.assertEqual(event["behavior"], "monitor_worker")
        self.assertEqual(event["evidence"]["currentTaskId"], "TASK-001")

    def test_completed_project_without_scanner_evidence_is_seen_before_map_scan(self):
        snapshot = graph_snapshot()
        snapshot["project_runtime"] = {
            "projectSlug": "demo",
            "projectState": {"status": "completed", "current_task_id": None},
            "scannerReport": {},
            "sandbox": {},
        }
        observer = ObserverPlane(snapshot_provider=lambda: snapshot)

        event = observer.observe_once(force=True)

        self.assertEqual(event["state"], "verifying_scanner")
        self.assertEqual(event["behavior"], "verify_scanner_evidence")
        self.assertEqual(event["uiAction"]["targetId"], "code-workbench")
        self.assertFalse(event["evidence"]["scannerReportExists"])
        self.assertIn("scanner final no certificado", event["message"])

    def test_completed_project_with_scanner_but_no_ready_sandbox_is_seen(self):
        snapshot = graph_snapshot()
        snapshot["project_runtime"] = {
            "projectSlug": "demo",
            "projectState": {"status": "completed", "current_task_id": None},
            "scannerReport": scanner_passed_report(),
            "sandbox": {"status": "stopped", "running": False, "ready": False},
        }
        observer = ObserverPlane(snapshot_provider=lambda: snapshot)

        event = observer.observe_once(force=True)

        self.assertEqual(event["state"], "verifying_sandbox")
        self.assertEqual(event["behavior"], "verify_sandbox_evidence")
        self.assertEqual(event["uiAction"]["targetId"], "algorithm-flow-section")
        self.assertFalse(event["evidence"]["running"])
        self.assertIn("sandbox real incompleto", event["message"])

    def test_integrity_tamper_has_priority_over_generic_map_scan(self):
        snapshot = graph_snapshot()
        snapshot["project_runtime"] = {
            "projectSlug": "demo",
            "projectState": {"status": "completed", "current_task_id": None},
            "scannerReport": scanner_passed_report(),
            "sandbox": {"status": "running", "running": True, "ready": True, "embedUrl": "http://127.0.0.1:5600/"},
            "integrityReport": {
                "validation": {"passed": False},
                "summary": {"totalFindings": 1},
                "findings": [
                    {
                        "type": "char_replaced",
                        "path": "src/app.py",
                        "line": 3,
                        "column": 12,
                        "expectedSha256": "old",
                        "actualSha256": "new",
                        "message": "Caracter reemplazado externamente.",
                    }
                ],
            },
        }
        observer = ObserverPlane(snapshot_provider=lambda: snapshot)

        event = observer.observe_once(force=True)

        self.assertEqual(event["state"], "char_level_tamper_detected")
        self.assertEqual(event["behavior"], "inspect_file_integrity")
        self.assertEqual(event["uiAction"]["targetId"], "code-workbench")
        self.assertEqual(event["evidence"]["line"], 3)
        self.assertEqual(event["evidence"]["column"], 12)

    def test_observer_persists_integrity_findings_with_sha256_fingerprint(self):
        with TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir) / "runtime"
            snapshot = graph_snapshot()
            snapshot["project_runtime"] = {
                "projectSlug": "demo",
                "runtimeDir": str(runtime_dir),
                "projectState": {"status": "completed", "current_task_id": None},
                "scannerReport": scanner_passed_report(),
                "sandbox": {"status": "running", "running": True, "ready": True, "embedUrl": "http://127.0.0.1:5600/"},
                "integrityReportPath": str(runtime_dir / "artifacts" / "file_integrity_report.json"),
                "integrityReport": {
                    "validation": {"passed": False},
                    "summary": {"totalFindings": 1},
                    "findings": [
                        {
                            "type": "char_replaced",
                            "path": "src/app.py",
                            "line": 3,
                            "column": 12,
                            "expectedSha256": "old",
                            "actualSha256": "new",
                            "message": "Caracter reemplazado externamente.",
                        }
                    ],
                },
            }
            observer = ObserverPlane(snapshot_provider=lambda: snapshot)

            event = observer.observe_once(force=True)

            report_path = runtime_dir / "artifacts" / "observer_findings.json"
            self.assertTrue(report_path.is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["report_type"], "observer_findings")
            self.assertEqual(report["summary"]["activeFindings"], 1)
            self.assertGreaterEqual(report["summary"]["observationScore"], 98)
            finding = report["findings"][0]
            self.assertEqual(finding["source"], "integrity")
            self.assertEqual(finding["state"], "char_level_tamper_detected")
            self.assertEqual(len(finding["fingerprintSha256"]), 64)
            self.assertEqual(event["snapshotSummary"]["observerFindingCount"], 1)
            self.assertGreaterEqual(event["snapshotSummary"]["observationScore"], 98)

    def test_repeated_same_visual_action_uses_idle_cooldown(self):
        snapshot = graph_snapshot()
        snapshot["lint"]["findings"] = [
            {
                "severity": "warning",
                "code": "missing_conceptual_node",
                "message": "Archivo sin nodo conceptual",
                "path": "workspace/projects/demo/src/app.py",
                "nodeId": "workspace__projects__demo__src__app_py",
                "line": 1,
            }
        ]
        observer = ObserverPlane(
            snapshot_provider=lambda: snapshot,
            config=ObserverConfig(min_emit_interval_seconds=0, idle_emit_interval_seconds=999),
        )

        first = observer.observe_once(force=True)
        repeated = observer.observe_once()

        self.assertIsNotNone(first)
        self.assertIsNone(repeated)

    def test_repair_event_has_priority_and_points_to_code_editor(self):
        observer = ObserverPlane(snapshot_provider=graph_snapshot)
        observer.record_external_event(
            {
                "op": "repair_session_start",
                "projectSlug": "demo",
                "relativePath": "src/app.py",
                "focusNodeId": "workspace__projects__demo__src__app_py",
            }
        )

        event = observer.observe_once(force=True)

        self.assertEqual(event["state"], "preparing_repair")
        self.assertEqual(event["behavior"], "repair_pre_scan")
        self.assertEqual(event["relativePath"], "src/app.py")
        self.assertEqual(event["uiAction"]["targetId"], "code-workbench")

    def test_persists_memory_and_timeline(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            observer = ObserverPlane(
                snapshot_provider=graph_snapshot,
                memory_path=root / "memory.json",
                timeline_path=root / "timeline.jsonl",
            )

            event = observer.observe_once(force=True)
            status = observer.status()

            self.assertTrue((root / "memory.json").exists())
            self.assertTrue((root / "timeline.jsonl").exists())
            self.assertEqual(status["memory"]["visitedNodeCount"], 1)
            self.assertEqual(status["timeline"][-1]["action"], event["action"])

    def test_editable_behavior_tree_can_disable_issue_inspection(self):
        snapshot = graph_snapshot()
        snapshot["lint"]["findings"] = [
            {
                "severity": "error",
                "code": "unresolved_import",
                "message": "Import roto",
                "path": "workspace/projects/demo/src/app.py",
                "nodeId": "workspace__projects__demo__src__app_py",
                "line": 7,
            }
        ]
        observer = ObserverPlane(snapshot_provider=lambda: snapshot)
        tree = observer.status()["behaviorTree"]
        for rule in tree["rules"]:
            if rule["id"] == "inspect_visual_issue":
                rule["enabled"] = False
        observer.update_behavior_tree(tree)

        event = observer.observe_once(force=True)

        self.assertEqual(event["state"], "detecting_issue")
        self.assertEqual(event["behavior"], "idle_watch")
        self.assertEqual(event["uiAction"]["type"], "micro-modal")

    def test_snapshot_is_scoped_to_active_project(self):
        snapshot = graph_snapshot()
        snapshot["graph"]["nodes"].append(
            {
                "id": "workspace__projects__old__src__legacy_py",
                "name": "legacy.py",
                "path": "workspace/projects/old/src/legacy.py",
                "workspaceProject": "old",
                "algorithm": {"steps": [{"id": "legacy"}]},
            }
        )
        snapshot["graph"]["edges"] = [
            {"from": "workspace__projects__old__src__legacy_py", "to": "workspace__projects__old__src__legacy_py"}
        ]
        snapshot["lint"]["findings"] = [
            {
                "severity": "error",
                "code": "legacy_error",
                "message": "Error viejo que no pertenece al proyecto activo",
                "path": "workspace/projects/old/src/legacy.py",
                "nodeId": "workspace__projects__old__src__legacy_py",
                "projectSlug": "old",
                "line": 4,
            }
        ]
        snapshot["active_project_slug"] = "demo"
        observer = ObserverPlane(snapshot_provider=lambda: snapshot)

        event = observer.observe_once(force=True)

        self.assertEqual(event["projectSlug"], "demo")
        self.assertEqual(event["focusNodeId"], "workspace__projects__demo__src__app_py")
        self.assertEqual(event["snapshotSummary"]["nodeCount"], 1)
        self.assertEqual(event["snapshotSummary"]["findingCount"], 0)

    def test_status_memory_and_timeline_are_scoped_to_active_project(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            demo_snapshot = graph_snapshot()
            observer = ObserverPlane(
                snapshot_provider=lambda: demo_snapshot,
                memory_path=root / "memory.json",
                timeline_path=root / "timeline.jsonl",
            )
            observer.observe_once(force=True)
            old_snapshot = graph_snapshot()
            old_snapshot["active_project_slug"] = "old"
            old_snapshot["graph"]["nodes"][0]["workspaceProject"] = "old"
            old_snapshot["graph"]["nodes"][0]["path"] = "workspace/projects/old/src/app.py"
            observer.snapshot_provider = lambda: old_snapshot
            observer.observe_once(force=True)
            observer.snapshot_provider = lambda: demo_snapshot

            status = observer.status()

            self.assertEqual(status["activeProjectSlug"], "demo")
            self.assertTrue(status["timeline"])
            self.assertTrue(all(event["projectSlug"] == "demo" for event in status["timeline"]))
            self.assertEqual(status["memory"]["seenFileCount"], 1)


    def test_repeated_finding_closes_incident_waiting_human(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            snapshot = graph_snapshot()
            snapshot["lint"]["findings"] = [
                {
                    "severity": "warning",
                    "code": "dead_flow",
                    "message": "Bloque sin flujo",
                    "path": "workspace/projects/demo/src/app.py",
                    "nodeId": "workspace__projects__demo__src__app_py",
                    "line": 11,
                }
            ]
            observer = ObserverPlane(
                snapshot_provider=lambda: snapshot,
                config=ObserverConfig(
                    min_emit_interval_seconds=0,
                    idle_emit_interval_seconds=0,
                    max_repeated_events=2,
                    incident_cooldown_seconds=999,
                ),
                incident_dir=root / "incidents",
            )

            first = observer.observe_once(force=True)
            second = observer.observe_once(force=True)
            closed = observer.observe_once(force=True)
            suppressed = observer.observe_once(force=True)

            self.assertEqual(first["incidentStatus"], "open")
            self.assertEqual(second["incidentStatus"], "open")
            self.assertEqual(closed["state"], "waiting_human")
            self.assertEqual(closed["stopReason"], "repeated_finding_suppressed")
            self.assertIsNone(suppressed)
            incident_path = next((root / "incidents").glob("OBS-*.json"))
            incident = json.loads(incident_path.read_text(encoding="utf-8"))
            self.assertEqual(incident["status"], "waiting_human")
            self.assertEqual(incident["stopReason"], "repeated_finding_suppressed")

    def test_incident_expires_after_max_ticks(self):
        snapshot = graph_snapshot()
        snapshot["lint"]["findings"] = [
            {
                "severity": "warning",
                "code": "dead_flow",
                "message": "Bloque sin flujo",
                "path": "workspace/projects/demo/src/app.py",
                "nodeId": "workspace__projects__demo__src__app_py",
                "line": 11,
            }
        ]
        observer = ObserverPlane(
            snapshot_provider=lambda: snapshot,
            config=ObserverConfig(
                min_emit_interval_seconds=0,
                idle_emit_interval_seconds=0,
                max_incident_ticks=1,
                max_repeated_events=10,
                incident_cooldown_seconds=0,
            ),
        )

        first = observer.observe_once(force=True)
        expired = observer.observe_once(force=True)

        self.assertEqual(first["incidentStatus"], "open")
        self.assertEqual(expired["state"], "expired")
        self.assertEqual(expired["stopReason"], "max_ticks")
        self.assertEqual(observer.status()["incident"]["status"], "expired")



if __name__ == "__main__":
    unittest.main()
