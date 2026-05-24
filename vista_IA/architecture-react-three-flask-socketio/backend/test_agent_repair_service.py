import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
for path in (BACKEND_DIR, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agent_repair_service import (
    build_agent_repair_requirement,
    build_repair_validation_commands,
    queue_agent_repair_task,
    suggested_repair_files,
)


class AgentRepairServiceTest(unittest.TestCase):
    def test_suggested_repair_files_adds_python_module_for_unresolved_import(self):
        issue = {
            "code": "unresolved_import",
            "evidence": {"module": "shared.helpers", "level": 1},
        }

        files = suggested_repair_files("src/app/main.py", issue)

        self.assertEqual(files, ["src/app/main.py", "src/app/shared/helpers.py"])

    def test_build_requirement_and_validation_commands_preserve_repair_contract(self):
        issue = {"line": 17, "code": "unresolved_import", "severity": "error", "message": "Falta modulo"}

        requirement = build_agent_repair_requirement(
            project_slug="demo",
            relative_path="src/app.py",
            issue=issue,
            extra_instruction="corrige import",
        )
        commands = build_repair_validation_commands(
            ["src/app.py", "frontend/app.js"],
            smoke_script_path=Path("/tmp/browser_render_smoke.py"),
        )

        self.assertIn("Proyecto existente: demo", requirement)
        self.assertIn("Linea reportada: 17", requirement)
        self.assertIn("corrige import", requirement)
        self.assertEqual(commands[0], "python3 -m py_compile src/app.py")
        self.assertIn("--frontend frontend --mode smoke", commands[1])

    def test_queue_agent_repair_task_persists_state_and_task_queue(self):
        with TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "demo"
            project_dir.mkdir()

            task = queue_agent_repair_task(
                project_slug="demo",
                project_dir=project_dir,
                relative_path="src/app.py",
                repair_files=["src/app.py"],
                requirement="repara src/app.py",
                now_provider=lambda: "2026-05-19T00:00:00+00:00",
            )

            state = json.loads((project_dir / "runtime" / "project_state.json").read_text(encoding="utf-8"))
            queue = json.loads((project_dir / "runtime" / "task_queue.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "initialized")
            self.assertEqual(task["expected_files"], ["src/app.py"])
            self.assertEqual(queue[0]["id"], task["id"])


if __name__ == "__main__":
    unittest.main()
