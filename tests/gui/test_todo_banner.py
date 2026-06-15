"""Tests for RobotWindow todoText banner (frame border)."""

import tkinter as tk
import unittest
from typing import Union

from robot.gui import RobotWindow, RobotWindowOptions
from robot.gui_theme import TODO_TEXT_BG, TODO_TEXT_BORDER, TODO_TEXT_HEIGHT
from robot.gui_todo import get_todo_banner_text
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
            text_widget = window.todo_label
            self.assertIsNotNone(frame)
            self.assertIsNotNone(text_widget)
            self.assertEqual(frame.cget("bg"), TODO_TEXT_BORDER)
            self.assertEqual(int(text_widget.cget("highlightthickness")), 0)
            self.assertEqual(get_todo_banner_text(text_widget), todo)
            self.assertEqual(text_widget.cget("bg"), TODO_TEXT_BG)
            self.assertEqual(int(text_widget.cget("height")), TODO_TEXT_HEIGHT)
            self.assertEqual(text_widget.master.master, frame)
            inner = text_widget.master
            pack_info = inner.pack_info()
            self.assertEqual(_pack_inset(pack_info["padx"]), 1)
            self.assertEqual(_pack_inset(pack_info["pady"]), 1)
            scrollbars = [
                child
                for child in inner.winfo_children()
                if isinstance(child, tk.Scrollbar)
            ]
            self.assertEqual(len(scrollbars), 1)
            slaves = window.root.pack_slaves()
            self.assertGreater(slaves.index(window.top_toolbar), slaves.index(frame))
        finally:
            window.close()

    def test_todo_banner_height_fixed_for_long_text(self) -> None:
        todo = " ".join(["Move the robot down."] * 20)
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow(
            "todo_long",
            RobotTask(
                envs=envs,
                todo_text=todo,
                script_constraints=ScriptConstraints(),
            ),
            run_env,
            RobotWindowOptions(),
        )
        try:
            text_widget = window.todo_label
            self.assertIsNotNone(text_widget)
            self.assertEqual(int(text_widget.cget("height")), TODO_TEXT_HEIGHT)
            self.assertEqual(get_todo_banner_text(text_widget), todo)
        finally:
            window.close()

    def test_todo_banner_copy_selected_text(self) -> None:
        todo = "Move the robot down."
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow(
            "todo_copy",
            RobotTask(
                envs=envs,
                todo_text=todo,
                script_constraints=ScriptConstraints(),
            ),
            run_env,
            RobotWindowOptions(),
        )
        try:
            text_widget = window.todo_label
            self.assertIsNotNone(text_widget)
            text_widget.focus_set()
            text_widget.tag_add(tk.SEL, "1.0", "end-1c")
            text_widget.event_generate("<<Copy>>", when="tail")
            window.root.update()
            self.assertEqual(window.root.clipboard_get(), todo)
        finally:
            window.close()

    def test_escape_from_todo_banner_closes_window(self) -> None:
        todo = "Move the robot down."
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        window = RobotWindow(
            "todo_escape",
            RobotTask(
                envs=envs,
                todo_text=todo,
                script_constraints=ScriptConstraints(),
            ),
            run_env,
            RobotWindowOptions(),
        )
        try:
            text_widget = window.todo_label
            self.assertIsNotNone(text_widget)
            text_widget.focus_set()
            text_widget.event_generate("<Escape>", when="tail")
            window.root.update()
            self.assertTrue(window.is_closed)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
