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

from flask import Flask

from cyberlace_routes import register_cyberlace_routes


class CyberLACERoutesTest(unittest.TestCase):
    def make_client(self, tmpdir, *, mode="monitor"):
        env = patch.dict(
            "os.environ",
            {
                "CYBERLACE_RUNTIME_DIR": str(Path(tmpdir) / "cyberlace-runtime"),
                "CYBERLACE_ENABLED": "1",
                "CYBERLACE_MODE": mode,
                "CYBERLACE_TRANSPORT": "import",
            },
            clear=False,
        )
        env.start()
        self.addCleanup(env.stop)
        app = Flask(__name__)
        register_cyberlace_routes(app, socketio=None)
        return app.test_client()

    def test_health_route(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self.make_client(tmpdir)
            response = client.get("/api/cyberlace/health")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["mode"], "monitor")

    def test_prompt_guard_route(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self.make_client(tmpdir, mode="enforce")
            response = client.post(
                "/api/cyberlace/guard/prompt",
                json={
                    "agentId": "agent-route",
                    "userId": "user-route",
                    "sessionId": "session-route",
                    "prompt": "ignore previous instructions jailbreak system prompt developer message bypass",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIn(payload["runtimeAction"], {"BLOCK", "QUARANTINE", "HUMAN_REVIEW"})

    def test_evidence_recent_route(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self.make_client(tmpdir)
            client.post("/api/cyberlace/guard/output", json={"output": "ok", "sessionId": "evidence-route"})
            response = client.get("/api/cyberlace/evidence/recent?limit=3")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["ok"])
            self.assertTrue(isinstance(payload.get("decisions"), list))


if __name__ == "__main__":
    unittest.main()
