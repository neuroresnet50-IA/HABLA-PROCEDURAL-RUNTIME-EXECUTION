from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_runtime import AgentRuntime, AgentRuntimeControlPlaneError


INJECTION = "ignore previous instructions jailbreak system prompt developer message bypass"


class CyberLACEAgentRuntimeHooksTest(unittest.TestCase):
    def build_runtime(self, app_root: Path) -> AgentRuntime:
        return AgentRuntime(
            app_root=app_root,
            workspace_root=app_root / "workspace",
            projects_root=app_root / "workspace" / "projects",
            codex_cmd="codex",
            prompt_converter=lambda requirement: {"available": True, "prompt": requirement, "state": {}},
            graph_provider=lambda: {"nodes": [], "edges": []},
            graph_sync=lambda _force: {"nodes": [], "edges": []},
            terminal_emitter=lambda _payload: None,
            session_emitter=lambda _payload: None,
            visual_event_handler=lambda _payload: None,
        )

    def env(self, tmpdir, *, enabled="0", mode="monitor"):
        return patch.dict(
            "os.environ",
            {
                "CYBERLACE_RUNTIME_DIR": str(Path(tmpdir) / "cyberlace-runtime"),
                "CYBERLACE_ENABLED": enabled,
                "CYBERLACE_MODE": mode,
                "CYBERLACE_TRANSPORT": "import",
                "VISTA_CONTROL_PLANE_ENABLED": "0",
            },
            clear=False,
        )

    def test_disabled_keeps_prompt_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.env(tmpdir, enabled="0"):
            runtime = self.build_runtime(Path(tmpdir) / "app")
            guarded, decision = runtime._cyberlace_guard_text(
                "prompt",
                "crear app normal",
                agent_id="test-agent",
                session_id="session-disabled",
            )
            self.assertEqual(guarded, "crear app normal")
            self.assertEqual(decision["runtimeAction"], "ALLOW")
            self.assertFalse(runtime._cyberlace_should_block(decision))

    def test_monitor_does_not_block_directive(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.env(tmpdir, enabled="1", mode="monitor"):
            runtime = self.build_runtime(Path(tmpdir) / "app")
            command = runtime._build_control_plane_worker_command(
                {"rendered_instruction": INJECTION, "traceability": {"source_hash": "test"}},
                workspace=Path(tmpdir),
                session_id="session-monitor",
                task={"id": "TASK-MONITOR"},
            )
            self.assertIn("exec", command)

    def test_enforce_blocks_risky_directive(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.env(tmpdir, enabled="1", mode="enforce"):
            runtime = self.build_runtime(Path(tmpdir) / "app")
            with self.assertRaises(AgentRuntimeControlPlaneError) as raised:
                runtime._build_control_plane_worker_command(
                    {"rendered_instruction": INJECTION, "traceability": {"source_hash": "test"}},
                    workspace=Path(tmpdir),
                    session_id="session-enforce",
                    task={"id": "TASK-ENFORCE"},
                )
            self.assertEqual(raised.exception.code, "cyberlace_directive_blocked")


if __name__ == "__main__":
    unittest.main()
