from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from map_lint import lint_graph


class MapLintRegressionTest(unittest.TestCase):
    def test_python_relative_import_missing_is_reported_without_name_error(self) -> None:
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            graph = {
                "nodes": [
                    {
                        "id": "node-app",
                        "path": "workspace/projects/demo-agent/src/app.py",
                        "layer": "backend",
                        "workspaceScene": "demo-agent",
                        "code": "from .missing import value\n\n\ndef run():\n    return value\n",
                        "algorithm": {"steps": [], "edges": []},
                    }
                ],
                "edges": [],
            }

            report = lint_graph(graph, project_root)

            self.assertTrue(
                any(finding["code"] == "python_relative_import_missing" for finding in report["findings"]),
                report,
            )


if __name__ == "__main__":
    unittest.main()
