import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from backend.agent_runtime import is_control_plane_state_path, is_material_project_path
from orchestrator.tool_invocation_policy import ToolInvocationPolicy
from orchestrator.validator import validate_task_execution


def create_task(task_id: str = "TASK-001") -> dict[str, Any]:
    return {
        "id": task_id,
        "title": "Create evidence",
        "goal": "Create one evidence file.",
        "status": "pending",
        "priority": 10,
        "dependencies": [],
        "expected_files": ["README.md"],
        "validation_commands": ["python3 -c 'print(1)'"],
        "timeout_seconds": 30,
        "max_retries": 1,
        "mode": "build",
        "checkpoint_key": None,
    }


class FakeToolRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def invoke(
        self,
        tool: str,
        *,
        project: str = "",
        dry_run: bool = False,
        confirm: str = "",
    ) -> dict[str, Any]:
        self.calls.append({"tool": tool, "project": project, "dryRun": dry_run, "confirm": confirm})
        if tool == "findings":
            return {
                "statusCode": 200,
                "ok": True,
                "projectId": project,
                "report": {
                    "summary": {
                        "activeFindings": 2,
                        "totalFindings": 3,
                        "bySeverity": {"error": 2},
                    }
                },
                "reportPath": f"/tmp/{project}/runtime/artifacts/observer_findings.json",
            }
        return {
            "statusCode": 200,
            "ok": True,
            "projectId": project,
            "reportPath": f"/tmp/{project}/runtime/artifacts/{tool}.json",
        }


class ToolInvocationPolicyTest(unittest.TestCase):
    def test_preflight_reads_observer_status_without_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "demo-project"
            runtime_dir = workspace / "runtime"
            runtime_dir.mkdir(parents=True)
            runner = FakeToolRunner()
            policy = ToolInvocationPolicy(
                runtime_dir=runtime_dir,
                workspace=workspace,
                project_slug="demo-project",
                runner=runner,
            )

            report = policy.run_preflight(create_task())

            self.assertEqual([call["tool"] for call in runner.calls], ["observer-status"])
            self.assertTrue(report["closureAllowed"])
            self.assertTrue((runtime_dir / "tool_invocation_policy.jsonl").is_file())

    def test_preflight_runs_integrity_and_findings_when_baseline_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "demo-project"
            runtime_dir = workspace / "runtime"
            (runtime_dir / "artifacts").mkdir(parents=True)
            (runtime_dir / "artifacts" / "agent_file_manifest.json").write_text("{}", encoding="utf-8")
            runner = FakeToolRunner()
            policy = ToolInvocationPolicy(
                runtime_dir=runtime_dir,
                workspace=workspace,
                project_slug="demo-project",
                runner=runner,
            )

            report = policy.run_preflight(create_task())

            self.assertEqual([call["tool"] for call in runner.calls], ["observer-status", "integrity", "findings"])
            self.assertEqual(report["activeFindings"], 2)
            latest = json.loads(
                (runtime_dir / "artifacts" / "tool_invocation_policy_latest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(latest["phase"], "preflight")

    def test_completion_gate_runs_scanner_and_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "demo-project"
            runtime_dir = workspace / "runtime"
            runtime_dir.mkdir(parents=True)
            runner = FakeToolRunner()
            policy = ToolInvocationPolicy(
                runtime_dir=runtime_dir,
                workspace=workspace,
                project_slug="demo-project",
                runner=runner,
            )
            task_result = {
                "task_id": "TASK-001",
                "completed": True,
                "files_created": ["README.md"],
                "files_modified": [],
                "validation_ran": ["python3 -c 'print(1)'"],
                "validation_passed": True,
                "blockers": [],
                "next_recommendation": "done",
            }

            report = policy.run_task_completion_gate(create_task(), task_result)

            self.assertEqual([call["tool"] for call in runner.calls], ["scanner", "findings"])
            self.assertTrue(report["closureAllowed"])
            self.assertEqual(report["activeFindings"], 2)

    def test_recovery_preview_uses_sniper_dry_run_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "demo-project"
            runtime_dir = workspace / "runtime"
            runtime_dir.mkdir(parents=True)
            runner = FakeToolRunner()
            policy = ToolInvocationPolicy(
                runtime_dir=runtime_dir,
                workspace=workspace,
                project_slug="demo-project",
                runner=runner,
            )
            task_result = {
                "task_id": "TASK-001",
                "completed": False,
                "files_created": [],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": False,
                "blockers": ["failed"],
                "next_recommendation": "recover",
            }

            policy.run_recovery_preview(create_task(), task_result)

            self.assertEqual([call["tool"] for call in runner.calls], ["findings", "sniper"])
            self.assertTrue(runner.calls[-1]["dryRun"])

    def test_tool_policy_artifacts_are_internal_not_product_evidence(self) -> None:
        relative = "runtime/artifacts/tool_invocations/TASK-001-preflight-20260519T000000Z.json"
        self.assertTrue(is_control_plane_state_path(relative))
        self.assertFalse(is_material_project_path(relative))

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / relative
            target.parent.mkdir(parents=True)
            target.write_text("{}", encoding="utf-8")
            task = create_task()
            task["expected_files"] = [relative]
            task["validation_commands"] = [
                f"python3 -c \"from pathlib import Path; assert Path({relative!r}).is_file()\""
            ]
            result = {
                "task_id": task["id"],
                "completed": True,
                "files_created": [relative],
                "files_modified": [],
                "validation_ran": [],
                "validation_passed": True,
                "blockers": [],
                "next_recommendation": "done",
            }

            validation = validate_task_execution(task, result, workspace=workspace)

            self.assertFalse(validation["task_result"]["completed"])
            self.assertIn(
                f"Expected file targets control-plane state: {relative}",
                validation["task_result"]["blockers"],
            )


if __name__ == "__main__":
    unittest.main()
