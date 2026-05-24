import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.first_interaction import run_first_interaction


class FirstInteractionTest(unittest.TestCase):
    def test_first_interaction_approves_and_runs_persisted_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            _write_workspace_files(workspace)
            _write_auto_policy(workspace)
            _write_security_policy(workspace)
            plan = [
                {
                    "id": "shell-command",
                    "title": "Shell command",
                    "command": ["bash", "-lc", "printf ok > boot.txt"],
                    "cwd": ".",
                    "timeout_seconds": 10,
                }
            ]
            (workspace / "runtime/autonomous_commands.json").write_text(
                json.dumps(plan),
                encoding="utf-8",
            )

            report = run_first_interaction(workspace=workspace, password="secret")

            self.assertEqual(report["status"], "completed")
            self.assertEqual(report["approval_action"], "created")
            self.assertEqual((workspace / "boot.txt").read_text(encoding="utf-8"), "ok")
            self.assertTrue((workspace / "runtime/operator_approval.json").exists())

    def test_first_interaction_blocks_denied_plan_before_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            _write_workspace_files(workspace)
            _write_auto_policy(workspace)
            _write_security_policy(workspace)
            plan = [
                {
                    "id": "delete-root",
                    "title": "Forbidden delete",
                    "command": ["rm", "-rf", "/"],
                    "cwd": ".",
                    "timeout_seconds": 10,
                }
            ]
            (workspace / "runtime/autonomous_commands.json").write_text(
                json.dumps(plan),
                encoding="utf-8",
            )

            report = run_first_interaction(workspace=workspace, password="secret")

            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["denied"][0]["decision"], "deny")
            self.assertFalse((workspace / "runtime/operator_approval.json").exists())


def _write_workspace_files(workspace: Path) -> None:
    (workspace / "runtime").mkdir(parents=True, exist_ok=True)
    (workspace / "AGENTS.md").write_text("## Policy\n", encoding="utf-8")
    (workspace / "PLANS.md").write_text("## Plan\n", encoding="utf-8")


def _write_auto_policy(workspace: Path) -> None:
    (workspace / "runtime/auto_approval_policy.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "allowed_prefixes": [["rg"]],
                "blocked_executables": [],
            }
        ),
        encoding="utf-8",
    )


def _write_security_policy(workspace: Path) -> None:
    (workspace / "runtime/security_policy.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "default_decision": "ask",
                "security_events_log": str(workspace / "runtime/security_events.jsonl"),
                "risk_categories": {
                    "read": {"activated": True, "decision": "allow", "risk_level": "low"},
                    "shell": {"activated": True, "decision": "ask", "risk_level": "high"},
                    "delete": {"activated": True, "decision": "ask", "risk_level": "high"},
                    "unknown": {"activated": True, "decision": "ask", "risk_level": "medium"},
                },
                "allow_prefixes": [["rg"]],
                "ask_prefixes": [["bash"], ["rm"]],
                "deny_prefixes": [["rm", "-rf", "/"]],
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
