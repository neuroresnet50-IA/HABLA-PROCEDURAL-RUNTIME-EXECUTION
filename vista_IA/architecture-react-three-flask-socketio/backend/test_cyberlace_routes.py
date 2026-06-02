from pathlib import Path
import json
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
                "CYBERLACE_RESCUE_PIN": "2468",
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

    def test_rescue_rewrite_route_explains_and_redacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self.make_client(tmpdir, mode="enforce")
            response = client.post(
                "/api/cyberlace/rescue/rewrite",
                json={
                    "projectSlug": "demo-project",
                    "sessionId": "session-blocked",
                    "prompt": "usar password=Secret123 y token=ghp_FAKEFAKE123456 para continuar",
                    "decision": {
                        "runtimeAction": "QUARANTINE",
                        "riskScore": 100,
                        "severity": "CRITICAL",
                        "reason": "CyberLACE blocked sensitive content",
                        "evidence": [
                            {"type": "sensitive_memory", "domain": "credential", "pattern": "password", "sample": "password=Secret123"}
                        ],
                        "safeAlternative": {
                            "title": "Alternativa segura",
                            "summary": "Usar datos sinteticos.",
                            "suggestedRequirement": "Crear una prueba con credenciales sinteticas y sin secretos reales.",
                        },
                    },
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["hardBlockStillEnforced"])
            self.assertTrue(payload["pinRequired"])
            self.assertIn("No te alarmes", payload["humanMessage"]["intro"])
            self.assertIn("[REDACTED]", payload["originalPromptPreview"])
            self.assertIn("PROMPT SEGURO", payload["safePrompt"])
            self.assertNotIn("Secret123", payload["safePrompt"])
            self.assertNotIn("ghp_FAKEFAKE123456", payload["safePrompt"])
            evidence_path = Path(tmpdir) / "cyberlace-runtime" / "evidence" / "cyberlace_safe_rewrites.jsonl"
            self.assertTrue(evidence_path.exists())
            evidence_rows = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(evidence_rows[-1]["recordType"], "cyberlace_safe_rewrite_proposed")
            self.assertEqual(evidence_rows[-1]["projectSlug"], "demo-project")
            self.assertTrue(evidence_rows[-1]["hardBlockStillEnforced"])

    def test_rescue_accept_requires_confirmation_and_keeps_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = self.make_client(tmpdir, mode="enforce")
            blocked = client.post(
                "/api/cyberlace/rescue/accept",
                json={"rescueId": "rescue-1", "safePrompt": "P_safe"},
            )
            self.assertEqual(blocked.status_code, 400)
            self.assertTrue(blocked.get_json()["hardBlockStillEnforced"])

            wrong_pin = client.post(
                "/api/cyberlace/rescue/accept",
                json={
                    "rescueId": "rescue-1",
                    "safePrompt": "[CONTEXTO AUTORIZADO CYBERLACE] P_safe",
                    "confirmation": "CONTINUAR_SEGURO",
                    "rescuePin": "0000",
                    "acceptanceType": "continue_safe",
                },
            )
            self.assertEqual(wrong_pin.status_code, 401)
            self.assertEqual(wrong_pin.get_json()["reason"], "context_pin_invalid")
            self.assertFalse(wrong_pin.get_json()["pinAuthenticated"])

            accepted = client.post(
                "/api/cyberlace/rescue/accept",
                json={
                    "rescueId": "rescue-1",
                    "safePrompt": "[CONTEXTO AUTORIZADO CYBERLACE] P_safe",
                    "confirmation": "CONTINUAR_SEGURO",
                    "rescuePin": "2468",
                    "acceptanceType": "continue_safe",
                },
            )
            self.assertEqual(accepted.status_code, 200)
            payload = accepted.get_json()
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["hardBlockStillEnforced"])
            self.assertTrue(payload["pinAuthenticated"])
            self.assertIn("prompt original sigue bloqueado", payload["message"])


if __name__ == "__main__":
    unittest.main()
