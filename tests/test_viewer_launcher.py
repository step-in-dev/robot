from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robot.loader import RobotTask
from robot.task_catalog import TaskCatalog

from tests.loader_runtime._helpers import (
    make_capture_robot_window_cls,
    patched_tasks_dir,
    write_minimal_task_env,
)


class ViewerLauncherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        repo_root_str = str(repo_root)
        if repo_root_str not in sys.path:
            sys.path.insert(0, repo_root_str)

    def test_main_opens_viewer_window_on_first_task(self) -> None:
        import viewer.viewer as viewer

        captured: list[dict[str, object]] = []
        CaptureRobotWindow = make_capture_robot_window_cls(captured)

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            for task_id in ("intro1", "intro2", "fun1"):
                write_minimal_task_env(base / f"{task_id}.env", task_id, width=1)
            with patched_tasks_dir(temp_dir):
                with patch("viewer.viewer.RobotWindow", CaptureRobotWindow):
                    exit_code = viewer.main()
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(captured), 1)
        call = captured[0]
        opts = call["options"]
        self.assertIsNotNone(opts)
        self.assertIsInstance(opts.viewer_catalog, TaskCatalog)
        self.assertEqual(call["task_id"], "intro1")
        self.assertIsNone(call.get("run_env"))
        self.assertIsNone(opts.script_path)
        task_def = call["task_definition"]
        self.assertIsInstance(task_def, RobotTask)
        self.assertEqual(len(task_def.envs), 1)
        self.assertEqual(task_def.todo_text, "todo for intro1")

    def test_main_exits_when_no_tasks(self) -> None:
        import viewer.viewer as viewer

        with tempfile.TemporaryDirectory() as temp_dir:
            with patched_tasks_dir(temp_dir):
                exit_code = viewer.main()
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
