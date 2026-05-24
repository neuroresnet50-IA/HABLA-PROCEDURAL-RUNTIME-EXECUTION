import sys
from pathlib import Path
from unittest.mock import patch
import unittest

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import app as backend_app


class ObserverAutoShutdownTest(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_enabled = backend_app.observer_plane.enabled
        self.previous_state = backend_app.observer_plane.context.state
        self.previous_signature = backend_app.observer_plane.context.last_signature
        self.previous_event_at = backend_app.observer_plane.context.last_event_at
        self.previous_manual_pin = (
            backend_app.OBSERVER_MANUAL_PIN_FILE.read_text(encoding="utf-8")
            if backend_app.OBSERVER_MANUAL_PIN_FILE.exists()
            else None
        )
        backend_app.write_observer_manual_pin(False, source="test", reason="test setup")

    def tearDown(self) -> None:
        backend_app.observer_plane.enabled = self.previous_enabled
        backend_app.observer_plane.context.state = self.previous_state
        backend_app.observer_plane.context.last_signature = self.previous_signature
        backend_app.observer_plane.context.last_event_at = self.previous_event_at
        backend_app.observer_plane.context.recent_external_event = None
        if self.previous_manual_pin is None:
            try:
                backend_app.OBSERVER_MANUAL_PIN_FILE.unlink()
            except FileNotFoundError:
                pass
        else:
            backend_app.OBSERVER_MANUAL_PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
            backend_app.OBSERVER_MANUAL_PIN_FILE.write_text(self.previous_manual_pin, encoding="utf-8")

    def test_closed_visual_event_disables_observer_plane(self):
        backend_app.observer_plane.enabled = True
        backend_app.observer_plane.context.state = "waiting_worker"
        backend_app.observer_plane.context.last_signature = "old"

        with patch.object(backend_app.socketio, "emit"):
            backend_app.consume_agent_visual_event(
                {
                    "op": "session_completed",
                    "sessionId": "agent-1",
                    "projectSlug": "demo",
                    "status": "completed",
                }
            )

        self.assertFalse(backend_app.observer_plane.enabled)
        self.assertEqual(backend_app.observer_plane.context.state, "idle")
        self.assertEqual(backend_app.observer_plane.context.last_signature, "")

    def test_observer_cannot_be_enabled_without_active_runtime_session(self):
        backend_app.observer_plane.enabled = False
        client = backend_app.app.test_client()

        with patch.object(backend_app.agent_runtime, "list_sessions", return_value=[]):
            response = client.post("/api/observer/enabled", json={"enabled": True})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["observer"]["enabled"])
        self.assertIn("no se activo", payload["message"])

    def test_human_pinned_observer_can_be_enabled_without_active_runtime_session(self):
        backend_app.observer_plane.enabled = False
        client = backend_app.app.test_client()

        with (
            patch.object(backend_app.agent_runtime, "list_sessions", return_value=[]),
            patch.object(backend_app, "start_observer_plane"),
            patch.object(backend_app.observer_plane, "observe_once", return_value=None),
        ):
            response = client.post("/api/observer/enabled", json={"enabled": True, "source": "human", "allowIdle": True})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["observer"]["enabled"])
        self.assertTrue(payload["observer"]["humanPinned"])

    def test_closed_visual_event_keeps_human_pinned_observer_enabled(self):
        backend_app.write_observer_manual_pin(True, source="human", reason="demo")
        backend_app.observer_plane.enabled = True
        backend_app.observer_plane.context.state = "waiting_worker"
        backend_app.observer_plane.context.last_signature = "old"

        with (
            patch.object(backend_app.socketio, "emit") as emit,
            patch.object(backend_app, "start_observer_plane"),
            patch.object(backend_app.observer_plane, "observe_once", return_value=None),
        ):
            backend_app.consume_agent_visual_event(
                {
                    "op": "session_completed",
                    "sessionId": "agent-1",
                    "projectSlug": "demo",
                    "status": "completed",
                }
            )

        self.assertTrue(backend_app.observer_plane.enabled)
        self.assertEqual(backend_app.observer_plane.context.state, "idle")
        emitted_ops = [call.args[1].get("op") for call in emit.call_args_list if len(call.args) > 1 and isinstance(call.args[1], dict)]
        self.assertIn("observer_auto_disable_skipped", emitted_ops)


if __name__ == "__main__":
    unittest.main()
