"""Tests for RobotWindow todoText banner (frame border)."""

import unittest
from typing import Union

from robot.gui import RobotWindow, RobotWindowOptions
from robot.gui_theme import TODO_TEXT_BG, TODO_TEXT_BORDER
from robot.loader import RobotTask, ScriptConstraints
from robot.model import RobotEnv
from robot.results import RunResult

from ._helpers import GuiTestCase, cell_1x1, make_env, requires_tk_display


def _pack_inset(value: Union[int, str, tuple]) -> int:
    if isinstance(value, tuple):
        return int(value[0])
    return int(value)


@requires_tk_display
class RobotWindowTodoBannerTest(GuiTestCase):
    def test_todo_banner_uses_border_frame(self) -> None:
        todo = "Move the robot down."
        envs = [make_env(cell_1x1()), make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow(
            "todo_border",
            RobotTask(
                envs=envs,
                todo_text=todo,
                script_constraints=ScriptConstraints(),
            ),
            run_env,
            RobotWindowOptions(),
        )
        try:
            frame = window.todo_frame
            label = window.todo_label
            self.assertIsNotNone(frame)
            self.assertIsNotNone(label)
            self.assertEqual(frame.cget("bg"), TODO_TEXT_BORDER)
            self.assertEqual(int(label.cget("highlightthickness")), 0)
            self.assertEqual(label.cget("text"), todo)
            self.assertEqual(label.cget("bg"), TODO_TEXT_BG)
            self.assertEqual(label.master, frame)
            pack_info = label.pack_info()
            self.assertEqual(_pack_inset(pack_info["padx"]), 1)
            self.assertEqual(_pack_inset(pack_info["pady"]), 1)
            slaves = window.root.pack_slaves()
            self.assertGreater(slaves.index(window.top_toolbar), slaves.index(frame))
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
