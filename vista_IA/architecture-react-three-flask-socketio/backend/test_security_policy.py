import tempfile
import unittest
from pathlib import Path

from orchestrator.security_policy import (
    create_operator_approval,
    decide_command,
    sha256_file,
    validate_security_policy,
)


def policy():
    return validate_security_policy(
        {
            "schema_version": 1,
            "default_decision": "ask",
            "risk_categories": {
                "read": {"activated": True, "decision": "allow", "risk_level": "low"},
                "test_or_build": {"activated": True, "decision": "allow", "risk_level": "low"},
                "shell": {"activated": True, "decision": "ask", "risk_level": "high"},
                "network": {"activated": True, "decision": "ask", "risk_level": "high"},
                "delete": {"activated": True, "decision": "ask", "risk_level": "high"},
                "permissions": {"activated": True, "decision": "ask", "risk_level": "high"},
                "processes": {"activated": True, "decision": "ask", "risk_level": "high"},
                "docker": {"activated": True, "decision": "ask", "risk_level": "high"},
                "unknown": {"activated": True, "decision": "ask", "risk_level": "medium"},
            },
            "allow_prefixes": [["rg"]],
            "ask_prefixes": [["bash"], ["curl"], ["rm"], ["chmod"], ["kill"], ["docker"]],
            "deny_prefixes": [["sudo"], ["rm", "-rf", "/"]],
        }
    )


class SecurityPolicyTest(unittest.TestCase):
    def test_allows_low_risk_prefix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            decision = decide_command(["rg", "needle"], policy=policy(), workspace=temp_dir)
        self.assertEqual(decision["decision"], "allow")
        self.assertEqual(decision["category"], "read")

    def test_high_risk_categories_are_ask_not_allow(self):
        commands = [
            (["bash", "-lc", "echo ok"], "shell"),
            (["curl", "https://example.com"], "network"),
            (["rm", "file.txt"], "delete"),
            (["chmod", "600", "file.txt"], "permissions"),
            (["kill", "123"], "processes"),
            (["docker", "ps"], "docker"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            for command, category in commands:
                with self.subTest(command=command):
                    decision = decide_command(command, policy=policy(), workspace=temp_dir)
                    self.assertEqual(decision["decision"], "ask")
                    self.assertEqual(decision["category"], category)

    def test_forbidden_prefix_denies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            decision = decide_command(["rm", "-rf", "/"], policy=policy(), workspace=temp_dir)
        self.assertEqual(decision["decision"], "deny")
        self.assertEqual(decision["risk_level"], "forbidden")

    def test_cwd_escape_denies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            decision = decide_command(["rg", "needle"], policy=policy(), workspace=workspace, cwd="..")
        self.assertEqual(decision["decision"], "deny")
        self.assertIn("escapes workspace", decision["reason"])

    def test_operator_approval_allows_high_risk_plan_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            plan_path = workspace / "plan.json"
            plan_path.write_text(
                '[{"id":"shell","command":["bash","-lc","echo ok"],"cwd":".","timeout_seconds":10}]',
                encoding="utf-8",
            )
            approval = create_operator_approval(
                plan_path=plan_path,
                workspace=workspace,
                categories=["shell"],
                password="secret",
                expires_hours=1,
                approval_file=workspace / "approval.json",
            )

            decision = decide_command(
                ["bash", "-lc", "echo ok"],
                policy=policy(),
                workspace=workspace,
                operator_approval=approval,
                approval_password="secret",
                plan_sha256=sha256_file(plan_path),
            )

        self.assertEqual(decision["decision"], "allow")
        self.assertEqual(decision["category"], "shell")
        self.assertIn("operator_approval_id", decision)

    def test_operator_approval_wrong_password_keeps_ask(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            plan_path = workspace / "plan.json"
            plan_path.write_text(
                '[{"id":"shell","command":["bash","-lc","echo ok"],"cwd":".","timeout_seconds":10}]',
                encoding="utf-8",
            )
            approval = create_operator_approval(
                plan_path=plan_path,
                workspace=workspace,
                categories=["shell"],
                password="secret",
                expires_hours=1,
                approval_file=workspace / "approval.json",
            )

            decision = decide_command(
                ["bash", "-lc", "echo ok"],
                policy=policy(),
                workspace=workspace,
                operator_approval=approval,
                approval_password="wrong",
                plan_sha256=sha256_file(plan_path),
            )

        self.assertEqual(decision["decision"], "ask")
        self.assertIn("password", decision["operator_approval_reason"])

    def test_operator_approval_does_not_override_deny(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            plan_path = workspace / "plan.json"
            plan_path.write_text(
                '[{"id":"delete-root","command":["rm","-rf","/"],"cwd":".","timeout_seconds":10}]',
                encoding="utf-8",
            )
            approval = create_operator_approval(
                plan_path=plan_path,
                workspace=workspace,
                categories=["delete"],
                password="secret",
                expires_hours=1,
                approval_file=workspace / "approval.json",
            )

            decision = decide_command(
                ["rm", "-rf", "/"],
                policy=policy(),
                workspace=workspace,
                operator_approval=approval,
                approval_password="secret",
                plan_sha256=sha256_file(plan_path),
            )

        self.assertEqual(decision["decision"], "deny")
        self.assertEqual(decision["risk_level"], "forbidden")


if __name__ == "__main__":
    unittest.main()
