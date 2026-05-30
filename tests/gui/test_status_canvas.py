"""Tests for RobotWindow status strip (Canvas) behavior."""

import tempfile
import unittest
from pathlib import Path

from robot.executor import ROBOT_PATH_COLLISION_USER_MESSAGE
from robot.gui import RobotWindowOptions
from robot.loader import ScriptConstraints
from robot.model import RobotEnv
from robot.gui_theme import (
    STATUS_ALL_CORRECT,
    STATUS_READY,
    STATUS_WRONG,
    STATUS_BG_ERROR,
    STATUS_BG_NEUTRAL,
    STATUS_BG_SUCCESS,
    TODO_TEXT_BORDER,
)
from robot.operator_limits import OPERATORS_LIMIT_MESSAGE_TEMPLATE
from robot.results import RunResult

from ._helpers import (
    GuiTestCase,
    cell_1x1,
    corridor,
    make_env,
    make_test_window,
    minimal_env_dict,
    requires_tk_display,
    test_window,
)

@requires_tk_display
class RobotWindowStatusCanvasTest(GuiTestCase):
    def test_status_row_has_border_like_todo_panel(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with test_window("status_border", envs, run_env) as window:
            self.assertEqual(int(window.status_canvas.cget("highlightthickness")), 1)
            self.assertEqual(
                window.status_canvas.cget("highlightbackground"), TODO_TEXT_BORDER
            )
            self.assertEqual(
                window.status_canvas.cget("highlightcolor"), TODO_TEXT_BORDER
            )

    def test_initial_status_background_is_neutral(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with test_window("status_bg_init", envs, run_env) as window:
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
            self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
            self.assertFalse(window._status_hatched)

    def test_status_row_is_below_controls_and_full_width(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with test_window("status_layout", envs, run_env) as window:
            self.assertNotEqual(window.status_canvas.master, window.controls)
            self.assertEqual(window.status_canvas.master, window.status_frame)
            slaves = window.root.pack_slaves()
            self.assertGreater(
                slaves.index(window.status_frame),
                slaves.index(window.controls),
            )
            self.assertEqual(window.status_frame.pack_info().get("fill"), "x")
            self.assertEqual(window.status_canvas.pack_info().get("fill"), "x")

    def test_initial_status_is_robot_ready(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with test_window("status_init", envs, run_env) as window:
            self.assertEqual(window.status_var.get(), STATUS_READY)

    def test_restore_sets_robot_ready(self) -> None:
        base = corridor()
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with test_window("status_restore", envs, run_env) as window:
            window.run_all()
            self.assertEqual(window.status_var.get(), STATUS_ALL_CORRECT)
            window.restore()
            self.assertEqual(window.status_var.get(), STATUS_READY)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
            self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
            self.assertFalse(window._status_hatched)

    def test_successful_run_all_shows_all_correct(self) -> None:
        base = corridor()
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(env: RobotEnv) -> RunResult:
            env.robot.move_right()
            return RunResult(status="success", message="ok")

        with test_window("status_success", envs, run_env) as window:
            window.run_all()
            self.assertEqual(window.status_var.get(), STATUS_ALL_CORRECT)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_SUCCESS)
            self.assertEqual(window._status_background, STATUS_BG_SUCCESS)
            self.assertFalse(window._status_hatched)

    def test_wrong_solution_shows_task_not_done(self) -> None:
        envs = [make_env(cell_1x1())]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="wrong", message="")

        with test_window("status_wrong", envs, run_env) as window:
            window.run_all()
            self.assertEqual(window.status_var.get(), STATUS_WRONG)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
            self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
            self.assertFalse(window._status_hatched)

    def test_wrong_solution_with_message_shows_custom_text(self) -> None:
        envs = [make_env(cell_1x1())]
        custom = OPERATORS_LIMIT_MESSAGE_TEMPLATE.format(actual=2, limit=1)

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="wrong", message=custom)

        with test_window("status_wrong_msg", envs, run_env) as window:
            window.run_all()
            self.assertEqual(window.status_var.get(), custom)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
            self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
            self.assertFalse(window._status_hatched)

    def test_finish_step_run_wrong_with_message_shows_custom_text(self) -> None:
        envs = [make_env(cell_1x1())]
        custom = "лимит операторов: сообщение"

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with test_window("finish_step_wrong_msg", envs, run_env) as window:
            window._finish_step_run(
                RunResult(status="wrong", message=custom)
            )
            self.assertEqual(window.status_var.get(), custom)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
            self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
            self.assertFalse(window._status_hatched)

    def test_run_all_success_with_limit_violation_shows_wrong(self) -> None:
        base = cell_1x1()
        envs = [make_env(dict(base)), make_env(dict(base))]

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="success", message="ok")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "run_lim.py"
            script.write_text(
                "move_right()\nmove_right()\n",
                encoding="utf-8",
            )
            with test_window(
                "run_lim",
                envs,
                run_env,
                options=RobotWindowOptions(script_path=script),
                constraints=ScriptConstraints(operators_limit=1),
            ) as window:
                window.run_all()
                expected = OPERATORS_LIMIT_MESSAGE_TEMPLATE.format(actual=2, limit=1)
                self.assertEqual(window.status_var.get(), expected)
                self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
                self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
                self.assertFalse(window._status_hatched)

    def test_finish_step_run_success_with_limit_violation_shows_wrong(self) -> None:
        envs = [make_env(cell_1x1())]

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "step_lim.py"
            script.write_text(
                "move_right()\nmove_right()\n",
                encoding="utf-8",
            )
            window = make_test_window(
                "step_lim",
                envs,
                None,
                options=RobotWindowOptions(script_path=script),
                constraints=ScriptConstraints(operators_limit=1),
            )
            try:
                window._finish_step_run(RunResult(status="success", message="ok"))
                expected = OPERATORS_LIMIT_MESSAGE_TEMPLATE.format(actual=2, limit=1)
                self.assertEqual(window.status_var.get(), expected)
                self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_NEUTRAL)
                self.assertEqual(window._status_background, STATUS_BG_NEUTRAL)
                self.assertFalse(window._status_hatched)
            finally:
                window.close()

    def test_error_shows_run_result_message_text(self) -> None:
        envs = [make_env(cell_1x1())]
        err_msg = "текст ошибки"

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="error", message=err_msg)

        with test_window("status_error", envs, run_env) as window:
            window.run_all()
            self.assertEqual(window.status_var.get(), err_msg)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_ERROR)
            self.assertEqual(window._status_background, STATUS_BG_ERROR)
            self.assertFalse(window._status_hatched)

    def test_crashed_uses_error_background(self) -> None:
        envs = [make_env(cell_1x1())]
        msg = ROBOT_PATH_COLLISION_USER_MESSAGE

        def run_env(_env: RobotEnv) -> RunResult:
            return RunResult(status="crashed", message=msg)

        with test_window("status_crashed", envs, run_env) as window:
            window.run_all()
            self.assertEqual(window.status_var.get(), msg)
            self.assertEqual(window.status_frame.cget("bg"), STATUS_BG_ERROR)
            self.assertEqual(window._status_background, STATUS_BG_ERROR)
            self.assertFalse(window._status_hatched)



if __name__ == "__main__":
    unittest.main()
