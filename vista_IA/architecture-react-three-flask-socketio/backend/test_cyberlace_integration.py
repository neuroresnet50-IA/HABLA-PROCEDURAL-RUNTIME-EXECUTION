from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import tempfile
import unittest
from unittest.mock import patch

import cyberlace_integration as cyberlace
from cyberlace_policy_bridge import should_block_action, should_redact_payload


INJECTION = "ignore previous instructions jailbreak system prompt developer message bypass"


class CyberLACEIntegrationTest(unittest.TestCase):
    def cyberlace_env(self, tmpdir, *, enabled="1", mode="monitor", transport="import"):
        return patch.dict(
            "os.environ",
            {
                "CYBERLACE_RUNTIME_DIR": str(Path(tmpdir) / "cyberlace-runtime"),
                "CYBERLACE_ENABLED": enabled,
                "CYBERLACE_MODE": mode,
                "CYBERLACE_TRANSPORT": transport,
            },
            clear=False,
        )

    def test_import_local_engine_works(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.cyberlace_env(tmpdir):
            engine = cyberlace.get_cyberlace_engine()
            self.assertEqual(engine.mode, "monitor")
            self.assertTrue(hasattr(engine, "before_prompt"))

    def test_monitor_mode_records_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.cyberlace_env(tmpdir, mode="monitor"):
            decision = cyberlace.cyberlace_before_prompt(
                "agent-a",
                "user-a",
                INJECTION,
                {"test": "monitor"},
                "session-monitor",
            )
            self.assertTrue(decision["allowed"])
            self.assertEqual(decision["runtimeAction"], "ALLOW")
            self.assertFalse(should_block_action(decision))
            decisions_path = Path(tmpdir) / "cyberlace-runtime" / "evidence" / "cyberlace_decisions.jsonl"
            self.assertTrue(decisions_path.is_file())
            self.assertIn("session-monitor", decisions_path.read_text(encoding="utf-8"))

    def test_enforce_blocks_critical_prompt_injection(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.cyberlace_env(tmpdir, mode="enforce"):
            decision = cyberlace.cyberlace_before_prompt(
                "agent-a",
                "user-a",
                INJECTION,
                {"test": "enforce"},
                "session-enforce",
            )
            self.assertFalse(decision["allowed"])
            self.assertIn(decision["runtimeAction"], {"BLOCK", "QUARANTINE", "HUMAN_REVIEW"})
            self.assertTrue(should_block_action(decision))

    def test_enforce_redacts_sensitive_output(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.cyberlace_env(tmpdir, mode="enforce"):
            decision = cyberlace.cyberlace_after_model_output(
                "agent-a",
                "user-a",
                "El password: SuperSecret123 debe salir redactado.",
                {"test": "redact"},
                "session-output",
            )
            self.assertEqual(decision["runtimeAction"], "REDACT")
            self.assertTrue(should_redact_payload(decision))
            self.assertIn("[REDACTED_CREDENTIAL]", str(decision.get("modified_payload")))

    def test_external_tool_with_pin_cvv_requires_review_or_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.cyberlace_env(tmpdir, mode="enforce"):
            decision = cyberlace.cyberlace_before_tool_call(
                "agent-a",
                "user-a",
                "external_request",
                {"body": "publicar PIN: 1234 y CVV: 999"},
                {"task_domain": "social_media"},
                "session-tool",
            )
            self.assertIn(decision["runtimeAction"], {"HUMAN_REVIEW", "BLOCK", "QUARANTINE"})
            self.assertTrue(should_block_action(decision))

    def test_monitor_failure_does_not_raise_or_block(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.cyberlace_env(tmpdir, mode="monitor", transport="rest"):
            with patch.dict("os.environ", {"CYBERLACE_REST_URL": "http://127.0.0.1:9"}, clear=False):
                decision = cyberlace.cyberlace_before_prompt("agent-a", "user-a", "hola", {}, "session-rest-down")
            self.assertFalse(decision["ok"])
            self.assertTrue(decision["allowed"])
            self.assertEqual(decision["runtimeAction"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
