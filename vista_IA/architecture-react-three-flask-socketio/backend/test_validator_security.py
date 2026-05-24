import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.validator import (
    default_validation_security_policy,
    validate_task_execution,
)


def create_task(validation_commands: list[str]) -> dict:
    return {
        "id": "TASK-VALIDATION-SECURITY-001",
        "title": "Validate security boundary",
        "goal": "Validation commands must pass through the security policy.",
        "status": "pending",
        "priority": 10,
        "dependencies": [],
        "expected_files": ["evidence.txt"],
        "validation_commands": validation_commands,
        "timeout_seconds": 60,
        "max_retries": 1,
        "mode": "build",
        "checkpoint_key": None,
    }


def create_result() -> dict:
    return {
        "task_id": "TASK-VALIDATION-SECURITY-001",
        "completed": True,
        "files_created": ["evidence.txt"],
        "files_modified": [],
        "validation_ran": [],
        "validation_passed": True,
        "blockers": [],
        "next_recommendation": "",
    }


class ValidatorSecurityTest(unittest.TestCase):
    def test_allows_low_risk_python_validation_and_records_decision(self) -> None:
        with TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "evidence.txt").write_text("ok\n", encoding="utf-8")
            validation = validate_task_execution(
                create_task(["python3 -c 'print(1)'"]),
                create_result(),
                workspace=workspace,
            )

            command = validation["validation"]["commands"][0]

            self.assertTrue(validation["task_result"]["validation_passed"])
            self.assertEqual(command["security_decision"]["decision"], "allow")
            self.assertEqual(command["security_decision"]["category"], "test_or_build")
            self.assertEqual(command["normalized_command"], ["python3", "-c", "print(1)"])
            self.assertTrue((workspace / "runtime" / "validation_security_events.jsonl").is_file())

    def test_blocks_shell_validation_before_it_can_modify_workspace(self) -> None:
        with TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "evidence.txt").write_text("ok\n", encoding="utf-8")
            validation = validate_task_execution(
                create_task(["bash -lc 'touch pwned.txt'"]),
                create_result(),
                workspace=workspace,
            )

            command = validation["validation"]["commands"][0]

            self.assertFalse(validation["task_result"]["validation_passed"])
            self.assertTrue(command["security_blocked"])
            self.assertEqual(command["security_decision"]["decision"], "deny")
            self.assertEqual(command["security_decision"]["category"], "shell")
            self.assertFalse((workspace / "pwned.txt").exists())
            self.assertTrue(
                any("Validation command blocked by security policy" in blocker for blocker in validation["task_result"]["blockers"])
            )

    def test_default_validation_policy_denies_unknown_commands(self) -> None:
        decision = default_validation_security_policy()["risk_categories"]["unknown"]

        self.assertEqual(decision["decision"], "deny")

    def test_invalid_validation_command_is_blocked_as_contract_failure(self) -> None:
        task = create_task(["unterminated ' quote"])
        with TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "evidence.txt").write_text("ok\n", encoding="utf-8")
            validation = validate_task_execution(task, create_result(), workspace=workspace)

        self.assertFalse(validation["task_result"]["validation_passed"])
        self.assertIn("Invalid validation command", validation["validation"]["commands"][0]["security_decision"]["reason"])


if __name__ == "__main__":
    unittest.main()
