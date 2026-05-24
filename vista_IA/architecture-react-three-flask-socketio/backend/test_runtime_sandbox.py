import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as backend_app


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class RuntimeSandboxEndpointTest(unittest.TestCase):
    def test_starts_static_project_sandbox_and_persists_state(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            project_dir = projects_root / "demo-app"
            frontend_dir = project_dir / "frontend"
            frontend_dir.mkdir(parents=True, exist_ok=True)
            (frontend_dir / "index.html").write_text("<main>demo</main>\n", encoding="utf-8")
            port = free_port()
            client = backend_app.app.test_client()

            try:
                with (
                    patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root),
                    patch.object(backend_app, "allocate_sandbox_port", return_value=port),
                ):
                    response = client.post("/api/projects/demo-app/sandbox/start")
                    self.assertEqual(response.status_code, 200)
                    payload = response.get_json()
                    sandbox = payload["sandbox"]
                    self.assertTrue(sandbox["running"])
                    self.assertTrue(sandbox["ready"])
                    self.assertEqual(sandbox["technology"], "static")
                    self.assertEqual(sandbox["previewKind"], "browser")
                    self.assertEqual(sandbox["port"], port)
                    self.assertEqual(sandbox["embedUrl"], sandbox["url"])
                    self.assertEqual(sandbox["healthcheck"]["reason"], "http_ready")
                    self.assertTrue((project_dir / "runtime" / "sandbox.json").is_file())
                    self.assertTrue((project_dir / "runtime" / "logs" / "sandbox.log").is_file())

                    status_response = client.get("/api/projects/demo-app/sandbox")
                    self.assertEqual(status_response.status_code, 200)
                    self.assertTrue(status_response.get_json()["sandbox"]["running"])

                    stop_response = client.post("/api/projects/demo-app/sandbox/stop")
                    self.assertEqual(stop_response.status_code, 200)
                    self.assertFalse(stop_response.get_json()["sandbox"]["running"])
            finally:
                with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                    backend_app.terminate_sandbox_process("demo-app", project_dir, reason="test_cleanup")

    def test_start_reports_missing_entrypoint(self):
        with TemporaryDirectory() as tmpdir:
            projects_root = Path(tmpdir) / "projects"
            (projects_root / "empty-app").mkdir(parents=True, exist_ok=True)
            client = backend_app.app.test_client()

            with patch.object(backend_app, "AGENT_PROJECTS_ROOT", projects_root):
                response = client.post("/api/projects/empty-app/sandbox/start")

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.get_json()["error"], "sandbox_entrypoint_not_found")


if __name__ == "__main__":
    unittest.main()
