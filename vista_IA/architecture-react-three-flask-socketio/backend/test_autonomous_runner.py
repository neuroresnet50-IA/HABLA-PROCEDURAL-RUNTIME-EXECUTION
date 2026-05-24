import json
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator.autonomous_runner import (
    is_command_allowed,
    run_autonomous_plan,
    validate_policy,
)
from orchestrator.security_policy import create_operator_approval, sha256_file


class AutonomousRunnerTest(unittest.TestCase):
    def test_allowed_command_runs_and_writes_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            policy = validate_policy(
                {
                    "schema_version": 1,
                    "allowed_prefixes": [[sys.executable, "-c"]],
                    "blocked_executables": [],
                }
            )
            plan = [
                {
                    "id": "create-file",
                    "title": "Create evidence file",
                    "command": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('evidence.txt').write_text('ok', encoding='utf-8')",
                    ],
                    "cwd": ".",
                    "timeout_seconds": 10,
                }
            ]

            report = run_autonomous_plan(
                plan=plan,
                policy=policy,
                workspace=workspace,
                log_path=workspace / "runtime/logs/autonomous_runner.jsonl",
                report_path=workspace / "runtime/artifacts/autonomous_runner_latest.json",
                dry_run=False,
            )

            self.assertTrue(report["completed"])
            self.assertEqual(report["passed"], 1)
            self.assertEqual((workspace / "evidence.txt").read_text(encoding="utf-8"), "ok")
            persisted = json.loads(
                (workspace / "runtime/artifacts/autonomous_runner_latest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(persisted["events"][0]["status"], "passed")

    def test_command_without_allowed_prefix_is_blocked(self):
        policy = validate_policy(
            {
                "schema_version": 1,
                "allowed_prefixes": [["rg"]],
                "blocked_executables": [],
            }
        )
        allowed, reason = is_command_allowed([sys.executable, "-c", "print('no')"], policy)
        self.assertFalse(allowed)
        self.assertIn("did not match", reason)

    def test_dangerous_executable_is_blocked_even_if_prefix_is_listed(self):
        policy = validate_policy(
            {
                "schema_version": 1,
                "allowed_prefixes": [["rm"]],
                "blocked_executables": [],
            }
        )
        allowed, reason = is_command_allowed(["rm", "-rf", "tmp"], policy)
        self.assertFalse(allowed)
        self.assertIn("blocked", reason)

    def test_cwd_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            policy = validate_policy(
                {
                    "schema_version": 1,
                    "allowed_prefixes": [[sys.executable, "-c"]],
                    "blocked_executables": [],
                }
            )
            plan = [
                {
                    "id": "escape",
                    "title": "Escape cwd",
                    "command": [sys.executable, "-c", "print('no')"],
                    "cwd": "..",
                    "timeout_seconds": 10,
                }
            ]

            report = run_autonomous_plan(
                plan=plan,
                policy=policy,
                workspace=workspace,
                log_path=workspace / "runtime/logs/autonomous_runner.jsonl",
                report_path=workspace / "runtime/artifacts/autonomous_runner_latest.json",
                dry_run=False,
            )

            self.assertFalse(report["completed"])
            self.assertEqual(report["blocked"], 1)
            self.assertIn("escapes workspace", report["events"][0]["policy_reason"])

    def test_security_policy_blocks_ask_decision_in_autonomous_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            auto_policy = validate_policy(
                {
                    "schema_version": 1,
                    "allowed_prefixes": [["bash"]],
                    "blocked_executables": [],
                }
            )
            security_policy = {
                "schema_version": 1,
                "default_decision": "ask",
                "risk_categories": {
                    "shell": {"activated": True, "decision": "ask", "risk_level": "high"},
                    "unknown": {"activated": True, "decision": "ask", "risk_level": "medium"},
                },
                "allow_prefixes": [],
                "ask_prefixes": [["bash"]],
                "deny_prefixes": [],
                "security_events_log": str(workspace / "runtime/security_events.jsonl"),
            }
            plan = [
                {
                    "id": "shell-command",
                    "title": "Shell command",
                    "command": ["bash", "-lc", "echo should-not-run"],
                    "cwd": ".",
                    "timeout_seconds": 10,
                }
            ]

            report = run_autonomous_plan(
                plan=plan,
                policy=auto_policy,
                workspace=workspace,
                log_path=workspace / "runtime/logs/autonomous_runner.jsonl",
                report_path=workspace / "runtime/artifacts/autonomous_runner_latest.json",
                dry_run=False,
                security_policy=security_policy,
            )

            self.assertFalse(report["completed"])
            self.assertEqual(report["blocked"], 1)
            self.assertEqual(report["events"][0]["security_decision"]["decision"], "ask")
            self.assertFalse((workspace / "should-not-run").exists())

    def test_operator_approval_allows_persisted_high_risk_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            plan_path = workspace / "plan.json"
            plan = [
                {
                    "id": "shell-command",
                    "title": "Shell command",
                    "command": ["bash", "-lc", "printf ok > approved.txt"],
                    "cwd": ".",
                    "timeout_seconds": 10,
                }
            ]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            auto_policy = validate_policy(
                {
                    "schema_version": 1,
                    "allowed_prefixes": [["rg"]],
                    "blocked_executables": [],
                }
            )
            security_policy = {
                "schema_version": 1,
                "default_decision": "ask",
                "risk_categories": {
                    "shell": {"activated": True, "decision": "ask", "risk_level": "high"},
                    "unknown": {"activated": True, "decision": "ask", "risk_level": "medium"},
                },
                "allow_prefixes": [],
                "ask_prefixes": [["bash"]],
                "deny_prefixes": [],
                "security_events_log": str(workspace / "runtime/security_events.jsonl"),
            }
            approval = create_operator_approval(
                plan_path=plan_path,
                workspace=workspace,
                categories=["shell"],
                password="secret",
                expires_hours=1,
                approval_file=workspace / "approval.json",
            )

            report = run_autonomous_plan(
                plan=plan,
                policy=auto_policy,
                workspace=workspace,
                log_path=workspace / "runtime/logs/autonomous_runner.jsonl",
                report_path=workspace / "runtime/artifacts/autonomous_runner_latest.json",
                dry_run=False,
                security_policy=security_policy,
                operator_approval=approval,
                approval_password="secret",
                plan_sha256=sha256_file(plan_path),
            )

            self.assertTrue(report["completed"])
            self.assertEqual(report["passed"], 1)
            self.assertEqual(report["events"][0]["security_decision"]["decision"], "allow")
            self.assertEqual((workspace / "approved.txt").read_text(encoding="utf-8"), "ok")


if __name__ == "__main__":
    unittest.main()
